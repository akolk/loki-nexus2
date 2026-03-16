import os
import logging
from typing import List
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)

_openai_client: AsyncOpenAI = None


def get_openai_client() -> AsyncOpenAI:
    """Get or create OpenAI client."""
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")
        _openai_client = AsyncOpenAI(api_key=api_key)
    return _openai_client


async def generate_embedding(text: str) -> List[float]:
    """
    Generate an embedding for the given text using OpenAI's text-embedding-3-small model.
    Returns a list of floats (1536 dimensions).
    """
    try:
        client = get_openai_client()
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        
        embedding = response.data[0].embedding
        return embedding
        
    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts.
    """
    try:
        client = get_openai_client()
        
        response = await client.embeddings.create(
            model="text-embedding-3-small",
            input=texts
        )
        
        embeddings = [item.embedding for item in sorted(response.data, key=lambda x: x.index)]
        return embeddings
        
    except Exception as e:
        logger.error(f"Error generating embeddings batch: {e}")
        raise
