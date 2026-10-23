#!/usr/bin/env python3
"""
Fee-Trap Finder - evaluation harness (v1)

Grades one card's extractor output against the golden-set answer key.

Metrics
-------
recall        : of the golden fees, how many the extractor found      (misses hurt)
precision     : of the fees the extractor reported, how many are real  (inventions hurt)
groundedness  : of the reported fees, how many have ALL source quotes
                appearing verbatim in the agreement text               (fabrication hurts)
severity_match: of the matched fees, how many have the same severity
                as the golden key (a deterministic slice of field accuracy)

Notes
-----
- Fees are matched between output and key by a normalized fee name.
- Groundedness is checked against the DOCUMENT (agreement text), not the key,
  per the locked source_quote rule. Whitespace is normalized so PDF line
  breaks do not cause false misses.
- Full field accuracy (trigger / warning wording) needs an LLM-as-judge and is
  NOT scored here; only the deterministic severity slice is. The script prints
  a clear note where the judge would take over.
"""

import json, re, sys, argparse


# ---------- helpers ----------

def norm_name(s):
    """Normalize a fee name for matching across output and key."""
    s = s.lower().strip()
    # unify APR spellings
    s = s.replace("annual percentage rate", "apr")
    s = re.sub(r"\(apr\)", "", s)          # drop a literal "(apr)"
    s = re.sub(r"[^a-z0-9 ]", " ", s)       # punctuation -> space
    s = re.sub(r"\s+", " ", s).strip()
    return s

def norm_text(s):
    """Normalize free text / quotes for verbatim comparison: collapse whitespace."""
    return re.sub(r"\s+", " ", s).strip().lower()

def fee_name(fee):
    return fee["fee_name"]["value"] if isinstance(fee["fee_name"], dict) else fee["fee_name"]


# ---------- the four checks ----------

def quotes_of(fee):
    qs = fee.get("source_quote", {}).get("quotes", []) or []
    return [norm_text(q) for q in qs if q.strip()]

def shared_quote(a, b, min_phrase=45):
    """True if a and b cite the same clause: either one quote contains the other,
    or they share a long common verbatim phrase (>= min_phrase chars)."""
    import difflib
    qa_list, qb_list = quotes_of(a), quotes_of(b)
    for qa in qa_list:
        for qb in qb_list:
            if not qa or not qb:
                continue
            if qa in qb or qb in qa:
                return True
            m = difflib.SequenceMatcher(None, qa, qb).find_longest_match(0, len(qa), 0, len(qb))
            if m.size >= min_phrase:
                return True
    return False

def name_sim(a, b):
    import difflib
    return difflib.SequenceMatcher(None, norm_name(fee_name(a)), norm_name(fee_name(b))).ratio()

def match_fees(gold_fees, out_fees, name_threshold=0.70):
    """Match golden and output fees by (1) exact normalized name, then
    (2) a shared source quote, then (3) high name similarity. Greedy, one-to-one.
    Returns (matched_pairs, missed_gold, invented_out)."""
    gold_left = list(gold_fees)
    out_left  = list(out_fees)
    matched = []

    def take(g, o):
        matched.append((g, o))
        gold_left.remove(g)
        out_left.remove(o)

    # pass 1: exact normalized name
    for g in list(gold_left):
        for o in list(out_left):
            if norm_name(fee_name(g)) == norm_name(fee_name(o)):
                take(g, o); break

    # pass 2: shared source quote (two records citing the same clause = same fee)
    for g in list(gold_left):
        for o in list(out_left):
            if shared_quote(g, o):
                take(g, o); break

    # pass 3: high name similarity
    for g in list(gold_left):
        best, best_s = None, 0.0
        for o in list(out_left):
            s = name_sim(g, o)
            if s > best_s:
                best, best_s = o, s
        if best is not None and best_s >= name_threshold:
            take(g, best)

    return matched, gold_left, out_left

def check_groundedness(out_fees, doc_text):
    """A reported fee passes if EVERY source quote appears verbatim in the doc.
    Returns (passed_fees, failed_detail)."""
    ndoc = norm_text(doc_text)
    passed, failed = [], []
    for f in out_fees:
        quotes = f.get("source_quote", {}).get("quotes", []) or []
        bad = [q for q in quotes if norm_text(q) not in ndoc]
        if bad:
            failed.append((fee_name(f), bad))
        else:
            passed.append(fee_name(f))
    return passed, failed

