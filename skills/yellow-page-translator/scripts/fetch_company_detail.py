#!/usr/bin/env python3
"""Fetch one company detail from Supabase REST (GET), flatten to CSV, optional value translation."""

from __future__ import annotations

import argparse
import base64
import csv
import json
import os
import sys
from pathlib import Path
import urllib.error
import urllib.parse
import urllib.request


def b64url_decode(segment: str) -> dict:
    padded = segment + "=" * ((4 - len(segment) % 4) % 4)
    raw = base64.urlsafe_b64decode(padded.encode("utf-8"))
    return json.loads(raw.decode("utf-8"))


def decode_jwt(token: str) -> tuple[dict, dict]:
    parts = token.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid JWT format (expected 3 segments).")
    return b64url_decode(parts[0]), b64url_decode(parts[1])


def request_json(base_url: str, token: str, table: str, params: dict[str, str]) -> list[dict]:
    query = urllib.parse.urlencode(params, safe="(),*")
    url = f"{base_url}/rest/v1/{table}?{query}"
    req = urllib.request.Request(
        url=url,
        method="GET",
        headers={
            "apikey": token,
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Prefer": "count=exact",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def find_company_id(base_url: str, token: str, company_name: str, lang: str) -> str:
    rows = request_json(
        base_url,
        token,
        "companies",
        {
            "select": "company_id,companies_i18n!inner(name,lang_code)",
            "companies_i18n.lang_code": f"eq.{lang}",
            "companies_i18n.name": f"eq.{company_name}",
            "limit": "1",
        },
    )
    if rows:
        return str(rows[0]["company_id"])

    rows = request_json(
        base_url,
        token,
        "companies",
        {
            "select": "company_id,companies_i18n!inner(name,lang_code)",
            "companies_i18n.lang_code": f"eq.{lang}",
            "companies_i18n.name": f"ilike.*{company_name}*",
            "limit": "1",
        },
    )
    if rows:
        return str(rows[0]["company_id"])

    raise ValueError(f"Company not found: {company_name}")


def fetch_company_detail(base_url: str, token: str, company_id: str) -> dict:
    select_expr = (
        "*,"
        "companies_i18n!left(*),"
        "industries!left(*,industries_i18n!left(*),services!left(*,services_i18n!left(*))),"
        "companies_address!left(*),"
        "companies_support!left(*)"
    )

    rows = request_json(
        base_url,
        token,
        "companies",
        {"select": select_expr, "company_id": f"eq.{company_id}", "limit": "1"},
    )
    if not rows:
        raise ValueError(f"Detail not found for company_id={company_id}")
    return rows[0]


def flatten_json(obj: object, prefix: str = "") -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            rows.extend(flatten_json(value, next_prefix))
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            next_prefix = f"{prefix}[{idx}]"
            rows.extend(flatten_json(value, next_prefix))
    else:
        rows.append((prefix, "" if obj is None else str(obj)))
    return rows


def should_translate_field(field: str, value: str) -> bool:
    """Field-level guardrails: skip identifiers, lang codes, company names, and address-like fields."""
    f = field.lower()

    # IDs / codes
    if f.endswith("industry_id") or ".industry_id" in f:
        return False
    if f.endswith("lang_code") or ".lang_code" in f:
        return False
    if f.endswith("company_id") or ".company_id" in f:
        return False

    # Company name should remain source-language
    if "companies_i18n" in f and f.endswith(".name"):
        return False
    if "company_name" in f:
        return False

    # Address-related fields should not be translated
    address_tokens = ["address", "city", "state", "province", "postcode", "postal", "zip", "country", "street"]
    if any(tok in f for tok in address_tokens):
        return False

    # Non-text-like / obvious literals
    v = value.strip()
    if not v:
        return False
    if v.replace(".", "", 1).isdigit():
        return False

    return True


def maybe_translate_text(field: str, text: str, target_lang: str, cache: dict[str, str]) -> str:
    key = f"{field}\n{text}"
    if not text or key in cache:
        return cache.get(key, text)

    if not should_translate_field(field, text):
        cache[key] = text
        return text

    lower = text.lower()
    if text.startswith(("http://", "https://")) or "@" in text or lower in {"true", "false"}:
        cache[key] = text
        return text

    try:
        params = urllib.parse.urlencode(
            {"client": "gtx", "sl": "auto", "tl": target_lang, "dt": "t", "q": text}
        )
        url = f"https://translate.googleapis.com/translate_a/single?{params}"
        req = urllib.request.Request(url=url, method="GET")
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        translated = "".join(seg[0] for seg in data[0] if seg and seg[0])
        cache[key] = translated or text
        return cache[key]
    except Exception:
        cache[key] = text
        return text


def write_csv(detail: dict, csv_path: Path, translate_to: str = "") -> None:
    flat_rows = flatten_json(detail)
    do_translate = bool(translate_to.strip())
    cache: dict[str, str] = {}

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if do_translate:
            writer.writerow(["field", "value", f"value_{translate_to}"])
            for field, value in flat_rows:
                writer.writerow([field, value, maybe_translate_text(field, value, translate_to, cache)])
        else:
            writer.writerow(["field", "value"])
            for field, value in flat_rows:
                writer.writerow([field, value])


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch one company detail via GET and save JSON+CSV")
    parser.add_argument("--token", default=os.getenv("SUPABASE_SERVICE_ROLE_KEY", ""), help="Service role JWT token")
    parser.add_argument("--company-id", default="", help="Target company_id (preferred)")
    parser.add_argument("--company-name", default="", help="Fallback lookup by company name")
    parser.add_argument("--lang", default="en", help="Language code for name lookup")
    parser.add_argument("--translate-to", default="zh-CN", help="Target language for translated CSV value column; empty to disable")
    parser.add_argument("--out-dir", default="test_result", help="Output directory")
    args = parser.parse_args()

    token = args.token.strip()
    if not token:
        print("Error: token is empty. Provide --token or set SUPABASE_SERVICE_ROLE_KEY.", file=sys.stderr)
        return 1

    if not args.company_id.strip() and not args.company_name.strip():
        print("Error: provide --company-id or --company-name.", file=sys.stderr)
        return 1

    try:
        _, payload = decode_jwt(token)
        ref = payload.get("ref")
        if not ref:
            raise ValueError("JWT payload has no 'ref' claim")
        base_url = f"https://{ref}.supabase.co"

        company_id = args.company_id.strip() or find_company_id(base_url, token, args.company_name.strip(), args.lang)
        detail = fetch_company_detail(base_url, token, company_id)
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTPError {exc.code}: {err_body}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / f"company_{company_id}_detail.json"
    csv_path = out_dir / f"company_{company_id}_detail.csv"

    json_path.write_text(json.dumps(detail, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(detail, csv_path, translate_to=args.translate_to)

    print(f"company_id: {company_id}")
    print(f"JSON saved: {json_path}")
    print(f"CSV saved: {csv_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
