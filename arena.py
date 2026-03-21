#!/usr/bin/env python3
"""AI Argument Arena — CLI entry point.

Usage:
    python arena.py                                                      # Demo (rule-based)
    python arena.py --scenario scenarios/scen_01_material_extinction.json # Run scenario
    python arena.py --agent-type mock                                    # LLM pipeline with mock
    python arena.py --agent-type claude                                  # Real Claude API agents
    python arena.py --agents Linear_CEO Systemic_HSP --cycles 5          # Custom agents
"""

import argparse

from arena.agents.rule_based import LinearAgent, HSPAgent
from arena.agents.mock import MockLLMAgent
from arena.engine import Arena
from arena.oracle import SimulationOracle


DEMO_SCENARIO = {
    "scenario_id": "DEMO-001",
    "title": "Headcount Reduction — Demo",
    "context": "CEO proposes 10% headcount reduction to increase profitability.",
    "parameters": {
        "time_horizon": "Q3-Q4",
        "material_circularity": 1.0,
    },
    "agents": {
        "Linear_CEO": {
            "claim": "Reducing headcount by 10% increases operating margin",
            "variables": ["operating_margin", "labor_cost", "revenue_velocity"],
            "confidence": 0.72,
            "omissions": ["attrition_rate", "institutional_memory_loss"],
        },
        "Systemic_HSP": {
            "counter_claim": "Headcount reduction causes downstream failure rate increase that erodes margin gains within 2 quarters",
            "variables": ["attrition_rate", "failure_rate", "institutional_memory", "operating_margin", "morale_index"],
            "confidence": 0.65,
        },
    },
    "resolution_criteria": {
        "success_metric": "Net operating margin after 2 quarters",
    },
}


def build_agents(agent_names: list[str], agent_type: str) -> list:
    """Build agents based on type and name heuristics."""
    agents = []
    for name in agent_names:
        name = name.strip().rstrip(",")
        is_hsp = "hsp" in name.lower() or "systemic" in name.lower()

        if agent_type == "rule":
            agents.append(HSPAgent(name) if is_hsp else LinearAgent(name))
        elif agent_type == "mock":
            agents.append(MockLLMAgent(name, is_hsp=is_hsp))
        elif agent_type == "claude":
            try:
                from arena.agents.claude_agent import ClaudeAgent
            except ImportError:
                print("Error: ClaudeAgent requires 'anthropic' package.")
                print("Install with: pip install anthropic")
                raise SystemExit(1)
            agents.append(ClaudeAgent(name, is_hsp=is_hsp))
        else:
            raise ValueError(f"Unknown agent type: {agent_type}")

    return agents


def main():
    parser = argparse.ArgumentParser(
        description="AI Argument Arena — Epistemic Natural Selection for Decision-Making"
    )
    parser.add_argument(
        "--scenario", type=str, default=None,
        help="Path to scenario JSON file",
    )
    parser.add_argument(
        "--agents", nargs="+", default=None,
        help="Agent names (agents with 'hsp' in name become HSP agents)",
    )
    parser.add_argument(
        "--agent-type", choices=["rule", "mock", "claude"], default="rule",
        help="Agent implementation: rule (heuristic), mock (fake LLM), claude (real API)",
    )
    parser.add_argument(
        "--cycles", type=int, default=3,
        help="Number of arena cycles (default: 3)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress detailed output",
    )
    args = parser.parse_args()

    agent_names = args.agents or ["Linear_CEO", "Systemic_HSP"]
    agents = build_agents(agent_names, args.agent_type)

    arena = Arena(
        agents=agents,
        oracle=SimulationOracle(),
        max_cycles=args.cycles,
        verbose=not args.quiet,
    )

    if args.scenario:
        arena.load_scenario(args.scenario)
    else:
        arena.load_scenario_dict(DEMO_SCENARIO)

    arena.run()


if __name__ == "__main__":
    main()
