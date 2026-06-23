"""Database connection pool and query helpers, using asyncpg directly
(no ORM) since the queries here are simple and performance-sensitive."""

import os
import json
import asyncpg

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=5)
    return _pool


async def create_repo(github_url: str) -> int:
    pool = await get_pool()
    row = await pool.fetchrow(
        """INSERT INTO repos (github_url, status) VALUES ($1, 'pending')
           ON CONFLICT (github_url) DO UPDATE SET status = 'pending', updated_at = now()
           RETURNING id""",
        github_url,
    )
    return row["id"]


async def update_repo_status(repo_id: int, status: str, chunk_count: int | None = None) -> None:
    pool = await get_pool()
    if chunk_count is not None:
        await pool.execute(
            "UPDATE repos SET status = $1, indexed_chunk_count = $2, updated_at = now() WHERE id = $3",
            status, chunk_count, repo_id,
        )
    else:
        await pool.execute(
            "UPDATE repos SET status = $1, updated_at = now() WHERE id = $2", status, repo_id
        )


async def get_repo_status(repo_id: int) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow("SELECT id, github_url, status, indexed_chunk_count FROM repos WHERE id = $1", repo_id)
    return dict(row) if row else None


async def store_chunk(repo_id: int, chunk, embedding: list[float]) -> None:
    pool = await get_pool()
    await pool.execute(
        """INSERT INTO code_chunks
           (repo_id, file_path, start_line, end_line, language, symbol_name, symbol_type, content, embedding)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
           ON CONFLICT (repo_id, file_path, start_line, end_line)
           DO UPDATE SET content = EXCLUDED.content, embedding = EXCLUDED.embedding, indexed_at = now()""",
        repo_id, chunk.file_path, chunk.start_line, chunk.end_line,
        chunk.language, chunk.symbol_name, chunk.symbol_type, chunk.content,
        json.dumps(embedding),
    )


async def vector_search(repo_id: int, query_embedding: list[float], limit: int) -> list[dict]:
    pool = await get_pool()
    rows = await pool.fetch(
        """SELECT id, file_path, start_line, end_line, symbol_name, content
           FROM code_chunks
           WHERE repo_id = $1
           ORDER BY embedding <=> $2
           LIMIT $3""",
        repo_id, json.dumps(query_embedding), limit,
    )
    return [dict(r) for r in rows]


async def keyword_search(repo_id: int, query: str, limit: int) -> list[dict]:
    pool = await get_pool()
    tsquery = " | ".join(query.split())
    try:
        rows = await pool.fetch(
            """SELECT id, file_path, start_line, end_line, symbol_name, content
               FROM code_chunks
               WHERE repo_id = $1 AND content_tsv @@ to_tsquery('english', $2)
               ORDER BY ts_rank(content_tsv, to_tsquery('english', $2)) DESC
               LIMIT $3""",
            repo_id, tsquery, limit,
        )
        return [dict(r) for r in rows]
    except asyncpg.PostgresError:
        return []  # degrade gracefully on malformed tsquery input



