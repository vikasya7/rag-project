"""
Embeds code chunks for storage.

Each chunk gets a small synthetic header (file path + symbol name)
prepended before embedding. This gives the embedding model plain-English
context — without it, a function named 'handle' embeds almost identically
regardless of which file it's in.
"""
from openai import AsyncOpenAI
from app.services.chunker import CodeChunk

client=AsyncOpenAI()

EMBEDDING_MODEL = "text-embedding-3-small"

def _build_embedding_input(chunk:CodeChunk)->str:
    header=f"// file: {chunk.file_path}\n// symbol:{chunk.symbol_name or 'anonymous'} ({chunk.symbol_type})\n"
    return header+chunk.content




