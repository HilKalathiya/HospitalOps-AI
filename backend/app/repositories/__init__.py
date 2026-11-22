"""
HospitalOps AI — Repositories package.

Domain repositories are the ONLY permitted path to MongoDB collection access.
No code outside this package should import motor collections directly.

See docs/architecture/service-patterns.md for the full repository pattern.
"""

from app.repositories.agent_messages import AgentMessageRepository
from app.repositories.agent_sessions import AgentSessionRepository

__all__ = [
    "AgentMessageRepository",
    "AgentSessionRepository",
]
