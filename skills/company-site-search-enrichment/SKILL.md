---
name: company-site-search-enrichment
description: Discover companies from Google-style web search, identify official websites, extract logo/intro/service/contact details, generate business hashtags, and export clean yellow-pages records (CSV/JSON/database-ready). Use when users ask to build or enrich company directories by location and industry, especially requests like “Search Sydney IT company and output CSV”.
---

# Company Site Search Enrichment

Extract structured company records from search + official websites for yellow pages workflows.

## Workflow

1. **Build search keywords**
   - Always include: `location + industry/service + company`.
   - Valid examples: `Sydney IT company`, `Melbourne accounting company`, `NSW Home Builder company`.
   - Keyword builder uses associative expansion (agent-like term association) and expands one seed to about 10 queries by default.
   - Formal parameter: `--expansion-count` (default 10; deprecated alias `--max-keywords`).
   - Entity-term expansion is enabled by default: `company` will be associated with terms like `business/agency/firm/provider/consultancy/studio/solutions/services/experts`.
   - Controls: `--expand-entity-terms` (default on), `--no-expand-entity-terms`, `--entity-terms`.
   - Reject keywords without `company`.

2. **Collect candidate websites (Playwright + Google)**
   - Use Playwright-driven Google search to collect title/url/rank.
   - Deduplicate by domain.
   - Prefer official company domains and homepage/about/services/contact pages.
   - De-prioritize job boards, review sites, social profiles, and aggregators.

3. **Visit official websites and extract raw data**
   - Target pages: homepage, about, services, contact.
   - Extract: company name, logo file, rich company description (meta + page text fallback), business scope summary, contact details, and address.
   - Merge signals across pages to improve completeness.

4. **Validate required fields**
   - Mandatory: `logo` and `company_description`.
   - Check only structural completeness in enrichment stage (do not run company/logo reasonability judges here).
   - If requirement fails: skip record and log reason.

5. **Enrich and normalize**
   - Generate 3–8 business hashtags from actual site content.
   - Clean text/URLs/phone/email/address format.
   - Remove duplicates and HTML artifacts.
   - Add confidence and traceability metadata.

6. **Export deliverables**
   - Output CSV/JSON/database-ready rows.
   - Include run summary metrics and skip reasons.

## Industry/Service Taxonomy Filters (New)

Use the following reference files as the authoritative filter lists:

- `references/industries.csv` (industry taxonomy; columns: `industry_id`, `name`)
- `references/services.csv` (service/sub-industry taxonomy; columns: `service_id`, `name`)

Rules:
- `seed_topic` must map to an English `name` from either taxonomy file.
- Industry and sub-industry filters are applied at keyword build stage.
- If `seed_topic` is not in taxonomy, fail fast with validation error.

## Australia Location Constraints (New)

`location` must be Australia major states/cities.

Allowed states/territories:
- NSW / New South Wales
- VIC / Victoria
- QLD / Queensland
- WA / Western Australia
- SA / South Australia
- TAS / Tasmania
- ACT / Australian Capital Territory
- NT / Northern Territory

Allowed major cities:
- Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Hobart, Darwin
- Gold Coast, Newcastle, Wollongong, Geelong, Sunshine Coast, Townsville, Cairns

Accepts combined forms like `Sydney NSW` or `Sydney, NSW`.

## Required Inputs

- `seed_topic` (industry keyword, e.g. IT/accounting)
- `location` (city/region)
- `output_format` (`csv|json|db`)

## Optional Inputs

- `max_companies`
- `language`
- `country`
- `search_depth`
- `expansion_count` (default 10)
- `location_mode` (`fixed|city|state|mixed`, default `mixed`)
- `mixed_city_ratio` (default `0.7`)
- `expand_entity_terms` (default true)
- `entity_terms` (comma-separated entity suffix dictionary)
- `official_site_only`
- `require_logo` (default true)
- `require_intro` (default true)
- `enable_hashtag_classification`
- `csv_path` / `db_target`

## Strict Output Contract (Must Follow Exactly)

Output records must match the CSV header from:
`company-yellow-page-output/sydney_builder_valid_top20.csv`

Field names and order must be exactly:

1. `company_name`
2. `official_website`
3. `logo_url`
4. `saved_logo_path`
5. `company_description`
6. `business_scope_summary`
7. `hashtags`
8. `phone`
9. `email`
10. `address`
11. `office_location`
12. `contact_page`
13. `about_page`
14. `services_page`
15. `source_search_keyword`
16. `company_site_score`
17. `logo_quality_score`
18. `extraction_confidence`
19. `extraction_status`
20. `extraction_timestamp`

