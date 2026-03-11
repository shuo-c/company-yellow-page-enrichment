#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from company_judge_agent import CompanyJudgeAgent
from logo_judge_agent import LogoJudgeAgent


def main() -> int:
    p = argparse.ArgumentParser(description="Independent company/logo reasonability check")
    p.add_argument("--infile", required=True, help="input JSONL (typically valid.jsonl)")
    p.add_argument("--out-passed", required=True)
    p.add_argument("--out-rejected", required=True)
    args = p.parse_args()

    in_path = Path(args.infile)
    out_passed = Path(args.out_passed)
    out_rejected = Path(args.out_rejected)
    out_passed.parent.mkdir(parents=True, exist_ok=True)

    company_judge = CompanyJudgeAgent()
    logo_judge = LogoJudgeAgent()

    passed = rejected = 0
    with in_path.open("r", encoding="utf-8") as src, out_passed.open("w", encoding="utf-8") as okf, out_rejected.open("w", encoding="utf-8") as rejf:
        for line in src:
            if not line.strip():
                continue
            r = json.loads(line)
            url = (r.get("official_website") or "").strip()
            title = (r.get("company_name") or "").strip()
            desc = (r.get("company_description") or "").strip()
            logo_path = (r.get("saved_logo_path") or "").strip()

            cj = company_judge.judge(url, title, desc)
            lj = logo_judge.judge(logo_path) if logo_path and Path(logo_path).exists() else None

            fail_reason = ""
            if not cj.passed:
                fail_reason = cj.reason or "not_company_website_or_directory"
            elif lj is None:
                fail_reason = "missing_logo_file"
            elif not lj.passed:
                fail_reason = lj.reason

            r["company_site_passed"] = bool(cj.passed)
            r["company_site_reason"] = cj.reason
            r["company_site_score"] = cj.score
            if lj is not None:
                r["logo_quality_score"] = lj.score

            if fail_reason:
                rejf.write(json.dumps({
                    "official_website": url,
                    "company_name": title,
                    "skip_reason": fail_reason,
                    "company_site_score": cj.score,
                    "logo_quality_score": r.get("logo_quality_score", 0.0),
                }, ensure_ascii=False) + "\n")
                rejected += 1
            else:
                okf.write(json.dumps(r, ensure_ascii=False) + "\n")
                passed += 1

    print(f"passed: {passed}")
    print(f"rejected: {rejected}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
