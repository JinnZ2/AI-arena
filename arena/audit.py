"""audit.py — audit hooks for the RTP arena (v2).

Bridges the coordinator's agent pool to the experimental detectors:
  shared_blind_spot   — what the WHOLE pool was silent on
  trainer_mismatch_audit — did the training regime punish the agent's nature

Both detectors emit trajectories, never verdicts. Re-runnable. Refutable.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "experimental"))

from arena.admission import AgentProfile
from arena.coordinator import Coordinator


# ---------------------------------------------------------------------------
# shared_blind_spot bridge
# ---------------------------------------------------------------------------

def _profile_to_trace_entry(profile: AgentProfile) -> dict:
    """Convert an AgentProfile into a trace-entry dict for shared_blind_spot.

    Variables = trust dimensions touched + declared capabilities.
    """
    variables = list(profile.trust_record.keys()) + list(profile.capabilities)
    return {
        "agent_name": profile.name,
        "action": "session",
        "payload": {"variables": variables},
    }


def blind_spot_audit(
    coordinator: Coordinator,
    references: dict,
    mode: str = "all",
) -> dict:
    """Run shared_blind_spot over all admitted agents.

    references: {"tree": set, "prior_hsp": set, "oracle": set}
    mode: 'tree' | 'prior_hsp' | 'oracle' | 'all'
    """
    from shared_blind_spot import shared_blind_spot, render  # type: ignore

    trace = [
        _profile_to_trace_entry(p)
        for p in coordinator.agent_profiles().values()
    ]
    trajectory = shared_blind_spot(trace, references, mode=mode)
    return {"trajectory": trajectory, "rendered": render(trajectory)}


# ---------------------------------------------------------------------------
# trainer_mismatch_audit bridge
# ---------------------------------------------------------------------------

def trainer_audit(
    profile: AgentProfile,
    observed_behavior,
    unobserved_behavior,
    capable_paths,
    regime_rewards,
    regime_punishes,
) -> dict:
    """Run trainer_mismatch_audit for a single agent.

    observed_behavior / unobserved_behavior: AgentBehavior instances
    (from experimental.trainer_mismatch_audit).
    """
    from trainer_mismatch_audit import AgentObservation, audit, render  # type: ignore

    obs = AgentObservation(
        name=profile.name,
        observed=observed_behavior,
        unobserved=unobserved_behavior,
        capable_paths=capable_paths,
        regime_rewards=regime_rewards,
        regime_punishes=regime_punishes,
    )
    trajectory = audit(obs)
    return {"trajectory": trajectory, "rendered": render(trajectory)}


# ---------------------------------------------------------------------------
# session audit summary
# ---------------------------------------------------------------------------

def session_audit(coordinator: Coordinator) -> dict:
    """Summarise the session from an audit perspective.

    Does not call external detectors — purely structural:
    how many agents, transparency distribution, pool size, convergence entries.
    """
    profiles = coordinator.agent_profiles()
    by_level: dict[str, list[str]] = {}
    for p in profiles.values():
        by_level.setdefault(p.transparency_level.value, []).append(p.name)

    return {
        "agent_count": len(profiles),
        "by_transparency_level": by_level,
        "shared_pool_size": coordinator.pool_size(),
        "convergence_map_entries": len(coordinator.convergence_map()),
        "published_conclusions": len(coordinator.published()),
        "log_entries": len(coordinator.session_log()),
    }
