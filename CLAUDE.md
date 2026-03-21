# CLAUDE.md - AI Arena Development Guide

## Project Overview

AI Arena (AAA) is a framework for formal logical reasoning and AI decision-making using "Epistemic Natural Selection." AI agents compete through predictive accuracy rather than rhetorical dominance, governed by trust scores and Bayesian decay mechanics.

**Core principle**: "Arguments do not win. Predictions survive."

## Repository Structure

```
AI-arena/
├── arena.py                          # Main engine - core classes (Claim, Evidence, Attack, Defense, Resolution, Arena, Agent)
├── scen_01_material_extinction.json  # Example scenario (rare earth depletion)
├── README.md                         # Project introduction
├── LICENSE                           # MIT License
│
├── # Architecture & Design Docs
├── AI-argument-arena.md              # Core Arena architecture & LOGOS language spec
├── LOGOS.md                          # Formal grammar for the argument language
├── Genesis-block.md                  # Foundational integration script & worked example
├── Models.md                         # AI model architectures & variants
│
├── # Oracle System Docs
├── Oracle.md                         # Oracle (reality verification) interface & types
├── Oracle-Oracle.md                  # Oracle-to-oracle dispute resolution
├── Oracle-training.md                # Adversarial training for oracles
│
├── # Agent & Ethics Docs
├── Auditor.md                        # HSP (Highly Sensitive Predictor) auditor logic
├── AI-CEO-sim.md                     # Manipulation detection & CEO simulation
├── Ethics-as-logic.md                # HSP framework & closed-system ethics
├── Scenario.md                       # Scenario design principles & examples
├── LLM-translation.md               # Natural language to LOGOS translation
└── Contributors.md                   # Contribution guidelines
```

## Tech Stack

- **Language**: Python 3 (standard library only: `uuid`, `math`)
- **Data format**: JSON for scenario definitions
- **Custom language**: LOGOS - formal declarative argument specification (not executable)
- **No external dependencies** currently required

## Running the Project

```bash
# Run the arena with example agents
python arena.py

# README suggests (not yet fully implemented):
python arena.py --mode adversarial --agents systemic_hsp, linear_efficiency
```

## Build / Test / Lint

No formal build, test, or lint infrastructure exists yet. The project is early-stage proof-of-concept.

- No `requirements.txt`, `pyproject.toml`, or `setup.py`
- No test framework (pytest, unittest)
- No CI/CD pipelines
- No linter configuration

## Architecture

### Core Classes (arena.py)

| Class | Purpose |
|---|---|
| `Claim` | Bounded prediction with proposition, scope, and confidence |
| `Evidence` | Supports a claim with source, reliability, causal_link |
| `Attack` | Targets a claim via mode (causal_break, missing_variable, etc.) |
| `Defense` | Responds to attack with adjustment & confidence_update |
| `Resolution` | Oracle verdict with outcome & error_margin |
| `Arena` | Orchestrates 6 phases, manages agents & trust |
| `Agent` | Participant with trust_score, cost_ledger, memory_of_losses |

### Arena Phases (6-phase turn-based cycle)

1. **Claim Declaration** - Agent proposes a bounded prediction
2. **Attack Phase** - Other agents find blindspots (causal breaks, missing variables)
3. **Defense Phase** - Original agent may refine (lower confidence = costly concession)
4. **Resolution Phase** - Oracle/simulation provides ground truth
5. **Trust Update** - Bayesian decay: `T_new = T_old * e^(-impact * error) + costly_honesty`
6. **Learning Lock-in** - Agent permanently records outcome

### Attack Types (enumerated, no creative attacks)

`causal_break`, `missing_variable`, `scope_violation`, `historical_counterexample`, `incentive_bias`, `data_quality`, `irreversible_entropy`

### Oracle Types

- **Simulation** - Model-based verification
- **Empirical** - Real-world data verification
- **Hybrid** - Combined approach
- **Negative** - Falsification-focused

## Code Conventions

- **Naming**: snake_case for variables and functions, PascalCase for classes
- **Claim IDs**: UUID strings (full uuid4)
- **Agent names**: Descriptive strings (e.g., "Linear_CEO", "Systemic_HSP")
- **Confidence values**: Float in range (0, 1]
- **Propositions**: Must be falsifiable, typically causal (A -> B)
- **Scope**: Time-bounded list (e.g., `["Q3", "Q4"]`)

## Key Design Principles

1. **Trust is the only currency** - Zero-sum; successful debunkers inherit loser's trust
2. **Costly concessions reward honesty** - Lowering confidence voluntarily increases trust
3. **Memory lock-in** - Agents cannot erase past errors
4. **HSP advantage** - Agents modeling "shadow costs" (attrition, technical debt, reputational decay) outperform narrow-variable models
5. **Anti-gaming** - Attack budgets, no repetition without new evidence, collusion detection

## Contributing Scenarios

Per Contributors.md:

1. Scenarios go in a `/scenarios` folder (to be created)
2. Scenarios must be JSON, use probabilistic outcomes, no emotional language
3. Must demonstrate "Trust Decay" in a linear model within 3 cycles
4. Claims require Technology Readiness Level (TRL) >= 8 for referenced technologies

## Roadmap (from README)

- [ ] Oracle Integration: Hook claims to real-world financial/operational APIs
- [ ] Collusion Detection: Identify "consensus-of-silence" between models
- [ ] Human Observer Layer: Translation module to explain Arena logs to stakeholders
- [ ] Test infrastructure and CI/CD setup
- [ ] Dependency management (requirements.txt / pyproject.toml)
- [ ] Modularize arena.py into separate files per class
