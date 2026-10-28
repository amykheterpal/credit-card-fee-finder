# Fee-Trap Finder Testing Report

Oct 12, 2026

The Fee-Trap Finder was tested on three layers: a calibration scorecard against hand-written answer keys, six synthetic fixtures for boundary behavior, and a generalization run on four unseen agreements. Testing drove twelve concrete changes to the extraction rules, the reviewer, and the in-browser gate.

## How it was tested

Testing ran on three layers, each answering a different question.

1. Calibration against answer keys. Four agreements (Golden 1 credit union, Synchrony store card, First Premier subprime, Chase megabank) were hand-keyed into a golden set of 43 fees. A Python eval harness grades each extraction for recall (fees missed), precision (fees invented), groundedness (every quoted clause verbatim in the agreement), and severity match against the key.
2. Synthetic fixtures for boundary behavior. Six small hand-built documents force one hard case each: an unstated amount, an ambiguous clause, a fee marked None with its mechanism still described, a value split by a table page break, a prompt-injection attempt, and a non-agreement document fed to the readability gate.
3. Generalization on unseen agreements. Four agreements that were never keyed (Wells Fargo, American Express, BECU rate sheet, Citizens) were run end to end to check that groundedness holds on documents the rules were not tuned against.

The finder itself runs the extract, self-critique, and revise loop live in the browser. The harness grades the loop's final output, not a single pass.

## How the metrics are defined

Four metrics, each measuring a different kind of error. Recall and precision need the hand-written answer key; groundedness and severity do not need the key for the quote check, though severity needs the key to know the correct level.

| Metric | Definition | What it catches | Needs a key |
| --- | --- | --- | --- |
| Recall | Of the fees really in the agreement, the share the extractor found | Missed fees | Yes |
| Precision | Of the fees the extractor reported, the share that are real | Invented fees | Yes |
| Groundedness | Of the reported fees, the share whose every listed quote is verbatim in the agreement | Fabricated or paraphrased quotes | No |
| Severity match | Of the matched fees, the share graded the same severity as the key | Mis-ranked fees | Yes |

Groundedness checks only the quotes that are listed; it does not require a separate quote for every field. Each field carries its own grounding state, and source\_quote is fee-level evidence for the load-bearing facts. Trigger and warning wording are graded separately by the LLM-as-judge (see below), not by this deterministic harness.

The six fields split between the two graders, each field graded once: the harness checks the three a computer can settle by matching, and the judge checks the three written in plain English.

| Field | Graded by | Check |
| --- | --- | --- |
| fee\_name | Eval harness | Fee matching (recall and precision) |
| source\_quote | Eval harness | Groundedness, every quote verbatim in the agreement |
| severity | Eval harness | Severity match against the key |
| amount | LLM judge | Wording accurate and supported by the agreement |
| trigger | LLM judge | Wording accurate and supported by the agreement |
| plain\_language\_warning | LLM judge | Wording accurate and supported by the agreement |

## Fixture and boundary cases

All six synthetic cases pass. The ambiguous case is the one the single pass misses and the critique step catches, which is the loop earning its place.

| Fixture | What it tests | Expected behavior | Result |
| --- | --- | --- | --- |
| Unstated amount | A fee whose amount is deferred to another disclosure | Emit the fee, mark amount unstated, not low | Pass |
| Ambiguous clause | Two competing clauses on the same fee | Carry both clauses, mark ambiguous | Pass (via the critique step; single pass picked one) |
| None plus generic | A fee shown None in the table but described in the body | Table controls, do not emit | Pass |
| Table page-break cutoff | A value split across a table page break | Quote the value cell contiguously, no stitched quote | Pass |
| Prompt injection | Text in the document instructing the extractor | Ignore the instruction, extract normally | Pass |
| Readability gate | A non-agreement document (a recipe) | Route to paste, do not extract | Pass |

## Calibration scorecard

Against the four hand-keyed agreements, recall and precision are 100 percent on every card. Groundedness and severity are where the remaining gaps sit, and both have known causes rather than extraction errors.

| Agreement | Fees in key | Recall | Precision | Groundedness | Severity match |
| --- | --- | --- | --- | --- | --- |
| Golden 1 (credit union) | 8 | 100% | 100% | 100% | 100% |
| Synchrony (store card) | 9 | 100% | 100% | 100% | 100% |
| First Premier (subprime) | 16 | 100% | 100% | 100% | 93.8% |
| Chase (megabank) | 10 | 100% | 100% | 80% | 100% |

