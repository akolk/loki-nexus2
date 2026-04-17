import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataSource, MetadataEndpoint
from backend.jobs.embeddings import generate_embedding

logger = logging.getLogger(__name__)

PDOK_INDEX_URL = "https://api.pdok.nl/index.json"


async def fetch_ogc_api_info(client: httpx.AsyncClient, api_url: str) -> Dict[str, Any]:
    """Fetch OGC API info to find tileserver and collections URLs."""
    result = {"tiles_url": None, "collections_url": None}
    
    try:
        response = await client.get(f"{api_url}?f=json", timeout=10)
        response.raise_for_status()
        data = response.json()
        
        for link in data.get("links", []):
            href = link.get("href", "")
            rel = link.get("rel", "")
            
            if "tilesets" in rel.lower() or "tile" in rel.lower():
                result["tiles_url"] = href
            if href.endswith("/collections") or "collections" in rel:
                if "collections" not in href or href.endswith("/collections"):
                    result["collections_url"] = href
        
    except Exception as e:
        logger.warning(f"Error fetching OGC API info from {api_url}: {e}")
    
    return result


async def fetch_collections_metadata(client: httpx.AsyncClient, collections_url: str) -> List[Dict[str, Any]]:
    """Fetch metadata for all collections in an OGC API endpoint."""
    collections = []
    
    try:
        response = await client.get(f"{collections_url}?f=json", timeout=15)
        response.raise_for_status()
        data = response.json()
        
        for coll in data.get("collections", []):
            coll_id = coll.get("id", "")
            coll_title = coll.get("title", "")
            coll_desc = coll.get("description", "")
            coll_keywords = coll.get("keywords", [])
            
            processed_keywords = []
            for kw in coll_keywords:
                if isinstance(kw, dict):
                    processed_keywords.append(kw.get("keyword", ""))
                elif isinstance(kw, str):
                    processed_keywords.append(kw)
            
            collection_item = {
                "id": coll_id,
                "title": coll_title or coll_id,
                "description": coll_desc,
                "keywords": processed_keywords
            }
            
            for link in coll.get("links", []):
                href = link.get("href", "")
                rel = link.get("rel", "")
                
                if "features" in rel or "items" in rel:
                    collection_item["features_url"] = href
                    break
            
            collections.append(collection_item)
            
    except Exception as e:
        logger.warning(f"Error fetching collections from {collections_url}: {e}")
    
    return collections


def get_or_create_pdok_source(session) -> MetadataSource:
    """Get or create the PDOK metadata source."""
    from sqlmodel import select
    
    source = session.exec(
        select(MetadataSource).where(MetadataSource.source_type == "pdok")
    ).first()
    
    if not source:
        source = MetadataSource(
            name="PDOK",
            base_url="https://api.pdok.nl",
            source_type="pdok",
            description="Publieke Dienstverlening op de Kaart - Dutch geospatial data API"
        )
        session.add(source)
        session.commit()
        session.refresh(source)
    
    return source


