# API Reference

Base URL: `http://localhost:8000/api/v1` (dev). Interactive docs are also
available at `/docs` (Swagger) and `/redoc`, but only when
`APP_ENV=development` — both are disabled in production.

All endpoints except `/auth/register`, `/auth/login`, `/auth/refresh`, and
`/health` require a `Authorization: Bearer <access_token>` header. A missing
or invalid token always returns **401** (not 403) — see
[Architecture](ARCHITECTURE.md#request-lifecycle-patterns) for why.

## Auth — `/auth`

| Method | Path | Body | Notes |
|---|---|---|---|
| POST | `/auth/register` | `{username, email, password, first_name?, last_name?}` | Password: 8–72 chars, needs 1 uppercase + 1 digit. Returns access + refresh tokens plus the user. |
| POST | `/auth/login` | `{username, password}` | Same response shape as register. |
| POST | `/auth/refresh` | `{refresh_token}` | Refresh tokens are stored server-side as a SHA-256 hash and checked for revocation. |
| POST | `/auth/logout` | — (auth required) | Revokes the caller's stored refresh tokens. |
| GET | `/auth/me` | — (auth required) | Current user profile. |

## Files — `/files`

| Method | Path | Notes |
|---|---|---|
| POST | `/files/upload` | `multipart/form-data`: `file`, `name`, `description?`, `is_public?`. Accepts CSV/XLSX/JSON up to `MAX_UPLOAD_SIZE_MB` (default 100MB). Creates a `Dataset` in `processing` status and returns immediately — parsing runs as a background task. Poll `GET /datasets/{id}` until `status` is `ready` or `error`. |

## Datasets — `/datasets`

| Method | Path | Notes |
|---|---|---|
| GET | `/datasets?page=&limit=&search=` | Paginated list, owner-scoped. |
| GET | `/datasets/{id}` | |
| GET | `/datasets/{id}/preview?rows=` | First N rows (max 500) as columns + row arrays. |
| PUT | `/datasets/{id}` | Update name/description/is_public. |
| DELETE | `/datasets/{id}` | Soft delete (`deleted_at` set) — also removes the dataset's ChromaDB schema collection. |

## Queries — `/queries` (natural language → SQL)

| Method | Path | Notes |
|---|---|---|
| POST | `/queries` | `{dataset_id, question, ai_model?: "granite"\|"openai"}`. Returns `202` with a query ID immediately — SQL generation + execution run as a background task. Poll `GET /queries/{id}` until `status` is `success` or `error`. |
| GET | `/queries/{id}` | Includes `generated_sql`, `results` (capped at 500 rows), `row_count`, `execution_time_ms`, `confidence_score`, `visualization_suggestion` (`bar`\|`line`\|`pie`\|`scatter`\|`table`). |
| GET | `/queries?dataset_id=&page=&limit=` | |
| DELETE | `/queries/{id}` | |

## Reports — `/reports` (PDF generation)

| Method | Path | Notes |
|---|---|---|
| POST | `/reports` | `{dataset_id, title, description?, query_ids: number[], visualization_ids?, include_insights?}`. **At least one of `query_ids` (non-empty) or `include_insights=true` is required** — a report with neither is rejected with 422, since it would otherwise generate an empty PDF. Returns `201` with a report ID immediately; PDF generation runs as a background task. |
| GET | `/reports/{id}` | Status: `pending` → `generating` → `completed` \| `error`. |
| GET | `/reports/{id}/download` | Streams the PDF. Requires auth (not a public link) — the frontend fetches it through the authenticated axios instance and triggers a browser download from the blob. |
| GET | `/reports` | List, owner-scoped. |
| DELETE | `/reports/{id}` | Also deletes the PDF file from disk. |

## Insights — `/insights` (statistical anomaly/trend detection)

Note: despite the "AI Insights" branding in the UI, detection here is
**statistical** (z-score outliers, null-ratio, skewness), not LLM-generated.
Generated automatically right after a dataset finishes parsing.

| Method | Path | Notes |
|---|---|---|
| GET | `/insights/{dataset_id}?insight_type=&severity=&limit=` | `insight_type`: `anomaly`\|`trend`\|`outlier`\|`correlation`. `severity`: `low`\|`medium`\|`high`\|`critical`. |
| POST | `/insights/{insight_id}/dismiss` | Soft-dismiss (excluded from future report `include_insights` content). |

## Visualizations — `/visualizations`

CRUD for saved chart configs (`chart_type`, `x_axis`, `y_axis`, `config`
JSON) tied to a query. Separate from the ad-hoc chart rendering
`QueryChart.tsx` does automatically from `visualization_suggestion` — this
is for explicitly saving a chart configuration.

| Method | Path |
|---|---|
| POST | `/visualizations` |
| GET | `/visualizations/{id}` |
| PUT | `/visualizations/{id}` |
| DELETE | `/visualizations/{id}` |

## Health — `/health`

| Method | Path | Notes |
|---|---|---|
| GET | `/health` | Liveness check, no auth required. Used by the Docker healthcheck. |

## Error format

All errors follow FastAPI's standard shape:

```json
{ "detail": "human-readable message" }
```

Validation errors (422) follow Pydantic's standard array-of-errors shape
under `detail`.
