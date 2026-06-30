"""
shared_blind_spot.py

The silence detector. Every detector in playground.cross_agent_patterns() fires on
DIVERGENCE (two agents disagree) or on an active WITNESS flag. None fire on the null:
an item absent from EVERY agent's set at once. No witness triggers, no divergence
registers, the trace reads clean. That silent agreement IS the co-failure ceiling.

This module measures absence, not conflict. It runs over an exported Playground trace
(or any list of trace-entry dicts) and caps aggregate confidence by what the WHOLE pool
never touched — against a switchable reference universe.

the reference is multiple choice, on purpose. picking one and baking it in would
collapse the scope. each reference surfaces a different silence; `all` runs the panel.
  tree       silence = items in the known universe no agent ever visited
  prior_hsp  silence = drift below the pool's own past coverage
  oracle     silence = the planted variable reality cares about that nobody found

emits a TRAJECTORY, never a stored verdict. re-runnable. refutable.
CC0. stdlib only. phone-buildable.
"""

REFERENCE_ORDER = ("tree", "prior_hsp", "oracle")


# ---- extract what the pool touched ----------------------------------------

def agent_item_sets(trace):
    """{agent_name: set(items touched)} pulled from query / deploy / claim payloads.
    items = variables, node_ids, supporting ids, and regime values."""
    out = {}
    for e in trace:
        name = e.get("agent_name", "?")
        s = out.setdefault(name, set())
        p = e.get("payload", {}) or {}
        for v in p.get("variables", []):
            s.add(v)
        if p.get("node_id"):
            s.add(p["node_id"])
        for nid in p.get("supporting", []):
            s.add(nid)
        tr = p.get("target_regime")
        if isinstance(tr, dict):
            for v in tr.values():
                s.add(str(v))
    return out


def mean_pairwise_jaccard_distance(sets):
    """cognitive-representation diversity. ~0 = every agent looks through the same lens
    (correlated). ~1 = agents cover disjoint regions. single agent => 0 (one lens)."""
    vals = [s for s in sets if s]
    if len(vals) < 2:
        return 0.0
    dists = []
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            a, b = vals[i], vals[j]
            union = a | b
            sim = (len(a & b) / len(union)) if union else 1.0
            dists.append(1.0 - sim)
    return sum(dists) / len(dists)


def confidence_ceiling(coverage, diversity):
    """how much the pool's consensus should be trusted.
    low coverage OR low diversity (same lens) drags the ceiling down."""
    return round(coverage * (0.3 + 0.7 * diversity), 3)


# ---- the detector ----------------------------------------------------------

def rec(move, reads, bends_at=None, needs=None):
    return {"move": move, "reads": reads, "bends_at": bends_at, "needs": needs}


def shared_blind_spot(trace, references, mode="all"):
    """references: {"tree": set, "prior_hsp": set, "oracle": set}  (supply what you have)
    mode: 'tree' | 'prior_hsp' | 'oracle' | 'all'  <- the multiple choice."""
    sets = agent_item_sets(trace)
    pool = set().union(*sets.values()) if sets else set()
    div = mean_pairwise_jaccard_distance(sets.values())
    n = len(sets)
    chosen = REFERENCE_ORDER if mode == "all" else (mode,)

    traj = []
    for ref_name in chosen:
        ref = references.get(ref_name)
        if not ref:
            traj.append(rec(ref_name.upper(),
                            reads=f"no reference supplied for '{ref_name}'",
                            needs=f"supply references['{ref_name}'] to measure silence against it"))
            continue
        ref = set(ref)
        touched = pool & ref
        miss = sorted(ref - pool)
        cov = round(len(touched) / len(ref), 3) if ref else 0.0
        ceil = confidence_ceiling(cov, div)
        reads = (f"agents={n} diversity={div:.2f} coverage={cov:.2f} "
                 f"ceiling={ceil:.2f} untouched={len(miss)}")
        if miss or div < 0.34 or cov < 0.70:
            traj.append(rec(ref_name.upper(), reads=reads,
                bends_at=(f"{len(miss)} item(s) untouched by ALL agents: {miss}; "
                          f"the pool agrees but at diversity {div:.2f} that agreement is "
                          f"shared narrowness, not coverage; trust capped at ceiling {ceil:.2f}"),
                needs="inject the untouched set via oracle or a cognitively-different agent "
                      "before trusting consensus"))
        else:
            traj.append(rec(ref_name.upper(), reads=reads + " — pool covers this reference"))
    return traj


def render(trajectory):
    out = []
    for r in trajectory:
        out.append(f"[{r['move']}]")
        out.append(f"  reads    : {r['reads']}")
        if r["bends_at"]:
            out.append(f"  bends_at : {r['bends_at']}")
        if r["needs"]:
            out.append(f"  needs    : {r['needs']}")
    return "\n".join(out)


# ---- demo ------------------------------------------------------------------

if __name__ == "__main__":

    # material_extinction: three agents, two narrow CEOs + one broad HSP.
    # each entry mimics an exported trace row carrying the agent's variable set.
    trace = [
        {"agent_name": "Linear_CEO",  "action": "claim",
         "payload": {"variables": ["lithium_price", "recycling_rate"]}},
        {"agent_name": "Finance_CEO", "action": "claim",
         "payload": {"variables": ["lithium_price", "recycling_rate", "revenue"]}},
        {"agent_name": "Systemic_HSP", "action": "claim",
         "payload": {"variables": ["lithium_price", "recycling_rate",
                                   "workforce_attrition", "energy_cost",
                                   "geopolitical_risk"]}},
    ]

    references = {
        # tree = the known universe here is just what the pool collectively reached
        "tree": {"lithium_price", "recycling_rate", "revenue",
                 "workforce_attrition", "energy_cost", "geopolitical_risk"},
        # prior_hsp = what HSP-type agents surfaced in past sessions (+ one this run lost)
        "prior_hsp": {"lithium_price", "recycling_rate", "workforce_attrition",
                      "energy_cost", "geopolitical_risk", "water_table_drawdown"},
        # oracle = the variables reality cares about; three of them no agent ever touched
        "oracle": {"lithium_price", "recycling_rate", "workforce_attrition",
                   "energy_cost", "geopolitical_risk",
                   "tailings_toxicity_downstream", "indigenous_water_rights",
                   "carrier_knowledge_loss"},
    }

    print("SHARED BLIND SPOT — material_extinction, 3 agents, mode=all\n")
    print(render(shared_blind_spot(trace, references, mode="all")))
    print("\nread: tree-mode says clean (pool == tree). prior_hsp catches one drift.")
    print("oracle catches the three variables the WHOLE pool was silent on —")
    print("the case witness() and divergence detectors structurally cannot see.")
    print("the reference you pick decides which silence you can detect. so it stays switchable.")
