"""routing.py — route reasoning artifacts to the correct pool (v2).

Pure logic layer. Returns destinations; does not write to disk.
Callers decide what to do with the destination.

shared_reasoning/
  proposals/       <- TRANSPARENT agents contributing new reasoning
  critiques/       <- TRANSPARENT agents critiquing others' work
  revisions/       <- TRANSPARENT agents revising their own prior submissions
  convergence_map/ <- structured record of where agents agree / disagree

private_reasoning/ <- PRIVATE agents; opaque to others during the session
"""

from __future__ import annotations

from arena.admission import AgentProfile, TransparencyLevel

POOL_SHARED = "shared"
POOL_PRIVATE = "private"

ARTIFACT_KINDS = frozenset({"proposal", "critique", "revision", "convergence_map"})

_SUBFOLDERS = {
    "proposal": "proposals",
    "critique": "critiques",
    "revision": "revisions",
    "convergence_map": "convergence_map",
}


def destination(agent: AgentProfile, kind: str) -> dict:
    """Logical destination for a reasoning artifact.

    Returns {"pool": ..., "subfolder": ...} or {"error": ...}.
    Does not touch the filesystem.
    """
    if kind not in ARTIFACT_KINDS:
        return {
            "error": (
                f"unknown artifact kind '{kind}'; "
                f"expected one of {sorted(ARTIFACT_KINDS)}"
            )
        }
    if agent.transparency_level == TransparencyLevel.TRANSPARENT:
        return {"pool": POOL_SHARED, "subfolder": _SUBFOLDERS[kind]}
    return {"pool": POOL_PRIVATE, "subfolder": None}


def route_batch(agent: AgentProfile, artifacts: list[dict]) -> list[dict]:
    """Return destinations for a list of {'kind': ..., 'content': ...} dicts."""
    results = []
    for art in artifacts:
        kind = art.get("kind", "")
        dest = destination(agent, kind)
        results.append({"kind": kind, **dest})
    return results
