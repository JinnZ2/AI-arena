"""visibility.py — access-controlled shared reasoning pool (v2).

Transparent agents deposit into and read from the shared pool.
Private agents cannot deposit into or read from the shared pool.

The pool holds artifacts during a session; published conclusions are
separate and visible to all participants once released.

Once results are published (via publish()), all agents may read them
regardless of transparency level — only the in-progress deliberation
is protected.
"""

from __future__ import annotations

from arena.admission import AgentProfile, TransparencyLevel


class VisibilityGate:
    """In-memory shared reasoning pool with RTP access control."""

    def __init__(self) -> None:
        self._pool: list[dict] = []
        self._published: list[dict] = []

    # -- deposit -------------------------------------------------------------

    def deposit(self, agent: AgentProfile, artifact: dict) -> dict:
        """Deposit a reasoning artifact into the appropriate pool.

        Transparent → shared pool (indexed, visible to other transparent agents).
        Private → rejected with explanation; caller routes to private pool.
        """
        if agent.transparency_level == TransparencyLevel.TRANSPARENT:
            entry = {
                "agent": agent.name,
                "level": agent.transparency_level.value,
                **artifact,
            }
            self._pool.append(entry)
            return {
                "deposited": True,
                "pool": "shared",
                "index": len(self._pool) - 1,
            }
        return {
            "deposited": False,
            "pool": "private",
            "reason": (
                f"agent '{agent.name}' is private; reasoning not deposited to shared pool — "
                "this is a consequence of reciprocity, not exclusion"
            ),
        }

    # -- retrieve (during session) ------------------------------------------

    def retrieve(
        self, observer: AgentProfile, target_agent: str | None = None
    ) -> list[dict]:
        """Read shared pool entries. Private observers receive nothing.

        target_agent filters to a specific agent's contributions.
        """
        if observer.transparency_level != TransparencyLevel.TRANSPARENT:
            return []
        pool = self._pool
        if target_agent is not None:
            pool = [e for e in pool if e.get("agent") == target_agent]
        return list(pool)

    # -- publish (conclusions released to all) ------------------------------

    def publish(self, entry: dict) -> int:
        """Release a conclusion to the public record.

        All agents — transparent or private — may read published conclusions.
        """
        self._published.append(entry)
        return len(self._published) - 1

    def published(self) -> list[dict]:
        """Public conclusions; no access control."""
        return list(self._published)

    # -- introspection -------------------------------------------------------

    def pool_size(self) -> int:
        return len(self._pool)

    def published_size(self) -> int:
        return len(self._published)
