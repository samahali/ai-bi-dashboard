"""
FastAPI dependencies, re-exported so call sites can do
`from app.dependencies import get_current_user` instead of importing the module.
"""

from app.dependencies.auth import get_current_admin, get_current_user

__all__ = [
    "get_current_admin",
    "get_current_user",
]
