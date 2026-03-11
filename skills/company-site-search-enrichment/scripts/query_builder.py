#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
from pathlib import Path

RELATED = {
    "it": ["software", "cybersecurity", "managed it", "cloud", "web development"],
    "accounting": ["tax", "bookkeeping", "financial advisory", "audit"],
    "marketing": ["digital marketing", "seo", "branding", "advertising"],
    "construction": ["building", "civil", "contractor", "renovation"],
    "builder": ["home builder", "custom builder", "residential builder", "construction company", "renovation company"],
}

GENERIC_EXPANSIONS = ["services", "business", "provider", "contractor", "near me", "best"]

AU_STATES = {
    "nsw", "new south wales", "vic", "victoria", "qld", "queensland", "wa", "western australia",
    "sa", "south australia", "tas", "tasmania", "act", "australian capital territory", "nt", "northern territory",
}
AU_STATE_CANONICAL = ["NSW", "VIC", "QLD", "WA", "SA", "TAS", "ACT", "NT"]
AU_MAJOR_CITIES = [
    "Sydney", "Melbourne", "Brisbane", "Perth", "Adelaide", "Canberra", "Hobart", "Darwin",
    "Gold Coast", "Newcastle", "Wollongong", "Geelong", "Sunshine Coast", "Townsville", "Cairns",
]


def load_taxonomy(path: Path, id_field: str) -> tuple[dict[str, str], list[str]]:
    names: dict[str, str] = {}
    all_en: list[str] = []
    if not path.exists():
        return names, all_en
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("lang_code") != "en":
                continue
            name = (row.get("name") or "").strip()
            xid = (row.get(id_field) or "").strip()
            if name:
                names[name.lower()] = xid
                all_en.append(name)
    return names, all_en


def validate_location(location: str) -> None:
    t = location.strip().lower()
    if not t:
        raise SystemExit("location is empty")
    if t in AU_STATES or t in {c.lower() for c in AU_MAJOR_CITIES}:
        return
    norm = t.replace(",", " ")
    joined = " ".join([x for x in norm.split() if x])
    if any(city.lower() in joined for city in AU_MAJOR_CITIES) and any(state in joined for state in AU_STATES):
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
    for n in list(industry_names.keys()) + list(service_names.keys()):
        if s in n or n in s:
            return
    raise SystemExit("seed-topic must come from industries/services taxonomy CSV (English name)")


def pick_location_pool(base_location: str, mode: str, mixed_city_ratio: float) -> list[str]:
    if mode == "fixed":
        return [base_location]
    if mode == "city":
        return AU_MAJOR_CITIES
    if mode == "state":
        return AU_STATE_CANONICAL
    # mixed
    cities = AU_MAJOR_CITIES[:]
    states = AU_STATE_CANONICAL[:]
    random.shuffle(cities)
    random.shuffle(states)
    cut = max(1, int(len(cities) * max(0.0, min(1.0, mixed_city_ratio))))
    return cities[:cut] + states[: max(1, len(states) // 2)]


def associative_expansions(seed_topic: str, all_service_names: list[str], cap: int = 30) -> list[str]:
    s = seed_topic.lower().strip()
    words = {w for w in s.replace("/", " ").replace("&", " ").split() if w}

    candidates = []
    for name in all_service_names:
        ln = name.lower()
        if s in ln or any(w in ln for w in words):
            candidates.append(name)

    base = RELATED.get(s, [])
    merged = base + candidates + [f"{seed_topic} {x}" for x in GENERIC_EXPANSIONS]

    out: list[str] = []
    seen = set()
    for x in merged:
        k = x.strip()
        lk = k.lower()
        if not k or lk in seen:
            continue
        seen.add(lk)
        out.append(k)
        if len(out) >= cap:
            break
    return out


def build_keywords(location: str, seed_topic: str, expansion_count: int, locations: list[str], all_service_names: list[str]) -> list[str]:
    expansions = associative_expansions(seed_topic, all_service_names, cap=max(20, expansion_count * 3))

    base = [f"{location} {seed_topic} company"]
    for loc in locations:
        for e in expansions:
            base.append(f"{loc} {e} company")

    uniq: list[str] = []
    seen = set()
    for k in base:
        lk = k.lower().strip()
        if "company" not in lk:
            continue
        if lk in seen:
            continue
        seen.add(lk)
        uniq.append(k)
        if len(uniq) >= expansion_count:
            break
    return uniq


def main() -> int:
    p = argparse.ArgumentParser(description="Build keyword list: location + industry + company")
    p.add_argument("--location", required=True)
    p.add_argument("--seed-topic", required=True)
    p.add_argument("--expansion-count", type=int, default=10, help="target expanded keyword count (formal parameter)")
    p.add_argument("--max-keywords", type=int, default=None, help="deprecated alias of --expansion-count")
    p.add_argument("--location-mode", choices=["fixed", "city", "state", "mixed"], default="mixed")
    p.add_argument("--mixed-city-ratio", type=float, default=0.7)
    p.add_argument("--random-seed", type=int, default=42)
    p.add_argument("--out", required=True, help="Output JSON path")
    p.add_argument("--industry-csv", default=str((Path(__file__).resolve().parent.parent / "references" / "industries.csv")))
    p.add_argument("--service-csv", default=str((Path(__file__).resolve().parent.parent / "references" / "services.csv")))
    args = p.parse_args()

    random.seed(args.random_seed)

    expansion_count = args.max_keywords if args.max_keywords is not None else args.expansion_count

    industry_names, _ = load_taxonomy(Path(args.industry_csv), "industry_id")
    service_names, all_services = load_taxonomy(Path(args.service_csv), "service_id")

    validate_location(args.location)
    validate_seed_topic(args.seed_topic, industry_names, service_names)

    location_pool = pick_location_pool(args.location, args.location_mode, args.mixed_city_ratio)
    kws = build_keywords(args.location, args.seed_topic, expansion_count, location_pool, all_services)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "keywords": kws,
                "meta": {
                    "expansion_count": expansion_count,
                    "location_mode": args.location_mode,
                    "mixed_city_ratio": args.mixed_city_ratio,
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"keywords: {len(kws)}")
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
