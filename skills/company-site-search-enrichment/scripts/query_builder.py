#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

RELATED = {
    "it": ["software", "cybersecurity", "managed it", "cloud", "web development"],
    "accounting": ["tax", "bookkeeping", "financial advisory", "audit"],
    "marketing": ["digital marketing", "seo", "branding", "advertising"],
    "construction": ["building", "civil", "contractor", "renovation"],
    "builder": ["home builder", "custom builder", "residential builder", "construction company", "renovation company"],
}

GENERIC_EXPANSIONS = [
    "services",
    "business",
    "provider",
    "contractor",
    "near me",
    "best",
]

AU_STATES = {
    "nsw", "new south wales",
    "vic", "victoria",
    "qld", "queensland",
    "wa", "western australia",
    "sa", "south australia",
    "tas", "tasmania",
    "act", "australian capital territory",
    "nt", "northern territory",
}

AU_MAJOR_CITIES = {
    "sydney", "melbourne", "brisbane", "perth", "adelaide", "canberra", "hobart", "darwin",
    "gold coast", "newcastle", "wollongong", "geelong", "sunshine coast", "townsville", "cairns",
}


def load_taxonomy_names(path: Path, id_field: str) -> dict[str, str]:
    names: dict[str, str] = {}
    if not path.exists():
        return names
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("lang_code") != "en":
                continue
            name = (row.get("name") or "").strip()
            xid = (row.get(id_field) or "").strip()
            if name:
                names[name.lower()] = xid
    return names


def validate_location(location: str) -> None:
    t = location.strip().lower()
    if not t:
        raise SystemExit("location is empty")
    if t in AU_STATES or t in AU_MAJOR_CITIES:
        return
    # allow combinations like "Sydney NSW" / "Sydney, NSW"
    norm = t.replace(",", " ")
    tokens = [x for x in norm.split() if x]
    joined = " ".join(tokens)
    if any(city in joined for city in AU_MAJOR_CITIES) and any(state in joined for state in AU_STATES):
        return
    raise SystemExit(
        "location must be Australia major states/cities (e.g. Sydney, Melbourne, Brisbane, Perth, Adelaide, Canberra, Hobart, Darwin, NSW, VIC, QLD, WA, SA, TAS, ACT, NT)"
    )


def validate_seed_topic(seed_topic: str, industry_names: dict[str, str], service_names: dict[str, str]) -> None:
    s = seed_topic.strip().lower()
    if not s:
        raise SystemExit("seed-topic is empty")
    if s in industry_names or s in service_names:
        return
    # loose contains match fallback (for inputs like "IT Support")
    for n in list(industry_names.keys()) + list(service_names.keys()):
        if s in n or n in s:
            return
    raise SystemExit("seed-topic must come from industries/services taxonomy CSV (English name)")


def build_keywords(location: str, seed_topic: str, max_keywords: int) -> list[str]:
    topic = seed_topic.strip().lower()
    base = [f"{location} {seed_topic} company"]

    expansions = RELATED.get(topic, [])
    if not expansions:
        expansions = [f"{seed_topic} {x}" for x in GENERIC_EXPANSIONS]

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
    p.add_argument("--industry-csv", default=str((Path(__file__).resolve().parent.parent / "references" / "industries.csv")))
    p.add_argument("--service-csv", default=str((Path(__file__).resolve().parent.parent / "references" / "services.csv")))
    args = p.parse_args()

    industry_names = load_taxonomy_names(Path(args.industry_csv), "industry_id")
    service_names = load_taxonomy_names(Path(args.service_csv), "service_id")

    validate_location(args.location)
    validate_seed_topic(args.seed_topic, industry_names, service_names)

    kws = build_keywords(args.location, args.seed_topic, args.max_keywords)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"keywords": kws}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"keywords: {len(kws)}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
