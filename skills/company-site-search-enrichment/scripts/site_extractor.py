#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")


class MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.in_title = False
        self.meta = {}
        self.logo = ""

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self.in_title = True
        if tag == "meta":
            name = d.get("name", "").lower()
            prop = d.get("property", "").lower()
            content = d.get("content", "")
            if name:
                self.meta[name] = content
            if prop:
                self.meta[prop] = content
        if tag == "img":
            alt = (d.get("alt") or "").lower()
            src = d.get("src") or ""
            if not self.logo and ("logo" in alt or "logo" in src.lower()):
                self.logo = src

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

    def handle_data(self, data):
        if self.in_title:
            self.title += data


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode("utf-8", errors="replace")


def abs_url(base: str, maybe: str) -> str:
    if not maybe:
        return ""
    return urllib.parse.urljoin(base, maybe)


def extract_one(url: str, keyword: str) -> dict:
    html = fetch(url)
    p = MetaParser()
    p.feed(html)

    desc = p.meta.get("description") or p.meta.get("og:description") or ""
    company = p.meta.get("og:site_name") or p.title.strip()
    logo = abs_url(url, p.logo)

    emails = sorted(set(EMAIL_RE.findall(html)))
    phones = sorted(set(PHONE_RE.findall(html)))

    text_desc = re.sub(r"\s+", " ", desc).strip()
    services = []
    for token in ["service", "solution", "consulting", "support", "development", "construction", "accounting", "marketing"]:
        if token in html.lower():
            services.append(token)

    return {
        "company_name": company,
        "official_website": url,
        "logo_url": logo,
        "company_description": text_desc,
        "business_scope_summary": ", ".join(sorted(set(services)))[:500],
        "hashtags": [],
        "phone": phones[0] if phones else "",
        "email": emails[0] if emails else "",
        "address": "",
        "office_location": "",
        "contact_page": abs_url(url, "/contact"),
        "about_page": abs_url(url, "/about"),
        "services_page": abs_url(url, "/services"),
        "source_search_keyword": keyword,
        "extraction_confidence": 0.6,
        "extraction_status": "raw",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract company fields from candidate websites")
    p.add_argument("--candidates", required=True, help="candidate JSONL")
    p.add_argument("--out", required=True, help="raw extracted JSONL")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    ok, fail = 0, 0
    with Path(args.candidates).open("r", encoding="utf-8") as src, out.open("w", encoding="utf-8") as dst:
        for line in src:
            row = json.loads(line)
            url = row.get("url", "")
            kw = row.get("source_search_keyword", "")
            try:
                rec = extract_one(url, kw)
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ok += 1
            except Exception as e:
                fail += 1
                dst.write(json.dumps({"official_website": url, "extraction_status": "error", "error": str(e)}) + "\n")

    print(f"ok: {ok}")
    print(f"fail: {fail}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
