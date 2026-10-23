#!/usr/bin/env python3
"""
Fee-Trap Finder - score the LLM judge.

Deterministic. Two things it reports:

  1. The judge's own pass rate per field (works with verdicts alone).
  2. If a labels file is given, how often the judge AGREES with those labels.
     Labels are either Amy's blind manual labels or, for the seeded
     calibration set, the known-correct verdict. Agreement with a trusted
     label is the headline: it says how far the judge can be trusted.

Records are matched between verdicts and labels by (fee_name, field).
"""

import json, argparse
from collections import defaultdict

FIELDS = ["amount", "trigger", "plain_language_warning"]


def key(r):
    if r.get("id"):
        return r["id"]
    return (r["fee_name"], r["field"])


def pct(x):
    return f"{100*x:5.1f}%"


def score(verdicts, labels=None):
    by_field_total = defaultdict(int)
    by_field_pass = defaultdict(int)
    for v in verdicts:
        by_field_total[v["field"]] += 1
        if v["verdict"] == "pass":
            by_field_pass[v["field"]] += 1

    out = {"n": len(verdicts), "pass_rate_by_field": {}, "pass_rate_overall": 0.0}
    total_pass = sum(by_field_pass.values())
    out["pass_rate_overall"] = total_pass / len(verdicts) if verdicts else 0.0
    for f in FIELDS:
        t = by_field_total[f]
        out["pass_rate_by_field"][f] = (by_field_pass[f] / t) if t else None

    if labels is not None:
        lab = {key(l): l["label"] for l in labels}
        agree = 0
        considered = 0
        disagreements = []
        judge_lenient = 0   # judge pass, label fail
        judge_harsh = 0     # judge fail, label pass
        field_agree = defaultdict(lambda: [0, 0])  # field -> [agree, total]
        for v in verdicts:
            k = key(v)
            if k not in lab:
                continue
            considered += 1
            field_agree[v["field"]][1] += 1
            if v["verdict"] == lab[k]:
                agree += 1
                field_agree[v["field"]][0] += 1
            else:
                disagreements.append({
                    "fee_name": v["fee_name"], "field": v["field"],
                    "judge": v["verdict"], "label": lab[k], "reason": v.get("reason", ""),
                })
                if v["verdict"] == "pass" and lab[k] == "fail":
                    judge_lenient += 1
                elif v["verdict"] == "fail" and lab[k] == "pass":
                    judge_harsh += 1
        out["calibration"] = {
            "considered": considered,
            "agreement": (agree / considered) if considered else 0.0,
            "judge_too_lenient": judge_lenient,
            "judge_too_harsh": judge_harsh,
            "agreement_by_field": {
                f: (field_agree[f][0] / field_agree[f][1]) if field_agree[f][1] else None
                for f in FIELDS
            },
            "disagreements": disagreements,
        }
    return out


def print_report(r):
    print("=" * 60)
    print(f"LLM JUDGE: {r['n']} field verdicts")
    print("=" * 60)
    print(f"  judge pass rate (overall)   {pct(r['pass_rate_overall'])}")
    for f in FIELDS:
        v = r["pass_rate_by_field"][f]
        print(f"    {f:<24} {pct(v) if v is not None else '  n/a'}")
    if "calibration" in r:
        c = r["calibration"]
        print("-" * 60)
        print(f"  CALIBRATION vs labels ({c['considered']} labeled)")
        print(f"  agreement with labels       {pct(c['agreement'])}  <-- headline")
        print(f"    judge too lenient (pass, label fail): {c['judge_too_lenient']}")
        print(f"    judge too harsh   (fail, label pass): {c['judge_too_harsh']}")
        for f in FIELDS:
            v = c["agreement_by_field"][f]
            print(f"    agree {f:<22} {pct(v) if v is not None else '  n/a'}")
        if c["disagreements"]:
            print("  DISAGREEMENTS:")
            for d in c["disagreements"]:
                print(f"    - {d['fee_name']} / {d['field']}: judge={d['judge']} label={d['label']}")
                print(f"        {d['reason'][:88]}")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--labels", help="optional labels file (human or known-correct)")
    args = ap.parse_args()
    verdicts = json.load(open(args.verdicts))
    labels = json.load(open(args.labels)) if args.labels else None
    print_report(score(verdicts, labels))


if __name__ == "__main__":
    main()
