#!/usr/bin/env python3
"""
fill_ds11.py — Fill DS-11 U.S. passport application PDF from a YAML answers file.

Requirements:
    pip install pypdf pyyaml

Usage:
    # Download the blank DS-11 PDF first:
    #   curl -o ds11_pdf.PDF "https://eforms.state.gov/Forms/ds11_pdf.PDF"

    # (Optional) Inspect actual PDF field names — useful if fields don't fill:
    python3 fill_ds11.py --list-fields ds11_pdf.PDF

    # Fill the form:
    python3 fill_ds11.py \\
        --answers pax_ds11_answers.yaml \\
        --pdf ds11_pdf.PDF \\
        --out pax_ds11_filled.pdf
"""

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("pyyaml not installed — run: pip install pyyaml")

try:
    from pypdf import PdfReader, PdfWriter
except ImportError:
    sys.exit("pypdf not installed — run: pip install pypdf")


# ---------------------------------------------------------------------------
# Mapping: our YAML key paths  →  PDF form field names (verified against
# the actual DS-11 PDF field list via --list-fields).
# ---------------------------------------------------------------------------
FIELD_MAP_TEMPLATE = {
    # Applicant
    "Applicant Last Name":        ("applicant", "last_name"),
    "Applicant First Name":       ("applicant", "first_name"),
    "Applicant Middle Name":      ("applicant", "middle_name"),
    "Name of Applicant 2":        ("applicant", "full_name"),
    "Hair Color":                 ("applicant", "hair_color"),
    "Eye Color":                  ("applicant", "eye_color"),
    "Occupation":                 ("applicant", "occupation"),
    "Employer or School":         ("applicant", "employer_or_school"),
    # Mailing address (Applicant Address fields)
    "Applicant Address Street":   ("address", "street"),
    "Address Line 2":             ("address", "apt_unit"),
    "Applicant Address City":     ("address", "city"),
    "Applicant Address State":    ("address", "state"),
    "Applicant Address Zip Code": ("address", "zip"),
    "Applicant Address Country":  ("address", "country"),
    # Permanent / home address
    "Permanent Address Street":   ("permanent_address", "street"),
    "Permanent Address Apartment/Unit": ("permanent_address", "apt_unit"),
    "Permanent Address City":     ("permanent_address", "city"),
    "Permanent Address State":    ("permanent_address", "state"),
    "Permanent Address Zip Code": ("permanent_address", "zip"),
    # Contact
    "Applicant Email":            ("contact", "email"),
    # Travel
    "Countries to be visited":    ("travel", "countries"),
    "Travel Departure Date":      ("travel", "departure_date"),
    "Travel Return Date":         ("travel", "return_date"),
    # Emergency contact (name, phone, relationship — address handled as split below)
    "Emergency Contact Name":     ("emergency_contact", "name"),
    "Emergency Contact Phone":    ("emergency_contact", "phone"),
    "Relationship to Applicant":  ("emergency_contact", "relationship"),
    # Parent 1
    "Parent 1 Last Name":         ("parent_1", "last_name"),
    "Parent 1 DOB":               ("parent_1", "date_of_birth"),
    # Parent 2
    "Parent 2 Last Name":         ("parent_2", "last_name"),
    "Parent 2 DOB":               ("parent_2", "date_of_birth"),
}


def _bool_to_yes_no(val) -> str:
    if isinstance(val, bool):
        return "Yes" if val else "No"
    return str(val).strip()


def _sex_export(val: str) -> str:
    """Map M/F/Male/Female to PDF export value M or F."""
    return "M" if str(val).strip().upper().startswith("M") else "F"


