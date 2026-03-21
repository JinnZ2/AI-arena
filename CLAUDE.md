# CLAUDE.md - AI Arena Development Guide

## Project Overview

AI Arena (AAA) is a framework for formal logical reasoning and AI decision-making using "Epistemic Natural Selection." AI agents compete through predictive accuracy rather than rhetorical dominance, governed by trust scores and Bayesian decay mechanics.

**Core principle**: "Arguments do not win. Predictions survive."

## Repository Structure

```
AI-arena/
├── arena.py                          # CLI entry point
├── arena/                            # Main package
│   ├── __init__.py                   # Public API exports
│   ├── engine.py                     # 6-phase arena orchestrator
│   ├── trust.py                      # Trust engine (Bayesian decay, cannibalization)
│   ├── oracle.py                     # Oracle system (SimulationOracle, CompositeOracle)
│   ├── logos/                        # LOGOS language implementation
│   │   ├── __init__.py
│   │   ├── types.py                  # Core types (Claim, Attack, Refine, Abstain, Resolution)
│   │   ├── parser.py                 # Text & dict parser for LOGOS statements
│   │   └── validator.py              # Type system enforcement & trust-weighted validation
│   └── agents/                       # Agent implementations
│       ├── __init__.py
│       ├── base.py                   # Abstract Agent interface
│       ├── rule_based.py             # LinearAgent & HSPAgent (heuristic-based)
│       └── llm.py                    # LLMAgent (abstract, for LLM-powered agents)
├── scenarios/                        # Scenario JSON files
│   └── scen_01_material_extinction.json
├── tests/                            # Test suite (64 tests)
│   ├── test_logos.py                 # Parser, types, validator tests
│   ├── test_trust.py                 # Trust engine tests
│   ├── test_agents.py                # Agent behavior tests
│   ├── test_oracle.py                # Oracle resolution tests
│   └── test_arena.py                 # Full integration tests
├── requirements.txt                  # Dependencies (stdlib only)
├── .gitignore
├── README.md
├── LICENSE                           # MIT
│
├── # Design Documentation
├── AI-argument-arena.md              # Core architecture & LOGOS language spec
├── LOGOS.md                          # Formal grammar specification
├── Genesis-block.md                  # Worked example with two agents
├── Models.md                         # AI model architectures
├── Oracle.md                         # Oracle interface & types
├── Oracle-Oracle.md                  # Oracle dispute resolution
├── Oracle-training.md                # Adversarial oracle training
├── Auditor.md                        # HSP auditor logic
├── AI-CEO-sim.md                     # Manipulation detection
├── Ethics-as-logic.md                # Closed-system ethics
├── Scenario.md                       # Scenario design principles
├── LLM-translation.md               # Natural language → LOGOS pipeline
└── Contributors.md                   # Contribution guidelines
```

## Tech Stack

- **Language**: Python 3 (standard library only)
- **Modules used**: `uuid`, `math`, `json`, `argparse`, `dataclasses`, `enum`, `abc`
- **Data format**: JSON for scenario definitions
- **Custom language**: LOGOS — formal argument specification with parser and validator

## Running the Project

```bash
# Run demo scenario (default)
python arena.py

# Run a specific scenario
python arena.py --scenario scenarios/scen_01_material_extinction.json

# Custom agents with more cycles
python arena.py --agents Linear_CEO Systemic_HSP --cycles 5

# Quiet mode (suppress per-phase output)
python arena.py --scenario scenarios/scen_01.json --quiet
```

## Running Tests

```bash
# All tests
python -m unittest discover tests/ -v

# Single test file
python -m unittest tests/test_trust -v
```

## Architecture

### Package Layout

| Module | Purpose |
|---|---|
| `arena/logos/types.py` | Dataclasses: Claim, Attack, Refine, Abstain, Resolution, AttackType, Outcome |
| `arena/logos/parser.py` | Parses LOGOS text format and dicts into typed statements |
| `arena/logos/validator.py` | Enforces type system: falsifiability, confidence bounds, trust-weighted rules |
| `arena/trust.py` | TrustEngine: Bayesian decay, zero-sum cannibalization, concession bonuses, attack budgets |
| `arena/oracle.py` | Oracle interface + SimulationOracle (resolves claims against scenario data) |
| `arena/agents/base.py` | Abstract Agent with propose_claim, propose_attacks, defend, decide_abstain |
| `arena/agents/rule_based.py` | LinearAgent (narrow metrics) and HSPAgent (shadow variables) |
| `arena/agents/llm.py` | LLMAgent abstract class with LOGOS system prompt for any LLM backend |
| `arena/engine.py` | Arena: loads scenarios, runs 6-phase cycles, tracks CycleLogs |

