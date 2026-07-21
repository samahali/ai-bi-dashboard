# Architecture

## Overview

The app is a full-stack BI dashboard: upload a data file, ask questions about
it in plain English, get back SQL, results, a chart, and optionally a PDF
report. There are four runtime services (Postgres, ChromaDB, FastAPI
backend, React frontend) plus an Nginx reverse proxy used only in the
`production` Docker Compose profile.

```
┌──────────────┐     ┌──────────────────────────────────────────────┐
│   Frontend    │     │                   Backend                    │
│  React + Vite │────▶│  FastAPI                                     │
│  (port 3000)  │     │  ├─ auth (JWT)                               │
└──────────────┘     │  ├─ files → FileParser → pandas                │
                      │  ├─ datasets                                 │
                      │  ├─ queries → BIAgent (text-to-SQL)          │
                      │  │             ├─ SchemaRAGStore ──▶ ChromaDB │
                      │  │             ├─ LangChain chain ──▶ LLM     │
                      │  │             └─ DatasetSQLExecutor ──▶ DuckDB│
                      │  ├─ reports → PDFGenerator (ReportLab)        │
                      │  └─ insights → InsightGenerator (statistical) │
                      └───────────────┬──────────────────┬───────────┘
                                      │                  │
                              ┌───────▼──────┐   ┌───────▼───────┐
                              │  PostgreSQL   │   │   ChromaDB     │
                              │ (app state)   │   │ (schema RAG)   │
                              └───────────────┘   └────────────────┘
```

## Backend layout

```
backend/app/
├── main.py              FastAPI app factory, lifespan, router wiring, CORS
├── config.py             Pydantic Settings — all env vars in one place
├── api/v1/                One router module per resource (auth, files,
│                          datasets, queries, reports, insights,
│                          visualizations, health)
├── api/dependencies.py    get_current_user() — JWT auth dependency
├── services/              Business logic, one per resource, takes an
│                          AsyncSession and does the actual work
├── ai/
│   ├── agent.py           BIAgent — orchestrates the text-to-SQL pipeline
│   ├── langchain_llms.py  WatsonxGraniteLLM — LangChain LLM wrapper
│   ├── rag_store.py       SchemaRAGStore — ChromaDB-backed column retrieval
│   ├── sql_executor.py    DatasetSQLExecutor — runs SQL via DuckDB
│   ├── validators.py      PromptInjectionValidator
│   └── prompts.py         Prompt templates
├── utils/
│   ├── file_parser.py     CSV/Excel/JSON → pandas → column metadata
│   ├── insight_generator.py  Statistical anomaly/trend detection
│   └── pdf_generator.py   ReportLab PDF building
├── db/
│   ├── models.py          SQLAlchemy ORM models (source of truth for schema)
│   ├── session.py         Async engine/session factory
│   └── migrations/        Alembic environment + versioned migrations
├── schemas/               Pydantic request/response models
├── middleware/            Error handlers, request logging
└── core/                  auth.py (JWT/bcrypt), exceptions.py
```

## Request lifecycle patterns

**Background tasks with their own DB session.** Any work that outlives the
HTTP request (file parsing, SQL generation, PDF generation) is fired with
`asyncio.create_task(...)` and opens its own `AsyncSessionLocal()` rather
than reusing the request-scoped session — the request's session may already
be closed by the time the background task runs. See `file_parser.py`,
`query_service.py`, `report_service.py`.

**Auth returns 401, never 403, for missing/invalid credentials.**
`get_current_user` uses `HTTPBearer(auto_error=False)` specifically so a
missing/malformed `Authorization` header surfaces as `UnauthorizedError`
(401) instead of FastAPI's default 403. 403 is reserved for ownership/ACL
checks (a valid, authenticated user trying to access someone else's
resource) — see `ForbiddenError` usages in the service layer.

## The text-to-SQL pipeline (BIAgent.process_question)

1. **Validate** the question via `PromptInjectionValidator` (regex
   blocklist + length/character-ratio checks) — rejects before any LLM call.
2. **Retrieve schema context (RAG).** `SchemaRAGStore` embeds each column of
   a dataset (name, type, sample values) into a per-dataset ChromaDB
   collection when the file finishes parsing. At query time, the question
   is embedded with the same deterministic hashing function and the top-15
   most relevant columns are retrieved — the LLM prompt gets a filtered
   schema instead of the full column list, which matters once a dataset has
   many columns. Falls back to the full schema if ChromaDB is unreachable or
   the dataset is small enough that filtering wouldn't help.
3. **Generate SQL.** A LangChain `Runnable` chain
   (`PromptTemplate | llm | StrOutputParser()`) drives either
   `WatsonxGraniteLLM` (a custom LangChain `LLM` wrapping the
   `ibm-watsonx-ai` SDK) or `ChatOpenAI`, depending on `default_llm_provider`
   / the request's `ai_model`. Granite init failure falls back to OpenAI
   automatically if a valid key is configured.
4. **Execute.** The cleaned SQL runs via `DatasetSQLExecutor` against a
   DuckDB in-memory table loaded from the dataset file — not against the
   app's own Postgres database, so even a successful SQL injection is
   contained to a throwaway in-memory copy of the uploaded file. A keyword
   denylist blocks destructive statements (DROP/DELETE/UPDATE/etc.) as a
   second layer of defense.
5. **Suggest a visualization** (`bar`/`line`/`pie`/`scatter`/`table`) based
   on the shape of the result set; persisted on the `Query` row and
   consumed by the frontend's `QueryChart` component.

## Why ChromaDB is pinned to `0.5.23` and the client to `0.6.3`

The ChromaDB server changed its collection-config response schema at some
point after 0.5.x in a way that older/newer-mismatched client versions
can't parse (`KeyError: '_type'` on `create_collection`). `0.6.3` (client) /
`0.5.23` (server) is the verified-compatible pair — see the comments in
`docker-compose.yml` and `backend/requirements.txt`. Bump both together,
deliberately, and re-verify against a live container before changing either.

## Database schema management

Alembic is the source of truth for schema in any environment where
`APP_ENV=production`. In development/test, `create_tables()` in
`app/db/session.py` still runs `Base.metadata.create_all()` on startup for
convenience — fast iteration without writing a migration for every model
tweak. See [Development](DEVELOPMENT.md) and [Deployment](DEPLOYMENT.md)
for the exact commands.
