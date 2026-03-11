---
name: yellow-page-translator
description: Batch-translate Yellow Pages company text fields (for example intro/description) from English to Chinese or other target languages, with resume support, protected-field handling, review polishing, merge, and summary report generation. Use when users ask to fetch/split records, run translate/review stages, continue from pending/error batches, and produce final deliverable files (jsonl/csv/sql-ready outputs).
---

# Yellow Pages Translation Assistant

Execute an end-to-end translation pipeline for company profile fields, and fetch single-company full detail snapshots from Supabase REST GET into JSON/CSV with optional translated value columns.

## Pipeline Stages

0. **single-company detail fetch (optional)**
   - Run `scripts/fetch_company_detail.py`.
   - Use GET to pull `companies` with broad nested relations (`companies_i18n`, `industries`, `services`, `companies_address`, `companies_support`).
   - Save JSON as `company_<company_id>_detail.json`.
   - Save CSV as `company_<company_id>_detail.csv`.
   - Optionally add a translated column (default `value_zh-CN`).

1. **fetch/split**
   - Read records from `jsonl/csv/json`.
   - Create `out/batches/batch_XXXX.input.jsonl`.
   - Create `out/todo/batch_XXXX.json` with `status=pending`.

2. **translate**
   - Process pending batches.
   - Default mode: expand from existing i18n source rows (`lang_code=en`) into target languages.
   - Keep source `en` row and append translated rows (for example `zh-CN`, `es`) with updated `lang_code`.
   - Translate only configured `FIELDS` (default `brief,description`).
   - Keep protected fields/patterns unchanged.
   - Write `batch_XXXX.translated.jsonl`.

3. **review**
   - Polish wording into professional industry tone.
   - Preserve facts.
   - Write `batch_XXXX.reviewed.jsonl`.

4. **merge**
   - Merge with priority: `reviewed > translated > input`.
   - Default final output format is CSV.
   - Write `out/final/companies_i18n.<target_lang>.<ext>`.

5. **report**
   - Generate `out/report/summary.md`.
   - Include done/pending/error counts and error reasons.
   - When all todo batches are `done`, delete intermediate folders (`out/batches`, `out/todo`) by default.

## Execution Contract

Run in this order by default:
0) Optional single-record pull: `scripts/fetch_company_detail.py`
1) `scripts/split_batches.py`
2) `scripts/translate_batch.py`
3) `scripts/review_batch.py`
4) `scripts/merge_final.py`
5) `scripts/build_report.py`

For API-based company detail export (single or batch), use detailed mode by default:
- Use broad GET select with nested relations (`companies_i18n`, `industries/industries_i18n/services/services_i18n`, `companies_address`, `companies_support`).
- Flatten nested JSON into one-row-per-company CSV with full field paths as column names.
- Never output a reduced/minimal CSV unless user explicitly asks for a slim schema.
- Prefer `scripts/export_companies_detail_csv.py` for multi-company detailed CSV exports.

Support:
- stage-only execution (translate-only/review-only/merge-only)
- resume mode (skip done, process pending/error)
- batch range control (`start_batch`, `end_batch`)

## Inputs

Read config from env and CLI overrides.

Minimum expected keys:
- `SOURCE_LANG` (default `en`)
- `TARGET_LANG` (for example `zh-CN`, `zh-TW`, `es`)
- `RECORDS_FILE`
- `OUTPUT_DIR`

Common optional keys:
- `BATCH_SIZE` (default `10`)
- `FIELDS` (default `brief,description`; can include `lang_code` in split stage)
- `SOURCE_LANG` (default `en`)
- `TARGET_LANGS` (for example `zh-CN,es`)
- `GLOSSARY_FILE`
- `NO_TRANSLATE_FIELDS`
- `RESUME` (default `true`)
- `COMPANY_ID` / CLI `--company-id` (for single-company detail fetch)
- `TRANSLATE_TO` / CLI `--translate-to` (for translated CSV value column)

## Guardrails

- Never translate company names (for example `companies_i18n.name`).
- Never translate identifier/code fields (for example `industry_id`, `company_id`, `lang_code`, legal identifiers).
- Never translate address-related fields (for example address/city/state/province/postcode/zip/country/street).
- Never fabricate qualifications, awards, metrics, or business claims.
- Preserve semantic equivalence; improve fluency only.
- Do not write back to DB unless user explicitly enables writeback and provides approved API contract.
- Never delete or modify existing `.env` files by default. Only change or remove `.env` files when the user explicitly asks for that action.

## Failure & Resume Policy

- Maintain one todo file per batch with status:
  - `pending` | `translated` | `done` | `error`
- Record error message and timestamp for failed batches.
- Resume should skip `done` by default and continue `pending/error`.
- When expected search results are not satisfied, automatically expand search scope using semantically similar terms and close synonyms before concluding no match.
- When execution stops because of `agents.defaults.timeoutSeconds`, return a partial-progress summary immediately (completed stages, completed batch ids/counts, current stage, and remaining pending/error batches).

## Reference Files

- `references/glossary.template.csv` for term mapping.
- `references/style-guide.md` for review tone and editing standards.
- `references/field-protection-rules.md` for no-translate rules.
