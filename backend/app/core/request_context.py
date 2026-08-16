"""
HospitalOps AI — Request Context.

Provides context variables to store per-request state (like request_id)
so it can be accessed by deep service/repository layers without being
explicitly threaded through every function call.
"""

from contextvars import ContextVar

# ContextVar for storing the unique request ID of the current API request.
# Defaults to None if accessed outside of a request context.
request_id_ctx_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Get the current request ID."""
    return request_id_ctx_var.get()
