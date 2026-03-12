#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path


def domain(url: str) -> str:
    try:
        return urllib.parse.urlparse(url).netloc.lower().removeprefix("www.")
    except Exception:
        return ""


def clean_google_href(href: str) -> str:
    if not href:
        return ""
    if href.startswith("/url?"):
        q = urllib.parse.urlparse(href).query
        params = urllib.parse.parse_qs(q)
        return params.get("q", [""])[0]
    return href




def clean_bing_href(href: str) -> str:
    if not href:
        return ""
    href = href.strip()
    if href.startswith("/"):
        return ""
    return href

def clean_duckduckgo_href(href: str) -> str:
    if not href:
        return ""
    href = href.replace("&amp;", "&")
    if href.startswith("//"):
        href = "https:" + href
    p = urllib.parse.urlparse(href)
    if "duckduckgo.com" in p.netloc and p.path.startswith("/l/"):
        params = urllib.parse.parse_qs(p.query)
        return params.get("uddg", [""])[0]
    return href


def try_accept_consent(page) -> None:
    candidates = [
        "I agree",
        "Accept all",
        "Accept",
        "Agree",
        "接受全部",
        "同意",
    ]
    for label in candidates:
        try:
            page.get_by_role("button", name=label).first.click(timeout=1200)
            page.wait_for_timeout(500)
            return
        except Exception:
            pass


