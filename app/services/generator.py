"""
Builds the final prompt from reranked chunks and streams the LLM answer
token by token via an async generator, for use with FastAPI's
StreamingResponse — no WebSocket needed.
"""


from collections.abc import AsyncIterator
from openai import AsyncOpenAI

client = AsyncOpenAI()

def _build_messages(question:str,chunks:list[dict])->list[dict]:
    context = "\n\n".join(
        f"### {c['file_path']} (lines {c['start_line']}-{c['end_line']})\n```\n{c['content']}\n```"
        for c in chunks
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a codebase assistant. Answer ONLY using the provided code context. "
                "Every claim must cite the specific file and line range it came from, like "
                "(file.py:12-20). If the context doesn't contain the answer, say so directly "
                "instead of guessing."
            ),
        },
        {"role": "user", "content": f"Question: {question}\n\nCode context:\n{context}"},
    ]

async def stream_answer(question:str,chunks:list[dict])->AsyncIterator[str]:
    stream=await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=_build_messages(question, chunks),
        stream=True,
    )

    async for part in stream:
        token = part.choices[0].delta.content
        if token:
            yield token