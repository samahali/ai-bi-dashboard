# Deployment

## Known gap: `docker-compose.yml`'s `production` profile isn't actually production-ready yet

Documenting this rather than glossing over it: `frontend/Dockerfile` has a
proper 3-stage build (`development` → `builder` → `production`, the last
being an Nginx image serving the static Vite build), and
`nginx/nginx.conf` exists as a reverse proxy — but:

- `docker-compose.yml`'s `frontend` service always targets `target: development`
  (the hot-reload Vite dev server), with no separate production-target
  service defined.
- `nginx/nginx.conf` proxies `location /` to `http://frontend:5173` — that's
  the **dev server's** port, not the static-file Nginx container from
  `frontend/Dockerfile`'s `production` stage. Under the current compose
  file, enabling the `production` profile puts an Nginx reverse proxy in
  front of another Nginx-serving-a-dev-server, which doesn't make sense.

**Until this is fixed**, the `production` Compose profile should not be
relied on as-is. The straightforward fix (tracked as a follow-up, not done
in this pass) is either:
- Add a second frontend service (e.g. `frontend-prod`) built with
  `target: production` from `frontend/Dockerfile`, and point
  `nginx/nginx.conf`'s `location /` at that container's port 80 instead of
  `frontend:5173`; or
- Skip the top-level `nginx/` proxy entirely and let the frontend's own
  `production`-stage Nginx (already built from `frontend/Dockerfile`) serve
  traffic directly, with the backend reachable at its own port/subdomain.

The backend's own production path (below) is real and does work correctly
independent of this frontend gap.

## Backend production build

`backend/Dockerfile`'s `production` stage:
- Installs only `requirements.txt` (no dev/test tooling).
- Copies `app/` and `alembic.ini`, plus `docker-entrypoint.sh`.
- Runs as non-root `appuser`.
- **Entrypoint runs `alembic upgrade head` before starting uvicorn** —
  schema migrations are applied automatically on container start, so there
  is no manual migration step to remember in a deploy pipeline. See
  [Architecture](ARCHITECTURE.md#database-schema-management).
- Serves via `uvicorn ... --workers 2` (tune worker count to available
  CPU — this is not auto-scaled).

To build and run just the backend's production image:

```bash
docker build --target production -t bi-backend:prod ./backend
docker run -d \
  -e DATABASE_URL=postgresql://user:pass@your-postgres-host:5432/bi_dashboard \
  -e APP_ENV=production \
  -e SECRET_KEY=<a real long random secret — do not use the dev default> \
  -e WATSONX_APIKEY=... -e WATSONX_URL=... -e WATSONX_PROJECT_ID=... \
  -e OPENAI_API_KEY=... \
  -e CHROMADB_HOST=your-chromadb-host -e CHROMADB_PORT=8000 \
  -p 8000:8000 \
  bi-backend:prod
```

`APP_ENV=production` matters beyond labeling: it disables `/docs`/`/redoc`
and skips the dev-only `create_all()` table creation in favor of the
Alembic migration the entrypoint just ran — see `app/main.py`.

## Environment variables that must change from `.env.example` defaults

| Variable | Why |
|---|---|
| `SECRET_KEY` | Defaults to a randomly generated value at process start if unset — **every JWT invalidates on every restart** unless this is set explicitly to a fixed, long, random value. |
| `DATABASE_URL` | Points at the dev `postgres` service hostname by default — must point at your real production Postgres. |
| `CHROMADB_HOST` / `CHROMADB_PORT` | Must point at a `chromadb/chroma:0.5.23`-compatible server (client is pinned to `0.6.3` for a reason — see [Security](SECURITY.md#dependency-versions)). Do not bump the ChromaDB server image without re-verifying client compatibility first. |
| `WATSONX_APIKEY` / `WATSONX_PROJECT_ID` / `OPENAI_API_KEY` | Placeholder values in `.env.example` — text-to-SQL queries fail with `AIServiceError` until at least one is a real, valid key. |
| `ALLOWED_ORIGINS` | Defaults to localhost dev ports — set to your actual frontend origin(s). |
| `APP_ENV` | Must be `production` to get the behaviors described above. |

## Database migrations in production

Handled automatically by `docker-entrypoint.sh` on container start (see
above). To run manually against a specific environment without starting the
app (e.g. from CI, before a blue/green swap):

```bash
docker run --rm \
  -e DATABASE_URL=postgresql://... \
  bi-backend:prod alembic upgrade head
```

Always back up the database before a migration that includes a
`downgrade()` you haven't tested — Alembic will run what's in the migration
file, not what you assume it does.

## Health checks

- Backend: `GET /api/v1/health` (used by `backend/Dockerfile`'s `HEALTHCHECK`).
- Frontend production image: `wget --spider http://localhost/` against the
  Nginx-served static build (once the gap above is resolved).

## Storage

`storage/uploads` and `storage/reports` are Docker named volumes
(`uploads_data`, `reports_data`) in the Compose setup — persisted across
container recreation, but not automatically backed up. For a real
production deployment, back these up the same way you'd back up the
database, or move to object storage (S3-compatible) if running multiple
backend replicas, since local-disk storage doesn't share across replicas.
