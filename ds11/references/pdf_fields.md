# DS-11 PDF Field Reference

Verified against the official DS-11 PDF from `https://eforms.state.gov/Forms/ds11_pdf.PDF`
using `fill_ds11.py --list-fields ds11_pdf.PDF` and `/AP/N` inspection for radio buttons.

Run `--list-fields` again if you see unexpected unmatched fields — the State Dept occasionally updates the form.

---

## Text Fields

### Applicant

| PDF Field Name | YAML Key | Notes |
|---|---|---|
| `Applicant Last Name` | `applicant.last_name` | |
| `Applicant First Name` | `applicant.first_name` | |
| `Applicant Middle Name` | `applicant.middle_name` | |
| `Name of Applicant 2` | `applicant.full_name` | Format: "Last, First Middle" |
| `Applicant DOB M` | *derived* | Month, zero-padded (MM) |
| `Applicant DOB D` | *derived* | Day, zero-padded (DD) |
| `Applicant DOB Y` | *derived* | Year (YYYY) |
| `Applicant DOB 2` | *derived* | Combined MM/DD/YYYY — top-right field |
| `Applicant SSN 1` | *derived* | First 3 digits of SSN |
| `Applicant SSN 2` | *derived* | Middle 2 digits of SSN |
| `Applicant SSN 3` | *derived* | Last 4 digits of SSN |
| `Applicant Place of Birth` | *derived* | Composite: `city, state_or_country` |
| `Hair Color` | `applicant.hair_color` | |
| `Eye Color` | `applicant.eye_color` | |
| `Height` | *derived* | Format: `3' 9.5"` |
| `Occupation` | `applicant.occupation` | |
| `Employer or School` | `applicant.employer_or_school` | |

### Mailing Address

| PDF Field Name | YAML Key |
|---|---|
| `Applicant Address Street` | `address.street` |
| `Address Line 2` | `address.apt_unit` |
| `Applicant Address City` | `address.city` |
| `Applicant Address State` | `address.state` |
| `Applicant Address Zip Code` | `address.zip` |
| `Applicant Address Country` | `address.country` |

### Permanent Address

| PDF Field Name | YAML Key |
|---|---|
| `Permanent Address Street` | `permanent_address.street` |
| `Permanent Address Apartment/Unit` | `permanent_address.apt_unit` |
| `Permanent Address City` | `permanent_address.city` |
| `Permanent Address State` | `permanent_address.state` |
| `Permanent Address Zip Code` | `permanent_address.zip` |

### Contact

| PDF Field Name | YAML Key | Notes |
|---|---|---|
| `Applicant Email` | `contact.email` | |
| `Applicant Phone 1` | *derived* | Area code (3 digits) |
| `Applicant Phone 2` | *derived* | Exchange (3 digits) |
| `Applicant Phone 3` | *derived* | Number (4 digits) |
| `Applicant Additional Contact Phone Numbers` | `contact.secondary_phone` | Full number string |

### Travel

| PDF Field Name | YAML Key |
|---|---|
| `Countries to be visited` | `travel.countries` (or "none" if blank) |
| `Travel Departure Date` | `travel.departure_date` |
| `Travel Return Date` | `travel.return_date` |

### Emergency Contact

| PDF Field Name | YAML Key |
|---|---|
| `Emergency Contact Name` | `emergency_contact.name` |
| `Emergency Contact Address` | `emergency_contact.street` |
| `Emergency Contact Apartment/Unit` | `emergency_contact.apt_unit` |
| `Emergency Contact City` | `emergency_contact.city` |
| `Emergency Contact State` | `emergency_contact.state` |
| `Emergency Contact Zip Code` | `emergency_contact.zip` |
| `Emergency Contact Phone` | `emergency_contact.phone` |
| `Relationship to Applicant` | `emergency_contact.relationship` |

### Previous Passport

| PDF Field Name | YAML Key |
|---|---|
| `Your name as printed on your most recent U.S. passport book and/or passport card` | `previous_passport.book_name_used` |
| `Name as printed on your most recent passport card` | `previous_passport.card_name_used` |

### Parents

| PDF Field Name | YAML Key | Notes |
|---|---|---|
| `Parent 1 Last Name` | `parent_1.last_name` | |
| `Parent 1 FM Name` | *derived* | `first_name + " " + middle_name` |
| `Parent 1 DOB` | `parent_1.date_of_birth` | |
| `Parent 1 Place of Birth` | *derived* | Composite: city + state/country |
| `Parent 2 Last Name` | `parent_2.last_name` | |
| `Parent 2 FM Name` | *derived* | `first_name + " " + middle_name` |
| `Parent 2 DOB` | `parent_2.date_of_birth` | |
| `Parent 2 Place of Birth` | *derived* | Composite: city + state/country |

---

## Radio Button / Checkbox Fields

Radio buttons require direct `/AS` manipulation — `pypdf`'s `update_page_form_field_values`
does not handle them. The `set_radio_button()` function in `fill_ds11.py` handles this.

Export values come from the PDF's `/AP/N` dictionary (verified via inspection).

| PDF Field Name | Export Values | YAML Source | Notes |
|---|---|---|---|
| `Gender` | `M` / `F` | `applicant.sex` | Applicant's sex |
| `Ever Married` | `Yes` / `No` | `applicant.married` | |
| `Parent 1 Gender` | `M` / `F` | `parent_1.sex` | |
| `Parent 1 US Citizen` | `Yes` / `No` | `parent_1.us_citizen` | |
| `Parent 2 Gender` | `M` / `F` | `parent_2.sex` | |
| `Parent 2 US Citizen` | `Yes` / `No` | `parent_2.us_citizen` | |
| `Ever Applied or Issued` | `Yes` / `No` | derived from `previous_passport.had_book` or `had_card` | |
| `Book Status Submitting` | `Submitting` | `previous_passport.book_disposition` | Standalone checkbox |
| `Book Status Lost` | `Lost` | `previous_passport.book_disposition` | Standalone checkbox |
| `Book Status Stolen` | `Stolen` | `previous_passport.book_disposition` | Standalone checkbox |
| `Book Status Possession` | `Possession` | `previous_passport.book_disposition` | Standalone checkbox |
| `Card Status Submitting` | `Submitting` | `previous_passport.card_disposition` | Standalone checkbox |
| `Card Status Lost` | `Lost` | `previous_passport.card_disposition` | Standalone checkbox |
| `Card Status Stolen` | `Stolen` | `previous_passport.card_disposition` | Standalone checkbox |
| `Card Status Possession` | `Possession` | `previous_passport.card_disposition` | Standalone checkbox |
| `Additional #` | `Cell` / `Home` / `Work` / `Other` | `contact.secondary_phone_type` | Secondary phone type |
| `Selection` | `Book` / `Card` / `Both` | derived from `passport_type.book` + `passport_type.card` | |
| `Regular or Large Book` | `Regular` / `Large` | hardcoded `Regular` | |

---

## Unimplemented / Future Fields

These fields exist in the PDF but are not mapped by the current script (not needed for DS-11 child applications):

- Divorced / Widow/Divorce Date
- Current Spouse fields
- Alien Number
- List all other names you have used

When adding DS-82 support, the `previous_passport` section will need additional handling for the `Your name as printed on your most recent U.S. passport book and/or passport card` combined field.
