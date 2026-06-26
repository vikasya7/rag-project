from dotenv import load_dotenv

load_dotenv()  # must run before any service module reads os.environ

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import index_route, ask_route

app = FastAPI(title="reposage", description="AST-aware RAG over a codebase")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(index_route.router)
app.include_router(ask_route.router)


@app.get("/")
async def root():
    return {"status": "ok", "service": "reposage"}