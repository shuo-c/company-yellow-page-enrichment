#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
import urllib.parse
from pathlib import Path


def domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def collect_with_playwright(query: str, per_keyword: int, delay_ms: int = 1200) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise SystemExit(
            "Playwright is required. Run scripts/setup_playwright.sh first. "
            f"Import error: {e}"
        )

    rows: list[dict] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num={max(per_keyword, 10)}"
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(delay_ms)

        # Try to accept consent dialog when present.
        for label in ["I agree", "Accept all", "Accept", "Agree"]:
            try:
                page.get_by_role("button", name=label).first.click(timeout=1500)
                page.wait_for_timeout(500)
                break
            except Exception:
                pass

        links = page.locator("a:has(h3)")
        count = links.count()
        rank = 0
        for i in range(count):
            if rank >= per_keyword:
                break
            a = links.nth(i)
            href = a.get_attribute("href") or ""
            title = a.locator("h3").first.inner_text(timeout=2000) if a.locator("h3").count() else ""

            if not href.startswith("http"):
                continue
            d = domain(href)
            if not d:
                continue

            rank += 1
            rows.append(
                {
                    "rank": rank,
                    "title": title.strip(),
                    "url": href,
                    "description": "",
                    "source_search_keyword": query,
                    "domain": d,
                }
            )

        browser.close()

    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Collect candidate company websites from Google via Playwright")
    p.add_argument("--keywords", required=True, help="keywords JSON from query_builder")
    p.add_argument("--out", required=True, help="output JSONL")
    p.add_argument("--per-keyword", type=int, default=10)
    p.add_argument("--delay-ms", type=int, default=1200)
    args = p.parse_args()

    kws = json.loads(Path(args.keywords).read_text(encoding="utf-8")).get("keywords", [])
    seen = set()
    rows = []

    for kw in kws:
        one = collect_with_playwright(kw, args.per_keyword, args.delay_ms)
        for r in one:
            d = r.get("domain", "")
            if not d or d in seen:
                continue
            seen.add(d)
            rows.append(r)
        time.sleep(0.5)

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
