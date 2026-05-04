import logging
import requests
from typing import List, Dict, Any, Optional
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataSource, MetadataEndpoint
from backend.jobs.embeddings import generate_embeddings_batch

logger = logging.getLogger(__name__)

PDOK_INDEX_URL = "https://api.pdok.nl/index.json"


def fetch_ogc_api_info(api_url: str) -> Dict[str, Any]:
    """Fetch OGC API info to find tileserver and collections URLs."""
    result = {"tiles_url": None, "collections_url": None}

    try:
        response = requests.get(f"{api_url}?f=json", timeout=10)
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


def fetch_collections_metadata(collections_url: str) -> List[Dict[str, Any]]:
    """Fetch metadata for all collections in an OGC API endpoint."""
    collections = []

    try:
        response = requests.get(f"{collections_url}?f=json", timeout=15)
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
                "keywords": processed_keywords,
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
            description="Publieke Dienstverlening op de Kaart - Dutch geospatial data API",
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

        response = requests.get(PDOK_INDEX_URL, timeout=30)
        response.raise_for_status()

        data = response.json()

        source = get_or_create_pdok_source(session)

        endpoints_added = 0
        endpoints_updated = 0

        collections = data.get("apis", [])

        # Pre-fetch existing endpoints into a dictionary for O(1) lookups
        existing_endpoints_list = session.exec(
            select(MetadataEndpoint).where(MetadataEndpoint.source_id == source.id)
        ).all()
        existing_endpoints = {ep.endpoint_url: ep for ep in existing_endpoints_list}

        # First pass: Collect all data and texts for embedding
        endpoints_to_process = []
        embedding_texts = []

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

                api_info = fetch_ogc_api_info(api_url)
                collections_url = api_info.get("collections_url")

                keywords = api.get("keywords", [])
                processed_keywords = []
                for kw in keywords:
                    if isinstance(kw, dict):
                        processed_keywords.append(kw.get("keyword", ""))
                    elif isinstance(kw, str):
                        processed_keywords.append(kw)

                keywords_str = (
                    ", ".join(processed_keywords) if processed_keywords else ""
                )
                embedding_text = f"{title}: {description}"
                if keywords_str:
                    embedding_text += f" Keywords: {keywords_str}"

                extra_data = {
                    "tiles_url": api_info.get("tiles_url"),
                    "collections_url": collections_url,
                    "keywords": processed_keywords,
                    "collections": [],
                }

                embedding_texts.append(embedding_text)
                endpoints_to_process.append({
                    "endpoint_url": api_url,
                    "title": title,
                    "description": description,
                    "api_type": "OGC API",
                    "extra_data": extra_data,
                })

                if collections_url:
                    collections_data = fetch_collections_metadata(collections_url)
                    logger.info(
                        f"Found {len(collections_data)} collections for {title}"
                    )

                    for coll in collections_data:
                        coll_url = coll.get("features_url", "")
                        if not coll_url:
                            continue

                        coll_id = coll.get("id", "")
                        coll_title = coll.get("title", "")
                        coll_desc = coll.get("description", "")

                        coll_keywords = coll.get("keywords", [])
                        coll_keywords_str = (
                            ", ".join(coll_keywords) if coll_keywords else ""
                        )
                        coll_embedding_text = f"{coll_title}: {coll_desc}"
                        if coll_keywords_str:
                            coll_embedding_text += f" Keywords: {coll_keywords_str}"

                        parent_title = (
                            title.replace(" (OGC API)", "")
                            .replace("OGC API", "")
                            .strip()
                        )
                        full_title = f"{parent_title} - {coll_title}"

                        coll_extra = {
                            "parent_endpoint": api_url,
                            "collection_id": coll_id,
                            "tiles_url": api_info.get("tiles_url"),
                            "keywords": coll_keywords,
                        }

                        embedding_texts.append(coll_embedding_text)
                        endpoints_to_process.append({
                            "endpoint_url": coll_url,
                            "title": full_title,
                            "description": coll_desc,
                            "api_type": "OGC API Collection",
                            "extra_data": coll_extra,
                        })

            except Exception as e:
                logger.warning(f"Error preparing PDOK API {title}: {e}")
                continue

        # Process embeddings in batches to optimize network calls
        batch_size = 100
        all_embeddings = []
        for i in range(0, len(embedding_texts), batch_size):
            batch_texts = embedding_texts[i:i + batch_size]
            try:
                batch_embeddings = await generate_embeddings_batch(batch_texts)
                all_embeddings.extend(batch_embeddings)
            except Exception as e:
                logger.error(f"Error generating embeddings for batch {i}: {e}")
                # Provide fallback empty embeddings
                all_embeddings.extend([None for _ in batch_texts])

        # Second pass: Update or Create endpoints using the pre-fetched dict and batched embeddings
        for idx, endpoint_data in enumerate(endpoints_to_process):
            try:
                endpoint_url = endpoint_data["endpoint_url"]
                title = endpoint_data["title"]
                description = endpoint_data["description"]
                api_type = endpoint_data["api_type"]
                extra_data = endpoint_data["extra_data"]
                embedding = all_embeddings[idx] if idx < len(all_embeddings) else None

                existing = existing_endpoints.get(endpoint_url)

                if existing:
                    existing.title = title
                    existing.description = description
                    if embedding:
                        existing.embedding = embedding
                    existing.api_type = api_type
                    existing.set_extra_metadata(extra_data)
                    endpoints_updated += 1
                else:
                    endpoint = MetadataEndpoint(
                        source_id=source.id,
                        endpoint_url=endpoint_url,
                        title=title,
                        description=description,
                        api_type=api_type,
                        embedding=embedding,
                    )
                    endpoint.set_extra_metadata(extra_data)
                    session.add(endpoint)
                    existing_endpoints[endpoint_url] = endpoint  # Keep dict synced
                    endpoints_added += 1

            except Exception as e:
                logger.warning(f"Error saving PDOK API endpoint {endpoint_url}: {e}")
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
