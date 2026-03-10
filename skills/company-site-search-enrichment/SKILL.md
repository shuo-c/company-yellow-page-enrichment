---
name: company-site-search-enrichment
description: Discover companies from Google-style web search, identify official websites, extract logo/intro/service/contact details, generate business hashtags, and export clean yellow-pages records (CSV/JSON/database-ready). Use when users ask to build or enrich company directories by location and industry, especially requests like “Search Sydney IT company and output CSV”.
---

# Company Site Search Enrichment

Extract structured company records from search + official websites for yellow pages workflows.

## Workflow

1. **Build search keywords**
   - Always include: `location + industry + company`.
   - Valid examples: `Sydney IT company`, `Melbourne accounting company`.
   - Reject keywords without `company`.

2. **Collect candidate websites**
   - Use search results to collect title/url/snippet/rank.
   - Deduplicate by domain.
   - Prefer official company domains and homepage/about/services/contact pages.
   - De-prioritize job boards, review sites, social profiles, and aggregators.

3. **Visit official websites and extract raw data**
   - Target pages: homepage, about, services, contact.
   - Extract: company name, logo, company description, services/business scope, contact details, address.

4. **Validate required fields**
   - Mandatory: `logo` and `company_description`.
   - If either is missing: skip record and log reason.

5. **Enrich and normalize**
   - Generate 3–8 business hashtags from actual site content.
   - Clean text/URLs/phone/email/address format.
   - Remove duplicates and HTML artifacts.
   - Add confidence and traceability metadata.

6. **Export deliverables**
   - Output CSV/JSON/database-ready rows.
   - Include run summary metrics and skip reasons.

## Required Inputs

- `seed_topic` (industry keyword, e.g. IT/accounting)
- `location` (city/region)
- `output_format` (`csv|json|db`)

## Optional Inputs

- `max_companies`
- `language`
- `country`
- `search_depth`
- `official_site_only`
- `require_logo` (default true)
- `require_intro` (default true)
- `enable_hashtag_classification`
- `csv_path` / `db_target`

## Required Output Fields

- `company_name`
- `official_website`
- `logo_url`
- `saved_logo_path` (mandatory local file path)
- `company_description`
- `business_scope_summary`
- `hashtags`

## Optional Output Fields

- `phone`, `email`, `address`, `office_location`
- `contact_page`, `about_page`, `services_page`, `social_links`
- `source_search_keyword`, `extraction_confidence`, `extraction_timestamp`, `extraction_status`

## Acceptance Rules

Only save record when all are true:
- official website found
- logo file downloaded and saved locally (`saved_logo_path` exists)
- company description extracted

Otherwise skip with reason:
- `missing_logo`
- `missing_logo_file`
- `missing_description`
- `unofficial_website`
- `duplicate_domain`
- `inaccessible_site`
- `insufficient_content`

## Guardrails

- Use official website as primary truth when available.
- Do not submit forms or log into private portals.
- Do not bypass paywalls/protected systems.
- Do not treat third-party directory data as primary truth unless explicit fallback is enabled.
- Continue processing when one site fails; never stop whole batch for single failure.

## Execution Pattern (Subtasks)

- Query Builder: generate/rank keywords (must include `company`).
- Search Collector: collect and deduplicate candidate domains.
- Website Extractor: crawl and extract structured fields.
- Data Cleaner: normalize and validate schema.
- Tag Generator: output business hashtags from content.
- Storage Writer: write CSV/JSON/DB-ready rows + summary report.

## Summary Metrics

Always report:
- keywords generated
- results inspected
- candidate domains found
- official sites visited
- valid companies extracted
- skipped by reason
- duplicates removed
- final rows written

## Script Entrypoints (v0.1)

- `scripts/query_builder.py`
- `scripts/search_collector.py` (requires `BRAVE_API_KEY`)
- `scripts/site_extractor.py`
- `scripts/normalize_and_validate.py`
- `scripts/export_records.py`
- `scripts/run_pipeline.py` (end-to-end runner)

Run example:

```bash
export BRAVE_API_KEY=...
python3 scripts/run_pipeline.py \
  --location Sydney \
  --seed-topic IT \
  --max-keywords 8 \
  --per-keyword 10 \
  --name sydney_it_companies
```

Default output directory:
- `/Users/derekchen/Desktop/company-yellow-page-output`
- Override by CLI: `--out-dir <path>`
- Override default globally: `ENRICHMENT_OUTPUT_DIR=<path>`

Outputs:
- `<out-dir>/<name>.csv`
- `<out-dir>/<name>.json`
- `<out-dir>/summary.md`
- `<out-dir>/logos/*` (downloaded logo files)
- `<out-dir>/work/*.jsonl` (intermediate files)