def collect_with_duckduckgo(query: str, per_keyword: int) -> list[dict]:
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        html = r.read().decode("utf-8", errors="replace")

    links = re.findall(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
    rows = []
    rank = 0
    seen = set()
    for href, title_html in links:
        if rank >= per_keyword:
            break
        href = clean_duckduckgo_href(href.strip())
        d = domain(href)
        if not href.startswith("http") or not d or d in seen:
            continue
        seen.add(d)
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        rank += 1
        rows.append({
            "rank": rank,
            "title": title,
            "url": href,
            "description": "",
            "source_search_keyword": query,
            "domain": d,
            "search_engine": "duckduckgo",
        })
    return rows




def collect_with_bing_playwright(query: str, per_keyword: int, delay_ms: int = 1500) -> list[dict]:
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
        search_url = f"https://www.bing.com/search?q={urllib.parse.quote_plus(query)}&count={max(per_keyword, 10)}&setlang=en"
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(delay_ms)

        try:
            page.wait_for_selector("#b_results, ol#b_results, li.b_algo", timeout=4000)
        except Exception:
            pass

        try:
            page.mouse.wheel(0, 1200)
            page.wait_for_timeout(300)
            page.mouse.wheel(0, -600)
        except Exception:
            pass

        selectors = [
            "#b_results li.b_algo h2 a",
            "ol#b_results li.b_algo h2 a",
            "li.b_algo h2 a",
            "#b_results li.b_algo a",
            "li.b_algo a",
            "main a[href^='http']",
        ]

        rank = 0
        seen_urls = set()

        for sel in selectors:
            try:
                nodes = page.locator(sel)
                count = nodes.count()
                for i in range(count):
                    if rank >= per_keyword:
                        break
                    a = nodes.nth(i)
                    href = clean_bing_href(a.get_attribute("href") or "")
                    if not href.startswith("http"):
                        continue
                    d = domain(href)
                    if not d:
                        continue
                    if d.endswith("bing.com") or d.endswith("microsoft.com"):
                        continue
                    if href in seen_urls:
                        continue
                    seen_urls.add(href)
                    title = (a.inner_text(timeout=1200) or "").strip()
                    if not title:
                        try:
                            title = (a.text_content(timeout=1200) or "").strip()
                        except Exception:
                            title = ""
                    rank += 1
                    rows.append(
                        {
                            "rank": rank,
                            "title": title,
                            "url": href,
                            "description": "",
                            "source_search_keyword": query,
                            "domain": d,
                            "search_engine": "bing",
                        }
                    )
            except Exception:
                continue

            if rank >= per_keyword:
                break

        browser.close()

    return rows




def collect_with_bing_rss(query: str, per_keyword: int) -> list[dict]:
    # lightweight fallback when Bing SERP DOM is blocked/changing
    url = f"https://www.bing.com/search?format=rss&q={urllib.parse.quote_plus(query)}&count={max(per_keyword, 10)}&setlang=en"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        xml = r.read().decode("utf-8", errors="replace")

    items = re.findall(r"<item>([\s\S]*?)</item>", xml, flags=re.I)
    rows = []
    rank = 0
    seen = set()
    for it in items:
        if rank >= per_keyword:
            break
        m_title = re.search(r"<title>([\s\S]*?)</title>", it, flags=re.I)
        m_link = re.search(r"<link>([\s\S]*?)</link>", it, flags=re.I)
        if not m_link:
            continue
        href = (m_link.group(1) or "").strip()
        d = domain(href)
        if not href.startswith("http") or not d or d in seen:
            continue
        seen.add(d)
        rank += 1
        rows.append({
            "rank": rank,
            "title": (m_title.group(1).strip() if m_title else ""),
            "url": href,
            "description": "",
            "source_search_keyword": query,
            "domain": d,
            "search_engine": "bing",
        })
    return rows

def collect_with_playwright(query: str, per_keyword: int, delay_ms: int = 1500) -> list[dict]:
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
        search_url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}&num={max(per_keyword, 10)}&hl=en"
        page.goto(search_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(delay_ms)

        try_accept_consent(page)

        selectors = [
            "a:has(h3)",
            "div#search a h3",
            "div.g a",
            "a[jsname]",
        ]

        seen_urls = set()
        rank = 0

        for sel in selectors:
            try:
                if sel == "div#search a h3":
                    nodes = page.locator(sel)
                    count = nodes.count()
                    for i in range(count):
                        if rank >= per_keyword:
                            break
                        h3 = nodes.nth(i)
                        a = h3.locator("xpath=ancestor::a[1]").first
                        href = clean_google_href(a.get_attribute("href") or "")
                        if not href.startswith("http"):
                            continue
                        d = domain(href)
                        if not d or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        rank += 1
                        rows.append(
                            {
                                "rank": rank,
                                "title": (h3.inner_text(timeout=1200) or "").strip(),
                                "url": href,
                                "description": "",
                                "source_search_keyword": query,
                                "domain": d,
                                "search_engine": "google",
                            }
                        )
                else:
                    nodes = page.locator(sel)
                    count = nodes.count()
                    for i in range(count):
                        if rank >= per_keyword:
                            break
                        n = nodes.nth(i)
                        href = ""
                        title = ""
                        if sel == "a:has(h3)":
                            href = clean_google_href(n.get_attribute("href") or "")
                            h3 = n.locator("h3").first
                            title = (h3.inner_text(timeout=1200) or "").strip() if h3.count() else ""
                        elif sel == "div.g a":
                            href = clean_google_href(n.get_attribute("href") or "")
                            title = (n.inner_text(timeout=1000) or "").split("\n")[0].strip()
                        else:
                            href = clean_google_href(n.get_attribute("href") or "")
                            title = (n.inner_text(timeout=1000) or "").split("\n")[0].strip()

                        if not href.startswith("http"):
                            continue
                        d = domain(href)
                        if not d or href in seen_urls:
                            continue
                        seen_urls.add(href)
                        rank += 1
                        rows.append(
                            {
                                "rank": rank,
                                "title": title,
                                "url": href,
                                "description": "",
                                "source_search_keyword": query,
                                "domain": d,
                                "search_engine": "google",
                            }
                        )
            except Exception:
                continue

            if rank >= per_keyword:
                break

        browser.close()

    return rows


def main() -> int:
    p = argparse.ArgumentParser(description="Collect candidate company websites from Google via Playwright")
    p.add_argument("--keywords", required=True, help="keywords JSON from query_builder")
    p.add_argument("--out", required=True, help="output JSONL")
    p.add_argument("--per-keyword", type=int, default=10, help="results per keyword batch")
    p.add_argument("--delay-ms", type=int, default=1500)
    p.add_argument("--retries", type=int, default=2)
    p.add_argument("--keyword-workers", type=int, default=5, help="parallel keyword workers")
    p.add_argument("--target-candidates", type=int, default=0, help="stop once this many unique domains are collected (0 = no limit)")
    p.add_argument("--engines", default="google,bing", help="comma-separated search engines in priority order: google,bing,duckduckgo")
    args = p.parse_args()

    kws = json.loads(Path(args.keywords).read_text(encoding="utf-8")).get("keywords", [])
    seen = set()
    rows = []

    engine_order = [e.strip().lower() for e in args.engines.split(",") if e.strip()]

    def collect_one_keyword(kw: str) -> list[dict]:
        one: list[dict] = []
        for eng in engine_order:
            if eng == "google":
                for attempt in range(args.retries + 1):
                    one = collect_with_playwright(kw, args.per_keyword, args.delay_ms)
                    if one:
                        break
                    time.sleep(1.0 + attempt)
                if one:
                    return one
            elif eng == "bing":
                for attempt in range(args.retries + 1):
                    one = collect_with_bing_playwright(kw, args.per_keyword, args.delay_ms)
                    if one:
                        break
                    time.sleep(1.0 + attempt)
                if not one:
                    try:
                        one = collect_with_bing_rss(kw, args.per_keyword)
                    except Exception:
                        one = []
                if one:
                    return one
            elif eng in {"duckduckgo", "ddg"}:
                one = collect_with_duckduckgo(kw, args.per_keyword)
                if one:
                    return one
        return one

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.keyword_workers)) as ex:
        fut_to_kw = {ex.submit(collect_one_keyword, kw): kw for kw in kws}
        for fut in concurrent.futures.as_completed(fut_to_kw):
            one = fut.result()
            for r in one:
                d = r.get("domain", "")
                if not d or d in seen:
                    continue
                seen.add(d)
                rows.append(r)
                if args.target_candidates > 0 and len(rows) >= args.target_candidates:
                    break
            if args.target_candidates > 0 and len(rows) >= args.target_candidates:
                break

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
