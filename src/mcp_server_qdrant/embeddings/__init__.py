from typing import List

from .factory import create_embedding_provider

async def embed_text(text: str) -> List[float]:
    """Embed a text string into a vector."""
    provider = create_embedding_provider()
    return await provider.embed_query(text)
