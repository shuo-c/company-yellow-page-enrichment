#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from logo_judge_agent import LogoJudgeAgent


def hashtags_from_text(text: str, scope: str) -> list[str]:
    t = (text + " " + scope).lower()
    tags = []
    mapping = {
        "#ITServices": ["it", "managed", "support"],
        "#Cybersecurity": ["security", "cyber"],
        "#CloudSolutions": ["cloud"],
        "#SoftwareDevelopment": ["software", "development"],
        "#Marketing": ["marketing", "seo", "brand"],
        "#Accounting": ["accounting", "tax", "bookkeeping"],
        "#Construction": ["construction", "building", "contractor"],
    }
    for tag, kws in mapping.items():
        if any(k in t for k in kws):
            tags.append(tag)
    return tags[:8]


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def main() -> int:
    p = argparse.ArgumentParser(description="Validate required fields and normalize extracted records")
    p.add_argument("--infile", required=True)
    p.add_argument("--out-valid", required=True)
    p.add_argument("--out-skipped", required=True)
    args = p.parse_args()

    valid = Path(args.out_valid)
    skipped = Path(args.out_skipped)
    valid.parent.mkdir(parents=True, exist_ok=True)

    seen_domains = set()
    judge = LogoJudgeAgent()
    ok = sk = 0
    with Path(args.infile).open("r", encoding="utf-8") as src, valid.open("w", encoding="utf-8") as v, skipped.open("w", encoding="utf-8") as s:
        for line in src:
            r = json.loads(line)
            site = clean(r.get("official_website", ""))
            logo = clean(r.get("logo_url", ""))
            saved_logo_path = clean(r.get("saved_logo_path", ""))
            desc = clean(r.get("company_description", ""))
            company_site_passed = bool(r.get("company_site_passed", True))
            company_site_reason = clean(r.get("company_site_reason", ""))
            domain = site.split("//")[-1].split("/")[0].lower()

            reason = ""
            if not site:
                reason = "unofficial_website"
            elif not company_site_passed:
                reason = company_site_reason or "not_company_website_or_directory"
            elif domain in seen_domains:
                reason = "duplicate_domain"
            elif not logo:
                reason = "missing_logo"
            elif not saved_logo_path:
                reason = "missing_logo_file"
            elif not Path(saved_logo_path).exists():
                reason = "missing_logo_file"
            else:
                jr = judge.judge(saved_logo_path)
                if not jr.passed:
                    reason = jr.reason
                    r["logo_quality_score"] = jr.score

            if not reason and not desc:
                reason = "missing_description"

            if reason:
                r["extraction_status"] = "skipped"
                r["skip_reason"] = reason
                s.write(json.dumps(r, ensure_ascii=False) + "\n")
                sk += 1
                continue

            seen_domains.add(domain)
            r["company_name"] = clean(r.get("company_name", ""))
            r["company_description"] = desc
            r["business_scope_summary"] = clean(r.get("business_scope_summary", ""))
            r["hashtags"] = hashtags_from_text(desc, r["business_scope_summary"])
            r["extraction_status"] = "valid"
            r["logo_quality_score"] = r.get("logo_quality_score", 0.8)
            r["extraction_confidence"] = 0.85 if r["hashtags"] else 0.75
            v.write(json.dumps(r, ensure_ascii=False) + "\n")
            ok += 1

    print(f"valid: {ok}")
    print(f"skipped: {sk}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
