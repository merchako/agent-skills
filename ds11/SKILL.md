---
name: ds11
description: Fill out a U.S. passport application end-to-end — handles DS-11 (new passport, first-time applicants, children under 16) and is structured for future DS-82 (adult renewal) support. Guides the user through all sections via a Q&A walkthrough or generates a blank template; writes answers to either a YAML or Markdown file; verifies completeness and format; then fills the official State Department PDF using a bundled Python script. Use this skill whenever someone wants to apply for a new U.S. passport, fill out a DS-11 form, prepare a passport application for a child or minor, collect the data needed for a passport, or generate a filled passport application PDF ready to print and submit.
---

# DS-11 Passport Application

This skill collects application data, writes it to a YAML or Markdown answers file, validates it, and generates a filled PDF using the official State Department DS-11 form.

See `examples/` for complete filled examples (fake data), `references/pdf_fields.md` for the verified field-name map, and `scripts/fill_ds11.py` for the PDF filler.

---

## Step 0: Identify the form

Ask which form the user needs:

- **DS-11** — New passport. Required for all first-time applicants and anyone under 16, even if they had a previous passport. Must be submitted in person with the child and both parents/guardians present (or a notarized DS-3053 from the absent parent).
- **DS-82** — Adult renewal (applicant was 16+ when last passport was issued, issued within 15 years, not lost/stolen). *Not yet implemented — tell the user DS-82 support is planned and guide them through DS-11 if applicable, or help them understand the renewal requirements.*

If the user isn't sure: ask whether this is a first passport or a renewal, and whether the applicant is under 16.

---

## Step 1: Choose mode and format

Ask two quick questions before collecting any data:

**Mode:**
- **(a) Guided walkthrough** — You ask each section's questions and build the file on their behalf.
- **(b) Empty template** — You generate a blank file they fill in directly and bring back.

**Format:**
- **(a) YAML** — Structured file with inline comments explaining each field. Best for users comfortable with a text editor; used directly by the filler script.
- **(b) Markdown tables** — Human-friendly tables, easier to fill in visually. You'll translate to YAML before running the script.

Also ask: where should the files be saved? Default to the current working directory.

---

## Step 2: Collect or generate answers

### Mode (a): Guided walkthrough

Walk through sections one at a time, confirming each before moving on. Build the answers file as you go.

**Section 1 — Applicant:**
Last name, first name, middle name, full name (Last, First Middle), DOB (MM/DD/YYYY), place of birth (city + state or country), SSN (9 digits — tell them to strip dashes; write "None" if not yet issued), sex (M/F/X), hair color, eye color, height (feet + inches separately), occupation, employer or school, ever married?

**Section 2 — Mailing address** (where passport should be sent):
Street, apt/unit, city, state, zip, country (blank if USA).
*If they mention possibly moving before the passport arrives: use current address; if they relocate during processing, call 1-877-487-2778 to update the State Dept before it ships.*

**Section 3 — Permanent address** (physical home, if different from mailing):
Same fields as mailing. Required when mailing address is a PO Box or differs from home.

**Section 4 — Contact:**
Email, primary phone + type (Cell/Home/Work), secondary phone + type.

**Section 5 — Travel plans:**
Countries to visit, departure date (MM/DD/YYYY), return date. If no specific plans, leave blank (the script writes "none" automatically).

**Section 6 — Emergency contact:**
Name, street, apt/unit, city, state, zip, phone, relationship to applicant.

**Section 7 — Previous U.S. passports:**
Ever issued a passport book? If yes: name used, book number, issue date (MM/DD/YYYY), disposition (Submitting with application / Lost / Stolen / In my possession).
Ever issued a passport card? Same fields.

**Section 8 — Parent 1 (signing parent / father):**
Last name, first + middle name, sex, DOB (MM/DD/YYYY), place of birth (city + state/country), U.S. citizen? If yes: by birth or naturalization. Naturalization certificate number if applicable.

**Section 9 — Parent 2 (mother / other parent):**
Same fields as Parent 1.

