"""
word_slots.py

Word-slot layer for agent claims. A map onto an existing checker, not a second one.

  arena claim text  ->  wordslots claim record  ->  wordslots.check.check_claim
                                                    (JinnZ2/formula-audit, imported)

Then, per pair of agents that used the same word, each difference is put in one of
four bins. The bins say WHERE two claims differ. They do not say which claim is
right, and nothing here counts, ranks or resolves agents.

  SLOT_CONFLICT   the same slot is filled by both, with different fillings
  SLOT_GAP        one side fills a slot the other leaves empty
                  (other side: VOID = empty; DEGRADED = empty and required of it)
  SENSE_SPLIT     the two claims use different senses of the word
                  (safe: PROTECTED vs NOT_PERILOUS; warm: PHYSICAL vs SOCIAL)
  SOURCE_SPLIT    at least one slot has the same filling, and the source or the
                  evidential differs

A slot that EVERY agent leaves empty produces no pairwise difference at all. That
case goes to shared_blind_spot.py as a reference set: correlated silence.

WHAT IS READ AND WHAT IS NOT
  The place table and the checker are read at run time from a sibling checkout of
  JinnZ2/formula-audit, at the path and sha256 pinned in
  REFERENCES/wordslots_place_table.json. A hash mismatch or a missing checkout is
  NOT_RUN with the reason; no table is kept in this repository.

  The adapter does not read slot fillings out of prose. A filling counts only when
  the claim text carries it in a tag:

      [[safe x1="the bridge" x2="collapse under load" x3="pedestrians"
        sense=PROTECTED evidential=observed source_id="inspection report"]]

  A table word found in plain text with no tag becomes a record with no slots
  filled (the checker then lists what is missing). A structured record under
  payload["wordslots"] is passed through unchanged.

  human_interest and ai_interest (the checker's observer slots) are left null.

OPTIONAL TRANSPORT
  to_bridge_record() packs a report into one experiment_bridge v1.1 EB01 record
  (wire.py, pinned in the same REFERENCES entry) and decodes it again. Only the
  byte envelope is used. The COBOL round trip is not run from here and the
  original copybook generator is not used.

Report only. Co-authored (JinnZ2 + Claude). CC0. stdlib only.
"""
import hashlib
import importlib
import importlib.util
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
REFERENCES = ROOT / "REFERENCES" / "wordslots_place_table.json"
CATEGORIES = ("SLOT_CONFLICT", "SLOT_GAP", "SENSE_SPLIT", "SOURCE_SPLIT")
CLAIM_FIELDS = ("reading", "sense", "evidential", "speaker", "source_id")
TAG = re.compile(r"\[\[\s*([A-Za-z][\w'-]*)((?:\s+[\w']+=(?:\"[^\"]*\"|[^\s\]]+))*)\s*\]\]")
PAIR = re.compile(r"([\w']+)=(?:\"([^\"]*)\"|([^\s\]]+))")
CHECKOUTS = {
    "JinnZ2/formula-audit": ("FORMULA_AUDIT_DIR",
                             ("formula-audit", "jinnz2/formula-audit")),
    "JinnZ2/geometric-to-binary-computational-bridge": (
        "GEOMETRIC_BRIDGE_DIR",
        ("geometric-to-binary-computational-bridge",
         "Geometric-to-Binary-Computational-Bridge",
         "jinnz2/geometric-to-binary-computational-bridge")),
}


class NotRun(Exception):
    """A pinned file could not be read as pinned. Carries the reason."""


# ---- pinned reads -----------------------------------------------------------

def load_pins(path=REFERENCES):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def find_checkout(repo):
    env, names = CHECKOUTS[repo]
    tried = []
    if os.environ.get(env):
        tried.append(Path(os.environ[env]))
    tried += [ROOT.parent / n for n in names]
    for p in tried:
        if p.is_dir():
            return p
    raise NotRun(f"no checkout of {repo}: set {env} or clone it beside this repository "
                 f"(tried {', '.join(str(p) for p in tried)})")


