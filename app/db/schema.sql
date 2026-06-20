-- Run this once against a Postgres database with pgvector enabled
-- (Neon and Supabase both support this).

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS repos (
  id BIGSERIAL PRIMARY KEY,
  github_url TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pending', -- pending | indexing | ready | failed
  indexed_chunk_count INT DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS code_chunks (
  id BIGSERIAL PRIMARY KEY,
  repo_id BIGINT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
  file_path TEXT NOT NULL,
  start_line INT NOT NULL,
  end_line INT NOT NULL,
  language TEXT NOT NULL,
  symbol_name TEXT,
  symbol_type TEXT NOT NULL,
  content TEXT NOT NULL,
  embedding VECTOR(1536) NOT NULL,
  content_tsv TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
  indexed_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (repo_id, file_path, start_line, end_line)
);

CREATE INDEX IF NOT EXISTS code_chunks_embedding_idx
  ON code_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS code_chunks_tsv_idx
  ON code_chunks USING gin (content_tsv);

CREATE INDEX IF NOT EXISTS code_chunks_repo_id_idx
  ON code_chunks (repo_id);