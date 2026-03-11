#!/usr/bin/env python3
"""Split source records into deterministic jsonl batches.

Input supports: jsonl / json(list) / csv
Output:
  - out/batches/batch_0001.input.jsonl
  - out/todo/batch_0001.json
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass
class Config:
    records_file: Path
    out_dir: Path
    batch_size: int
    key_field: str
    fields: list[str]


def read_jsonl(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            yield json.loads(line)


def read_json(path: Path) -> Iterator[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("json input must be an array of objects")
    for row in data:
        if isinstance(row, dict):
            yield row


def read_csv(path: Path) -> Iterator[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            yield dict(row)


def read_records(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".jsonl":
        return list(read_jsonl(path))
    if suffix == ".json":
        return list(read_json(path))
    if suffix == ".csv":
        return list(read_csv(path))
    raise ValueError(f"unsupported file type: {path}")


def chunked(items: list[dict], n: int) -> Iterable[list[dict]]:
    for i in range(0, len(items), n):
        yield items[i : i + n]


def normalize_record(row: dict, key_field: str, fields: list[str]) -> dict:
    out = {key_field: row.get(key_field)}
    for f in fields:
        out[f] = row.get(f)
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_todo(path: Path, batch_name: str, count: int) -> None:
    payload = {
        "batch": batch_name,
        "status": "pending",
        "count": count,
        "error": None,
        "completed_at": None,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> Config:
    p = argparse.ArgumentParser(description="Split records into translation batches")
    p.add_argument("--records-file", required=True)
    p.add_argument("--out-dir", default="out")
    p.add_argument("--batch-size", type=int, default=10)
    p.add_argument("--key-field", default="company_key")
    p.add_argument("--fields", default="lang_code,brief,description", help="comma-separated")
    a = p.parse_args()
    return Config(
        records_file=Path(a.records_file),
        out_dir=Path(a.out_dir),
        batch_size=a.batch_size,
        key_field=a.key_field,
        fields=[x.strip() for x in a.fields.split(",") if x.strip()],
    )


def main() -> None:
    cfg = parse_args()
    rows = read_records(cfg.records_file)
    normalized = [normalize_record(r, cfg.key_field, cfg.fields) for r in rows]

    batches_dir = cfg.out_dir / "batches"
    todo_dir = cfg.out_dir / "todo"
    batches_dir.mkdir(parents=True, exist_ok=True)
    todo_dir.mkdir(parents=True, exist_ok=True)

    created = 0
    for idx, batch in enumerate(chunked(normalized, cfg.batch_size), start=1):
        batch_name = f"batch_{idx:04d}"
        input_file = batches_dir / f"{batch_name}.input.jsonl"
        todo_file = todo_dir / f"{batch_name}.json"
        write_jsonl(input_file, batch)
        write_todo(todo_file, batch_name, len(batch))
        created += 1

    print(f"created_batches={created}")
    print(f"records={len(normalized)}")
    print(f"out_dir={cfg.out_dir}")


if __name__ == "__main__":
    main()
