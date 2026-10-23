# Sources

All agreements are public credit card agreements filed with the Consumer
Financial Protection Bureau (CFPB) and retrieved from the CFPB credit card
agreement database: https://www.consumerfinance.gov/credit-cards/agreements/

The PDFs are included for provenance. The matching `.txt` file in
`agreements/` is the exact text the extractor and the groundedness check were
run against; text extraction varies by tool, so the committed text is what
makes the scored numbers reproducible.

## Keyed agreements (golden set)

| Issuer | Product | Files |
| --- | --- | --- |
| JPMorgan Chase Bank, N.A. | Cardmember Agreement (COL00100) | agreements/chase.pdf, agreements/chase.txt |
| Golden 1 Credit Union | Platinum Rewards Credit Card Agreement | agreements/golden1.pdf, agreements/golden1.txt |
| Synchrony Bank | American Signature Credit Card Account Agreement | agreements/synchrony.pdf, agreements/synchrony.txt |
| First PREMIER Bank | Credit Card Contract and Account Opening Disclosures | agreements/first_premier.pdf, agreements/first_premier.txt |

Note on First Premier: the source PDF carries an "ONLINE COPY" watermark that
corrupts the raw text layer, so `agreements/first_premier.txt` is a cleaned,
de-watermarked reconstruction of the disclosure pages, used as the groundedness
document.

## Unseen agreements (generalization set, not keyed)

| Issuer | Product | Files |
| --- | --- | --- |
| Wells Fargo | Active Cash | demo_set/wells_fargo.pdf, .txt |
| American Express | EveryDay | demo_set/amex.pdf, .txt |
| BECU | Cash Back Visa (two-card rate sheet) | demo_set/ratesheet.pdf, .txt |
| Citizens | Amp | demo_set/citizens.pdf, .txt |
