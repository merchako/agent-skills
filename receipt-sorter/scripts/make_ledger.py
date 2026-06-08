#!/usr/bin/env python3
"""Write receipts.csv by walking the organized output tree and parsing filenames.

Usage: python3 make_ledger.py <dest-root>

Parses files named like:
  2020-01-04 Home Depot $17.74 (+return).pdf
  2021-07-30 Target return -$129.90.pdf
  Medical/Megan Mercado/2021-01-19 Kirkwood Eye Center $236.70.pdf

Filenames are the single source of truth, so the ledger always matches what's on disk.
Skips the `_original scans/` archive.
"""
import os, re, sys, csv
from collections import Counter

AMT = re.compile(r'(-?)\$([\d,]+\.\d{2})')
DATE = re.compile(r'^(\d{4}-\d{2}-\d{2})')

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: make_ledger.py <dest-root>")
    dest = sys.argv[1]
    rows = []
    for dirpath, _dirs, files in os.walk(dest):
        if "_original scans" in dirpath:
            continue
        for fn in files:
            if not fn.lower().endswith(".pdf"):
                continue
            rel = os.path.relpath(dirpath, dest)
            if rel == ".":
                continue
            parts = rel.split(os.sep)
            vendor = parts[0]
            sub = parts[1] if len(parts) > 1 else ""
            md = DATE.match(fn)
            date = md.group(1) if md else ""
            ms = AMT.findall(fn)
            total = ""
            if ms:
                sign, num = ms[-1]
                total = ("-" if sign else "") + num.replace(",", "")
            low = fn.lower()
            if " return " in low or low.endswith("return.pdf") or total.startswith("-"):
                typ = "return"
            elif "(+return)" in low:
                typ = "purchase (+return)"
            elif "gift order" in low or " order " in low:
                typ = "order"
            elif vendor == "Product references":
                typ = "product label"
            elif vendor == "Medical":
                typ = "medical"
            else:
                typ = "purchase"
            rows.append([vendor, sub, date, total, typ, fn])

    rows.sort(key=lambda r: (r[0], r[1], r[2], r[5]))
    out = os.path.join(dest, "receipts.csv")
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["vendor", "subgroup", "date", "total_usd", "type", "file"])
        w.writerows(rows)
    print(f"Wrote {out} with {len(rows)} rows.")
    for k, n in sorted(Counter(r[0] for r in rows).items()):
        print(f"  {k}: {n}")

if __name__ == "__main__":
    main()
