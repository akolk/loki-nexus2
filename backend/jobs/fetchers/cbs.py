import logging
import requests
from typing import List, Dict, Any, Optional
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataSource, MetadataEndpoint
from backend.jobs.embeddings import generate_embeddings_batch

logger = logging.getLogger(__name__)

CBS_DATASETS_URL = "https://datasets.cbs.nl/odata/v1/Datasets"


def fetch_endpoint_metadata(identifier: str) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a specific CBS endpoint."""
    try:
        url = f"https://opendata.cbs.nl/ODataApi/odata/{identifier}"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        data = response.json()

        metadata = {"url": url}

        if "value" in data and data["value"]:
            metadata["categories"] = data["value"]

        return metadata
    except Exception as e:
        logger.warning(f"Error fetching metadata for {identifier}: {e}")
        return None


def get_or_create_cbs_source(session) -> MetadataSource:
    """Get or create the CBS metadata source."""
    from sqlmodel import select

    source = session.exec(
        select(MetadataSource).where(MetadataSource.source_type == "cbs")
    ).first()

    if not source:
        source = MetadataSource(
            name="CBS",
            base_url="https://opendata.cbs.nl",
            source_type="cbs",
            description="Centraal Bureau voor de Statistiek - Dutch statistics API",
        )
        session.add(source)
        session.commit()
        session.refresh(source)

    return source


async def fetch_cbs_metadata() -> str:
    """
    Fetch metadata from CBS OData API and store in database.
    Returns a summary of the operation.
    """
    session = get_metadata_session()
    from sqlmodel import select

    try:
        logger.info(f"Fetching CBS metadata from {CBS_DATASETS_URL}")

        response = requests.get(CBS_DATASETS_URL, timeout=30)
        response.raise_for_status()

        data = response.json()

        source = get_or_create_cbs_source(session)

        endpoints_added = 0
        endpoints_updated = 0
        total_datasets = 0

        value = data.get("value", [])
        total_datasets = len(value)
        logger.info(f"Found {total_datasets} CBS datasets to process")

        # Pre-fetch existing endpoints into a dictionary for O(1) lookups
        existing_endpoints_list = session.exec(
            select(MetadataEndpoint).where(MetadataEndpoint.source_id == source.id)
        ).all()
        existing_endpoints = {ep.endpoint_url: ep for ep in existing_endpoints_list}

        # First pass: collect all necessary text for embeddings
        datasets_to_process = []
        embedding_texts = []

        for dataset in value:
            identifier = dataset.get("Identifier", "")
            title = dataset.get("Title", "")
            description = dataset.get("Description", "")
            frequency = dataset.get("Frequency", "")
            keywords = dataset.get("Keywords", "")

            odata_url = f"https://opendata.cbs.nl/ODataApi/odata/{identifier}"

            embedding_text = f"{title}: {description}"
            if keywords:
                embedding_text += f" Keywords: {keywords}"

            embedding_texts.append(embedding_text)
            datasets_to_process.append({
                "identifier": identifier,
                "title": title,
                "description": description,
                "frequency": frequency,
                "keywords": keywords,
                "odata_url": odata_url,
            })

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
                # Provide fallback empty embeddings to keep indexing synced
                all_embeddings.extend([None for _ in batch_texts])

        # Second pass: Update or Create endpoints using the pre-fetched dict and batched embeddings
        for idx, dataset_info in enumerate(datasets_to_process):
            try:
                identifier = dataset_info["identifier"]
                title = dataset_info["title"]
                description = dataset_info["description"]
                frequency = dataset_info["frequency"]
                keywords = dataset_info["keywords"]
                odata_url = dataset_info["odata_url"]
                embedding = all_embeddings[idx] if idx < len(all_embeddings) else None

                endpoint_metadata = fetch_endpoint_metadata(identifier)

                extra_data = {
                    "frequency": frequency,
                    "identifier": identifier,
                    "keywords": keywords,
                    "endpoint_metadata": endpoint_metadata,
                }

                existing = existing_endpoints.get(odata_url)

                if existing:
                    existing.title = title
                    existing.description = description
                    if embedding:
                        existing.embedding = embedding
                    existing.api_type = "CBS OData"
                    existing.set_extra_metadata(extra_data)
                    endpoints_updated += 1
                else:
                    endpoint = MetadataEndpoint(
                        source_id=source.id,
                        endpoint_url=odata_url,
                        title=title,
                        description=description,
                        api_type="CBS OData",
                        embedding=embedding,
                    )
                    endpoint.set_extra_metadata(extra_data)
                    session.add(endpoint)
                    existing_endpoints[odata_url] = endpoint  # Keep dict synced
                    endpoints_added += 1

                processed = endpoints_added + endpoints_updated
                if processed % 10 == 0:
                    logger.info(f"Processed {processed}/{total_datasets} CBS datasets")

            except Exception as e:
                logger.warning(f"Error processing dataset {identifier}: {e}")
                continue

        session.commit()

        result = f"CBS metadata sync completed: {endpoints_added} added, {endpoints_updated} updated"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error fetching CBS metadata: {e}")
        raise
    finally:
        session.close()
