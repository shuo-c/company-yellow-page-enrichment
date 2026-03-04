---
name: yellow-page-translator
description: Batch-translate Yellow Pages company text fields (for example intro/description) from English to Chinese or other target languages, with resume support, protected-field handling, review polishing, merge, and summary report generation. Use when users ask to fetch/split records, run translate/review stages, continue from pending/error batches, and produce final deliverable files (jsonl/csv/sql-ready outputs).
---

# Yellow Pages Translation Assistant

Execute an end-to-end translation pipeline for company profile fields.

## Pipeline Stages

1. **fetch/split**
   - Read records from `jsonl/csv/json`.
   - Create `out/batches/batch_XXXX.input.jsonl`.
   - Create `out/todo/batch_XXXX.json` with `status=pending`.

2. **translate**
   - Process pending batches.
   - Translate only configured `FIELDS`.
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
1) `scripts/split_batches.py`
2) `scripts/translate_batch.py`
3) `scripts/review_batch.py`
4) `scripts/merge_final.py`
5) `scripts/build_report.py`

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
- `FIELDS` (for example `intro,description`)
- `GLOSSARY_FILE`
- `NO_TRANSLATE_FIELDS`
- `RESUME` (default `true`)

## Guardrails

- Never translate protected fields (for example company name, address, phone, email, website/url, legal identifiers).
- Never fabricate qualifications, awards, metrics, or business claims.
- Preserve semantic equivalence; improve fluency only.
- Do not write back to DB unless user explicitly enables writeback and provides approved API contract.

## Failure & Resume Policy

- Maintain one todo file per batch with status:
  - `pending` | `translated` | `done` | `error`
- Record error message and timestamp for failed batches.
- Resume should skip `done` by default and continue `pending/error`.

## Reference Files

- `references/glossary.template.csv` for term mapping.
- `references/style-guide.md` for review tone and editing standards.
- `references/field-protection-rules.md` for no-translate rules.