async def fetch_pdok_metadata() -> str:
    """
    Fetch metadata from PDOK index and store in database.
    Returns a summary of the operation.
    """
    session = get_metadata_session()
    from sqlmodel import select
    
    try:
        logger.info(f"Fetching PDOK metadata from {PDOK_INDEX_URL}")
        
        async with httpx.AsyncClient() as client:
            response = await client.get(PDOK_INDEX_URL, timeout=30)
            response.raise_for_status()

            data = response.json()

            source = get_or_create_pdok_source(session)

            endpoints_added = 0
            endpoints_updated = 0

            collections = data.get("apis", [])

            existing_endpoints = session.exec(
                select(MetadataEndpoint).where(MetadataEndpoint.source_id == source.id)
            ).all()
            existing_dict = {ep.endpoint_url: ep for ep in existing_endpoints}

            for api in collections:
                title = ""
                try:
                    title = api.get("title", "")
                    description = api.get("description", "")
                    
                    api_url = None
                    if "links" in api:
                        for link in api["links"]:
                            if link.get("rel") == "root":
                                api_url = link.get("href")
                                break

                    if not api_url:
                        continue

                    logger.info(f"Processing PDOK API: {title}")

                    api_info = await fetch_ogc_api_info(client, api_url)
                    collections_url = api_info.get("collections_url")

                    existing = existing_dict.get(api_url)

                    keywords = api.get("keywords", [])
                    processed_keywords = []
                    for kw in keywords:
                        if isinstance(kw, dict):
                            processed_keywords.append(kw.get("keyword", ""))
                        elif isinstance(kw, str):
                            processed_keywords.append(kw)

                    keywords_str = ", ".join(processed_keywords) if processed_keywords else ""
                    embedding_text = f"{title}: {description}"
                    if keywords_str:
                        embedding_text += f" Keywords: {keywords_str}"

                    embedding = await generate_embedding(embedding_text)

                    extra_data = {
                        "tiles_url": api_info.get("tiles_url"),
                        "collections_url": collections_url,
                        "keywords": processed_keywords,
                        "collections": []
                    }

                    if existing:
                        existing.title = title
                        existing.description = description
                        existing.embedding = embedding
                        existing.api_type = "OGC API"
                        existing.set_extra_metadata(extra_data)
                        endpoints_updated += 1
                    else:
                        endpoint = MetadataEndpoint(
                            source_id=source.id,
                            endpoint_url=api_url,
                            title=title,
                            description=description,
                            api_type="OGC API",
                            embedding=embedding
                        )
                        endpoint.set_extra_metadata(extra_data)
                        session.add(endpoint)
                        existing_dict[api_url] = endpoint
                        endpoints_added += 1

                    session.commit()

                    if collections_url:
                        collections_data = await fetch_collections_metadata(client, collections_url)
                        logger.info(f"Found {len(collections_data)} collections for {title}")
                        
                        for coll in collections_data:
                            coll_url = coll.get("features_url", "")
                            if not coll_url:
                                continue

                            coll_id = coll.get("id", "")
                            coll_title = coll.get("title", "")
                            coll_desc = coll.get("description", "")

                            coll_existing = existing_dict.get(coll_url)

                            coll_keywords = coll.get("keywords", [])
                            coll_keywords_str = ", ".join(coll_keywords) if coll_keywords else ""
                            coll_embedding_text = f"{coll_title}: {coll_desc}"
                            if coll_keywords_str:
                                coll_embedding_text += f" Keywords: {coll_keywords_str}"

                            coll_embedding = await generate_embedding(coll_embedding_text)

                            parent_title = title.replace(" (OGC API)", "").replace("OGC API", "").strip()
                            full_title = f"{parent_title} - {coll_title}"

                            coll_extra = {
                                "parent_endpoint": api_url,
                                "collection_id": coll_id,
                                "tiles_url": api_info.get("tiles_url"),
                                "keywords": coll_keywords
                            }

                            if coll_existing:
                                coll_existing.title = full_title
                                coll_existing.description = coll_desc
                                coll_existing.embedding = coll_embedding
                                coll_existing.api_type = "OGC API Collection"
                                coll_existing.set_extra_metadata(coll_extra)
                            else:
                                coll_endpoint = MetadataEndpoint(
                                    source_id=source.id,
                                    endpoint_url=coll_url,
                                    title=full_title,
                                    description=coll_desc,
                                    api_type="OGC API Collection",
                                    embedding=coll_embedding
                                )
                                coll_endpoint.set_extra_metadata(coll_extra)
                                session.add(coll_endpoint)
                                existing_dict[coll_url] = coll_endpoint

                except Exception as e:
                    logger.warning(f"Error processing API {title}: {e}")
                    continue

            session.commit()
        
        result = f"PDOK metadata sync completed: {endpoints_added} added, {endpoints_updated} updated"
        logger.info(result)
        return result
        
    except Exception as e:
        logger.error(f"Error fetching PDOK metadata: {e}")
        raise
    finally:
        session.close()