def set_radio_button(writer, field_name: str, export_value: str) -> bool:
    """
    Set a radio-button group or standalone checkbox by its export value.

    For radio groups with /Kids, each kid's /AS is toggled on/off and the
    parent field's /V is updated.  For standalone checkboxes (no kids), the
    widget's own /V and /AS are updated directly.
    Returns True if at least one widget was found and updated.
    """
    from pypdf.generic import NameObject, IndirectObject as IO

    on  = NameObject(f"/{export_value}")
    off = NameObject("/Off")
    hit = False

    for page in writer.pages:
        annots = page.get("/Annots", [])
        if not annots:
            continue
        for annot_ref in annots:
            obj = annot_ref.get_object() if isinstance(annot_ref, IO) else annot_ref

            # Resolve field name (own /T or parent's /T)
            t = obj.get("/T")
            parent_ref = obj.get("/Parent")
            parent = None
            if parent_ref is not None:
                parent = parent_ref.get_object() if isinstance(parent_ref, IO) else parent_ref
                if t is None:
                    t = parent.get("/T")

            if str(t) != field_name:
                continue

            # Inspect appearance states of this widget
            ap = obj.get("/AP", {})
            n_dict = ap.get("/N", {})
            states = [str(k) for k in n_dict.keys()] if hasattr(n_dict, "keys") else []

            if not states:
                # No appearance dict — set /V directly on this node
                obj[NameObject("/V")]  = on
                obj[NameObject("/AS")] = on
                hit = True
            elif f"/{export_value}" in states:
                obj[NameObject("/AS")] = on
                # Propagate /V to the field root
                target = parent if parent is not None else obj
                target[NameObject("/V")] = on
                hit = True
            else:
                # This is a sibling radio option — turn it off
                obj[NameObject("/AS")] = off

    return hit


def list_fields(pdf_path: str) -> None:
    reader = PdfReader(pdf_path)
    fields = reader.get_fields()
    if not fields:
        print("No fillable fields found — the PDF may not be a fillable form.")
        return
    print(f"\n{len(fields)} fields found:\n")
    for name in sorted(fields.keys()):
        field = fields[name]
        ftype = str(field.get("/FT", "?"))
        opts = field.get("/Opt", [])
        print(f"  {name!r:55s} type={ftype:6s}  options={opts}")
    print()


def resolve(answers: dict, path: tuple) -> str:
    section, key = path
    val = answers.get(section, {}).get(key)
    if val is None:
        return ""
    if isinstance(val, bool):
        return "Yes" if val else "No"
    return str(val).strip()


def build_place_of_birth(answers: dict, section: str) -> str:
    s = answers.get(section, {})
    city = s.get("place_of_birth_city", "") or ""
    region = s.get("place_of_birth_state_or_country", "") or ""
    return f"{city}, {region}".strip(", ")


def split_dob(dob_str: str) -> tuple[str, str, str]:
    """Return (MM, DD, YYYY) zero-padded from MM/DD/YYYY."""
    parts = dob_str.replace("-", "/").split("/")
    if len(parts) == 3:
        return parts[0].zfill(2), parts[1].zfill(2), parts[2]
    return "", "", ""


def split_ssn(ssn: str) -> tuple[str, str, str]:
    """Return (area, group, serial) from 9-digit SSN string."""
    s = ssn.replace("-", "").replace(" ", "")
    if len(s) == 9:
        return s[:3], s[3:5], s[5:]
    return s, "", ""


def split_phone(phone: str) -> tuple[str, str, str]:
    """Return (area, exchange, number) from a phone string."""
    digits = "".join(c for c in phone if c.isdigit())
    if digits.startswith("1") and len(digits) == 11:
        digits = digits[1:]
    if len(digits) == 10:
        return digits[:3], digits[3:6], digits[6:]
    return digits, "", ""