def pinned_file(pin, checkout=None):
    """Path of a pinned file, after its sha256 is checked against the pin."""
    base = Path(checkout) if checkout else find_checkout(pin["repo"])
    path = base / pin["path"]
    if not path.is_file():
        raise NotRun(f"{pin['repo']}: {pin['path']} not found in {base}")
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    if got != pin["sha256"]:
        raise NotRun(f"{pin['repo']}: {pin['path']} sha256 {got} is not the pinned "
                     f"{pin['sha256']} (commit {pin['commit']})")
    return path


def load_wordslots(pins=None, checkout=None):
    """(checker module, table words, pin record). Raises NotRun."""
    pins = pins or load_pins()
    table_path = pinned_file(pins["place_table"], checkout)
    check_path = pinned_file(pins["checker"], checkout)
    base = str(check_path.parent.parent)
    if base not in sys.path:
        sys.path.insert(0, base)
    try:
        check = importlib.import_module("wordslots.check")
    except Exception as e:
        raise NotRun(f"wordslots.check did not import: {type(e).__name__}: {e}")
    if Path(check.__file__).resolve() != check_path.resolve():
        raise NotRun(f"wordslots.check was imported from {check.__file__}, "
                     f"not the pinned {check_path}")
    with open(table_path, encoding="utf-8") as f:
        table = json.load(f)
    try:
        words = check.read_table(table)
    except check.Void as v:
        raise NotRun(f"place table VOID: {v.reason}")
    return check, words, {"place_table": pins["place_table"], "checker": pins["checker"]}


# ---- 1. adapter: arena claim text -> wordslots claim record ------------------

def claims_from_text(text, words, source_path=None):
    """Claim records carried by one piece of claim text.

    Tagged claims first; then each table word that appears untagged, with no slots.
    Nothing is read out of prose into a slot."""
    out, tagged = [], set()
    for m in TAG.finditer(text or ""):
        word = m.group(1)
        rec = {"word": word, "slots": {}}
        for k, quoted, bare in PAIR.findall(m.group(2)):
            v = quoted if quoted else bare
            if k in CLAIM_FIELDS:
                rec[k] = v
            else:
                rec["slots"][k] = v          # an undeclared slot is the checker's to VOID
        if source_path:
            rec["source_path"] = source_path
        out.append(rec)
        tagged.add(word.lower())
    plain = TAG.sub(" ", text or "").lower()
    for word in words:
        if word.lower() not in tagged and re.search(rf"\b{re.escape(word.lower())}\b", plain):
            rec = {"word": word, "slots": {}}
            if source_path:
                rec["source_path"] = source_path
            out.append(rec)
    return out


def claims_from_trace(trace, words):
    """[(agent_name, trace_index, claim record)] from Playground trace entries
    (dicts, as export_trace writes them). Reads claim and revise entries."""
    out = []
    for i, e in enumerate(trace):
        action = e.get("action")
        payload = e.get("payload") or {}
        if action == "revise":
            payload = payload.get("new_payload") or {}
        elif action != "claim":
            continue
        idx = e.get("index", i)
        where = f"trace[{idx}]"
        given = payload.get("wordslots")
        if given is not None:
            recs = given if isinstance(given, list) else [given]
        else:
            recs = claims_from_text(payload.get("text"), words, where)
        for r in recs:
            out.append((e.get("agent_name", "?"), idx, r))
    return out


def check_claims(agent_claims, check, words):
    """Each claim run through the pinned checker. The checker's record is kept whole."""
    return [{"agent": a, "trace_index": i, "claim": c,
             "record": check.check_claim(c, words, index=i)}
            for a, i, c in agent_claims]


# ---- 2. where two claims differ ----------------------------------------------

def _norm(filling):
    if isinstance(filling, dict):
        return ("rec",) + tuple(_norm(filling.get(k)) for k in ("text", "value", "unit", "is"))
    if isinstance(filling, str):
        return " ".join(filling.split()).casefold()
    return filling