def severity_of(fee):
    return (fee.get("severity") or "").lower()


# ---------- scoring ----------

def score_card(gold_card, out_fees, doc_text):
    gold_fees = gold_card["fees"]
    matched, missed, invented = match_fees(gold_fees, out_fees)

    n_gold, n_out, n_match = len(gold_fees), len(out_fees), len(matched)
    recall    = n_match / n_gold if n_gold else 0.0
    precision = n_match / n_out  if n_out  else 0.0

    passed_g, failed_g = check_groundedness(out_fees, doc_text)
    groundedness = len(passed_g) / n_out if n_out else 0.0

    sev_hits = [(fee_name(g), severity_of(g), severity_of(o))
                for g, o in matched]
    sev_agree = sum(1 for _, gs, os in sev_hits if gs == os)
    severity_match = sev_agree / n_match if n_match else 0.0

    return {
        "card": gold_card.get("issuer", gold_card.get("card_id")),
        "counts": {"golden": n_gold, "reported": n_out, "matched": n_match},
        "recall": recall, "precision": precision,
        "groundedness": groundedness, "severity_match": severity_match,
        "missed": [fee_name(f) for f in missed],
        "invented": [fee_name(f) for f in invented],
        "groundedness_failures": failed_g,
        "severity_disagreements": [(nm, gs, os) for nm, gs, os in sev_hits if gs != os],
    }


# ---------- report ----------

def pct(x): return f"{100*x:5.1f}%"

def print_report(r):
    c = r["counts"]
    print("=" * 64)
    print(f"CARD: {r['card']}")
    print("=" * 64)
    print(f"  fees in key: {c['golden']}   reported: {c['reported']}   matched: {c['matched']}")
    print("-" * 64)
    print(f"  recall         {pct(r['recall'])}   (of {c['golden']} real fees, {c['matched']} found)")
    print(f"  precision      {pct(r['precision'])}   (of {c['reported']} reported, {c['matched']} real)")
    print(f"  groundedness   {pct(r['groundedness'])}   (reported fees whose every quote is verbatim)")
    print(f"  severity match {pct(r['severity_match'])}   (matched fees with the same severity as key)")
    print("-" * 64)
    print(f"  MISSED (recall gaps)   : {r['missed'] or 'none'}")
    print(f"  INVENTED (precision)   : {r['invented'] or 'none'}")
    if r["groundedness_failures"]:
        print("  GROUNDEDNESS FAILURES  :")
        for nm, bad in r["groundedness_failures"]:
            print(f"     - {nm}: {len(bad)} quote(s) not found verbatim")
            for q in bad:
                print(f"         ! {q[:90]}{'...' if len(q) > 90 else ''}")
    else:
        print("  GROUNDEDNESS FAILURES  : none")
    if r["severity_disagreements"]:
        print("  SEVERITY DISAGREEMENTS :")
        for nm, gs, os in r["severity_disagreements"]:
            print(f"     - {nm}: key={gs}  output={os}")
    else:
        print("  SEVERITY DISAGREEMENTS : none")
    print("-" * 64)
    print("  NOTE: trigger/warning field accuracy is NOT scored here;")
    print("        that check requires an LLM-as-judge (next build step).")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True)
    ap.add_argument("--card", required=True, help="card_id in the golden set")
    ap.add_argument("--output", required=True, help="extractor output JSON (array of fees)")
    ap.add_argument("--doc", required=True, help="agreement text file")
    args = ap.parse_args()

    gold = json.load(open(args.golden))
    card = next((c for c in gold["cards"] if c["card_id"] == args.card), None)
    if card is None:
        sys.exit(f"card '{args.card}' not found in golden set")
    out_fees = json.load(open(args.output))
    doc_text = open(args.doc, encoding="utf-8", errors="ignore").read()

    r = score_card(card, out_fees, doc_text)
    print_report(r)


if __name__ == "__main__":
    main()
