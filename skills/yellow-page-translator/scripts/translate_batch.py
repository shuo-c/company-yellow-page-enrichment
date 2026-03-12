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
from functools import lru_cache
from typing import List

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


def _normalize_lang(lang: str) -> str:
    m = {
        "zh": "zh-CN",
        "zh_cn": "zh-CN",
        "zh-cn": "zh-CN",
        "zh-tw": "zh-TW",
        "es-es": "es",
        "es-mx": "es",
        "en-us": "en",
        "en-gb": "en",
    }
    key = (lang or "").strip().lower()
    return m.get(key, lang)


def _split_text_for_translation(text: str, max_len: int = 3500) -> List[str]:
    t = (text or "").strip()
    if len(t) <= max_len:
        return [t]

    # sentence-ish split first
    parts = re.split(r"(?<=[.!?。！？])\s+", t)
    chunks: List[str] = []
    cur = ""
    for p in parts:
        if not p:
            continue
        if len(cur) + len(p) + 1 <= max_len:
            cur = f"{cur} {p}".strip()
        else:
            if cur:
                chunks.append(cur)
            if len(p) <= max_len:
                cur = p
            else:
                # hard split very long segment
                for i in range(0, len(p), max_len):
                    chunks.append(p[i : i + max_len])
                cur = ""
    if cur:
        chunks.append(cur)
    return chunks or [t]


@lru_cache(maxsize=4096)
def translate_text(text: str, target_lang: str, source_lang: str = "en", engine: str = "mock") -> str:
    if engine == "mock":
        return f"[{target_lang}] {text}"

    if engine == "google":
        try:
            from deep_translator import GoogleTranslator
        except Exception as e:
            raise RuntimeError(
                "engine=google requires deep-translator. install with: pip3 install deep-translator"
            ) from e

        src = _normalize_lang(source_lang)
        tgt = _normalize_lang(target_lang)
        translator = GoogleTranslator(source=src, target=tgt)

        chunks = _split_text_for_translation(text)
        out_chunks: List[str] = []
        for c in chunks:
            c = c.strip()
            if not c:
                continue
            try:
                tr = translator.translate(c)
                if not tr:
                    tr = c
            except Exception:
                tr = c
            out_chunks.append(tr)
        return "\n".join(out_chunks).strip()

    raise NotImplementedError("supported engines: mock, google")


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
    p.add_argument("--target-lang", help="single target lang (kept for backward compatibility)")
    p.add_argument("--target-langs", default="", help="comma-separated target langs, e.g. zh-CN,es")
    p.add_argument("--source-lang", default="en", help="only rows with this lang_code will be expanded")
    p.add_argument("--lang-code-field", default="lang_code")
    p.add_argument("--engine", default="mock")
    p.add_argument("--fields", default="brief,description", help="comma-separated")
    p.add_argument("--no-translate-fields", default="company_name,address,website,url")
    p.add_argument("--include-source", action="store_true", default=True, help="keep source rows in output")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    batch_file = Path(args.batch_file)
    rows = read_jsonl(batch_file)

    fields = [x.strip() for x in args.fields.split(",") if x.strip()]
    no_translate = {x.strip() for x in args.no_translate_fields.split(",") if x.strip()}

    target_langs = [x.strip() for x in (args.target_langs or "").split(",") if x.strip()]
    if not target_langs and args.target_lang:
        target_langs = [args.target_lang.strip()]
    if not target_langs:
        raise ValueError("provide --target-lang or --target-langs")

    out_rows: list[dict] = []
    skipped = 0
    for row in rows:
        row_lang = str(row.get(args.lang_code_field, "") or "").strip()

        # Keep non-source rows untouched (already translated or from other langs)
        if row_lang and row_lang != args.source_lang:
            out_rows.append(dict(row))
            continue

        # Keep source row (default behavior for i18n expansion)
        if args.include_source:
            out_rows.append(dict(row))

        # Expand source i18n row into each target language row
        for target_lang in target_langs:
            if target_lang == row_lang:
                continue

            out = dict(row)
            out[args.lang_code_field] = target_lang
            out["source_lang_code"] = row_lang or args.source_lang

            for field in fields:
                if field in no_translate:
                    continue
                value = row.get(field)
                if should_skip_value(value):
                    skipped += 1
                    continue
                out[field] = translate_text(
                    str(value),
                    target_lang,
                    source_lang=(row_lang or args.source_lang),
                    engine=args.engine,
                )
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
    print(f"target_langs={','.join(target_langs)}")
    print(f"skipped_values={skipped}")


if __name__ == "__main__":
    main()
