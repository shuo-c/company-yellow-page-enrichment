#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
import re
import urllib.parse


@dataclass
class CompanyJudgeResult:
    passed: bool
    reason: str
    score: float


class CompanyJudgeAgent:
    """Heuristic judge for filtering non-company or directory/listing websites."""

    DIRECTORY_DOMAINS = {
        "yellowpages.com.au",
        "yellowpages.com",
        "yelp.com",
        "truelocal.com.au",
        "hotfrog.com.au",
        "wordofmouth.com.au",
        "oneflare.com.au",
    }

    DIRECTORY_PATTERNS = [
        r"\byellow\s*pages\b",
        r"\bbusiness\s*directory\b",
        r"\blisting(s)?\b",
        r"\btop\s*\d+\b",
        r"\bbest\s+.*\s+in\s+",
        r"\bcompare\b",
        r"\breview(s)?\b",
    ]

    COMPANY_SIGNALS = [
        r"\babout\s+us\b",
        r"\bcontact\s+us\b",
        r"\bour\s+services\b",
        r"\bpty\s+ltd\b",
        r"\bprivacy\s+policy\b",
        r"\bterms\s+of\s+service\b",
    ]

    def judge(self, website_url: str, page_title: str, html: str) -> CompanyJudgeResult:
        parsed = urllib.parse.urlparse(website_url)
        d = parsed.netloc.lower().removeprefix("www.")

        if d in self.DIRECTORY_DOMAINS:
            return CompanyJudgeResult(False, "directory_site", 0.05)

        text = f"{page_title}\n{html[:12000]}".lower()

        dir_hits = sum(1 for p in self.DIRECTORY_PATTERNS if re.search(p, text))
        company_hits = sum(1 for p in self.COMPANY_SIGNALS if re.search(p, text))

        # Score > 0 means more likely a real company website.
        score = (company_hits * 0.25) - (dir_hits * 0.3)

        if dir_hits >= 2 and company_hits == 0:
            return CompanyJudgeResult(False, "not_company_website_or_directory", max(0.0, 0.3 + score))

        if score < -0.2:
            return CompanyJudgeResult(False, "not_company_website_or_directory", max(0.0, 0.4 + score))

        return CompanyJudgeResult(True, "ok", min(1.0, 0.5 + score))
