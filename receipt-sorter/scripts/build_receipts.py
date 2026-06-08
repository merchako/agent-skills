#!/usr/bin/env python3
"""Build organized receipt PDFs from a JSON spec.

Usage: python3 build_receipts.py spec.json

Spec format (see examples/spec_example.json):
{
  "dest": "/abs/path/to/output/root",
  "outputs": [
    {"folder": "Home Depot",
     "name": "2020-01-04 Home Depot $17.74 (+return).pdf",
     "pages": [{"src": "/abs/Scanned Document 5.pdf", "page": 12},
               {"src": "/abs/Scanned Document 5.pdf", "page": 13}]},
    {"folder": "Uniqlo",
     "name": "2020-12-14 Uniqlo $114.86.pdf",
     "pages": [{"src": "/abs/receipt.jpeg"}]}
  ]
}

- `page` is 1-indexed; omit it for single-image sources.
- Image sources (.jpg/.png/.jpeg/.tif/.heic) are converted to a PDF page via ImageMagick.
- Folders may be nested (e.g. "Medical/Megan Mercado").
- Verifies coverage: reports source pages used more than once or never (catches dropped
  receipts and duplicate scans). Intentional drops should be noted by the caller.
"""
import os, sys, json, subprocess, tempfile
from collections import Counter

IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".heic", ".bmp", ".gif")

def main():
    if len(sys.argv) < 2:
        sys.exit("usage: build_receipts.py spec.json")
    spec = json.load(open(sys.argv[1]))
    dest = spec["dest"]
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        sys.exit("pypdf not installed — run: pip install pypdf")

    readers = {}
    def reader(path):
        if path not in readers:
            readers[path] = PdfReader(path)
        return readers[path]

    used = Counter()        # (src,page) -> count, for PDF sources
    seen_sources = set()
    built = []
    tmpfiles = []

    for out in spec["outputs"]:
        outdir = os.path.join(dest, out["folder"])
        os.makedirs(outdir, exist_ok=True)
        w = PdfWriter()
        for pg in out["pages"]:
            src = pg["src"]
            seen_sources.add(src)
            if src.lower().endswith(IMG_EXT):
                tf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                tf.close(); tmpfiles.append(tf.name)
                subprocess.run(["magick", src, "-auto-orient", tf.name], check=True)
                for p in reader(tf.name).pages:
                    w.add_page(p)
            else:
                page = pg["page"]
                w.add_page(reader(src).pages[page - 1])
                used[(src, page)] += 1
        outpath = os.path.join(outdir, out["name"])
        with open(outpath, "wb") as fh:
            w.write(fh)
        built.append(outpath)

    for t in tmpfiles:
        try: os.unlink(t)
        except OSError: pass

    print(f"Built {len(built)} files into {dest}")

    # coverage report for PDF sources
    dupes = {k: v for k, v in used.items() if v > 1}
    if dupes:
        print("\n⚠ Source pages used more than once (check for unintended reuse):")
        for (s, p), n in sorted(dupes.items()):
            print(f"  {os.path.basename(s)} p{p}  ×{n}")
    missing = []
    for src in seen_sources:
        if src.lower().endswith(IMG_EXT):
            continue
        total = len(reader(src).pages)
        for i in range(1, total + 1):
            if (src, i) not in used:
                missing.append((src, i))
    if missing:
        print("\n⚠ Source pages NOT used (dropped — confirm each is intentional):")
        for s, p in sorted(missing):
            print(f"  {os.path.basename(s)} p{p}")
    if not dupes and not missing:
        print("Coverage: every source page used exactly once. ✓")

if __name__ == "__main__":
    main()