**Section 10 — Passport type:**
Book ($135 + $35 acceptance fee), card ($30 extra, wallet-size, land/sea borders only), or both?

### Mode (b): Empty template

Generate an empty file based on the chosen format:
- **YAML**: use `examples/ds11_answers_example.yaml` as your template — read it, strip all values, keep all keys and comments intact.
- **Markdown**: create tables matching `examples/ds11_tables_example.md`, leaving value cells blank.

Tell the user to fill it in and return when ready.

---

## Step 3: Verify answers

Before generating the PDF, check for issues:

**Required fields** (flag if missing):
- Applicant: last name, first name, DOB, place of birth, SSN (or "None"), sex, height (both feet and inches)
- Mailing address: street, city, state, zip
- At least one parent: last name, first/middle name, DOB, sex, U.S. citizen status
- Emergency contact: name, phone

**Format rules:**
- Dates → `MM/DD/YYYY` (e.g. `07/22/2020`, not `July 22 2020` or `2020-07-22`)
- SSN → exactly 9 digits, no dashes (e.g. `513294867`); strip dashes if the user wrote them
- Height → both feet and inches present
- Previous passport → if `had_book` or `had_card` is true, `name_used` and `disposition` must be filled

Surface all issues clearly and offer to fix them before proceeding.

---

## Step 4: Generate the PDF

**Requirements:** `uv` (preferred) or Python 3 with `pip install pyyaml pypdf`.

**1. Download the blank DS-11** (skip if already present):
```bash
curl -o ds11_pdf.PDF "https://eforms.state.gov/Forms/ds11_pdf.PDF"
```

**2. If answers are in Markdown format**, convert to YAML first — read the tables and write an equivalent `.yaml` file matching the structure in `examples/ds11_answers_example.yaml`.

**3. Run the filler:**
```bash
UV_CACHE_DIR=/tmp/ds11env uv run --with pyyaml --with pypdf \
  python3 PATH_TO_SKILL/scripts/fill_ds11.py \
  --answers answers.yaml \
  --pdf ds11_pdf.PDF \
  --out applicant_ds11_filled.pdf
```

Replace `PATH_TO_SKILL` with the actual path to this skill's directory. The script reports filled/unmatched counts. If the PDF field names have changed (form was updated), run `--list-fields ds11_pdf.PDF` and compare against `references/pdf_fields.md`.

**Reminder to user:** The filled PDF requires a **wet-ink signature at the acceptance facility**. Do not sign it beforehand — it will invalidate the form.

---

## Step 5: Optional visual verification

After the PDF is generated, offer to check it:

> "Would you like me to verify the filled form? Open the PDF, screenshot any pages you want checked, and share the image."

When reviewing a screenshot:
1. Cross-reference visible text fields against the answers file — flag anything blank that should be filled, or any value that looks wrong.
2. Check radio buttons specifically (Sex, U.S. Citizen, Married, Passport Type, Phone Type) — these are the most likely to need manual correction since they require low-level PDF manipulation.
3. Note any fields that appear unfilled and suggest using `--list-fields` if field names may have changed.

---

## Extensibility: DS-82 (renewal)

DS-82 differences from DS-11:
- No parental information sections
- Applicant must have been 16+ when last passport was issued
- Applicant submits the old passport with the application
- Can be mailed (no in-person requirement)
- Different fees (~$130, no acceptance fee)

To add DS-82 support: create `references/ds82.md` with DS-82-specific field mappings, add `scripts/fill_ds82.py`, and update Step 0 to route there. The YAML structure can share the `applicant`, `address`, `contact`, and `travel` sections; DS-82 replaces `parent_1`/`parent_2` with a `previous_passport` section that includes the submitted book details.

---

## Key reminders for DS-11 in-person submission

- Both parents must appear with the child, OR the absent parent submits a notarized **DS-3053 Statement of Consent**
- Photo: 2"×2", taken within 6 months, white/off-white background, full face
- Bring the original birth certificate (raised seal) + a photocopy — originals are returned
- Child passports are valid **5 years** only (not 10)
- Fees: check/money order payable to "U.S. Department of State"; note child's name and DOB on memo line
