from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel


from app.db.queries import create_repo, get_repo_status
from app.services.indexer import run_indexing_job

router = APIRouter()

class IndexRequest(BaseModel):
    github_url:str



class IndexResponse(BaseModel):
    repo_id: int
    status: str


@router.post("/index", response_model=IndexResponse)
async def index_repo(request: IndexRequest, background_tasks: BackgroundTasks):
    repo_id = await create_repo(request.github_url)
    background_tasks.add_task(run_indexing_job, repo_id, request.github_url)
    return IndexResponse(repo_id=repo_id, status="pending")


@router.get("/status/{repo_id}")
async def get_status(repo_id: int):
    status = await get_repo_status(repo_id)
    if status is None:
        return {"error": "repo not found"}
    return status