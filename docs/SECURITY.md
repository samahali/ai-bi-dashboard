# Security

This documents what's actually implemented, written to hold up to a
technical read of the code, not as marketing copy.

## Authentication

- Passwords hashed with **bcrypt** directly (`bcrypt` package, 12 rounds),
  truncated to 72 bytes before hashing/verifying to respect bcrypt's limit.
  See `app/core/auth.py`.
- JWT access + refresh tokens (`python-jose`, HS256). Refresh tokens are
  stored server-side as a **SHA-256 hash** (not the raw token) in
  `refresh_tokens`, so a leaked database dump doesn't hand out valid tokens
  directly, and logout/revocation works by marking the stored row revoked.
- **Tokens are delivered as `HttpOnly` cookies** (`app/core/cookies.py`), not
  in `localStorage` — client-side JavaScript, and therefore any XSS, cannot
  read them. Cookies are `SameSite=Lax` and `Secure` in production (forced
  regardless of the raw `cookie_secure` setting once `APP_ENV=production`,
  so a misconfiguration can't downgrade them). The refresh token cookie is
  path-scoped to `/api/v1/auth/refresh` so it isn't sent on every request.
  `get_current_user` reads the access token from the cookie, with an
  `Authorization: Bearer` header kept as a fallback for non-browser clients.
- `SECRET_KEY` defaults to `secrets.token_urlsafe(64)` **generated at
  process start** if not set via env — convenient for local dev, but means
  every existing JWT becomes invalid on restart if you forget to set
  `SECRET_KEY` in a real deployment. **Always set `SECRET_KEY` explicitly in
  production.**
- Missing/invalid credentials always return **401**, never 403 — see
  [Architecture](ARCHITECTURE.md#request-lifecycle-patterns).
- JWTs are stateless, so logout revokes the stored refresh token and clears
  both cookies, but an already-issued access token remains cryptographically
  valid until its expiry. With HttpOnly cookies it can't be exfiltrated in
  the first place, so this is the standard, accepted trade-off for JWT auth.

## Text-to-SQL injection surface

The LLM generates real SQL that gets executed — an inherently higher-risk
surface than parameterized queries, mitigated in layers:

1. **Prompt hardening** (`build_text_to_sql_prompt`, `app/ai/prompts.py`) —
   the untrusted user question is wrapped in explicit `<<<QUESTION>>>`
   delimiters with instructions to treat its contents as data only and
   ignore any embedded instructions; delimiter characters are stripped from
   the question so it can't close the block early and inject trailing
   instructions.
2. **Input validation** (`PromptInjectionValidator`, `app/ai/validators.py`)
   — a regex blocklist against the user's natural-language question
   (injection phrasing, SQL keywords, file-access function names, delimiter
   spoofing), plus a max length (2000 chars) and a non-alphanumeric-ratio
   check. This is a **blocklist**, not a classifier — bypassable via
   paraphrasing, so it is a first layer, not a guarantee.
3. **Generated-SQL validation** (`DatasetSQLExecutor._validate_sql`) —
   parses the generated SQL with `sqlglot` into an AST and enforces, by
   construction rather than by denylist: exactly one statement; its root
   node is a SELECT, a set operation (UNION/INTERSECT/EXCEPT), or a
   WITH/CTE wrapping one of those — any other root (INSERT, DROP, PRAGMA,
   stacked statements, …) is rejected outright; and every base table the
   query references resolves to one of the dataset's actual known table
   names (the exact set the LLM was told about), so a hallucinated or
   injected table name is caught before execution. An explicit pre-filter
   also rejects known DuckDB file/network function names (`read_csv`,
   `read_parquet`, `copy`, `install`, `load`, …) as a fast, early-fail check
   ahead of the engine-level guarantee below.
4. **Hardened execution engine** (`app/ai/sql_executor.py`) — the DuckDB
   connection runs with `enable_external_access=false` and extension
   auto-install/auto-load disabled. This is the **real guarantee**: even SQL
   that evades the parser-based checks (e.g. an unlisted file-reading
   function or an obfuscated form) is refused by the engine itself, which
   will not read any local file or URL.
5. **Blast radius containment** — generated SQL runs against **in-memory
   DataFrames** built from the uploaded file (one per sheet, for
   multi-sheet Excel datasets), not the app's PostgreSQL database, so it
   can never touch `users`, `datasets`, or other real tables.
6. **No sample data values sent to the LLM.** The schema block in the
   SQL-generation prompt (`BIAgent._format_schema`) includes only column
   name, type, and nullability — never real values from the uploaded file.
   The dataset's actual data therefore isn't sent to the external LLM
   provider (OpenAI/Watsonx) as part of building query context; only its
   structure is.

Net assessment: layered defense-in-depth with a parser-based (AST)
allowlist for what the generated SQL is permitted to be, plus an
engine-level guarantee against file/URL access as the final backstop.

## File uploads

The on-disk path for an uploaded file is built entirely from
server-controlled values — a random UUID plus the validated extension
(`app/services/file_service.py`). The client-supplied filename is reduced
to its basename (`Path(...).name`, which strips any `../` traversal
sequences) and used only for the display `file_name` field, never the
path. A final `is_relative_to` check confirms the resolved path stays
inside the user's upload directory before anything is written. File type
is validated against an allowlist (`csv`, `xlsx`, `json`) and size against
`MAX_UPLOAD_SIZE_MB`.

## CORS

Origin-restricted via `ALLOWED_ORIGINS` (comma-separated allowlist, not a
wildcard) — required to be a specific origin (not `*`) because the app
sends credentialed (cookie) requests. `allow_methods=["*"]` /
`allow_headers=["*"]` is permissive on methods/headers — worth tightening
to explicit methods if deployed with a different trust model.

## Rate limiting

Enforced via `slowapi`. The shared `Limiter` lives in
`app/core/rate_limit.py`, `SlowAPIMiddleware` is registered in
`app/main.py`, and `@limiter.limit(f"{settings.rate_limit_per_minute}/minute")`
is applied to the most abuse-prone endpoints: `POST /auth/register`,
`POST /auth/login` (brute-force), and `POST /queries` (LLM-cost spam).

## Secrets

- `.env` is gitignored and should be stored `600` (owner read/write only).
- No secret is ever logged — `structlog` is configured on request/response
  metadata (method, path, status, duration), not payload bodies. The
  refresh token is read from a cookie, never a query string.
- **Rotate, don't just re-permission.** Tightening file permissions does
  not un-expose a credential that was already world-readable or pasted
  anywhere. If a Watsonx/OpenAI API key or `SECRET_KEY` has ever been
  exposed, rotate it at the source — plaintext env values cannot un-leak
  themselves.

## Dependency version notes

- `chromadb` server and client versions must stay compatible — server
  pinned to `0.5.23`, client to `0.6.3` (see
  [Architecture](ARCHITECTURE.md#why-chromadb-is-pinned-to-0523-and-the-client-to-063)).
  Bump both together, deliberately.
- The app requires Python 3.11+ (uses `list[str]`-style builtin generics
  throughout).

Run `pip list --outdated` periodically and re-verify compatibility (not
just "does it install," but "does it actually import and run") before
bumping dependencies — a clean `pip install` does not guarantee the app
boots.