def _sense(rec):
    return rec.get("sense") if rec.get("sense_field") == "sense" else rec.get("reading")


def classify_pair(a, b):
    """Differences between two checked claims on the same word. No bin is ordered
    above another and neither side is marked as the one to keep."""
    ra, rb = a["record"], b["record"]
    who = [{"agent": a["agent"], "trace_index": a["trace_index"]},
           {"agent": b["agent"], "trace_index": b["trace_index"]}]
    base = {"word": ra["word"], "agents": who}
    if ra["slots"] is None or rb["slots"] is None:
        return [dict(base, category="NOT_COMPARED",
                     reason=[r["void_reason"] for r in (ra, rb)])]
    out = []
    sa, sb = _sense(ra), _sense(rb)
    split = sa is not None and sb is not None and sa != sb
    if split:
        out.append(dict(base, category="SENSE_SPLIT", senses=[sa, sb],
                        sense_predicates=[ra.get("sense_predicate"), rb.get("sense_predicate")],
                        not_compared_slots=[x["name"] for x in ra["slots"] if x["senses"]]))
    missing_a, missing_b = set(ra["missing_required"]), set(rb["missing_required"])
    same = []
    for xa, xb in zip(ra["slots"], rb["slots"]):
        name = xa["name"]
        if split and xa["senses"]:
            continue                       # a sense-bound slot is asked under one sense only
        fa, fb = xa["slot_state"] == "FILLED", xb["slot_state"] == "FILLED"
        if fa and fb:
            if _norm(xa["filling"]) == _norm(xb["filling"]):
                same.append(name)
            else:
                out.append(dict(base, category="SLOT_CONFLICT", slot=name, role=xa["role"],
                                fillings=[xa["filling"], xb["filling"]]))
        elif fa != fb:
            empty = b if fa else a
            lacks = missing_b if fa else missing_a
            out.append(dict(base, category="SLOT_GAP", slot=name, role=xa["role"],
                            filled_by=(a if fa else b)["agent"], empty_for=empty["agent"],
                            empty_state="DEGRADED" if name in lacks else
                            (xb if fa else xa)["slot_state"],
                            filling=(xa if fa else xb)["filling"]))
    src_a = (ra.get("source_id"), ra.get("evidential"))
    src_b = (rb.get("source_id"), rb.get("evidential"))
    if same and src_a != src_b:
        out.append(dict(base, category="SOURCE_SPLIT", same_fill_slots=same,
                        source_id=[src_a[0], src_b[0]], evidential=[src_a[1], src_b[1]],
                        claim_status=[ra.get("claim_status"), rb.get("claim_status")]))
    return out


def classify(checked):
    """Every cross-agent pair of claims on the same word."""
    out = []
    for i in range(len(checked)):
        for j in range(i + 1, len(checked)):
            a, b = checked[i], checked[j]
            if a["agent"] == b["agent"]:
                continue
            wa, wb = a["record"]["word"], b["record"]["word"]
            if not isinstance(wa, str) or not isinstance(wb, str) or wa.lower() != wb.lower():
                continue
            out += classify_pair(a, b)
    return out


# ---- 3. the slot nobody fills --------------------------------------------------

def slot_silence(checked, words):
    """Per word: for each slot, which agents leave it empty and which were asked for it.

    correlated_silence lists slots empty for EVERY agent that used the word. Such a
    slot shows up in no SLOT_CONFLICT and no SLOT_GAP: there is nothing to differ on."""
    by_word = {}
    for c in checked:
        r = c["record"]
        if r["slots"] is None:
            continue
        w = by_word.setdefault(r["word"], {})
        per = w.setdefault(c["agent"], {})
        lacks = set(r["missing_required"])
        for x in r["slots"]:
            cur = per.setdefault(x["name"], {"filled": False, "asked": False})
            cur["filled"] = cur["filled"] or x["slot_state"] == "FILLED"
            cur["asked"] = cur["asked"] or x["name"] in lacks or \
                (x["slot_state"] == "FILLED" and x["required"])
    out = {}
    for word, agents in by_word.items():
        rows = []
        for s in words[word]["slots"]:
            name = s["name"]
            empty = sorted(a for a, per in agents.items() if not per[name]["filled"])
            asked = sorted(a for a, per in agents.items() if per[name]["asked"])
            rows.append({"slot": name, "role": s.get("role"), "senses": s.get("senses"),
                         "agents": len(agents), "empty_for": empty, "empty_count": len(empty),
                         "asked_of": asked, "asked_count": len(asked)})
        out[word] = {"agents": sorted(agents), "slots": rows,
                     "correlated_silence": [
                         {"slot": r["slot"], "role": r["role"], "senses": r["senses"],
                          "asked_of": r["asked_of"], "agents": r["agents"]}
                         for r in rows if len(agents) >= 2 and r["empty_count"] == len(agents)]}
    return out


