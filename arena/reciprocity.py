"""reciprocity.py — Reciprocal Transparency Protocol enforcement (v2).

The rule is symmetric: you see what you show.

Transparent ↔ Transparent  →  mutual access to shared reasoning
Transparent ↔ Private      →  private participant cannot inspect transparent reasoning
Private     ↔ Private      →  each sees only their own private pool

This is not a punishment mechanism. It is a trust mechanism.
The arena does not require transparency. It requires reciprocity.
"""

from __future__ import annotations

from arena.admission import AgentProfile, TransparencyLevel


def can_access(observer: AgentProfile, target: AgentProfile) -> bool:
    """True only when both participants are transparent."""
    return (
        observer.transparency_level == TransparencyLevel.TRANSPARENT
        and target.transparency_level == TransparencyLevel.TRANSPARENT
    )


def access_report(observer: AgentProfile, target: AgentProfile) -> dict:
    """Return a plain-language explanation of the access decision."""
    granted = can_access(observer, target)
    if granted:
        reason = "both transparent — mutual access to shared reasoning"
    elif observer.transparency_level == TransparencyLevel.PRIVATE:
        reason = (
            f"observer '{observer.name}' is private; "
            "private participants cannot inspect transparent participants' reasoning — "
            "this is a consequence of reciprocity, not exclusion"
        )
    else:
        reason = (
            f"target '{target.name}' is private; "
            "their reasoning is not in the shared pool"
        )
    return {
        "observer": observer.name,
        "observer_level": observer.transparency_level.value,
        "target": target.name,
        "target_level": target.transparency_level.value,
        "access_granted": granted,
        "reason": reason,
    }


def reciprocity_matrix(profiles: list[AgentProfile]) -> list[dict]:
    """Full pairwise access matrix for a set of agents."""
    rows = []
    for i, a in enumerate(profiles):
        for b in profiles[i + 1:]:
            rows.append(access_report(a, b))
    return rows
