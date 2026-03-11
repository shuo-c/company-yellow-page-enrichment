#!/usr/bin/env python3
"""Merge reviewed/translated batches into final file.

Priority per batch: reviewed > translated > input
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_csv(path: Path, rows: list[dict], headers: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def build_headers_from_input(input_batches: list[Path], merged_rows: list[dict]) -> list[str]:
    """Use API/input header order as canonical CSV schema.

    - Primary source: first input batch first row key order
    - Any extra keys from processed rows are appended at the end (stable order)
    """
    base_headers: list[str] = []
    if input_batches:
        first_rows = read_jsonl(input_batches[0])
        if first_rows:
            base_headers = list(first_rows[0].keys())

    # append unseen keys from merged rows without reordering base schema
    seen = set(base_headers)
    for row in merged_rows:
        for k in row.keys():
            if k not in seen:
                base_headers.append(k)
                seen.add(k)

    return base_headers


def pick_best_file(batch_prefix: str, batches_dir: Path) -> Path | None:
    candidates = [
        batches_dir / f"{batch_prefix}.reviewed.jsonl",
        batches_dir / f"{batch_prefix}.translated.jsonl",
        batches_dir / f"{batch_prefix}.input.jsonl",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Merge batches to final output")
    p.add_argument("--out-dir", default="out")
    p.add_argument("--target-lang", required=True)
    p.add_argument("--output-format", choices=["jsonl", "csv"], default="csv")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    batches_dir = out_dir / "batches"
    final_dir = out_dir / "final"

    input_batches = sorted(batches_dir.glob("batch_*.input.jsonl"))
    merged: list[dict] = []
    used = []

    for p in input_batches:
        prefix = p.name.replace(".input.jsonl", "")
        chosen = pick_best_file(prefix, batches_dir)
        if chosen is None:
            continue
        merged.extend(read_jsonl(chosen))
        used.append(chosen.name)

    ext = args.output_format
    final_file = final_dir / f"companies_i18n.{args.target_lang}.{ext}"
    if args.output_format == "jsonl":
        write_jsonl(final_file, merged)
    else:
        headers = build_headers_from_input(input_batches, merged)
        write_csv(final_file, merged, headers)

    print(f"final_file={final_file}")
    print(f"rows={len(merged)}")
    print("used_files=")
    for name in used:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
