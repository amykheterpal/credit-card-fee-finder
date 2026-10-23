#!/usr/bin/env python3
"""
Fee-Trap Finder - LLM-as-judge (field-accuracy grader)

Grades the fuzzy fields the deterministic harness cannot score: trigger,
plain_language_warning, and amount. It is a SECOND check on top of the golden
set, not a replacement for it. The golden set stays the benchmark.

Design (mirrors eval_harness.py: model step and scoring step are separate)
--------------------------------------------------------------------------
  build : pair matched fees (same matcher as the harness), and emit one judge
          INPUT record per field to grade -> judge_inputs.json
  run   : read judge_inputs.json, call the judge model on each record, and
          write one VERDICT per record -> judge_verdicts.json
  Scoring lives in score_judge.py so it stays deterministic and reviewable.

Model access
------------
run() calls the Anthropic API using the ANTHROPIC_API_KEY environment variable.
The key is read from the environment and is never written to disk, so nothing
secret lands in the repo. If no key is set, run() can instead load
pre-computed verdicts from a file (--verdicts), which is how the judge is run
inside Claude Code, where the model is already available without a key.
"""

import json, os, sys, argparse

# reuse the harness matcher so "which extracted fee is which golden fee" is
# decided the same way in both tools
from eval_harness import match_fees, fee_name

JUDGE_FIELDS = ["amount", "trigger", "plain_language_warning"]


def field_value(fee, field):
    f = fee.get(field)
    if isinstance(f, dict):
        return f.get("value", "")
    return f or ""


def load_prompt(path="judge_prompt.md"):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


# ---------- build: matched fees -> one input record per field ----------

def build_inputs(gold_card, out_fees, doc_text):
    gold_fees = gold_card["fees"]
    matched, _missed, _invented = match_fees(gold_fees, out_fees)
    records = []
    for g, o in matched:
        for field in JUDGE_FIELDS:
            records.append({
                "fee_name": fee_name(o),
                "field": field,
                "extracted": field_value(o, field),
                "golden": field_value(g, field),
            })
    return records


# ---------- run: call the judge model on each record ----------

def judge_field(record, doc_text, prompt):
    """Call the judge model on one field record. Returns {verdict, reason}.
    Uses the Anthropic API via ANTHROPIC_API_KEY. Raises if no key is set so
    the caller can fall back to a pre-computed verdicts file."""
    import anthropic  # imported here so the script loads without the SDK
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the env
    user = (
        f"FIELD: {record['field']}\n\n"
        f"EXTRACTED:\n{record['extracted']}\n\n"
        f"GOLDEN:\n{record['golden']}\n\n"
        f"DOCUMENT:\n{doc_text}"
    )
    msg = client.messages.create(
        model=os.environ.get("JUDGE_MODEL", "claude-opus-4-8"),
        max_tokens=300,
        system=prompt,
        messages=[{"role": "user", "content": user}],
    )
    text = msg.content[0].text.strip()
    return json.loads(text)


def run(inputs, doc_text, prompt):
    verdicts = []
    for rec in inputs:
        v = judge_field(rec, doc_text, prompt)
        verdicts.append({**rec, "verdict": v["verdict"], "reason": v["reason"]})
    return verdicts


# ---------- cli ----------

def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="pair matched fees and emit judge inputs")
    b.add_argument("--golden", required=True)
    b.add_argument("--card", required=True)
    b.add_argument("--output", required=True, help="extractor output JSON")
    b.add_argument("--doc", required=True)
    b.add_argument("--out", required=True, help="where to write judge_inputs.json")

    r = sub.add_parser("run", help="call the judge model on each input")
    r.add_argument("--inputs", required=True)
    r.add_argument("--doc", required=True)
    r.add_argument("--prompt", default="judge_prompt.md")
    r.add_argument("--out", required=True, help="where to write judge_verdicts.json")

    args = ap.parse_args()

    if args.cmd == "build":
        gold = json.load(open(args.golden))
        card = next((c for c in gold["cards"] if c["card_id"] == args.card), None)
        if card is None:
            sys.exit(f"card '{args.card}' not found")
        out_fees = json.load(open(args.output))
        doc_text = open(args.doc, encoding="utf-8", errors="ignore").read()
        recs = build_inputs(card, out_fees, doc_text)
        json.dump(recs, open(args.out, "w"), indent=2)
        print(f"wrote {len(recs)} judge inputs to {args.out}")

    elif args.cmd == "run":
        inputs = json.load(open(args.inputs))
        doc_text = open(args.doc, encoding="utf-8", errors="ignore").read()
        prompt = load_prompt(args.prompt)
        verdicts = run(inputs, doc_text, prompt)
        json.dump(verdicts, open(args.out, "w"), indent=2)
        print(f"wrote {len(verdicts)} verdicts to {args.out}")


if __name__ == "__main__":
    main()
