import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.database_metadata import get_metadata_session
from backend.models_metadata import MetadataSource, MetadataEndpoint
from backend.jobs.embeddings import generate_embeddings_batch
from sqlmodel import select

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

    try:
        logger.info(f"Fetching CBS metadata from {CBS_DATASETS_URL}")

        async with httpx.AsyncClient() as client:
            response = await client.get(CBS_DATASETS_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()

            source = get_or_create_cbs_source(session)

            existing_endpoints = session.exec(
                select(MetadataEndpoint).where(MetadataEndpoint.source_id == source.id)
            ).all()
            endpoint_dict = {ep.endpoint_url: ep for ep in existing_endpoints}

            endpoints_added = 0
            endpoints_updated = 0

            value = data.get("value", [])
            total_datasets = len(value)
            logger.info(f"Found {total_datasets} CBS datasets to process")

            # Collect datasets and embedding texts
            dataset_batch = []
            embedding_texts = []

            for dataset in value:
                try:
                    identifier = dataset.get("Identifier", "")
                    title = dataset.get("Title", "")
                    description = dataset.get("Description", "")
                    frequency = dataset.get("Frequency", "")
                    keywords = dataset.get("Keywords", "")

                    odata_url = f"https://opendata.cbs.nl/ODataApi/odata/{identifier}"

                    embedding_text = f"{title}: {description}"
                    if keywords:
                        embedding_text += f" Keywords: {keywords}"

                    dataset_batch.append(
                        {
                            "identifier": identifier,
                            "title": title,
                            "description": description,
                            "frequency": frequency,
                            "keywords": keywords,
                            "odata_url": odata_url,
                        }
                    )
                    embedding_texts.append(embedding_text)
                except Exception as e:
                    logger.warning(
                        f"Error collecting dataset {dataset.get('Identifier', 'unknown')}: {e}"
                    )

            # Generate embeddings in batches of 100
            embeddings = []
            batch_size = 100
            for i in range(0, len(embedding_texts), batch_size):
                batch_texts = embedding_texts[i : i + batch_size]
                try:
                    batch_embeddings = await generate_embeddings_batch(batch_texts)
                    embeddings.extend(batch_embeddings)
                except Exception as e:
                    logger.error(
                        f"Error generating embeddings for batch {i//batch_size}: {e}"
                    )
                    # In case of error, append None or empty lists to maintain index alignment
                    embeddings.extend([None] * len(batch_texts))

            # Process metadata
            for i, ds in enumerate(dataset_batch):
                try:
                    identifier = ds["identifier"]
                    odata_url = ds["odata_url"]

                    endpoint_metadata = await fetch_endpoint_metadata(
                        client, identifier
                    )

                    extra_data = {
                        "frequency": ds["frequency"],
                        "identifier": identifier,
                        "keywords": ds["keywords"],
                        "endpoint_metadata": endpoint_metadata,
                    }

                    existing = endpoint_dict.get(odata_url)

                    if existing:
                        existing.title = ds["title"]
                        existing.description = ds["description"]
                        if embeddings[i] is not None:
                            existing.embedding = embeddings[i]
                        existing.api_type = "CBS OData"
                        existing.set_extra_metadata(extra_data)
                        endpoints_updated += 1
                    else:
                        endpoint = MetadataEndpoint(
                            source_id=source.id,
                            endpoint_url=odata_url,
                            title=ds["title"],
                            description=ds["description"],
                            api_type="CBS OData",
                            embedding=(
                                embeddings[i] if embeddings[i] is not None else []
                            ),
                        )
                        endpoint.set_extra_metadata(extra_data)
                        session.add(endpoint)
                        endpoint_dict[odata_url] = endpoint
                        endpoints_added += 1

                    processed = endpoints_added + endpoints_updated
                    if processed % 10 == 0:
                        logger.info(
                            f"Processed {processed}/{total_datasets} CBS datasets"
                        )

                except Exception as e:
                    logger.warning(f"Error processing dataset {ds['identifier']}: {e}")

        session.commit()

        result = f"CBS metadata sync completed: {endpoints_added} added, {endpoints_updated} updated"
        logger.info(result)
        return result

    except Exception as e:
        logger.error(f"Error fetching CBS metadata: {e}")
        raise
    finally:
        session.close()
