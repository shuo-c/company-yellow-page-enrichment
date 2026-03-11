#!/usr/bin/env python3
"""Review translated batch with simple style polishing.

Input:  *.translated.jsonl
Output: *.reviewed.jsonl
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
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


def polish_text(text: str) -> str:
    text = text.strip()
    # lightweight Chinese copy polish for scaffold
    text = text.replace("  ", " ")
    if text and text[-1] not in "。！？!?":
        text += "。"
    return text


def update_todo(todo_file: Path, status: str, error: str | None = None) -> None:
    payload = {}
    if todo_file.exists():
        payload = json.loads(todo_file.read_text(encoding="utf-8"))
    payload.update(
        {
            "status": status,
            "error": error,
            "completed_at": datetime.now(timezone.utc).isoformat() if status == "done" else None,
        }
    )
    todo_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Review one translated batch")
    p.add_argument("--batch-file", required=True, help="path to *.translated.jsonl")
    p.add_argument("--fields", default="intro,description", help="comma-separated")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    batch_file = Path(args.batch_file)
    fields = [x.strip() for x in args.fields.split(",") if x.strip()]
    rows = read_jsonl(batch_file)

    out_rows = []
    changed = 0
    for row in rows:
        out = dict(row)
        for f in fields:
            val = out.get(f)
            if isinstance(val, str) and val.strip():
                new_val = polish_text(val)
                if new_val != val:
                    changed += 1
                out[f] = new_val
        out_rows.append(out)

    out_file = batch_file.with_name(batch_file.name.replace(".translated.jsonl", ".reviewed.jsonl"))
    write_jsonl(out_file, out_rows)

    batch_name = batch_file.stem.replace(".translated", "")
    todo_file = batch_file.parent.parent / "todo" / f"{batch_name}.json"
    try:
        update_todo(todo_file, "done")
    except Exception:
        pass

    print(f"batch_file={batch_file}")
    print(f"reviewed_file={out_file}")
    print(f"rows={len(rows)}")
    print(f"polished_fields={changed}")


if __name__ == "__main__":
    main()