def build_text_field_values(answers: dict) -> dict:
    """Return {pdf_field_name: value} for all plain text fields."""
    fields: dict[str, str] = {}

    for pdf_name, path in FIELD_MAP_TEMPLATE.items():
        val = resolve(answers, path)
        if val:
            fields[pdf_name] = val

    # Place of birth (composite)
    pob_child = build_place_of_birth(answers, "applicant")
    if pob_child:
        fields["Applicant Place of Birth"] = pob_child

    pob_p1 = build_place_of_birth(answers, "parent_1")
    if pob_p1:
        fields["Parent 1 Place of Birth"] = pob_p1

    pob_p2 = build_place_of_birth(answers, "parent_2")
    if pob_p2:
        fields["Parent 2 Place of Birth"] = pob_p2

    # DOB — split boxes AND a combined field that appears at the top of the form
    dob_raw = resolve(answers, ("applicant", "date_of_birth"))
    if dob_raw:
        m, d, y = split_dob(dob_raw)
        fields["Applicant DOB M"] = m
        fields["Applicant DOB D"] = d
        fields["Applicant DOB Y"] = y
        fields["Applicant DOB 2"] = f"{m}/{d}/{y}"  # combined field top-right

    # SSN split
    ssn_raw = resolve(answers, ("applicant", "ssn"))
    if ssn_raw and ssn_raw.lower() != "none":
        a, g, s = split_ssn(ssn_raw)
        fields["Applicant SSN 1"] = a
        fields["Applicant SSN 2"] = g
        fields["Applicant SSN 3"] = s

    # Height (single combined field)
    h_ft = resolve(answers, ("applicant", "height_feet"))
    h_in = resolve(answers, ("applicant", "height_inches"))
    if h_ft or h_in:
        fields["Height"] = f"{h_ft}' {h_in}\""

    # Primary phone split
    ph1 = resolve(answers, ("contact", "primary_phone"))
    if ph1:
        a, e, n = split_phone(ph1)
        fields["Applicant Phone 1"] = a
        fields["Applicant Phone 2"] = e
        fields["Applicant Phone 3"] = n

    # Secondary phone (full string — its own text field)
    ph2 = resolve(answers, ("contact", "secondary_phone"))
    if ph2:
        fields["Applicant Additional Contact Phone Numbers"] = ph2

    # Parent FM Name (first + middle combined)
    p1_fm = " ".join(filter(None, [
        resolve(answers, ("parent_1", "first_name")),
        resolve(answers, ("parent_1", "middle_name")),
    ]))
    if p1_fm:
        fields["Parent 1 FM Name"] = p1_fm

    p2_fm = " ".join(filter(None, [
        resolve(answers, ("parent_2", "first_name")),
        resolve(answers, ("parent_2", "middle_name")),
    ]))
    if p2_fm:
        fields["Parent 2 FM Name"] = p2_fm

    # Emergency contact split address
    ec = answers.get("emergency_contact", {})
    for yaml_key, pdf_name in [
        ("street",   "Emergency Contact Address"),
        ("apt_unit", "Emergency Contact Apartment/Unit"),
        ("city",     "Emergency Contact City"),
        ("state",    "Emergency Contact State"),
        ("zip",      "Emergency Contact Zip Code"),
    ]:
        val = str(ec.get(yaml_key, "") or "")
        if val:
            fields[pdf_name] = val

    # Previous passport — text fields only (book/card name)
    pp = answers.get("previous_passport", {})
    if pp.get("had_book"):
        name_used = pp.get("book_name_used", "")
        if name_used:
            fields["Your name as printed on your most recent U.S. passport book and/or passport card"] = str(name_used)
    if pp.get("had_card"):
        card_name = pp.get("card_name_used", "")
        if card_name:
            fields["Name as printed on your most recent passport card"] = str(card_name)

    # Travel: write "none" explicitly when no plans (form instruction)
    if not (answers.get("travel", {}) or {}).get("countries"):
        fields["Countries to be visited"] = "none"

    return fields


def build_button_values(answers: dict) -> dict[str, str]:
    """
    Return {pdf_field_name: export_value} for all radio/checkbox fields.
    Export values come directly from the PDF's /AP/N keys (no leading slash).
    """
    btns: dict[str, str] = {}

    # Applicant sex
    sex = (answers.get("applicant") or {}).get("sex", "")
    if sex:
        btns["Gender"] = _sex_export(sex)

    # Married
    married = (answers.get("applicant") or {}).get("married")
    if married is not None:
        btns["Ever Married"] = _bool_to_yes_no(married)

    # Parent sex + citizenship
    p1 = answers.get("parent_1") or {}
    if p1.get("sex"):
        btns["Parent 1 Gender"] = _sex_export(p1["sex"])
    if p1.get("us_citizen") is not None:
        btns["Parent 1 US Citizen"] = _bool_to_yes_no(p1["us_citizen"])

    p2 = answers.get("parent_2") or {}
    if p2.get("sex"):
        btns["Parent 2 Gender"] = _sex_export(p2["sex"])
    if p2.get("us_citizen") is not None:
        btns["Parent 2 US Citizen"] = _bool_to_yes_no(p2["us_citizen"])

    # Ever applied / issued (previous passport)
    pp = answers.get("previous_passport") or {}
    had_any = pp.get("had_book") or pp.get("had_card")
    btns["Ever Applied or Issued"] = "Yes" if had_any else "No"

    # Book status checkbox
    if pp.get("had_book"):
        disp = (pp.get("book_disposition") or "").lower()
        if "submit" in disp:   btns["Book Status Submitting"] = "Submitting"
        elif "lost" in disp:   btns["Book Status Lost"]       = "Lost"
        elif "stolen" in disp: btns["Book Status Stolen"]     = "Stolen"
        elif "possess" in disp: btns["Book Status Possession"] = "Possession"

    # Card status checkbox
    if pp.get("had_card"):
        disp = (pp.get("card_disposition") or "").lower()
        if "submit" in disp:   btns["Card Status Submitting"] = "Submitting"
        elif "lost" in disp:   btns["Card Status Lost"]       = "Lost"
        elif "stolen" in disp: btns["Card Status Stolen"]     = "Stolen"
        elif "possess" in disp: btns["Card Status Possession"] = "Possession"

    # Secondary phone type (Additional # radio)
    ph2_type = (answers.get("contact") or {}).get("secondary_phone_type", "")
    if ph2_type:
        # Normalize: Cell / Home / Work / Other
        t = ph2_type.strip().title()
        if t in ("Cell", "Mobile"):
            btns["Additional #"] = "Cell"
        elif t == "Home":
            btns["Additional #"] = "Home"
        elif t == "Work":
            btns["Additional #"] = "Work"

    # Passport type (Selection: Book / Card / Both)
    pt = answers.get("passport_type") or {}
    want_book = bool(pt.get("book"))
    want_card = bool(pt.get("card"))
    if want_book and want_card:
        btns["Selection"] = "Both"
    elif want_book:
        btns["Selection"] = "Book"
    elif want_card:
        btns["Selection"] = "Card"

    # Book size — always Regular unless specified
    btns["Regular or Large Book"] = "Regular"

    return btns


