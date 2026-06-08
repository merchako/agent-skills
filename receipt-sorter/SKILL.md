---
name: receipt-sorter
description: OCR a folder of scanned receipt PDFs/images on macOS and organize them into per-vendor subfolders with date-stamped filenames (YYYY-MM-DD Vendor $total.pdf), splitting multi-receipt scans, pairing returns with their original purchase, and writing a receipts.csv ledger. Everything runs locally for financial privacy. Use this skill whenever the user has scanned, photographed, or downloaded receipts/invoices that need OCR, renaming by the receipt's own date (not the scan date), grouping by vendor or content, or general receipt-folder cleanup — e.g. "sort my scanned receipts", "OCR these receipts and rename them", "organize my receipts folder", "my scan inbox is a mess", "group these receipts by vendor", "extract the date and total from these receipts". Trigger even when the user doesn't say the word "OCR" — a folder of jumbled `Scanned Document N.pdf` files or receipt photos is the cue.
---

# Receipt Sorter

Turn a pile of jumbled receipt scans into a clean, searchable archive: one PDF per
transaction, filed under `Vendor/YYYY-MM-DD Vendor $total.pdf`, with a `receipts.csv`
ledger and the original scans preserved.

This is a **local, privacy-preserving** pipeline — receipts are personal financial
documents, so never send them to a cloud OCR/receipt API. Everything below runs on the
user's Mac.

## Why the model does the OCR itself

For a normal batch (tens of pages), the most accurate path is: rasterize each page to a
PNG, run `tesseract` for a fast text baseline, then **read the page images yourself** to
confirm vendor, date, and total. Vision-language reading beats traditional OCR on faded
thermal and crumpled receipts, and it lets you reason about things tesseract can't —
which pages belong to the same receipt, whether a page is a return, and which return
matches which purchase. `tesseract` is the assist; your eyes are the authority. See
`references/ocr-tips.md` for the crop-and-read techniques that make faint totals legible.

## The pipeline

Work in phases and **show the user the plan before moving or renaming anything** — the
final step is destructive-ish (it reorganizes their files), and grouping decisions
(per-transaction vs per-vendor, where returns go) are theirs to make.

### 1. Inventory
Run `scripts/inventory.py <folder>` to list every PDF/image with page count and whether
it already has a text layer. Multi-page PDFs are the important signal: a single scan
often bundles several unrelated receipts (and even different vendors) across its pages.

### 2. OCR every page
Rasterize with Ghostscript and OCR with tesseract:
```
gs -q -dNOPAUSE -dBATCH -sDEVICE=png16m -r300 -sOutputFile='work/NAME__p%03d.png' "in.pdf"
tesseract page.png - --psm 4 -l eng
```
Then read the page images. For each page record: **vendor, date (the receipt's own
date), total, type** (purchase / return / refund / order / invoice), and note any page
that bundles multiple receipts or is a return that references an original
(Home Depot prints `ORIG REC: ... MM/DD/YY`). When a total or date is faint, crop and
enlarge that region and read it — don't silently guess. See `references/ocr-tips.md`.

### 3. Decide the grouping (with the user)
Default convention, which works well and is what to propose first:
- **One file per transaction.** Each purchase is its own PDF.
- **Returns/refunds are appended as extra pages** to the purchase they match (via the
  `ORIG REC` cross-reference or an obvious date/amount match). A return whose original
  isn't in the batch becomes its own `... return -$xx.xx.pdf` file.
- **Vendor subfolders.** Filename: `YYYY-MM-DD Vendor $total.pdf` (returns:
  `YYYY-MM-DD Vendor return -$xx.xx.pdf`).
- Confirm this vs. one-combined-file-per-vendor before building. Surface anything
  ambiguous (a vendor with many receipts, a multi-origin return) using the *actual*
  contents, not in the abstract.

Handle non-standard items explicitly and ask where they go:
- **Medical receipts** — often best grouped per patient (`Medical/<Patient Name>/`).
- **Product labels / box photos** — not purchases; a `Product references/` subfolder.
- **Undated online order screenshots** — keep them, but flag that the name can't carry a
  date (e.g. `Vendor $total (no date on receipt).pdf`).

### 4. Build the files
Write a JSON spec (see `examples/spec_example.json`) mapping each output file to its
source pages, then:
```
python3 scripts/build_receipts.py spec.json
```
It splits/recombines pages with `pypdf`, converts image sources to PDF, and **verifies
full coverage** — reporting any source page used twice or not at all (catch dropped
receipts and duplicate scans here).

### 5. Add a searchable text layer
```
scripts/text_layer.sh <output-folder>
```
Runs `ocrmypdf --skip-text` on every built PDF so the whole archive is full-text
searchable in Finder/Preview. (`--skip-text` leaves already-digital PDFs untouched.)

### 6. Archive originals + write the ledger
Move the source scans into `<dest>/_original scans/` (preserve, don't delete — let the
user verify first). Then:
```
python3 scripts/make_ledger.py <dest>
```
walks the final tree and writes `receipts.csv` (vendor, subgroup, date, total, type,
file) by parsing the filenames — a single source of truth that always matches disk.

## Principles that matter

- **Confirm before reorganizing.** Present the full inventory + proposed structure and
  get a yes. Moving someone's financial records is high-trust.
- **Never drop a page silently.** Account for every source page; if you intentionally
  skip one (e.g. a duplicate scan), say so and log it.
- **Flag low-confidence reads.** A faded total is better surfaced as "best read $179.97,
  please verify" than buried as fact. Note it in the ledger too.
- **Merge into an existing archive carefully.** If the destination already has receipts,
  match its vendor-folder names so new files land beside old ones; check its existing
  naming convention and reconcile with the user.
- **Tools:** `tesseract`, Ghostscript (`gs`), ImageMagick (`magick`), `pypdf`,
  `ocrmypdf`, `python3` — all via Homebrew. Install any that are missing with `brew` /
  `pip`. Fallback OCR for large batches: Apple Vision via `pip install ocrmac`
  (on-device).

## Reference
- `references/ocr-tips.md` — reading faint thermal receipts, identifying vendors from the
  store address when the logo won't OCR, matching returns to purchases, common date
  formats and gotchas.
- `examples/spec_example.json` — the build spec format.
