#!/usr/bin/env python3
"""Translate *.input.jsonl into *.translated.jsonl.

Default engine is mock (safe for scaffolding):
  text -> "[<target_lang>] <text>"

This is intentional so the pipeline works end-to-end before wiring real APIs.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from datetime import datetime, timezone

URL_RE = re.compile(r"https?://\S+", re.I)
EMAIL_RE = re.compile(r"\b[\w.%-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\+?\d[\d\-()\s]{6,}\d")


def read_jsonl(path: Path) -> list[dict]:
    out = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def should_skip_value(value: object) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    return bool(URL_RE.search(text) or EMAIL_RE.search(text) or PHONE_RE.search(text))


def translate_text(text: str, target_lang: str, engine: str = "mock") -> str:
    if engine == "mock":
        return f"[{target_lang}] {text}"
    raise NotImplementedError("only --engine mock is implemented in scaffold")


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
    p = argparse.ArgumentParser(description="Translate one batch input file")
    p.add_argument("--batch-file", required=True, help="path to *.input.jsonl")
    p.add_argument("--target-lang", required=True)
    p.add_argument("--engine", default="mock")
    p.add_argument("--fields", default="intro,description", help="comma-separated")
    p.add_argument("--no-translate-fields", default="company_name,address,website,url")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    batch_file = Path(args.batch_file)
    rows = read_jsonl(batch_file)

    fields = [x.strip() for x in args.fields.split(",") if x.strip()]
    no_translate = {x.strip() for x in args.no_translate_fields.split(",") if x.strip()}

    out_rows: list[dict] = []
    skipped = 0
    for row in rows:
        out = dict(row)
        for field in fields:
            if field in no_translate:
                continue
            value = row.get(field)
            if should_skip_value(value):
                skipped += 1
                continue
            out[field] = translate_text(str(value), args.target_lang, args.engine)
        out_rows.append(out)

    out_file = batch_file.with_name(batch_file.name.replace(".input.jsonl", ".translated.jsonl"))
    write_jsonl(out_file, out_rows)

    # update todo
    batch_name = batch_file.stem.replace(".input", "")
    todo_file = batch_file.parent.parent / "todo" / f"{batch_name}.json"
    try:
        update_todo(todo_file, "translated")
    except Exception:
        pass

    print(f"batch_file={batch_file}")
    print(f"translated_file={out_file}")
    print(f"rows={len(out_rows)}")
    print(f"skipped_values={skipped}")


if __name__ == "__main__":
    main()
