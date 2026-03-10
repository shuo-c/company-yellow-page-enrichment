#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

RELATED = {
    "it": ["software", "cybersecurity", "managed it", "cloud", "web development"],
    "accounting": ["tax", "bookkeeping", "financial advisory", "audit"],
    "marketing": ["digital marketing", "seo", "branding", "advertising"],
    "construction": ["building", "civil", "contractor", "renovation"],
}


def build_keywords(location: str, seed_topic: str, max_keywords: int) -> list[str]:
    topic = seed_topic.strip().lower()
    base = [f"{location} {seed_topic} company"]
    expansions = RELATED.get(topic, [])
    for e in expansions:
        base.append(f"{location} {e} company")
    uniq: list[str] = []
    for k in base:
        if "company" not in k.lower():
            continue
        if k not in uniq:
            uniq.append(k)
    return uniq[:max_keywords]


def main() -> int:
    p = argparse.ArgumentParser(description="Build keyword list: location + industry + company")
    p.add_argument("--location", required=True)
    p.add_argument("--seed-topic", required=True)
    p.add_argument("--max-keywords", type=int, default=10)
    p.add_argument("--out", required=True, help="Output JSON path")
    args = p.parse_args()

    kws = build_keywords(args.location, args.seed_topic, args.max_keywords)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"keywords": kws}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"keywords: {len(kws)}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
