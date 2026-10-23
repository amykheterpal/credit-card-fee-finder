# LLM-as-judge: calibration results

The judge grades the three fields the deterministic harness cannot score:
`amount`, `trigger`, and `plain_language_warning`. Before trusting it, it was
validated two ways. The golden set remains the benchmark; the judge is a
second check.

## 1. Seeded sanity check

A 16-case set with known-correct verdicts, balanced 8 pass / 8 fail, built from
real Chase and Golden 1 clauses (`calibration_cases.json`). Each case is a
deliberate pattern: a valid paraphrase, a dropped fee tier, a wrong figure, an
invented grace period, an unsupported penalty-APR claim, and so on.

- Agreement with the known-correct verdicts: **16 / 16 (100%)**, no lenient or
  harsh misses.

This confirms the judge passes clearly-correct fields and fails clearly-wrong
ones. It is a floor, not the trust number, because the cases are clear by
design.

## 2. Human agreement on a real card (First Premier)

First Premier is the subprime agreement, the messiest card and the best stress
test. All 48 fields (16 fees x 3) were hand-labeled pass/fail by the PM, blind
to the judge's verdicts, then compared.

- **Agreement with the human labels: 46 / 48 (95.8%)**
- By field: trigger 100%, warning 93.8%, amount 93.8%
- Zero cases where the judge passed a field the human failed (no false passes)

### The two disagreements (both the judge stricter than the human)

| Field | Judge | Human | What it was |
| --- | --- | --- | --- |
| Collection Costs / amount | fail | pass | Amount left blank. Judge wanted it to at least state no figure is given and the costs are open-ended; human accepted the blank since the document states no figure. A genuine judgment call. |
| Copying Fee / warning | fail | pass | Warning says the fee is "easy to avoid by using online copies," which the First Premier document never mentions. Judge flagged it as unsupported advice. |

On review, the PM agreed both of the judge's stricter calls were defensible.
The labels above are kept exactly as submitted blind (not revised to match the
judge), so 95.8% is a clean blind measurement rather than a post-hoc number.
One third-disagreement in the raw submission (Program Fee amount) was a PM
labeling slip, a correct amount failed by association with the program-fee
misattribution in its trigger and warning, and was corrected to pass.

### A bug the labeling caught in the answer key

While labeling, the PM caught an error in the golden set itself: the First
Premier Program Fee was keyed as reducing available credit to about $225 on a
$300 limit. That is wrong. The $95 Program Fee is paid up front before the
account opens (out of pocket, not drawn from the line); the $225 figure is the
$300 limit minus the $75 first-year Annual Fee. The golden set was corrected
(v1.9) and the quote moved to the Annual Fee. The blind extractor output still
carries the original misattribution, so the judge now correctly fails those two
Program Fee fields. This is the eval working as intended: human review caught an
error in the answer key that both automated graders had propagated.

## How to reproduce

```
# build the per-field judge inputs from an extraction + golden + document
python llm_judge.py build --golden fee_trap_golden_set.json --card first_premier \
    --output extraction_first_premier_v2.json --doc first_premier_clean.txt \
    --out judge_inputs.json

# run the judge (needs ANTHROPIC_API_KEY; or supply pre-computed verdicts)
python llm_judge.py run --inputs judge_inputs.json --doc first_premier_clean.txt \
    --out judge_verdicts.json

# score the judge's pass rates, and agreement vs a human-label file
python score_judge.py --verdicts judge_verdicts_first_premier.json \
    --labels labels_first_premier.json
```
