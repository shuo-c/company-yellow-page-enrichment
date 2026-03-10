# yellow-page-translator — Skill Brief (Step 1)

## Problem to Solve
This skill batch-translates company profile text (such as intro/description) from English into Chinese or other target languages, then performs industry-tone review and produces delivery-ready outputs. It replaces the manual flow of export -> copy/paste translation -> manual proofreading -> merge back.

## Target Users
- Primary: the maintainer running translation scripts and content updates
- Secondary: operations/content editors who need publish-ready multilingual text quickly
- Potential: engineers who need standardized output files for DB writeback or release

## Trigger Phrases (examples)
1. "Use .env.prod to translate intro and description for these company keys from English to Chinese, batch size 10, then merge reviewed output."
2. "Run translate stage only for batches/batch_0003.jsonl to zh-CN, keep company name/address/website unchanged."
3. "Translation is done; run review (industry tone) and generate final merged output."
4. "Generate an additional Spanish (es) version for the same keys and output a diff report showing skipped/protected fields."
5. "Resume from last interruption: skip done batches, process pending/error only."

## Inputs
- Config source
  - env_file: .env path (default .env)
  - records_file: records path (jsonl/csv/json)
- Language parameters
  - source_lang: default en
  - target_lang: zh-CN / zh-TW / es / ja ...
- Field selection
  - fields: list of fields to translate (e.g., intro, description, services)
- Batch control
  - batch_size: default 10
  - start_batch / end_batch: optional range
  - resume: default true
- Terminology protection
  - no_translate_fields: fields never translated (e.g., company_name, address)
  - glossary_file: optional term glossary
- Output format
  - output_format: jsonl / csv / sql (default jsonl)
  - output_dir: default ./out

## Outputs
- Raw cache
  - out/raw/*.json or out/raw.jsonl
- Batch artifacts
  - out/batches/batch_0001.input.jsonl
  - out/batches/batch_0001.translated.jsonl
  - out/batches/batch_0001.reviewed.jsonl
- Todo / status tracking
  - out/todo/batch_0001.json (status, error, completion time, counts)
- Final merged file
  - out/final/companies_i18n.<target_lang>.<ext>
- Report (recommended)
  - out/report/summary.md (counts, skipped items, failures, glossary hits)

## Boundaries
- Do not write directly to DB unless explicitly authorized and API contract is provided
- Do not translate protected proper nouns/identifiers (company name, address, personal names, phone, email, website)
- Do not fabricate qualifications, awards, or business claims
- Do not bypass access controls or assume unsupported API capabilities

## Acceptance Criteria
- Correctness
  - Every key is traceable in output (result or skipped/error)
  - Protected-field rules are enforced
  - Review output improves fluency while preserving meaning
- Usability
  - Supports resume without reprocessing done batches
  - Failures are diagnosable via todo and summary report
- Efficiency
  - Stable output under batch_size=10
- Delivery
  - Final format meets contract (jsonl/csv/sql) and is ready for writeback/release
