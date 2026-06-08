#!/usr/bin/env python3
"""Inventory a folder of receipt scans: page counts + whether each has a text layer.

Usage: python3 inventory.py <folder>

Multi-page PDFs are flagged because a single scan often bundles several unrelated
receipts (and even different vendors) across its pages — those are the ones that need
splitting downstream.
"""
import os, sys

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: inventory.py <folder>")
    folder = sys.argv[1]
    try:
        from pypdf import PdfReader
    except ImportError:
        sys.exit("pypdf not installed — run: pip install pypdf")

    files = sorted(
        f for f in os.listdir(folder)
        if f.lower().endswith((".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic"))
        and not f.startswith(".")
    )
    if not files:
        print("No PDFs/images found in", folder)
        return

    print(f"{'pages':>5}  {'text':>5}  file")
    print("-" * 60)
    multipage = []
    for f in files:
        path = os.path.join(folder, f)
        if f.lower().endswith(".pdf"):
            try:
                r = PdfReader(path)
                pc = len(r.pages)
                txt = sum(len((p.extract_text() or "").strip()) for p in r.pages)
                has_text = "yes" if txt > 40 else "no"
            except Exception as e:
                pc, has_text = "ERR", str(e)[:20]
            if isinstance(pc, int) and pc > 1:
                multipage.append((f, pc))
        else:
            pc, has_text = "img", "no"
        print(f"{str(pc):>5}  {has_text:>5}  {f}")

    if multipage:
        print("\nMulti-page PDFs (likely bundle several receipts — inspect each page):")
        for f, pc in multipage:
            print(f"  [{pc} pp] {f}")

if __name__ == "__main__":
    main()
