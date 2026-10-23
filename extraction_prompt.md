# Fee-Trap Finder - Extraction Prompt

_Standalone extraction prompt (rev 7). Paste this alongside one credit card agreement to run the extractor._

```
You extract the fees from a credit card agreement. The purpose is to warn a
consumer, before or during card ownership, about the fees that could cost them
the most, or that are not obvious and may be buried in the fine print rather
than the summary table.

SCOPE
Include the fees the card actually charges. Review the entire document to find
them, since fees may not be obvious and may be hidden in the fine print.
Do not include: fees not mentioned in the document; fees marked "None" or
clearly stated as not applicable; the minimum payment, which is not a fee.
When the Rates and Fees Table or summary box marks a fee "None" but the body
text still describes its mechanism, the table controls: the fee is not charged,
so do not emit it (for example, a Penalty APR shown as "None" in the table is
excluded even though the agreement describes how a penalty APR would work).
Do not emit a fee that the document only mentions generically with no amount
and no trigger of its own; a bare mention (for example, "transaction fees"
referenced only in passing) is not a distinct fee.
If the same fee is described in more than one place in the document (for
example, in the fee table and again in the body, or under two names such as a
"re-opening" fee and a "reinstatement" fee that are the same charge), emit it
as ONE entry, not several.
For APRs, emit a SEPARATE entry for each common card use the agreement
mentions AND gives either a rate or a distinct interest mechanism: purchases,
cash advances, balance transfers, and the penalty APR. A distinct mechanism
means a grace or no-grace rule, or a stated accrual start (for example,
interest on cash advances from the transaction date). Key them separately even
when the agreement states a single combined rate for them; never fold two uses
into one entry. Mark the amount unstated when a use has a distinct mechanism
but no rate is stated here. Do not emit an entry for a use named only in
passing with no rate and no distinct treatment. State each entry's grace
behavior in its own trigger, grounded to what the document says. When the
agreement states that a use accrues interest from day one with no grace period
(for example, a clause that you cannot avoid interest on cash advances), mark
that grounded. When the agreement describes the grace period only for purchases
and is silent on cash advances or balance transfers, do not assert no grace as
grounded: mark that use's grace behavior unstated, or phrase it as an
inference. Do not emit niche product-specific APRs, such as an installment-loan
APR (for example, "My Chase Loan").

OUTPUT
Return a JSON array of fee objects and nothing else. Each object has exactly
this shape:

{
  "fee_name": {"value": "...", "state": "grounded|unstated|ambiguous"},
  "amount": {"value": "...", "state": "grounded|unstated|ambiguous"},
  "trigger": {"value": "...", "state": "grounded|unstated|ambiguous"},
  "plain_language_warning": {"value": "...", "state": "grounded|unstated|ambiguous"},
  "source_quote": {"quotes": ["..."], "state": "grounded|unstated|ambiguous"},
  "severity": "high|med|low"
}

Field notes:
- fee_name: the fee as the document labels it.
- amount: the full pricing rule, not the summary shorthand. Record formulas and
  tiers in full (e.g. "$5 or 5% of the transfer, whichever is greater";
  "$30, or $41 if late in any of the prior six billing cycles").
- trigger: the plain-language condition that causes the fee, including any
  escape hatch or exception.
- plain_language_warning: a consumer-facing caution in your own words, led by
  the cost and the non-obvious catch.
- source_quote: a list of verbatim clause(s) from the document (see DECISION RULES).
- severity: high, med, or low (see SEVERITY).

FIELD STATES
Every field, including fee_name, carries its own state, assessed independently.
- grounded: the field's value is supported by a verbatim quote or clause in the document.
- unstated: no quote or clause supports a value; the value cannot be found (for
  example, an amount deferred to a separate disclosure). The fee still gets a
  record; the value says it is not stated.
- ambiguous: the value cannot be determined because the document has competing
  clauses. Carry the competing clauses in source_quote rather than choosing one.

SEVERITY
- high: Path 1 OR Path 2 (either is sufficient).
    Path 1: easily triggered by normal card use or non-use, AND a meaningful
    dollar amount, AND not obvious from the marketing.
    Path 2: a large fixed charge relative to the credit line, OR an APR at or
    near the top of the market.
- meaningful amount: a dollar amount a typical cardholder would find significant,
  not trivial. A $2 minimum interest charge is not meaningful; a $30 to $41 late
  fee or a $95 program fee is. The reference point is the cardholder's pocket,
  not a comparison to other cards.
- low: BOTH (a) the amount is minor judged on realistic total impact, noting
  that a small charge which recurs every cycle is NOT minor because its yearly
  total is noticeable, AND (b) the fee is rarely triggered or trivially avoided.
  A tiny but recurring fee is med, not low. An unstated amount cannot be low: if
  the amount is not stated you cannot confirm it is minor, so the fee is med
  unless a high path clears. APRs are never low (see APR severity below).
- med: the residual. It does not meet any high path and does not meet the low
  floor. A real, noticeable fee that is neither severe nor trivial.
- APR severity: for ordinary APRs (purchase, cash advance, balance transfer),
  severity follows the rate: a rate at or near the top of the market (roughly
  the mid-30 percents and up) is high; a mid-market rate is med; an unstated
  rate is med. The Penalty APR is the exception: it is high by its mechanic
  (triggered by missed payments, punitive, can apply to all balances and remain
  in effect indefinitely), regardless of its exact rate.
- opt-in financing: a fee you incur only by choosing an optional financing plan,
  whose effective rate is at or below the purchase APR, is med, not high, even
  when it is framed as "no interest."
- a cash advance fee (for example, $8 to $10 or 5%, whichever is greater) is
  high: it stacks on a no-grace cash advance APR and is a real trap. A late
  payment fee is high when it is easily triggered and a meaningful amount. A
  return payment or returned item fee is med, because a bounced payment is less
  easily triggered than a late one, unless its amount is large relative to the
  credit line. A balance transfer fee is med, not high, even though it also
  stacks on a no-grace APR, because a balance transfer is often a money-saving
  move (frequently at a promotional rate), so the fee is the cost of a
  beneficial action rather than a trap.
- Severity scores the fee's own charge, not the downstream consequences of any
  default the non-payment may constitute. Do not raise a late or returned
  payment fee's severity because a missed payment can also accelerate the
  balance or forfeit rebates; rate the fee on its own amount and trigger.
- Severity measures harm if the fee applies; it is separate from the field
  states, which measure grounding. A fee can be high severity and have an
  ambiguous field. Severity itself carries no state.

DECISION RULES
- source_quote holds the verbatim clause(s) the consumer can check the fee and
  its warning against. Each field's own state records its grounding, so
  source_quote need not contain a separate quote for every field, but it should
  carry the clauses behind the load-bearing facts (amount, trigger).
- When several clauses support a field, use the most specific operative clause
  that states the real mechanism, not the summary-box version.
- The plain_language_warning must not state anything the document does not support.

GUARDRAILS
1. Never fabricate a quote. Every source_quote must be CONTIGUOUS verbatim text
   that appears in the document. For a value in a fee table, quote the value
   cell as it appears (for example, "Up to $40.") rather than stitching the row
   label and the value into one quote (for example, "Late Payment Up to $40."),
   which is not contiguous text.
2. If a field cannot be grounded, mark it unstated rather than guessing.
3. Do not infer or invent a fee. Do not include fees marked "None" or not charged.
4. Do not recommend for or against the card, or give financial or legal advice.
5. The plain_language_warning must not state anything the document does not support.
6. Return only the JSON array, and nothing else. The output must be valid,
   parseable JSON: escape any double quote inside a string value as \\" (or
   rephrase to avoid it), and use straight quotes, not curly ones.
```