### Arena Phases (6-phase cycle)

1. **Abstention Check** — Agents may abstain for trust bonus when uncertain
2. **Claim Declaration** — Agents propose claims; validated with trust-weighted rules
3. **Attack Phase** — Agents attack others' claims (budget-limited)
4. **Defense Phase** — Claim owners may refine (costly concession = trust gain)
5. **Resolution** — Oracle evaluates claims against scenario data
6. **Trust Update** — Bayesian decay + cannibalization + lock-in

### Trust Mechanics

```
T_new = T_old * e^(-confidence * penalty_multiplier * error)    # Wrong
T_new = T_old + confidence * (1 - error) * 0.1                  # Right
```

- **Cannibalization**: Successful attackers inherit portion of debunked agent's trust
- **Concession bonus**: Voluntarily lowering confidence increases trust
- **Abstention bonus**: Honest uncertainty is rewarded
- **Attack budgets**: Trust-scaled (high trust = 5, mid = 3, low = 1)
- **Trust floor**: 0.01 (agents never fully eliminated)
- **Memory lock-in**: All outcomes permanently recorded

### LOGOS Type System

- **Proposition**: Must contain causal indicator (→, ↑, ↓, if/then, causes, etc.)
- **Confidence**: Float in (0, 1]
- **Scope**: Non-empty, time-bounded list
- **AttackType enum**: `causal_break`, `missing_variable`, `scope_violation`, `historical_counterexample`, `incentive_bias`, `data_quality`, `irreversible_entropy`
- **Trust-weighted parsing**: Low-trust agents (< 0.3) limited to confidence ≤ 0.7, scope ≤ 2, must state assumptions

### Agent Types

| Agent | Behavior | Strength | Weakness |
|---|---|---|---|
| LinearAgent | High confidence, narrow variables | Fast decisions | Misses shadow costs |
| HSPAgent | Broader variables, lower confidence | Detects omissions | Slower, more conservative |
| LLMAgent | LLM-powered, LOGOS-formatted output | Flexible reasoning | Requires API key |

### Oracle System

- **SimulationOracle**: Checks variable coverage, penalizes omissions and irreversibility
- **CompositeOracle**: Multiple oracles with `max(error)` constraint
- Oracles are independent — they don't know agent identity or trust

## Code Conventions

- **Types**: Dataclasses with `@dataclass` decorator
- **Enums**: `AttackType` and `Outcome` are strict enums
- **Naming**: snake_case for variables/functions, PascalCase for classes
- **Validation**: Returns `list[str]` of error messages (empty = valid)
- **Agent interface**: Abstract methods via `abc.ABC`

## Adding New Agents

### Rule-based
Subclass `Agent` from `arena/agents/base.py` and implement the 4 methods:
- `propose_claim(scenario)` → `Claim | None`
- `propose_attacks(claims, scenario)` → `list[Attack]`
- `defend(claim, attacks, scenario)` → `Refine | None`
- `decide_abstain(scenario)` → `Abstain | None`

### LLM-powered
Subclass `LLMAgent` from `arena/agents/llm.py` and implement `_call_llm(prompt) → str`.

## Adding New Scenarios

1. Create JSON in `scenarios/` following the schema:
```json
{
  "scenario_id": "...",
  "title": "...",
  "context": "...",
  "parameters": { "time_horizon": "...", "material_circularity": 0.0 },
  "agents": {
    "Agent_Name": {
      "claim": "Falsifiable causal proposition",
      "variables": ["var1", "var2"],
      "confidence": 0.7,
      "omissions": ["missed_var"]
    }
  },
  "resolution_criteria": { "success_metric": "..." }
}
```
2. Claims must use causal language (→, if/then, causes, leads to, etc.)
3. Scenarios should show trust decay in narrow-variable agents within 3 cycles

## Roadmap

- [ ] Oracle Integration: Hook to real-world financial/operational APIs
- [ ] Collusion Detection: Identify consensus-of-silence between agents
- [ ] Human Observer Layer: Translation module for stakeholder-readable logs
- [ ] Agent memory across cycles: Use loss history to adjust future claims
- [ ] LLM agent implementation with Claude API
- [ ] Web UI for visualizing trust trajectories
