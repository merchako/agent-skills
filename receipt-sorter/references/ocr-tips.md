# OCR & extraction tips for receipts

Techniques learned from real batches of scanned US retail receipts. The goal is accurate
**vendor, date, and total** for every receipt, plus correct grouping of multi-receipt
scans and returns.

## Reading faint / thermal receipts

Thermal receipts fade, especially the totals column on the right edge. When tesseract or
a full-page read can't resolve a number, crop the region and enlarge it:

```bash
# header band (logo + date), top 42%
magick page.png -crop ${W}x$((H*42/100))+0+0 +repage -resize 1400x hdr.png
# total band — crop a horizontal strip around the SUBTOTAL/TOTAL lines and zoom the right side
magick page.png -crop $((W*60/100))x$((H*8/100))+$((W*30/100))+$((H*18/100)) +repage -resize 1600x tot.png
```
Then read the crop. If a digit is physically lost to fading, say so and use your best
read with a flag (e.g. "$179.97, middle digit smudged") rather than presenting a guess as
fact. Cross-checks that often recover a number:
- `subtotal + tax = total` (US sales tax is typically 6–9%).
- The card-charge line (`MASTERCARD 99.97`) equals the total.
- A refund's "$X will be removed from your total" line equals the original's subtotal.

## Identifying the vendor when the logo won't OCR

Logos are images and OCR poorly. Use the **store address / phone** line, which is text:
- "251 S. INDUSTRIAL BLVD, EULESS TX" + "How doers get more done" → Home Depot
- "Ace Rewards number" → Ace Hardware; "ACE MART RESTAURANT SUPPLY" is a different store
- "EXPECT MORE. PAY LESS." → Target
- "Welcome to IKEA <city>" → IKEA
- "Thank You for Shopping at Calloway's" → Calloway's Nursery
- Plant/SKU names (CORDYLINE, POTHOS) → a nursery/garden center
- Rotated invoices: `magick in.png -rotate 90 +repage out.png` then read.

## Dates

- Use the **receipt's printed transaction date**, not the scan date and not a
  "RETURN BY" / "EXPIRES" / rewards "As of" date.
- US receipts are `MM/DD/YY`. Watch for `YY/MM/DD` (some IKEA receipts) — disambiguate
  with the other dates on the page.
- Output ISO `YYYY-MM-DD` so files sort chronologically.

## Multiple receipts in one scan

A single PDF (or one long photo) frequently contains several receipts, sometimes from
different vendors and different years. Treat each **page** as potentially its own receipt
until proven otherwise. Conversely, one receipt can span pages (an itemized list + its
return policy) — keep those together.

## Matching returns to purchases

- **Home Depot / Lowe's** print `ORIG REC: <store> <reg> <txn> MM/DD/YY` on refunds.
  Match that store+number+date to the original purchase's header line to pair them.
- A refund may reference **several** originals (a multi-item return) — keep it standalone
  rather than forcing it onto one purchase.
- Returns carry **negative** totals (`-$54.09`, or `TOTAL REFUND $129.90-`).
- A purchase fully reversed by a same-batch return: keep both, appended in one file, so
  the story is intact.

## Duplicate scans

The same receipt is sometimes scanned twice (front/back feed, re-scan). Identical
invoice number + date + total = duplicate — keep one, and **log** that you dropped the
other so the page-coverage check doesn't look like a lost receipt.

## Non-receipt items that show up in receipt folders

- **Product labels / box photos** (flooring label, tool box) — not purchases. Propose a
  `Product references/` subfolder; keep the descriptive name, no date/total.
- **Medical receipts** — provider is the "vendor"; often best grouped per patient
  (`Medical/<Patient Name>/`). Be extra careful with these; confirm routing with the user.
- **Online order confirmations / screenshots** — may have no printed date; keep them but
  name them so it's clear the date is unknown.
