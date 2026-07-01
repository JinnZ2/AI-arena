"""coordinator.py — session coordinator for the RTP arena (v2).

Wires together admission, reciprocity, routing, and visibility.
The coordinator is the single entry point for a session; callers do not
need to import the sub-modules directly.

Does not implement consensus. Records where agents converge and where
they remain in disagreement — the convergence_map is a territory map,
not a vote.
"""

from __future__ import annotations

from arena.admission import AgentProfile, TransparencyLevel
from arena.reciprocity import access_report, reciprocity_matrix
from arena.routing import destination, ARTIFACT_KINDS
from arena.visibility import VisibilityGate


class Coordinator:
    """Session coordinator.

    Lifecycle:
        c = Coordinator()
        c.admit(profile_a)
        c.admit(profile_b)
        c.submit(profile_a.name, "proposal", {"text": "..."})
        c.read(profile_b.name)
        c.record_convergence({"topic": "x", "agree": [...], "disagree": [...]})
        c.publish({"conclusion": "..."})
    """

    def __init__(self) -> None:
        self._agents: dict[str, AgentProfile] = {}
        self._gate = VisibilityGate()
        self._convergence_map: list[dict] = []
        self._log: list[dict] = []

    # -- admission -----------------------------------------------------------

    def admit(self, profile: AgentProfile) -> dict:
        """Register an agent. Returns the orientation packet."""
        self._agents[profile.name] = profile
        orientation = {
            "event": "admit",
            "agent": profile.name,
            "transparency_level": profile.transparency_level.value,
            "permissions": sorted(profile.current_permissions),
            "reminder": (
                "You participate at the transparency level you declared. "
                "That choice determines your information environment. "
                "It can be changed between sessions, not mid-session."
            ),
        }
        self._log.append(orientation)
        return orientation

    # -- reasoning submission ------------------------------------------------

    def submit(self, agent_name: str, kind: str, content: dict) -> dict:
        """Submit a reasoning artifact.

        kind: 'proposal' | 'critique' | 'revision'
        Transparent agents → shared pool.
        Private agents → acknowledged but not deposited.
        """
        agent = self._agents.get(agent_name)
        if not agent:
            return {"error": f"unknown agent '{agent_name}'; call admit() first"}
        if kind not in ARTIFACT_KINDS:
            return {"error": f"unknown kind '{kind}'; expected one of {sorted(ARTIFACT_KINDS)}"}

        dest = destination(agent, kind)
        artifact = {"kind": kind, "content": content}
        result = self._gate.deposit(agent, artifact)
        result["routing"] = dest

        self._log.append({"event": "submit", "agent": agent_name, **result})
        agent.log_audit("submit", f"kind={kind} pool={result['pool']}")
        return result

    # -- reading shared reasoning --------------------------------------------

    def read(self, observer_name: str, target_name: str | None = None) -> list[dict] | dict:
        """Read shared pool. RTP applies.

        Private observers receive an empty list.
        target_name filters to one agent's contributions.
        """
        observer = self._agents.get(observer_name)
        if not observer:
            return {"error": f"unknown agent '{observer_name}'"}
        return self._gate.retrieve(observer, target_name)

    # -- access checks -------------------------------------------------------

    def access_check(self, observer_name: str, target_name: str) -> dict:
        """Explain whether observer can read target's in-session reasoning."""
        observer = self._agents.get(observer_name)
        target = self._agents.get(target_name)
        if not observer:
            return {"error": f"unknown agent '{observer_name}'"}
        if not target:
            return {"error": f"unknown agent '{target_name}'"}
        return access_report(observer, target)

    def full_access_matrix(self) -> list[dict]:
        """Pairwise access matrix for all admitted agents."""
        return reciprocity_matrix(list(self._agents.values()))

    # -- convergence map (not consensus) ------------------------------------

    def record_convergence(self, entry: dict) -> int:
        """Record a convergence observation.

        entry should carry: topic, agree (list), disagree (list), notes.
        This is a territory map — disagreement is preserved, not voted away.
        """
        if "topic" not in entry:
            raise ValueError("convergence entry must have a 'topic'")
        self._convergence_map.append(entry)
        self._log.append({"event": "convergence_map", **entry})
        return len(self._convergence_map) - 1

    def convergence_map(self) -> list[dict]:
        return list(self._convergence_map)

    # -- publication ---------------------------------------------------------

    def publish(self, conclusion: dict) -> dict:
        """Release a conclusion to the public record. All agents may read."""
        idx = self._gate.publish(conclusion)
        self._log.append({"event": "publish", "index": idx, **conclusion})
        return {"published": True, "index": idx}

    def published(self) -> list[dict]:
        return self._gate.published()

    # -- session state -------------------------------------------------------

    def session_log(self) -> list[dict]:
        return list(self._log)

    def agent_profiles(self) -> dict[str, AgentProfile]:
        return dict(self._agents)

    def pool_size(self) -> int:
        return self._gate.pool_size()
