import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataSource, MetadataEndpoint
from backend.jobs.embeddings import generate_embeddings_batch

logger = logging.getLogger(__name__)

CBS_DATASETS_URL = "https://datasets.cbs.nl/odata/v1/Datasets"


async def fetch_endpoint_metadata(
    client: httpx.AsyncClient, identifier: str
) -> Optional[Dict[str, Any]]:
    """Fetch metadata for a specific CBS endpoint."""
    try:
        url = f"https://opendata.cbs.nl/ODataApi/odata/{identifier}"
        response = await client.get(url, timeout=15.0)
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

        async with httpx.AsyncClient() as client:
            response = await client.get(CBS_DATASETS_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            source = get_or_create_cbs_source(session)

            # Pre-fetch existing endpoints
            existing_endpoints_query = session.exec(
                select(MetadataEndpoint).where(MetadataEndpoint.source_id == source.id)
            ).all()
            existing_endpoints = {
                ep.endpoint_url: ep for ep in existing_endpoints_query
            }

            endpoints_added = 0
            endpoints_updated = 0
            total_datasets = 0

            value = data.get("value", [])
            total_datasets = len(value)
            logger.info(f"Found {total_datasets} CBS datasets to process")

            # Batch processing for embeddings
            batch_size = 100

            for i in range(0, len(value), batch_size):
                batch_datasets = value[i : i + batch_size]

                # Prepare data for batch embeddings
                texts_to_embed = []
                for dataset in batch_datasets:
                    title = dataset.get("Title", "")
                    description = dataset.get("Description", "")
                    keywords = dataset.get("Keywords", "")

                    embedding_text = f"{title}: {description}"
                    if keywords:
                        embedding_text += f" Keywords: {keywords}"
                    texts_to_embed.append(embedding_text)

                # Fetch batch embeddings
                try:
                    embeddings = await generate_embeddings_batch(texts_to_embed)
                except Exception as e:
                    logger.warning(f"Failed to generate embeddings for batch: {e}")
                    embeddings = [None] * len(texts_to_embed)

                for idx, dataset in enumerate(batch_datasets):
                    try:
                        identifier = dataset.get("Identifier", "")
                        title = dataset.get("Title", "")
                        description = dataset.get("Description", "")
                        frequency = dataset.get("Frequency", "")
                        keywords = dataset.get("Keywords", "")

                        odata_url = (
                            f"https://opendata.cbs.nl/ODataApi/odata/{identifier}"
                        )

                        existing = existing_endpoints.get(odata_url)
                        embedding = embeddings[idx]

                        endpoint_metadata = await fetch_endpoint_metadata(
                            client, identifier
                        )

                        extra_data = {
                            "frequency": frequency,
                            "identifier": identifier,
                            "keywords": keywords,
                            "endpoint_metadata": endpoint_metadata,
                        }

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
                                embedding=embedding if embedding else None,
                            )
                            endpoint.set_extra_metadata(extra_data)
                            session.add(endpoint)
                            existing_endpoints[odata_url] = endpoint
                            endpoints_added += 1

                    except Exception as e:
                        logger.warning(f"Error processing dataset {identifier}: {e}")
                        continue

                processed = i + len(batch_datasets)
                if processed % 100 == 0:
                    logger.info(f"Processed {processed}/{total_datasets} CBS datasets")

        session.commit()

        result = f"CBS metadata sync completed: {endpoints_added} added, {endpoints_updated} updated"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error fetching CBS metadata: {e}")
        raise
    finally:
        session.close()
