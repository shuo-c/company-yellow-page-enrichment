# Field Protection Rules

Fields listed here should be copied as-is (no translation), unless explicitly overridden.

## Default protected fields
- company_key
- company_name
- legal_name
- address
- city
- state
- postcode
- country
- phone
- email
- website
- url
- contact_name
- latitude
- longitude

## Pattern-level protection
Even if field is not in protected list, skip translating values that match:
- URL pattern
- Email pattern
- Phone-number pattern

## Optional per-run override
Runtime args can override defaults:
- `--no-translate-fields company_name,address,website,url`

## Safety rule
If uncertain whether a value is a proper noun or identifier, prefer keep-as-is and flag in report.
