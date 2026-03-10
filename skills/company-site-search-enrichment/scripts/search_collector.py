#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path


def brave_search(api_key: str, query: str, count: int, country: str = "AU", lang: str = "en") -> list[dict]:
    params = urllib.parse.urlencode({
        "q": query,
        "count": str(count),
        "country": country,
        "search_lang": lang,
    })
    url = f"https://api.search.brave.com/res/v1/web/search?{params}"
    req = urllib.request.Request(url, method="GET", headers={"X-Subscription-Token": api_key, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8", errors="replace"))
    items = data.get("web", {}).get("results", [])
    out = []
    for i, it in enumerate(items, 1):
        out.append({
            "rank": i,
            "title": it.get("title", ""),
            "url": it.get("url", ""),
            "description": it.get("description", ""),
            "source_search_keyword": query,
        })
    return out


def domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def main() -> int:
    p = argparse.ArgumentParser(description="Collect candidate company websites from Brave search")
    p.add_argument("--keywords", required=True, help="keywords JSON from query_builder")
    p.add_argument("--out", required=True, help="output JSONL")
    p.add_argument("--country", default="AU")
    p.add_argument("--lang", default="en")
    p.add_argument("--per-keyword", type=int, default=10)
    args = p.parse_args()

    api_key = os.getenv("BRAVE_API_KEY", "").strip()
    if not api_key:
        raise SystemExit("Error: BRAVE_API_KEY is empty")

    kws = json.loads(Path(args.keywords).read_text(encoding="utf-8")).get("keywords", [])
    seen = set()
    rows = []
    for kw in kws:
        for r in brave_search(api_key, kw, args.per_keyword, args.country, args.lang):
            d = domain(r["url"])
            if not d or d in seen:
                continue
            seen.add(d)
            r["domain"] = d
            rows.append(r)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"candidates: {len(rows)}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
