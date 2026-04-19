import logging
import hashlib
import time
from typing import Optional, List, Dict, Any
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataEndpoint, MetadataSource
from backend.jobs.embeddings import generate_embedding
from sqlmodel import select

logger = logging.getLogger(__name__)

_embedding_cache: Dict[str, tuple] = {}
_metadata_cache: Dict[str, tuple] = {}
CACHE_TTL = 300


def _get_cache_key(*args) -> str:
    return hashlib.md5(str(args).encode()).hexdigest()


def find_endpoint(
        query: str,
        source_type: str = "pdok",
        top_k: int = 1,
        filter_geojson: bool = False) -> str:
    """
    Find the best matching endpoint using vector similarity search.

    Args:
        query: The user's query to match against endpoint metadata
        source_type: "pdok" or "cbs"
        top_k: Number of results to return
        filter_geojson: If True, only return GeoJSON-capable endpoints (OGC API Features with /collections)

    Returns:
        JSON string with endpoint information
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    result = loop.run_until_complete(
        find_endpoint_async(
            query,
            source_type,
            top_k,
            filter_geojson))
    logger.info(result)
    return result


async def find_endpoint_async(
        query: str,
        source_type: str = "pdok",
        top_k: int = 1,
        filter_geojson: bool = False) -> str:
    """
    Async version of find_endpoint with caching.
    """
    import json

    cache_key = _get_cache_key(query, source_type, top_k, filter_geojson)
    current_time = time.time()

    if cache_key in _metadata_cache:
        cached_result, cached_time = _metadata_cache[cache_key]
        if current_time - cached_time < CACHE_TTL:
            logger.info(f"Cache hit for: {query}")
            return cached_result

    session = get_metadata_session()

    try:
        source = session.exec(select(MetadataSource).where(
            MetadataSource.source_type == source_type)).first()

        if not source:
            result = json.dumps({
                "error": f"No metadata source found for {source_type}",
                "url": None,
                "title": None,
                "description": None,
                "api_type": None
            })
            _metadata_cache[cache_key] = (result, current_time)
            return result

        emb_cache_key = f"emb_{query}_{source_type}"
        if emb_cache_key in _embedding_cache:
            query_embedding, emb_time = _embedding_cache[emb_cache_key]
            if current_time - emb_time < CACHE_TTL:
                logger.info(f"Embedding cache hit for: {query}")
        else:
            query_embedding = await generate_embedding(query)
            _embedding_cache[emb_cache_key] = (query_embedding, current_time)

        from sqlalchemy import text

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        if filter_geojson and source_type == "pdok":
            sql = text("""
                SELECT id, source_id, endpoint_url, title, description, api_type, extra_metadata,
                       embedding <=> cast(:embedding_str as vector) as distance
                FROM metadata_endpoint
                WHERE source_id = :source_id
                  AND endpoint_url LIKE '%/ogc/%'
                ORDER BY embedding <=> cast(:embedding_str as vector)
                LIMIT :top_k
            """)
        else:
            sql = text("""
                SELECT id, source_id, endpoint_url, title, description, api_type, extra_metadata,
                       embedding <=> cast(:embedding_str as vector) as distance
                FROM metadata_endpoint
                WHERE source_id = :source_id
                ORDER BY embedding <=> cast(:embedding_str as vector)
                LIMIT :top_k
            """)

        result = session.execute(sql, {
            "embedding_str": embedding_str,
            "source_id": source.id,
            "top_k": top_k
        })

        rows = result.fetchall()

        if not rows:
            return json.dumps({
                "error": f"No endpoints found for {source_type}",
                "url": None,
                "title": None,
                "description": None,
                "api_type": None
            })

        results = []
        for row in rows:
            extra_metadata = None
            tiles_url = None
            collections_url = None

            if row.extra_metadata:
                extra_metadata = json.loads(row.extra_metadata)
                tiles_url = extra_metadata.get("tiles_url")
                collections_url = extra_metadata.get("collections_url")

            preferred_url = tiles_url or collections_url or row.endpoint_url

            results.append({
                "url": row.endpoint_url,
                "title": row.title,
                "description": row.description,
                "api_type": row.api_type,
                "source": source_type,
                "extra_metadata": extra_metadata,
                "tiles_url": tiles_url,
                "collections_url": collections_url,
                "preferred_url": preferred_url,
                "distance": row.distance
            })

        if top_k == 1:
            result = json.dumps(results[0])
        else:
            result = json.dumps({"results": results, "count": len(results)})

        _metadata_cache[cache_key] = (result, current_time)
        return result

    except Exception as e:
        logger.error(f"Error finding endpoint: {e}")
        return json.dumps({
            "error": str(e),
            "url": None,
            "title": None,
            "description": None,
            "api_type": None,
            "results": [] if top_k > 1 else None
        })
    finally:
        session.close()


def search_metadata(
        query: str,
        source_type: Optional[str] = None,
        limit: int = 10) -> List[dict]:
    """
    Search metadata endpoints (synchronous version for API endpoints).
    """
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(
        search_metadata_async(
            query, source_type, limit))


async def search_metadata_async(
        query: str,
        source_type: Optional[str] = None,
        limit: int = 10) -> List[dict]:
    """
    Search metadata endpoints.
    """
    session = get_metadata_session()

    try:
        query_embedding = await generate_embedding(query)

        from sqlalchemy import text

        embedding_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        if source_type:
            sql = text("""
                SELECT e.id, e.endpoint_url, e.title, e.description, e.api_type,
                       s.name as source_name, s.source_type,
                       e.embedding <=> cast(:embedding_str as vector) as distance
                FROM metadata_endpoint e
                JOIN metadata_source s ON e.source_id = s.id
                WHERE s.source_type = :source_type
                ORDER BY e.embedding <=> cast(:embedding_str as vector)
                LIMIT :limit
            """)
            result = session.execute(sql,
                                     {"embedding_str": embedding_str,
                                      "source_type": source_type,
                                      "limit": limit})
        else:
            sql = text("""
                SELECT e.id, e.endpoint_url, e.title, e.description, e.api_type,
                       s.name as source_name, s.source_type,
                       e.embedding <=> cast(:embedding_str as vector) as distance
                FROM metadata_endpoint e
                JOIN metadata_source s ON e.source_id = s.id
                ORDER BY e.embedding <=> cast(:embedding_str as vector)
                LIMIT :limit
            """)
            result = session.execute(
                sql, {"embedding_str": embedding_str, "limit": limit})

        rows = result.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row.id,
                "url": row.endpoint_url,
                "title": row.title,
                "description": row.description,
                "api_type": row.api_type,
                "source_name": row.source_name,
                "source_type": row.source_type,
                "distance": row.distance
            })

        return results

    except Exception as e:
        logger.error(f"Error searching metadata: {e}")
        return []
    finally:
        session.close()
