# Security

This documents what's actually implemented, what's partial, and known
limitations — written to hold up to a technical read of the code, not as
marketing copy.

## Security review status

An OWASP-LLM-focused review was performed and its findings remediated
(each fix verified against the live running stack):

| Finding | Severity | Status |
|---|---|---|
| LLM-generated SQL could read arbitrary local files via DuckDB file functions | Critical | Fixed — engine-level `enable_external_access=false` + denylist |
| Path traversal via unsanitized upload filename | Critical | Fixed — UUID-only path, basename-only display name |
| Prompt injection guard was a single bypassable blocklist | High | Hardened — delimited prompt + expanded validation + engine guarantee |
| JWT tokens stored in `localStorage` (XSS-stealable) | Medium | Fixed — migrated to `HttpOnly` cookies |
| `.env` (and `.history/` copies) world-readable | Low | Fixed — `600` perms, `.history/` gitignored |

The one item requiring action **outside the code**: any API key that was
world-readable or pasted into a chat/screenshot must be **rotated at the
source** — see [Secrets](#secrets).

## Authentication

- Passwords hashed with **bcrypt** directly (`bcrypt` package, 12 rounds),
  truncated to 72 bytes before hashing/verifying to respect bcrypt's limit.
  See `app/core/auth.py`.
- JWT access + refresh tokens (`python-jose`, HS256). Refresh tokens are
  stored server-side as a **SHA-256 hash** (not the raw token) in
  `refresh_tokens`, so a leaked database dump doesn't hand out valid tokens
  directly, and logout/revocation works by marking the stored row revoked.
- **Tokens are delivered as `HttpOnly` cookies** (`app/core/cookies.py`), not
  in `localStorage` — so client-side JavaScript, and therefore any XSS,
  cannot read them. Cookies are `SameSite=Lax` (blocks the common CSRF
  vectors for this same-origin app) and `Secure` in production. The refresh
  token cookie is path-scoped to `/api/v1/auth/refresh` so it isn't sent on
  every request. `get_current_user` reads the access token from the cookie,
  with an `Authorization: Bearer` header kept as a fallback for non-browser
  API clients.
- `SECRET_KEY` defaults to `secrets.token_urlsafe(64)` **generated at
  process start** if not set via env — convenient for local dev, but means
  every existing JWT becomes invalid on restart if you forget to set
  `SECRET_KEY` in a real deployment. **Always set `SECRET_KEY` explicitly in
  production.**
- Missing/invalid credentials always return **401**, never 403 — see
  [Architecture](ARCHITECTURE.md#request-lifecycle-patterns).
- Note: JWTs are stateless, so logout revokes the (stored) refresh token and
  clears both cookies, but an already-issued access token remains
  cryptographically valid until its 60-minute expiry. With HttpOnly cookies
  it can't be exfiltrated in the first place, so this is the standard,
  accepted trade-off for JWT auth.

## Text-to-SQL injection surface

The LLM generates real SQL that gets executed — this is inherently a
higher-risk surface than parameterized queries, mitigated in layers:

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
3. **Generated-SQL validation** (`DatasetSQLExecutor._validate_sql_safety`)
   — word-boundary-tokenized denylist covering DDL/DML keywords **and**
   DuckDB file/network functions (`read_csv`, `read_parquet`, `read_json`,
   `copy`, `install`, `load`, …), plus rejection of stacked (multi-)
   statements. Word-boundary matching avoids false positives like a
   `created_at` column tripping the `CREATE` rule.
4. **Hardened execution engine** (`app/ai/sql_executor.py`) — the DuckDB
   connection runs with `enable_external_access=false` and extension
   auto-install/auto-load disabled. This is the **real guarantee**: even
   SQL that evades the denylist (e.g. an unlisted file-reading function or
   an obfuscated form) is refused by the engine itself, which will not read
   any local file or URL. Verified live — `SELECT * FROM read_csv('/etc/passwd')`
   is rejected both at validation and at the engine.
5. **Blast radius containment** — generated SQL runs against an **in-memory
   DataFrame** built from the uploaded file, not the app's PostgreSQL
   database, so it can never touch `users`, `datasets`, or other real
   tables.

Net assessment: layered defense-in-depth with an engine-level guarantee
against file/URL access, not just denylists. A further hardening step would
be replacing the denylists with a positive SQL AST allowlist (parse and
verify a single `SELECT` with no dangerous constructs).

## File uploads

The on-disk path for an uploaded file is built entirely from server-
controlled values — a random UUID plus the validated extension
(`app/services/file_service.py`). The client-supplied filename is reduced to
its basename (`Path(...).name`, which strips any `../` traversal sequences)
and used only for the display `file_name` field, never the path. A final
`is_relative_to` check confirms the resolved path stays inside the user's
upload directory before anything is written. File type is validated against
an allowlist (`csv`, `xlsx`, `json`) and size against `MAX_UPLOAD_SIZE_MB`.
Verified live — an upload with filename `../../../../tmp/evil.csv` is stored
safely inside the user's directory, not at the traversal target.

## CORS

Origin-restricted via `ALLOWED_ORIGINS` (comma-separated allowlist, not a
wildcard) — required to be a specific origin (not `*`) because the app now
sends credentialed (cookie) requests. `allow_methods=["*"]` /
`allow_headers=["*"]` is permissive on methods/headers — worth tightening to
explicit methods if deployed with a different trust model.

## Rate limiting

Enforced via `slowapi`. The shared `Limiter` lives in `app/core/rate_limit.py`,
`SlowAPIMiddleware` is registered in `app/main.py`, and
`@limiter.limit(f"{settings.rate_limit_per_minute}/minute")` is applied to
the most abuse-prone endpoints: `POST /auth/register`, `POST /auth/login`
(brute-force), and `POST /queries` (LLM-cost spam). Verified live — the
61st request within a minute to `/auth/login` returns `429`.

## Secrets

- `.env` is gitignored and stored `600` (owner read/write only). The editor
  local-history directory `.history/` — which had accumulated old `.env`
  copies containing the same secrets, world-readable — is now gitignored and
  its files tightened to `600` as well.
- No secret is ever logged — `structlog` is configured on request/response
  metadata (method, path, status, duration), not payload bodies. The refresh
  token is read from a cookie, never a query string.
- **Rotate, don't just re-permission.** Tightening file permissions does not
  un-expose a credential that was already world-readable or pasted anywhere.
  If a Watsonx/OpenAI API key or `SECRET_KEY` has ever been exposed, rotate
  it at the source — plaintext env values cannot un-leak themselves.

## Dependency versions

Two real, verified-broken pins existed in `requirements.txt` before this
review and have been fixed (not just bumped speculatively — each was
reproduced and confirmed broken before changing):

- `langchain==0.2.1` / `langchain-openai==0.1.8` imported a pydantic v1
  compat shim that crashes on Python 3.12
  (`TypeError: ForwardRef._evaluate() missing 'recursive_guard'`).
- `chromadb` server pinned to `:latest` (1.0.0, v2-API-only) was
  incompatible with any client version resolvable alongside the pinned
  `fastapi==0.111.0` — verified via direct testing. Both server and client
  are now pinned to a verified-compatible pair (`0.5.23` server /
  `0.6.3` client) — see [Architecture](ARCHITECTURE.md).

Run `pip list --outdated` periodically and re-verify compatibility (not just
"does it install," but "does it actually import and run") before bumping
further — this codebase has direct evidence that a clean `pip install` does
not guarantee the app boots.
