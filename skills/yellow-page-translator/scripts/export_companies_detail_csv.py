#!/usr/bin/env python3
"""Export detailed companies CSV via Supabase REST GET with flattened nested fields."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path


def b64url_decode(segment: str) -> dict:
    padded = segment + "=" * ((4 - len(segment) % 4) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def decode_ref(token: str) -> str:
    payload = b64url_decode(token.split(".")[1])
    ref = payload.get("ref")
    if not ref:
        raise ValueError("JWT payload missing ref")
    return ref


def request_json(base_url: str, token: str, params: dict[str, str]) -> tuple[list[dict], str]:
    q = urllib.parse.urlencode(params, safe="(),*")
    url = f"{base_url}/rest/v1/companies?{q}"
    req = urllib.request.Request(
        url,
        method="GET",
        headers={
            "apikey": token,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "count=exact",
        },
    )
    with urllib.request.urlopen(req, timeout=90) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        cr = resp.headers.get("content-range", "")
    return json.loads(body), cr


def flatten(obj: object, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            np = f"{prefix}.{k}" if prefix else k
            out.update(flatten(v, np))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            np = f"{prefix}[{i}]"
            out.update(flatten(v, np))
    else:
        out[prefix] = "" if obj is None else str(obj)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description="Export detailed flattened CSV for companies")
    p.add_argument("--token", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""))
    p.add_argument("--industry-name", default="")
    p.add_argument("--industry-lang", default="en")
    p.add_argument("--name-ilike", default="")
    p.add_argument("--batch-size", type=int, default=1)
    p.add_argument("--out-dir", default=".")
    p.add_argument("--out-name", default="companies_detail.csv")
    args = p.parse_args()

    token = args.token.strip()
    if not token:
        raise SystemExit("Error: token is empty")

    ref = decode_ref(token)
    base_url = f"https://{ref}.supabase.co"

    select_expr = (
        "*,companies_i18n!left(*),"
        "industries!left(*,industries_i18n!left(*),services!left(*,services_i18n!left(*))),"
        "companies_address!left(*),companies_support!left(*)"
    )

    filters: dict[str, str] = {}
    if args.industry_name:
        filters["industries.industries_i18n.name"] = f"ilike.*{args.industry_name}*"
        filters["industries.industries_i18n.lang_code"] = f"eq.{args.industry_lang}"
    if args.name_ilike:
        filters["companies_i18n.name"] = f"ilike.*{args.name_ilike}*"

    _, cr = request_json(base_url, token, {"select": "company_id", **filters, "limit": "1"})
    total = int(cr.split("/")[-1]) if "/" in cr and cr.split("/")[-1].isdigit() else 0

    all_rows: list[dict] = []
    bs = max(1, args.batch_size)
    for offset in range(0, total, bs):
        rows, _ = request_json(
            base_url,
            token,
            {"select": select_expr, **filters, "limit": str(bs), "offset": str(offset)},
        )
        all_rows.extend(rows)
        if (offset + bs) % 100 == 0:
            print(f"progress: {min(offset + bs, total)}/{total}")
        time.sleep(0.02)

    flat_rows = [flatten(r) for r in all_rows]
    headers = sorted({k for d in flat_rows for k in d.keys()})

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / args.out_name
    json_path = out_dir / (Path(args.out_name).stem + ".json")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=headers)
        w.writeheader()
        for d in flat_rows:
            w.writerow(d)

    json_path.write_text(json.dumps(all_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"total_target: {total}")
    print(f"fetched_rows: {len(all_rows)}")
    print(f"csv: {csv_path}")
    print(f"json: {json_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
