"""
Embeds code chunks for storage.

Each chunk gets a small synthetic header (file path + symbol name)
prepended before embedding. This gives the embedding model plain-English
context — without it, a function named 'handle' embeds almost identically
regardless of which file it's in.
"""
from openai import AsyncOpenAI
import os
from app.services.chunker import CodeChunk

def get_client():
    return AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])

EMBEDDING_MODEL = "text-embedding-3-small"

def _build_embedding_input(chunk:CodeChunk)->str:
    header=f"// file: {chunk.file_path}\n// symbol:{chunk.symbol_name or 'anonymous'} ({chunk.symbol_type})\n"
    return header+chunk.content

async def embed_chunks(chunks: list[CodeChunk], batch_size: int = 50) -> list[tuple[CodeChunk, list[float]]]:
    results: list[tuple[CodeChunk, list[float]]] = []

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        inputs = [_build_embedding_input(c) for c in batch]
        print(f"Calling OpenAI for batch {i}...")

        try:
            response = await get_client().embeddings.create(model=EMBEDDING_MODEL, input=inputs)
            print(f"Got response: {type(response)}")
        except Exception as e:
            print(f"OpenAI call failed: {e}")
            raise

        for chunk, item in zip(batch, response.data):
            results.append((chunk, item.embedding))

        print(f"Embedded {min(i + batch_size, len(chunks))}/{len(chunks)} chunks")

    return results

async def embed_query(query:str)->list[float]:
    response = await get_client().embeddings.create(model=EMBEDDING_MODEL, input=query)
    return response.data[0].embedding


