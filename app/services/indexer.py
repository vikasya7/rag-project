"""
Orchestrates the full indexing pipeline for one repo:
clone -> walk -> chunk -> embed -> store.

Runs as a FastAPI background task so /index returns immediately while
indexing continues in the background.
"""

from app.services.cloner import clone_repo, cleanup_repo, CloneError
from app.services.repo_walker import walk_repo
from app.services.chunker import chunk_file
from app.services.embedder import embed_chunks
from app.db.queries import update_repo_status, store_chunk


async def run_indexing_job(repo_id: int, github_url: str) -> None:
    try:
        await update_repo_status(repo_id, "indexing")

        local_path = clone_repo(github_url)
        try:
            files = walk_repo(local_path)
            print(f"Found {len(files)} source files in {github_url}")

            all_chunks = []
            for file_path in files:
                all_chunks.extend(chunk_file(file_path))
            print(f"Produced {len(all_chunks)} chunks")

            print("Starting embedding...")
            embedded = await embed_chunks(all_chunks)
            print(f"Embedding done, got {len(embedded)} results")
            print("Starting store...")
            for i, (chunk, embedding) in enumerate(embedded):
               print(f"Storing chunk {i}")
               await store_chunk(repo_id, chunk, embedding)

            await update_repo_status(repo_id, "ready", chunk_count=len(embedded))
            print(f"Indexed {len(embedded)} chunks for repo {repo_id}")

        finally:
            cleanup_repo(local_path)

    except CloneError as e:
        print(f"Clone failed for repo {repo_id}: {e}")
        await update_repo_status(repo_id, "failed")
    except Exception as e:
        print(f"Indexing failed for repo {repo_id}: {e}")
        await update_repo_status(repo_id, "failed")