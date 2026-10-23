# Credit Card Fee Finder

An agentic tool that reads a credit card agreement and surfaces the fees that
cost a consumer the most, each in plain language and tied to the exact clause
it came from, plus an evaluation harness that grades the tool against a
hand-built answer key.

Built as a hands-on AI product project: document extraction, structured output,
grounding, and evaluation of generated text.

## Results at a glance

- **Recall and precision: 100%** across the four hand-keyed agreements (43 fees).
  It missed no real fee and invented none.
- **Groundedness: 100%** on three of the four keyed agreements, and on three of
  four unseen agreements it was never tuned on. The two sub-100 scores (Chase
  80%, Citizens 91.7%) are PDF-spacing string-match artifacts, not fabricated
  quotes.
- **Severity: matches the key on 3 of 4** keyed cards; 93.8% on the fourth.
- **LLM-as-judge agrees with hand labels 95.8%** (46/48) on the hardest card, and
  100% on a seeded sanity set.
- **Boundary cases: all six synthetic fixtures pass** (unstated amount, ambiguity,
  table-None, table cutoff, prompt injection, readability gate).

Full detail below, in `testing_report/`, and in
`calibration/judge_calibration_results.md`.

## The two pieces

**1. The Fee-Trap Finder.** Upload a credit card agreement, get back a ranked
list of its fees. For each fee: the name, the amount (full pricing rule, not the
summary-box number), what triggers it, a plain-language warning, the exact
source quote, and a severity (high / med / low). It runs a three-step agent loop
in the browser: it drafts the fee list, critiques its own draft, then revises.
A readability gate routes scanned or watermarked PDFs to a paste fallback rather
than extracting them badly.

**2. The eval harness.** Grades an extraction against a golden set (a
hand-written answer key of the true fees) on four deterministic measures, plus a
separate LLM-as-judge for the fields a string match cannot grade.

## Extraction schema (per fee)

```
fee_name, amount, trigger, plain_language_warning, source_quote, severity
```

Every field except severity carries its own grounding state
(`grounded` / `unstated` / `ambiguous`). `source_quote` is fee-level evidence:
the verbatim clause(s) a reader can check the fee against.

## How the evaluation works

The harness (`eval_harness.py`) grades the things a computer can settle by
matching:

- **recall** - of the fees really in the agreement, how many were found
- **precision** - of the fees reported, how many are real
- **groundedness** - of the reported fees, how many have every quote verbatim in
  the agreement (needs the document, not the key)
- **severity match** - of the matched fees, how many got the same severity as
  the key

The three fields a string match cannot grade (`amount`, `trigger`,
`plain_language_warning`) are handled by the **LLM-as-judge** (`llm_judge.py`,
`score_judge.py`), which reads each field against the agreement and the golden
answer and rules pass or fail with a reason. The golden set stays the benchmark;
the judge is a second check, and it was calibrated before being trusted.

## Results

### Calibration scorecard (four hand-keyed agreements)

| Agreement | Fees | Recall | Precision | Groundedness | Severity |
| --- | --- | --- | --- | --- | --- |
| Golden 1 (credit union) | 8 | 100% | 100% | 100% | 100% |
| Synchrony (store card) | 9 | 100% | 100% | 100% | 100% |
| First Premier (subprime) | 16 | 100% | 100% | 100% | 93.8% |
| Chase (megabank) | 10 | 100% | 100% | 80% | 100% |

Chase groundedness at 80% is a string-match artifact (spacing the PDF
introduced inside otherwise-verbatim quotes), not a fabricated quote.

### Generalization (four unseen agreements, groundedness only, no key)

Wells Fargo 100%, American Express 100%, BECU 100%, Citizens 91.7% (same
spacing artifact). These were never tuned against.

### LLM-as-judge calibration

- Seeded sanity set (16 cases, known answers): 100% agreement.
- Human agreement on First Premier (48 fields, hand-labeled blind): **95.8%
  (46/48)**. Both disagreements were the judge being stricter than the human;
  zero cases where it passed a field the human failed. The labeling also caught
  an error in the answer key itself, which was corrected (see
  `calibration/judge_calibration_results.md`).

## Repo layout

```
finder.html                      the live finder (single-page app)
extraction_prompt.md             the standalone extraction prompt
eval_harness.py                  deterministic grader (recall/precision/groundedness/severity)
judge_prompt.md                  the LLM-as-judge prompt (separate from extraction)
llm_judge.py                     builds per-field judge inputs and runs the judge
score_judge.py                   scores the judge (pass rates, agreement vs labels)
golden_set/                      the hand-written answer key (43 fees, v1.9)
agreements/                      the four keyed agreements: source PDF + exact text run against
extractions/                     blind extractor output for each keyed agreement
calibration/                     judge calibration set, verdicts, human labels, and writeup
fixtures/                        six synthetic boundary-case documents
demo_set/                        four unseen agreements + their blind extractions
testing_report/                  the full testing report
```

## Running it

The harness and the judge scorer use only the Python standard library.

```bash
# grade one keyed agreement against the golden set
python eval_harness.py --golden golden_set/fee_trap_golden_set.json \
    --card first_premier --output extractions/first_premier.json \
    --doc agreements/first_premier.txt

# score the judge against the human labels
python score_judge.py --verdicts calibration/judge_verdicts_first_premier.json \
    --labels calibration/labels_first_premier.json
```

Running the judge over fresh fields (`llm_judge.py run`) calls the Anthropic API
and reads its key from the `ANTHROPIC_API_KEY` environment variable. The key is
never stored in the repo. See `requirements.txt`.

The finder runs as a published Claude Artifact and calls Claude at runtime on
the viewer's own Claude account, so there is no server and no API key in the
page. `finder.html` is the source.

## Scope

The pilot is scoped to readable, text-based agreements, with a paste fallback
for anything the in-browser extractor cannot read cleanly. Scanned and
watermarked PDFs are out of scope and are routed to paste by the readability
gate. OCR for those is a deliberate next step, because scanned documents skew
toward subprime agreements, where the fee traps are worst.

## Sources

The agreements are public filings from the CFPB credit card agreement database.
See `SOURCES.md`.
