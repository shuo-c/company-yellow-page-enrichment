#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from datetime import datetime, timezone

FIELDS = [
    "company_name", "official_website", "logo_url", "company_description", "business_scope_summary", "hashtags",
    "phone", "email", "address", "office_location", "contact_page", "about_page", "services_page",
    "source_search_keyword", "extraction_confidence", "extraction_status", "extraction_timestamp"
]


def main() -> int:
    p = argparse.ArgumentParser(description="Export valid records to CSV/JSON and summary")
    p.add_argument("--valid-jsonl", required=True)
    p.add_argument("--skipped-jsonl", required=True)
    p.add_argument("--out-dir", required=True)
    p.add_argument("--name", default="company_enrichment")
    args = p.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    csv_path = out / f"{args.name}.csv"
    json_path = out / f"{args.name}.json"
    summary = out / "summary.md"

    valid_rows, skipped_rows = [], []
    for line in Path(args.valid_jsonl).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        r["hashtags"] = ",".join(r.get("hashtags", []))
        r["extraction_timestamp"] = datetime.now(timezone.utc).isoformat()
        valid_rows.append(r)
    for line in Path(args.skipped_jsonl).read_text(encoding="utf-8").splitlines():
        if line.strip():
            skipped_rows.append(json.loads(line))

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for r in valid_rows:
            w.writerow({k: r.get(k, "") for k in FIELDS})

    json_path.write_text(json.dumps(valid_rows, ensure_ascii=False, indent=2), encoding="utf-8")

    reason_counts = {}
    for r in skipped_rows:
        reason = r.get("skip_reason", "unknown")
        reason_counts[reason] = reason_counts.get(reason, 0) + 1

    lines = [
        "# Run Summary",
        f"- total_valid: {len(valid_rows)}",
        f"- total_skipped: {len(skipped_rows)}",
        "- skipped_reasons:",
    ]
    for k, v in sorted(reason_counts.items()):
        lines.append(f"  - {k}: {v}")
    lines.append(f"- csv: {csv_path}")
    lines.append(f"- json: {json_path}")

    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"csv: {csv_path}")
    print(f"json: {json_path}")
    print(f"summary: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
