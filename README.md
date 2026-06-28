# reposage

Ask natural-language questions about any public GitHub repository and get answers grounded in citations to exact file and line ranges.

paste a GitHub URL → it indexes the codebase → ask anything → get answers with source citations

---

## What makes this different from a basic RAG demo

Most "chat with your codebase" projects split code into fixed-size text chunks every N tokens. This breaks functions in half mid-body, which means the embedding for that chunk represents half a function's logic with no surrounding context — retrieval quality suffers badly as a result.

reposage fixes this with three specific decisions:

**1. AST-aware chunking**
Every file is parsed into an Abstract Syntax Tree using tree-sitter. Chunks are emitted at semantic boundaries — one chunk per function, class, or method — not at arbitrary token windows. A file with 3 functions and 2 classes produces 5+ chunks, each representing a complete, self-contained unit of logic. This means embeddings capture the full meaning of a function, not half of it.

**2. Hybrid retrieval with Reciprocal Rank Fusion**
Pure vector search fails on exact symbol lookups. If you ask "where is `processPayment` defined," a semantic embedding model may not weight the literal identifier heavily enough. Pure keyword search fails on paraphrased questions like "where do we charge a customer's card." reposage runs both in parallel — vector search (semantic) and Postgres full-text search (lexical) — and merges the results with Reciprocal Rank Fusion, letting both result sets vote without manually tuning a blend weight.

**3. Cross-encoder reranking**
After hybrid retrieval returns the top 20 candidates, a cross-encoder reranker (Cohere) re-scores them by looking at the query and each candidate together in one pass — much more accurate than embedding similarity alone, which compares them independently. The top 5 after reranking go into the LLM prompt. This two-stage funnel (retrieve wide, rerank narrow) is standard in production search systems.

---

## Architecture

User pastes GitHub URL

         ↓

POST /index → clone repo (shallow, depth=1)

          ↓

Walk source files (.ts, .tsx, .js, .jsx, .py)

          ↓

tree-sitter AST parse → chunk per function/class/method

          ↓

OpenAI text-embedding-3-small → embed each chunk

(synthetic header prepended: file path + symbol name)

          ↓

Store in Postgres + pgvector (vector index + tsvector for full-text)

          ↓

GET /status/{repo_id} → poll until ready

          ↓

User asks a question

          ↓

POST /ask → hybrid retrieve (vector + keyword, top 20)

          ↓

Reciprocal Rank Fusion merge

          ↓

Cohere cross-encoder rerank → top 5

          ↓

Build prompt with chunks as context + citation instructions

          ↓

GPT-4o-mini streamed response → SSE tokens to frontend

          ↓

Answer with file:line citations



---

## Tech stack

**Backend**
- FastAPI + uvicorn — async Python web framework
- asyncpg — async Postgres driver (no ORM, raw SQL for performance)
- tree-sitter + tree-sitter-languages — AST parsing for TS, JS, Python
- OpenAI Python SDK — embeddings (text-embedding-3-small) and generation (gpt-4o-mini)
- Cohere rerank API — cross-encoder reranking
- GitPython — shallow git clone of public repos
- Postgres + pgvector (Neon) — vector storage with HNSW index + full-text search

**Frontend**
- Next.js 14 (App Router) — React framework
- Tailwind CSS v4 — styling
- Native fetch + ReadableStream — SSE consumption without extra libraries

---

## API

### `POST /index`
Clones and indexes a public GitHub repo in the background.

**Request:**
```json
{ "github_url": "https://github.com/owner/repo" }
```

**Response:**
```json
{ "repo_id": 1, "status": "pending" }
```

### `GET /status/{repo_id}`
Poll this to track indexing progress.

**Response:**
```json
{
  "id": 1,
  "github_url": "https://github.com/owner/repo",
  "status": "ready",
  "indexed_chunk_count": 253
}
```
Status values: `pending` → `indexing` → `ready` | `failed`

### `POST /ask`
Ask a question about an indexed repo. Returns a Server-Sent Events stream.

**Request:**
```json
{ "repo_id": 1, "question": "how does authentication work" }
```

**SSE events:**



---

## Setup

### Backend

```bash
cd rag-project
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# fill in DATABASE_URL, OPENAI_API_KEY, COHERE_API_KEY
```

Run the schema against your Postgres database (Neon or Supabase):
```bash
psql $DATABASE_URL -f app/db/schema.sql
```

Start the server:
```bash
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Visit `http://localhost:3000`

---

## Design decisions worth noting

**Why Postgres full-text search instead of a dedicated BM25 library:** asyncpg + pgvector already give us a single database for both vector and keyword search. Postgres `tsvector` with `ts_rank` provides BM25-equivalent ranking without running a separate search engine. One less service to maintain, same quality.

**Why SSE instead of WebSockets:** this is a request-response pattern — one user, one query, one streamed response. WebSockets are built for bidirectional real-time communication (like a multiplayer game or a collaborative editor). SSE is simpler, works over plain HTTP, and is the right tool for one-directional token streaming.

**Why shallow clone (depth=1):** we only need the current state of the code, not the full git history. A shallow clone is significantly faster and uses a fraction of the disk space, which matters when you're cloning repos on a server with limited storage.

**Why a two-table schema (repos + code_chunks):** the `repos` table tracks indexing state so the frontend can poll progress without holding a long HTTP connection open. The `code_chunks` table scopes every chunk to a `repo_id` so multiple repos can coexist in the same database without their chunks colliding in search results.

**Graceful degradation on reranking:** if the Cohere API is down or the key is missing, the system falls back to hybrid search order rather than returning an error. Quality dips slightly, but the system stays available — a deliberate tradeoff.

---

## Scope and known limitations

- Public repos only (no GitHub OAuth for private repos in v1)
- Supports TypeScript, JavaScript, and Python source files
- No incremental re-indexing yet — re-submitting the same URL re-embeds everything
- Indexing runs as a FastAPI background task, not a persistent job queue — fine for a single instance, would need Celery or RQ at real scale
- Large repos (10k+ files) will be slow to index and may exceed OpenAI embedding API rate limits

---

## What I would add next

- Incremental re-indexing: watch for file changes and re-embed only changed files
- Support for more languages via tree-sitter grammars (Go, Rust, Java)
- A self-hosted embedding model to cut API costs
- Persistent job queue (Celery + Redis) for production-grade background indexing
- Private repo support via GitHub OAuth