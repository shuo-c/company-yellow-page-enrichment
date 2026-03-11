#!/usr/bin/env python3
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
ADDRESS_RE = re.compile(r"\b\d{1,5}\s+[A-Za-z0-9\s.,'-]{8,}(?:WA|NSW|VIC|QLD|SA|TAS|ACT|NT)\s*\d{3,4}\b", re.I)


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


def clean_text_from_html(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def first_nonempty(*vals: str) -> str:
    for v in vals:
        if v and v.strip():
            return v.strip()
    return ""


def summarize_scope(text: str) -> str:
    candidates = []
    for sent in re.split(r"(?<=[.!?])\s+", text):
        s = sent.strip()
        if not s:
            continue
        low = s.lower()
        if any(k in low for k in ["service", "solution", "build", "construction", "renovation", "project", "commercial", "residential"]):
            candidates.append(s)
        if len(candidates) >= 3:
            break
    return " ".join(candidates)[:700]


def safe_slug(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_")
    return s[:80] or "unknown_company"


def download_logo(logo_url: str, logos_dir: Path, website_url: str, company_name: str) -> str:
    if not logo_url:
        return ""
    logos_dir.mkdir(parents=True, exist_ok=True)
    parsed = urllib.parse.urlparse(logo_url)
    ext = Path(parsed.path).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".ico"}:
        ext = ".png"
    digest = hashlib.sha1((website_url + "|" + logo_url).encode("utf-8")).hexdigest()[:10]
    slug = safe_slug(company_name)
    target = logos_dir / f"{slug}_{digest}{ext}"

    req = urllib.request.Request(logo_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        data = r.read()
    if not data:
        return ""
    target.write_bytes(data)
    return str(target)


def fetch_optional_page(base_url: str, path: str) -> tuple[str, str]:
    url = abs_url(base_url, path)
    try:
        return url, fetch(url)
    except Exception:
        return url, ""


def extract_one(url: str, keyword: str, logos_dir: Path) -> dict:
    html = fetch(url)
    p = MetaParser()
    p.feed(html)

    homepage_text = clean_text_from_html(html)

    contact_page, contact_html = fetch_optional_page(url, "/contact")
    about_page, about_html = fetch_optional_page(url, "/about")
    services_page, services_html = fetch_optional_page(url, "/services")

    contact_text = clean_text_from_html(contact_html)
    about_text = clean_text_from_html(about_html)
    services_text = clean_text_from_html(services_html)

    desc_meta = first_nonempty(p.meta.get("description", ""), p.meta.get("og:description", ""))
    desc_fallback = first_nonempty(about_text[:500], homepage_text[:500])
    company_description = first_nonempty(desc_meta, desc_fallback)

    company = first_nonempty(p.meta.get("og:site_name", ""), p.title.strip())
    logo = abs_url(url, p.logo)
    saved_logo_path = ""
    try:
        saved_logo_path = download_logo(logo, logos_dir, url, company)
    except Exception:
        saved_logo_path = ""

    joined_text = "\n".join([homepage_text, about_text, services_text, contact_text])
    emails = sorted(set(EMAIL_RE.findall(joined_text)))
    phones = sorted(set(PHONE_RE.findall(joined_text)))
    addresses = sorted(set(ADDRESS_RE.findall(joined_text)))

    return {
        "company_name": company,
        "official_website": url,
        "logo_url": logo,
        "saved_logo_path": saved_logo_path,
        "company_description": re.sub(r"\s+", " ", company_description).strip()[:1200],
        "business_scope_summary": summarize_scope(first_nonempty(services_text, homepage_text, about_text)),
        "hashtags": [],
        "phone": phones[0] if phones else "",
        "email": emails[0] if emails else "",
        "address": addresses[0] if addresses else "",
        "office_location": keyword.split()[0] if keyword else "",
        "contact_page": contact_page,
        "about_page": about_page,
        "services_page": services_page,
        "source_search_keyword": keyword,
        "company_site_passed": True,
        "company_site_reason": "not_checked",
        "company_site_score": 0.0,
        "extraction_confidence": 0.6,
        "extraction_status": "raw",
    }


def main() -> int:
    p = argparse.ArgumentParser(description="Extract company fields from candidate websites")
    p.add_argument("--candidates", required=True, help="candidate JSONL")
    p.add_argument("--out", required=True, help="raw extracted JSONL")
    p.add_argument("--logos-dir", required=True, help="directory to save downloaded logo files")
    p.add_argument("--workers", type=int, default=5, help="parallel workers (default: 5)")
    p.add_argument("--task-timeout", type=int, default=30, help="per-task timeout seconds (default: 30)")
    args = p.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    items = []
    with Path(args.candidates).open("r", encoding="utf-8") as src:
        for line in src:
            if line.strip():
                items.append(json.loads(line))

    def job(row: dict) -> dict:
        url = row.get("url", "")
        kw = row.get("source_search_keyword", "")
        return extract_one(url, kw, Path(args.logos_dir))

    ok, fail, timeout = 0, 0, 0
    with out.open("w", encoding="utf-8") as dst, concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = []
        for row in items:
            futs.append((row, ex.submit(job, row)))

        for row, fut in futs:
            url = row.get("url", "")
            try:
                rec = fut.result(timeout=max(1, args.task_timeout))
                dst.write(json.dumps(rec, ensure_ascii=False) + "\n")
                ok += 1
            except concurrent.futures.TimeoutError:
                timeout += 1
                fut.cancel()
                dst.write(json.dumps({"official_website": url, "extraction_status": "error", "error": "task_timeout"}) + "\n")
            except Exception as e:
                fail += 1
                dst.write(json.dumps({"official_website": url, "extraction_status": "error", "error": str(e)}) + "\n")

    print(f"ok: {ok}")
    print(f"fail: {fail}")
    print(f"timeout: {timeout}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
