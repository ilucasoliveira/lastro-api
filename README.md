# Lastro

> 🚧 Work in progress. See the roadmap below for what exists today.

Ask questions about Brazilian financial regulation (Pix rules, bank fees,
consumer rights) and get answers grounded in the official documents from
Banco Central and CMN. Every answer cites the document and page it came from,
and when the documents do not cover a question, the API says so instead of
guessing.

The name is a pun: *lastro* is the backing behind a currency, and here it is
the backing behind every answer.

## How it works

```
PDF ──► extract text per page ──► split into chunks ──► embed ──► Postgres + pgvector
                                                                        │
question ──► embed ──► nearest chunks ◄─────────────────────────────────┘
                              │
                              ▼
                 Claude answers using only those chunks,
                 citing document and page for each claim
```

This is retrieval-augmented generation (RAG), built step by step without a
framework, so every stage is explicit and testable on its own.

## Stack

- Python 3.14, FastAPI
- SQLAlchemy 2.0 (async) + asyncpg, Alembic
- PostgreSQL 18 + pgvector
- Claude (Anthropic API) for answer generation
- Docker Compose, GitHub Actions, Ruff, pytest

## Roadmap

- [x] Project skeleton, health checks, CI
- [ ] Ingestion: PDF upload, text extracted and stored per page
- [ ] Chunking with overlap, page numbers preserved
- [ ] Embeddings and vector search with pgvector
- [ ] Answers from Claude with page citations, streamed over SSE
- [ ] Evaluation suite: retrieval recall and answer faithfulness, run in CI
- [ ] Hybrid search (Postgres full text + vectors) and reranking
- [ ] Web front end and public deploy

## Running locally

```bash
cp .env.example .env          # then fill in the values
docker compose up -d db
poetry install
poetry run fastapi dev app/main.py
```

The interactive docs are at http://127.0.0.1:8000/docs.

## License

MIT