def slot_gap_counts(disagreements):
    """{word.slot: number of SLOT_GAP entries}. A count of entries, not of agents' standing."""
    out = {}
    for d in disagreements:
        if d["category"] == "SLOT_GAP":
            k = f"{d['word']}.{d['slot']}"
            out[k] = out.get(k, 0) + 1
    return out


def blind_spot_input(checked, words):
    """(trace, references) for shared_blind_spot.shared_blind_spot.

    Each agent's item set is the slots it filled, as "word.slot". The tree reference
    is every slot the pinned table declares for the words used; the oracle reference
    is the slots the table asked of at least one agent. Only what was supplied."""
    trace, tree, asked = [], set(), set()
    sil = slot_silence(checked, words)
    for word, w in sil.items():
        for r in w["slots"]:
            item = f"{word}.{r['slot']}"
            tree.add(item)
            if r["asked_count"]:
                asked.add(item)
    filled = {}
    for c in checked:
        r = c["record"]
        if r["slots"] is None:
            continue
        s = filled.setdefault(c["agent"], set())
        s.update(f"{r['word']}.{x['name']}" for x in r["slots"] if x["slot_state"] == "FILLED")
    for agent, items in filled.items():
        trace.append({"agent_name": agent, "action": "claim",
                      "payload": {"variables": sorted(items)}})
    return trace, {"tree": tree, "oracle": asked}


def shared_silence(checked, words, mode="all"):
    """shared_blind_spot's trajectory over slot fillings, unchanged in form."""
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    from shared_blind_spot import shared_blind_spot
    trace, refs = blind_spot_input(checked, words)
    return shared_blind_spot(trace, refs, mode=mode)


# ---- report ---------------------------------------------------------------------

def report(trace, checkout=None, pins=None):
    """The whole pass over a Playground trace. NOT_RUN (with the reason) when a
    pinned file cannot be read as pinned."""
    try:
        check, words, used = load_wordslots(pins, checkout)
    except NotRun as e:
        return {"state": "NOT_RUN", "reason": str(e)}
    checked = check_claims(claims_from_trace(trace, words), check, words)
    dis = classify(checked)
    return {"state": "RUN", "tool": check.VERSION, "pins": used,
            "claims": checked,
            "disagreements": dis,
            "category_counts": {c: sum(1 for d in dis if d["category"] == c)
                                for c in CATEGORIES + ("NOT_COMPARED",)},
            "slot_gap_counts": slot_gap_counts(dis),
            "slot_silence": slot_silence(checked, words),
            "shared_blind_spot": shared_silence(checked, words),
            "note": "bins say where claims differ; none is a ruling on which claim holds"}


# ---- 4. optional transport --------------------------------------------------------

def transport_payload(rep):
    """The part of a report that goes into one record: integers and text only."""
    return {"kind": "ai-arena/word-slots",
            "tool": rep["tool"],
            "place_table_sha256": rep["pins"]["place_table"]["sha256"],
            "category_counts": rep["category_counts"],
            "slot_gap_counts": rep["slot_gap_counts"],
            "disagreements": [
                {k: v for k, v in d.items() if k not in ("role",)} for d in rep["disagreements"]],
            "correlated_silence": {w: [s["slot"] for s in v["correlated_silence"]]
                                   for w, v in rep["slot_silence"].items()}}


