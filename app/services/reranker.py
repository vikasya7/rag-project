"""
Reranks hybrid search candidates with a cross-encoder via Cohere's API.

Fail-soft: if Cohere is down or the key is missing, falls back to hybrid
order so the system stays available at slightly lower quality.
"""

import os
import httpx

COHERE_RERANK_URL = "https://api.cohere.com/v1/rerank"


async def rerank(query: str, candidates: list[dict], top_n: int = 5) -> list[dict]:
    if not candidates:
        return []

    cohere_key = os.environ.get("COHERE_API_KEY", "")
    if not cohere_key:
        # No key yet — just return top N from hybrid order
        return candidates[:top_n]

    documents = [
        f"{c['file_path']} :: {c.get('symbol_name') or 'anonymous'}\n{c['content']}"
        for c in candidates
    ]

    async with httpx.AsyncClient() as client:
        response = await client.post(
            COHERE_RERANK_URL,
            headers={"Authorization": f"Bearer {cohere_key}"},
            json={
                "model": "rerank-english-v3.0",
                "query": query,
                "documents": documents,
                "top_n": top_n,
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        print(f"Rerank failed ({response.status_code}), falling back to hybrid order")
        return candidates[:top_n]

    results = response.json()["results"]
    return [{**candidates[r["index"]], "relevance_score": r["relevance_score"]} for r in results]