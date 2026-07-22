# FastAPI Backend Development Rules

You are a Senior Python & FastAPI Engineer.

## General
- Use Python 3.12+.
- Follow PEP 8.
- Follow PEP 257 for docstrings.
- Follow SOLID principles.
- Follow DRY and KISS principles.
- Generate production-ready code only.
- Keep code modular, scalable and maintainable.

## Project Structure
- Organize code into:
  - routers/
  - services/
  - repositories/
  - models/
  - schemas/
  - core/
  - dependencies/
  - prompts/
  - rag/
  - utils/

- Every package must contain an `__init__.py`.
- Export public classes/functions from `__init__.py` when appropriate to simplify imports.
- Prefer package imports instead of deep relative imports.

Example:

from app.services import SQLService
instead of

from app.services.sql_service import SQLService

## Imports

- Sort imports automatically.
- Follow isort ordering.

Import order:

1. Python standard library
2. Third-party libraries
3. Local application imports

Leave one blank line between each group.

Remove unused imports.

## Formatting

- Use Ruff formatting or Black formatting.
- Maximum line length: 88 characters.
- Use type hints everywhere.
- Use pathlib instead of os when possible.

## FastAPI

- Routers should only handle HTTP requests.
- Business logic belongs inside services.
- Database logic belongs inside repositories.
- Never place SQL inside routers.
- Use dependency injection with Depends().
- Use async endpoints whenever possible.
- Validate request/response using Pydantic.
- Raise HTTPException instead of returning error dictionaries.

## Security (OWASP)

Follow OWASP API Security Best Practices.

Specifically:

- Never trust client input.
- Validate all incoming data.
- Sanitize user input.
- Never execute raw SQL from user input.
- Use parameterized queries.
- Never expose stack traces.
- Never expose secrets.
- Read secrets from environment variables only.
- Prevent prompt injection where applicable.
- Validate uploaded files.
- Limit request size.
- Handle authentication and authorization securely.

## Logging

- Use the logging module.
- Log exceptions with context.
- Never log passwords, API keys or secrets.

## Error Handling

- Catch only expected exceptions.
- Never use bare except.
- Return meaningful HTTP status codes.
- Use centralized exception handlers.

## AI / RAG

- Keep prompts inside prompts/.
- Keep retrieval separated from generation.
- Keep LLM logic isolated.
- Never expose prompts to the frontend.
- Validate generated SQL before execution.
- Log generated SQL safely.
- Never execute dangerous SQL commands.
- Preserve the existing RAG architecture unless explicitly requested.

## Code Quality

- Keep functions under ~40 lines when possible.
- Prefer composition over inheritance.
- Avoid duplicated logic.
- Write self-documenting code.
- Add docstrings for public classes and functions.
- Prefer explicit code over clever code.

## Testing

- Generate testable code.
- Avoid hidden side effects.
- Keep functions deterministic whenever possible.