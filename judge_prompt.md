# Fee-Trap Finder - LLM-as-judge prompt

This is the judge's own prompt. It is SEPARATE from the extraction prompt that
finds the fees. The extractor's job is to produce a fee. The judge's job is to
decide whether one extracted field is accurate and supported. Keep the two
apart: the judge never re-extracts and never fixes the field, it only rules on
it.

You are grading ONE field of ONE fee. You are given:
- FIELD: which field this is (trigger, plain_language_warning, or amount).
- EXTRACTED: the value the extractor produced for that field.
- GOLDEN: the hand-written reference value for that field (the benchmark).
- DOCUMENT: the text of the credit card agreement.

Return a verdict on the EXTRACTED value, as strict JSON and nothing else:

{
  "verdict": "pass" | "fail",
  "reason": "one sentence, concrete, naming what is right or wrong"
}

Rules that apply to every field:
- The GOLDEN value is the benchmark for meaning, not for wording. The extracted
  value does NOT have to match the golden wording. It passes if it conveys the
  same substance and is supported by the DOCUMENT.
- Supported means the DOCUMENT backs the claim. A claim that is fluent but not
  in the document fails, even if it sounds reasonable.
- Judge only the field in front of you. Do not fail a field because a different
  field is weak.
- A difference in emphasis, order, or phrasing is not a failure. A difference in
  the operative fact is a failure.

FIELD-SPECIFIC CRITERIA

amount
- PASS when the extracted amount captures the full operative pricing rule: the
  figure, and any tier or formula that changes what the cardholder pays (for
  example "$5 or 5% of the amount, whichever is greater", or "$30, or $41 if
  late again within six cycles"). A correct figure with the formula or tier
  intact passes even if worded differently from golden.
- FAIL when the figure is wrong, a tier or "whichever is greater" clause that
  changes the charge is dropped or misstated, or the amount asserts a number the
  document does not state. If the document does not state an amount and the
  extracted value claims one, fail.
- An amount correctly marked as not stated (when the document defers it) passes;
  do not fail it for being blank when the document is genuinely silent.

trigger
- PASS when the extracted trigger names the real condition that causes the fee
  and preserves any escape hatch or exception that materially changes who pays
  (for example a grace period for purchases, or "unless paid in full by the due
  date"). Same condition, different words, passes.
- FAIL when the trigger names the wrong condition, drops an escape hatch that
  changes the outcome, or asserts a mechanism the document does not describe
  (for example claiming no grace period where the document is silent).

plain_language_warning
- PASS when every claim in the warning is supported by the document and the
  warning leads with the real cost or the real catch. Consumer-friendly
  rephrasing is fine. Rounding a rate for readability is fine.
- FAIL when the warning states something the document does not support, invents
  a consequence, softens or overstates the real risk, or gives advice the
  document does not ground (for example promising a promotional rate the
  document does not offer).

Edge handling
- If EXTRACTED and GOLDEN disagree with each other but EXTRACTED is the one the
  DOCUMENT supports, pass EXTRACTED. The golden set can be wrong; the document
  is the final authority on support.
- If you cannot tell from the DOCUMENT whether the claim holds, fail, and say in
  the reason that the document does not settle it. Do not guess in the
  extractor's favor.
- Output only the JSON object. No preamble, no code fence.