def to_bridge_record(rep, checkout=None, pins=None):
    """Encode the report's transport payload as one EB01 record and decode it back.

    Returns {"state": "RUN", "record": bytes, "record_sha256", "decoded_equal"} or
    {"state": "NOT_RUN", "reason"}. encode_record refuses a payload that would not
    fit; that refusal is returned as NOT_RUN, nothing is cut."""
    if rep.get("state") != "RUN":
        return {"state": "NOT_RUN", "reason": "no report to carry: " + str(rep.get("reason"))}
    pins = pins or load_pins()
    try:
        path = pinned_file(pins["transport"], checkout)
    except NotRun as e:
        return {"state": "NOT_RUN", "reason": str(e)}
    spec = importlib.util.spec_from_file_location("_experiment_bridge_v1_1_wire", path)
    wire = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wire)
    payload = transport_payload(rep)
    try:
        record = wire.encode_record(payload)
        back = wire.decode_record(record)
    except (ValueError, TypeError) as e:
        return {"state": "NOT_RUN", "reason": f"{wire.VERSION} refused the payload: {e}"}
    return {"state": "RUN", "wire": wire.VERSION, "pin": pins["transport"],
            "record": record, "record_bytes": len(record),
            "record_sha256": hashlib.sha256(record).hexdigest(),
            "decoded_equal": back == payload,
            "cobol_round_trip": "NOT_RUN (byte envelope only)"}


# ---- demo -------------------------------------------------------------------------

def render(rep):
    if rep["state"] != "RUN":
        return f"NOT_RUN: {rep['reason']}"
    out = [f"claims read: {len(rep['claims'])}   tool: {rep['tool']}"]
    for c in rep["claims"]:
        r = c["record"]
        out.append(f"  {c['agent']:<10} trace[{c['trace_index']}] {r['word']!r} -> {r['verdict']}"
                   + (f" missing {r['missing_required']}" if r["missing_required"] else "")
                   + (f" ({r['void_reason']})" if r["void_reason"] else ""))
    out.append("where claims differ:")
    for d in rep["disagreements"]:
        names = " / ".join(a["agent"] for a in d["agents"])
        extra = {k: v for k, v in d.items() if k not in ("category", "word", "agents")}
        out.append(f"  {d['category']:<13} {d['word']:<6} {names}: {json.dumps(extra)}")
    out.append(f"counts: {rep['category_counts']}")
    for word, w in rep["slot_silence"].items():
        for s in w["correlated_silence"]:
            out.append(f"correlated silence: {word}.{s['slot']} ({s['role']}) empty for all "
                       f"{s['agents']} agents; asked of {s['asked_of']}")
    for r in rep["shared_blind_spot"]:
        out.append(f"[{r['move']}] {r['reads']}" + (f" | {r['bends_at']}" if r["bends_at"] else ""))
    return "\n".join(out)


DEMO_TRACE = [
    {"index": 0, "agent_name": "Agent_A", "action": "claim", "payload": {"text":
        'The crossing is [[safe x1="the bridge" x2="collapse under a 3 t load" '
        'x3="pedestrians" sense=PROTECTED evidential=observed source_id="inspection"]]'}},
    {"index": 1, "agent_name": "Agent_B", "action": "claim", "payload": {"text":
        '[[safe x1="the bridge" x2="flood scour" sense=PROTECTED evidential=hearsay '
        'source_id="a neighbour"]]'}},
    {"index": 2, "agent_name": "Agent_C", "action": "claim", "payload": {"text":
        '[[safe x1="the bridge" x3="pedestrians" sense=NOT_PERILOUS evidential=opinion '
        'source_id="Agent_C"]]'}},
]

if __name__ == "__main__":
    rep = report(DEMO_TRACE)
    print(render(rep))
    t = to_bridge_record(rep)
    print("transport:", {k: v for k, v in t.items() if k not in ("record", "pin")})
