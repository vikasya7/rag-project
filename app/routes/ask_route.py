from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from app.services.retrieval import hybrid_retrieve
from app.services.reranker import rerank
from app.services.generator import stream_answer

router = APIRouter()


class AskRequest(BaseModel):
    repo_id: int
    question: str


@router.post("/ask")
async def ask_question(request: AskRequest):
    candidates = await hybrid_retrieve(request.repo_id, request.question, candidate_pool_size=20)
    ranked = await rerank(request.question, candidates, top_n=5)

    if not ranked:
        async def empty_stream():
            yield "No relevant code found. Has this repo finished indexing?"
        return StreamingResponse(empty_stream(), media_type="text/event-stream")

    sources = [
        {
            "file_path": c["file_path"],
            "start_line": c["start_line"],
            "end_line": c["end_line"]
        }
        for c in ranked
    ]

    async def event_stream():
        yield f"event: sources\ndata: {json.dumps(sources)}\n\n"
        async for token in stream_answer(request.question, ranked):
            yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

