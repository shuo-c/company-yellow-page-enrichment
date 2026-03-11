#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str]) -> None:
    print("$", " ".join(cmd))
    p = subprocess.run(cmd)
    if p.returncode != 0:
        raise SystemExit(p.returncode)


def main() -> int:
    p = argparse.ArgumentParser(description="Run end-to-end company site enrichment pipeline")
    p.add_argument("--location", required=True)
    p.add_argument("--seed-topic", required=True)
    p.add_argument("--expansion-count", type=int, default=10, help="keyword expansion count passed to query_builder")
    p.add_argument("--max-keywords", type=int, default=None, help="deprecated alias of --expansion-count")
    p.add_argument("--batch-size", type=int, default=10, help="candidate rows per keyword batch")
    p.add_argument("--target-candidates", type=int, default=50, help="target candidate domains before extraction")
    p.add_argument("--workers", type=int, default=5, help="parallel extractor workers")
    p.add_argument("--per-keyword", type=int, default=None, help="deprecated alias of --batch-size")
    default_out_dir = os.getenv("ENRICHMENT_OUTPUT_DIR", "/Users/derekchen/Desktop/company-yellow-page-output")
    p.add_argument("--out-dir", default=default_out_dir)
    p.add_argument("--name", default="company_enrichment")
    args = p.parse_args()

    root = Path(__file__).resolve().parent
    out = Path(args.out_dir)
    work = out / "work"
    work.mkdir(parents=True, exist_ok=True)

    keywords = work / "keywords.json"
    cands = work / "candidates.jsonl"
    raw = work / "raw_extracted.jsonl"
    valid = work / "valid.jsonl"
    skipped = work / "skipped.jsonl"
    logos_dir = out / "logos"

    py = sys.executable
    per_keyword = args.per_keyword if args.per_keyword is not None else args.batch_size

    kw_count = args.max_keywords if args.max_keywords is not None else args.expansion_count
    run([py, str(root / "query_builder.py"), "--location", args.location, "--seed-topic", args.seed_topic, "--expansion-count", str(kw_count), "--location-mode", "mixed", "--mixed-city-ratio", "0.7", "--out", str(keywords)])
    run([
        py,
        str(root / "search_collector.py"),
        "--keywords",
        str(keywords),
        "--out",
        str(cands),
        "--per-keyword",
        str(per_keyword),
        "--keyword-workers",
        str(args.workers),
        "--target-candidates",
        str(args.target_candidates),
    ])
    run([
        py,
        str(root / "site_extractor.py"),
        "--candidates",
        str(cands),
        "--out",
        str(raw),
        "--logos-dir",
        str(logos_dir),
        "--workers",
        str(args.workers),
    ])
    run([py, str(root / "normalize_and_validate.py"), "--infile", str(raw), "--out-valid", str(valid), "--out-skipped", str(skipped)])
    run([py, str(root / "export_records.py"), "--valid-jsonl", str(valid), "--skipped-jsonl", str(skipped), "--out-dir", str(out), "--name", args.name])

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
