"""
Shared slowapi Limiter instance.

Lives in its own module (not app/main.py) so route modules can import it
for `@limiter.limit(...)` decorators without a circular import — main.py
imports the route modules, so the route modules can't import back from
main.py.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