Notes:
- Do not add/remove/reorder columns in final CSV export.
- `hashtags` must be comma-separated in CSV (e.g. `#TagA,#TagB`).
- `extraction_timestamp` must be ISO-8601.
- `company_site_score` and `logo_quality_score` are reserved quality fields; enrichment stage may default them and independent quality-check task may overwrite them.

### Canonical example (strict shape)

```json
{
  "company_name": "Sydney Commercial Builders",
  "official_website": "https://sydneycommercialbuilders.com.au/",
  "logo_url": "https://sydneycommercialbuilders.com.au/wp-content/uploads/2019/12/logo-5.png",
  "saved_logo_path": "/Users/derekchen/Desktop/company-yellow-page-output/logos/Sydney_Commercial_Builders_6278e365aa.png",
  "company_description": "Commercial builder in Sydney delivering fit-outs, refurbishment and construction services.",
  "business_scope_summary": "Office fit-outs, facade refurbishment, fire protection and related building works.",
  "hashtags": "#Construction,#CommercialFitout",
  "phone": "0417 417 400",
  "email": "admin@example.com",
  "address": "1 Bligh Street, Sydney, NSW 2000",
  "office_location": "Sydney",
  "contact_page": "https://sydneycommercialbuilders.com.au/contact",
  "about_page": "https://sydneycommercialbuilders.com.au/about",
  "services_page": "https://sydneycommercialbuilders.com.au/services",
  "source_search_keyword": "Sydney commercial builder company",
  "company_site_score": 0.0,
  "logo_quality_score": 0.8,
  "extraction_confidence": 0.85,
  "extraction_status": "valid",
  "extraction_timestamp": "2026-03-10T05:54:15.312657+00:00"
}
```

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

Company/logo reasonability checks are now an independent post-task via `scripts/company_logo_quality_check.py`.

## Guardrails

- Use official website as primary truth when available.
- Do not submit forms or log into private portals.
- Do not bypass paywalls/protected systems.
- Do not treat third-party directory data as primary truth unless explicit fallback is enabled.
- Continue processing when one site fails; never stop whole batch for single failure.
- Hard reject rule in enrichment stage: only required-field validation failures are rejected.
- CompanyJudgeAgent/LogoJudgeAgent checks run in the independent quality-check task.
- Keep strict one-to-one mapping between company record and saved logo file: only valid company records may retain logo files. For rejected records, remove orphan logo files and keep only minimal skip reason logs.
- Saved logo filenames must be company-name aligned (sanitized company slug + unique suffix) for traceability.
- Default extraction runtime policy: parallel workers = 5, per-task timeout = 30 seconds.
- When requested target count is **>= 20**, switch to **parallel distributed processing** (batched keyword/candidate collection and parallel extraction workers).
- In parallel mode, any single task exceeding **30s** must be skipped and marked timeout, without blocking the full run.
- If timeouts occur continuously (consecutive timeout failures), pause the pipeline for **10 minutes** and then resume from remaining batches.

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

## Script Entrypoints (v0.2)

- `scripts/query_builder.py` (now validates taxonomy + AU location constraints)
- `scripts/search_collector.py` (Playwright search; default engines `google,bing`, optional fallback `duckduckgo`)
- `scripts/site_extractor.py`
- `scripts/normalize_and_validate.py`
- `scripts/company_logo_quality_check.py` (independent post-task)
- `scripts/export_records.py`
- `scripts/run_pipeline.py` (end-to-end runner)

Run example:

```bash
bash scripts/setup_playwright.sh
python3 scripts/run_pipeline.py \
  --location Sydney \
  --seed-topic IT \
  --expansion-count 10 \
  --batch-size 10 \
  --target-candidates 50 \
  --workers 5 \
  --name sydney_it_companies \
  # optional: --engines google,bing,duckduckgo --min-results-per-keyword 3
```

Notes:
- `--batch-size 10` means **10 candidates per keyword batch**, not a global hard cap.
- `--workers 5` means 5 parallel workers for collection/extraction.
- Use `--target-candidates` to control overall candidate volume.

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

## Migration / Environment Declaration

For cross-machine skill migration, declare and install runtime exactly:

- Python dependency file: `requirements.txt` (includes `playwright`)
- Setup script: `scripts/setup_playwright.sh`
- Browser runtime install: `python3 -m playwright install chromium`

Required migration steps:
1. Copy/install the skill folder.
2. Run `bash scripts/setup_playwright.sh`.
3. Verify with a small test run (`--max-keywords 1 --per-keyword 3`).



Search engine resilience:
- Bing uses dual-path collection: Playwright DOM + Bing RSS fallback, then merged/deduped.
- Google uses Playwright DOM extraction with lightweight HTML fallback parser.
- DuckDuckGo uses html endpoint with lite endpoint fallback, then merged/deduped.
- If an engine returns fewer than `min_results_per_keyword` (default 3), collector tries next engine in `--engines` order.
