#!/usr/bin/env python3
from __future__ import annotations

import argparse
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
    p.add_argument("--max-keywords", type=int, default=8)
    p.add_argument("--per-keyword", type=int, default=10)
    p.add_argument("--out-dir", default="./out")
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
    run([py, str(root / "query_builder.py"), "--location", args.location, "--seed-topic", args.seed_topic, "--max-keywords", str(args.max_keywords), "--out", str(keywords)])
    run([py, str(root / "search_collector.py"), "--keywords", str(keywords), "--out", str(cands), "--per-keyword", str(args.per_keyword)])
    run([py, str(root / "site_extractor.py"), "--candidates", str(cands), "--out", str(raw), "--logos-dir", str(logos_dir)])
    run([py, str(root / "normalize_and_validate.py"), "--infile", str(raw), "--out-valid", str(valid), "--out-skipped", str(skipped)])
    run([py, str(root / "export_records.py"), "--valid-jsonl", str(valid), "--skipped-jsonl", str(skipped), "--out-dir", str(out), "--name", args.name])

    print("done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
