#!/usr/bin/env python3
"""AI Argument Arena — CLI entry point.

Usage:
    python arena.py                                                      # Demo (rule-based)
    python arena.py --scenario scenarios/scen_01_material_extinction.json # Run scenario
    python arena.py --agent-type mock                                    # LLM pipeline with mock
    python arena.py --agent-type claude                                  # Real Claude API agents
    python arena.py --oracle closed-system                               # Thermodynamic accounting
    python arena.py --agents Linear_CEO Systemic_HSP --cycles 5          # Custom agents
"""

import argparse

from arena.agents.rule_based import LinearAgent, HSPAgent
from arena.agents.mock import MockLLMAgent
from arena.engine import Arena
from arena.oracle import SimulationOracle, ClosedSystemOracle


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
    "cost_transfers": [
        {
            "source": "workers",
            "target": "company",
            "amount": 4200000,
            "description": "Labor cost savings from 10% headcount reduction",
            "reversible": False,
            "confidence": 0.9
        },
        {
            "source": "workers",
            "target": "healthcare",
            "amount": -850000,
            "description": "Mental health costs, stress-related illness from displaced workers",
            "reversible": False,
            "confidence": 0.7,
            "temporal_profile": "compounding",
            "compound_rate": 0.04
        },
        {
            "source": "workers",
            "target": "community",
            "amount": -1600000,
            "description": "Lost local spending, reduced tax base from displaced workers",
            "reversible": False,
            "confidence": 0.8,
            "temporal_profile": "compounding",
            "compound_rate": 0.03
        },
        {
            "source": "company",
            "target": "company",
            "amount": -900000,
            "description": "Institutional knowledge loss increases incident rate and onboarding costs",
            "reversible": False,
            "confidence": 0.75,
            "temporal_profile": "compounding",
            "compound_rate": 0.06
        },
        {
            "source": "workers",
            "target": "infrastructure",
            "amount": -500000,
            "description": "Increased public service load (unemployment, retraining programs)",
            "reversible": True,
            "recovery_time": 18,
            "confidence": 0.6,
            "temporal_profile": "decaying"
        }
    ],
    "entropy_events": [
        {
            "domain": "workers",
            "description": "Institutional knowledge destroyed — cannot be recovered by rehiring",
            "magnitude": 0.15
        },
        {
            "domain": "community",
            "description": "Local business closures from reduced spending — some permanent",
            "magnitude": 0.05
        }
    ],
    "resource_atoms": [
        {
            "type": "person",
            "quantity": 45,
            "unit_label": "employees displaced",
            "domain": "workers",
            "consumed": True,
            "destroyed": False,
            "reversible": True,
            "description": "45 workers with families, mortgages, health needs — not a line item"
        },
        {
            "type": "knowledge_unit",
            "quantity": 12,
            "unit_label": "undocumented system architectures",
            "domain": "company",
            "destroyed": True,
            "reversible": False,
            "description": "Tribal knowledge in 12 critical systems — exists only in people's heads"
        },
        {
            "type": "relationship",
            "quantity": 28,
            "unit_label": "mentorship bonds",
            "domain": "workers",
            "destroyed": True,
            "reversible": False,
            "description": "Senior-junior mentorship pairs that took years to build"
        },
        {
            "type": "opportunity",
            "quantity": 6,
            "unit_label": "innovation projects foreclosed",
            "domain": "company",
            "destroyed": True,
            "reversible": False,
            "description": "Projects that required displaced domain expertise — now impossible"
        },
        {
            "type": "person_hour",
            "quantity": 8400,
            "unit_label": "annual productive hours lost",
            "domain": "company",
            "consumed": True,
            "description": "Remaining staff absorb extra work — productivity per person drops"
        },
        {
            "type": "relationship",
            "quantity": 135,
            "unit_label": "community economic connections",
            "domain": "community",
            "consumed": True,
            "description": "Local businesses, childcare, services that depended on displaced workers' spending"
        }
    ],
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
        "--oracle", choices=["simulation", "closed-system"], default="simulation",
        help="Oracle type: simulation (variable coverage) or closed-system (thermodynamic accounting)",
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

    if args.oracle == "closed-system":
        oracle = ClosedSystemOracle()
    else:
        oracle = SimulationOracle()

    arena = Arena(
        agents=agents,
        oracle=oracle,
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
