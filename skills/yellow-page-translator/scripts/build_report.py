#!/usr/bin/env python3
"""Build summary report from todo + outputs."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


def load_todos(todo_dir: Path) -> list[dict]:
    out = []
    for p in sorted(todo_dir.glob("batch_*.json")):
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            payload["_file"] = p.name
            out.append(payload)
        except Exception:
            out.append({"_file": p.name, "status": "error", "error": "invalid json"})
    return out


def count_by_status(todos: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for t in todos:
        s = t.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate markdown summary report")
    p.add_argument("--out-dir", default="out")
    p.add_argument("--target-lang", required=True)
    p.add_argument("--cleanup-intermediate", action="store_true", default=True)
    p.add_argument("--no-cleanup-intermediate", action="store_false", dest="cleanup_intermediate")
    return p.parse_args()


def all_todos_done(todos: list[dict]) -> bool:
    if not todos:
        return False
    return all(t.get("status") == "done" for t in todos)


def main() -> None:
    args = parse_args()
    out_dir = Path(args.out_dir)
    todo_dir = out_dir / "todo"
    report_dir = out_dir / "report"
    final_dir = out_dir / "final"

    todos = load_todos(todo_dir)
    counts = count_by_status(todos)

    final_candidates = sorted(final_dir.glob(f"companies_i18n.{args.target_lang}.*"))
    final_file = final_candidates[-1].name if final_candidates else "(not found)"

    lines = []
    lines.append("# Translation Summary")
    lines.append("")
    lines.append(f"- Generated at (UTC): {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"- Target language: {args.target_lang}")
    lines.append(f"- Final file: {final_file}")
    lines.append("")
    lines.append("## Batch status")
    for k in sorted(counts.keys()):
        lines.append(f"- {k}: {counts[k]}")

    errors = [t for t in todos if t.get("status") in {"error", "failed"} or t.get("error")]
    lines.append("")
    lines.append("## Errors")
    if not errors:
        lines.append("- none")
    else:
        for e in errors:
            lines.append(f"- {e.get('_file')}: {e.get('error')}")

    report_dir.mkdir(parents=True, exist_ok=True)
    report_file = report_dir / "summary.md"
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    cleaned = False
    if args.cleanup_intermediate and all_todos_done(todos):
        batches_dir = out_dir / "batches"
        if batches_dir.exists():
            shutil.rmtree(batches_dir)
        if todo_dir.exists():
            shutil.rmtree(todo_dir)
        cleaned = True

    print(f"summary={report_file}")
    print(f"cleanup_intermediate={cleaned}")


if __name__ == "__main__":
    main()