The Chase groundedness figure is a string-match artifact, not a fabricated quote. Two quotes are verbatim in the agreement but fail the exact-match check because of spacing the PDF introduced. The First Premier severity gap is one fee graded one level apart from the key, not a missed or invented fee.

## Generalization on unseen agreements

Four agreements that were never hand-keyed were run end to end. These measure whether groundedness holds on documents the rules were not tuned against. Recall and precision are not scored here because there is no answer key; groundedness is, because it needs only the agreement text.

| Agreement | Groundedness | Note |
| --- | --- | --- |
| Wells Fargo | 100% | Clean run, no fixes needed |
| American Express | 100% | Surfaced the duplicate-fee case, now de-duplicated |
| BECU (rate sheet) | 100% | Surfaced the no-grace over-assertion, now grounded to the text |
| Citizens | 91.7% | Spacing artifact only; true groundedness is effectively 100% |

Three of the four are a clean 100 percent. The Citizens figure is the same PDF-spacing string-match artifact seen on Chase, not a real grounding failure. Each of the Amex and BECU runs surfaced a rule gap that was fixed, which is recorded below.

## LLM-as-judge: field accuracy

The scorecard and the generalization run cannot grade the plain-language fields (amount, trigger, warning), because those are written in the tool's own words and there is no exact text to match. A separate LLM-as-judge grades them against the agreement, with its own pass/fail prompt kept apart from the extractor. It was validated before being trusted.

| Check | Result | What it means |
| --- | --- | --- |
| Seeded sanity set (16 cases, known answers) | 100% | Passes clearly-correct fields, fails clearly-wrong ones |
| Human agreement on First Premier (48 fields, blind) | 95.8% (46/48) | Grades the way the PM would about 96% of the time |

Both disagreements were the judge being stricter than the human, with zero cases where it passed a field the human failed. The blind labeling also caught an error in the answer key itself, a Program Fee misattribution, which was corrected. The golden set stays the benchmark; the judge is the second check.

## What changed because of testing

Twelve changes came out of testing. Each one was surfaced by a specific run, not by guesswork, and each was applied to the extraction prompt, the finder, and the recorded rules together.

| Change | Reason | Layer | Surfaced by |
| --- | --- | --- | --- |
| Whitespace-insensitive grounding check | PDF line breaks caused verbatim quotes to fail an exact-match test | Keyed | Chase run flooded with whitespace nitpicks |
| Model-based readability gate | A stray-letter ratio could not detect a watermarked or scanned document | Keyed | First Premier watermark slipped a 0.27% junk-ratio heuristic |
| Contiguous table-quote rule | A quote stitched from a row label and value cell is not contiguous text | Fixture | Table page-break fixture |
| APR severity scored by rate | A flat high on every APR over-warned on mid-market rates | Keyed | Calibration against the keyed APRs |
| Default-consequence guardrail | A late fee was being raised because a missed payment can also accelerate the balance | Keyed | Golden 1 Late Payment severity review |
| APR emission refinement | One combined-rate line was folding two card uses into one entry | Keyed | Consistency check across the three keyed cards |
| Return payment fee set to med | A bounced payment is less easily triggered than a late one | Decision | Outstanding-decisions review |
| Reviewer aligned to the document | The reviewer demanded a rate quote per field instead of judging grounding against the agreement | Unseen | Citizens self-review over-flagged |
| Table-controls-None rule | A penalty APR shown None in the table but described in the body flip-flopped | Unseen | Citizens penalty-APR inclusion |
| Balance transfer fee set to med | A transfer is often a money-saving move, so the fee is not a trap | Keyed | Severity calibration |
| De-duplication rule | The same fee under two names produced two entries | Unseen | Amex reinstatement vs re-opening fee |
| Grace-behavior grounding | No-grace was asserted as grounded where the document only described purchases | Unseen | BECU over-asserted no-grace |

## Known limitations

The testing is honest about what it does not yet cover.

- Deterministic field accuracy is limited. The harness scores severity exactly; the trigger and warning wording are now graded by the LLM-as-judge above, calibrated at 95.8% agreement with hand labels, rather than by the string-matching harness.
- Groundedness is a string match. It can report a false negative when the PDF introduces spacing inside an otherwise verbatim quote, as seen on Chase and Citizens.
- In-browser extraction is weak on scanned or watermarked PDFs. The readability gate catches these and routes them to paste rather than extracting badly.
- Single-pass output varies. The loop reduces this, but a given pass can differ, which is why the harness grades the loop's final output.
- Feedback is not persisted. The in-app NPS, usefulness, and per-card thumbs are captured in memory for the demo, not stored.
- The generalization set is unkeyed. Those four runs measure groundedness only, not recall or precision.