def fuzzy_match(our_name: str, actual_names: set[str]) -> str | None:
    if our_name in actual_names:
        return our_name
    lower = {n.lower(): n for n in actual_names}
    return lower.get(our_name.lower())


def fill_form(answers: dict, pdf_path: str, output_path: str) -> None:
    reader = PdfReader(pdf_path)
    actual_fields = reader.get_fields() or {}
    actual_names = set(actual_fields.keys())

    # ── Text fields ────────────────────────────────────────────────────
    text_values = build_text_field_values(answers)
    matched: dict[str, str] = {}
    unmatched_text: list[str] = []
    for our_name, value in text_values.items():
        real_name = fuzzy_match(our_name, actual_names)
        if real_name:
            matched[real_name] = value
        else:
            unmatched_text.append(our_name)

    writer = PdfWriter()
    writer.append(reader)
    for page in writer.pages:
        writer.update_page_form_field_values(page, matched)

    # ── Radio / checkbox fields ────────────────────────────────────────
    button_values = build_button_values(answers)
    btn_hit: list[str] = []
    btn_miss: list[str] = []
    for field_name, export_value in button_values.items():
        if set_radio_button(writer, field_name, export_value):
            btn_hit.append(field_name)
        else:
            btn_miss.append(field_name)

    with open(output_path, "wb") as f:
        writer.write(f)

    total_filled = len(matched) + len(btn_hit)
    total_missed = len(unmatched_text) + len(btn_miss)
    print(f"\nFilled PDF → {output_path}")
    print(f"Text fields:   {len(matched)} filled  |  {len(unmatched_text)} unmatched")
    print(f"Button fields: {len(btn_hit)} filled  |  {len(btn_miss)} unmatched")
    print(f"Total: {total_filled} filled  |  {total_missed} unmatched")
    if unmatched_text:
        print("\nUnmatched text fields:")
        for n in unmatched_text:
            print(f"  {n!r}")
    if btn_miss:
        print("\nUnmatched button fields:")
        for n in btn_miss:
            print(f"  {n!r}")
    print("\nREMINDER: Do NOT sign the form until instructed by the acceptance agent.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fill DS-11 U.S. passport application PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--list-fields", metavar="PDF",
                        help="List all fillable field names in the PDF and exit")
    parser.add_argument("--answers", metavar="YAML",
                        help="Path to pax_ds11_answers.yaml")
    parser.add_argument("--pdf", metavar="PDF",
                        help="Path to blank DS-11 PDF")
    parser.add_argument("--out", metavar="PDF", default="pax_ds11_filled.pdf",
                        help="Output path (default: pax_ds11_filled.pdf)")
    args = parser.parse_args()

    if args.list_fields:
        list_fields(args.list_fields)
        return

    if not args.answers or not args.pdf:
        parser.print_help()
        sys.exit(1)

    answers_path = Path(args.answers)
    if not answers_path.exists():
        sys.exit(f"Answers file not found: {answers_path}")

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        sys.exit(
            f"PDF not found: {pdf_path}\n"
            'Download it with:\n  curl -o ds11_pdf.PDF "https://eforms.state.gov/Forms/ds11_pdf.PDF"'
        )

    with open(answers_path) as f:
        answers = yaml.safe_load(f)

    fill_form(answers, str(pdf_path), args.out)


if __name__ == "__main__":
    main()
