#!/usr/bin/env python3
"""AI Argument Arena — CLI entry point.

Usage:
    python arena.py                                              # Run demo
    python arena.py --scenario scenarios/scen_01_material_extinction.json  # Run scenario
    python arena.py --agents Linear_CEO Systemic_HSP --cycles 5  # Custom agents
"""

import argparse
import sys

from arena.agents.rule_based import LinearAgent, HSPAgent
from arena.engine import Arena
from arena.oracle import SimulationOracle


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
        "--cycles", type=int, default=3,
        help="Number of arena cycles (default: 3)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress detailed output",
    )
    args = parser.parse_args()

    # Build agents
    agent_names = args.agents or ["Linear_CEO", "Systemic_HSP"]
    agents = []
    for name in agent_names:
        name = name.strip().rstrip(",")
        if "hsp" in name.lower() or "systemic" in name.lower():
            agents.append(HSPAgent(name))
        else:
            agents.append(LinearAgent(name))

    # Build arena
    arena = Arena(
        agents=agents,
        oracle=SimulationOracle(),
        max_cycles=args.cycles,
        verbose=not args.quiet,
    )

    # Load and run
    if args.scenario:
        arena.load_scenario(args.scenario)
    else:
        # Default demo scenario
        arena.load_scenario_dict({
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
        })

    arena.run()


if __name__ == "__main__":
    main()
