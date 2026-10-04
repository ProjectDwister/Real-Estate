"""Build the sanitized public dataset from local IGR metadata CSVs and
optional parsed Index II CSVs.

Raw input folders are git-ignored because they may contain party names.
Only data/master_transactions.csv, data/coverage.csv and data/status.json
are intended for GitHub.
"""
from __future__ import annotations
import json
import re
from datetime import datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
META_DIR = ROOT / "data" / "input_metadata"
PARSED_DIR = ROOT / "data" / "input_parsed_indexii"
OUT = ROOT / "data" / "master_transactions.csv"
COVERAGE = ROOT / "data" / "coverage.csv"
STATUS = ROOT / "data" / "status.json"
KEY = ["doc_no", "registration_date", "sro_code", "document_name"]

PUBLIC_COLS = [
    "year","registration_date","doc_no","document_name","doc_group","village",
    "property_no","sro_name","sro_code","property_description","building_name",
    "unit_no","floor_no","area_sqft","consideration_amount","market_value",
    "rate_per_sqft","rent_amount","deposit_amount","source_kind","record_quality"
]

def txt(v):
    return "" if pd.isna(v) else re.sub(r"\s+", " ", str(v)).strip()

def norm(s):
    return s.fillna("").astype(str).str.strip().str.replace(r"\s+", " ", regex=True)

def read_csvs(folder):
    frames = []
    for p in sorted(folder.glob("*.csv")):
        try:
            x = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
            x["_input_file"] = p.name
            frames.append(x)
        except Exception as e:
            print("Skipping", p, e)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

def doc_group(name):
    s = txt(name).lower()
    if any(k in s for k in ["leave and licenses","leave and licence","leave & license","लिव्ह"]):
        return "Rent / Licence"
    if any(k in s for k in ["sale deed","agreement to sale","सेल डीड","अँग्रीमेंट टू सेल"]):
        return "Sale / Agreement"
    if any(k in s for k in ["mortgage","deposit of title","pawn","गहाणखत"]):
        return "Mortgage / Security"
    if any(k in s for k in ["gift","बक्षीसपत्र"]):
        return "Gift"
    if any(k in s for k in ["release","रिलीज","reconveyance","रिकन्व्हेन्स"]):
        return "Release / Reconveyance"
    if any(k in s for k in ["correction","चुक दुरुस्ती"]):
        return "Correction"
    return "Other"

def extract_unit(desc):
    patterns = [
        r"(?:flat|apartment/flat|unit)\s*(?:no\.?|number)?\s*[:#-]?\s*([A-Za-z0-9/-]+)",
        r"फ्लॅट\s*नं\.?\s*[:#-]?\s*([A-Za-z0-9/-]+)",
        r"सदनिका\s*नं\.?\s*[:#-]?\s*([^,;]+)",
    ]
    for p in patterns:
        m = re.search(p, desc, re.I)
        if m:
            return txt(m.group(1))[:60]
    return ""

def extract_building(desc):
    patterns = [
        r"Building Name\s*:\s*([^\n,]+)",
        r"इमारतीचे नाव\s*:\s*([^,;]+)",
        r"(AJMERA\s+[A-Z][A-Z ]{2,35})",
    ]
    for p in patterns:
        m = re.search(p, desc, re.I)
        if m:
            return txt(m.group(1))[:100]
    return ""

def extract_floor(desc):
    for p in [
        r"Floor No\s*:\s*([^,;]+)",
        r"माळा नं\s*:\s*([^,;]+)",
        r"(\d{1,2})(?:st|nd|rd|th)\s+floor",
    ]:
        m = re.search(p, desc, re.I)
        if m:
            return txt(m.group(1))[:40]
    return ""

def extract_area_sqft(desc):
    pats = [
        r"([\d,.]+)\s*(?:sq\.?\s*ft|sqft|square\s*feet|square\s*foot|चौरस\s*फूट)",
        r"([\d,.]+)\s*(?:sq\.?\s*m|sqm|square\s*met(?:er|re)s?|चौरस\s*मीटर)",
    ]
    for i, p in enumerate(pats):
        m = re.search(p, desc, re.I)
        if m:
            try:
                n = float(m.group(1).replace(",", ""))
                return round(n if i == 0 else n * 10.7639, 2)
            except Exception:
                pass
    return ""

def choose(df, *names):
    for n in names:
        if n in df.columns:
            return df[n]
    return pd.Series([""] * len(df), index=df.index, dtype="object")

def main():
    meta = read_csvs(META_DIR)
    if meta.empty:
        print("No metadata CSVs found in", META_DIR)
        return

    for c in KEY:
        if c not in meta:
            meta[c] = ""

    meta["_key"] = (
        norm(meta.doc_no) + "|" + norm(meta.registration_date) + "|" +
        norm(meta.sro_code) + "|" + norm(meta.document_name)
    )
    meta = meta.drop_duplicates("_key", keep="first").copy()

    parsed = read_csvs(PARSED_DIR)
    if not parsed.empty:
        for c in KEY:
            if c not in parsed:
                parsed[c] = ""
        parsed["_key"] = (
            norm(parsed.doc_no) + "|" + norm(parsed.registration_date) + "|" +
            norm(parsed.sro_code) + "|" + norm(parsed.document_name)
        )
        parsed = parsed.drop_duplicates("_key", keep="last")
        keep = [
            c for c in parsed.columns
            if c not in {"seller_name","purchaser_name","source_metadata_file","saved_screenshot"}
        ]
        df = meta.merge(parsed[keep], on="_key", how="left", suffixes=("", "_parsed"))
    else:
        df = meta

    out = pd.DataFrame(index=df.index)
    out["year"] = choose(df, "search_year", "year")
    out["registration_date"] = choose(df, "registration_date")
    out["doc_no"] = choose(df, "doc_no")
    out["document_name"] = choose(df, "document_name", "doc_type")
    out["doc_group"] = out.document_name.map(doc_group)
    out["village"] = choose(df, "search_village", "village").map(lambda x: txt(x).title())
    out["property_no"] = choose(df, "search_property_no", "property_no")
    out["sro_name"] = choose(df, "sro_name")
    out["sro_code"] = choose(df, "sro_code")
    out["property_description"] = choose(df, "property_description")

    out["building_name"] = choose(df, "building_name").fillna("")
    miss = out.building_name.astype(str).str.strip() == ""
    out.loc[miss, "building_name"] = out.loc[miss, "property_description"].map(extract_building)

    out["unit_no"] = choose(df, "unit_no", "flat_no").fillna("")
    miss = out.unit_no.astype(str).str.strip() == ""
    out.loc[miss, "unit_no"] = out.loc[miss, "property_description"].map(extract_unit)

    out["floor_no"] = choose(df, "floor_no").fillna("")
    miss = out.floor_no.astype(str).str.strip() == ""
    out.loc[miss, "floor_no"] = out.loc[miss, "property_description"].map(extract_floor)

    out["area_sqft"] = choose(df, "area_sqft", "area").fillna("")
    miss = out.area_sqft.astype(str).str.strip() == ""
    out.loc[miss, "area_sqft"] = out.loc[miss, "property_description"].map(extract_area_sqft)

    for c in ["consideration_amount","market_value","rate_per_sqft","rent_amount","deposit_amount"]:
        out[c] = choose(df, c)

    out["source_kind"] = "Maharashtra IGR"
    out["record_quality"] = out.apply(
        lambda r: "Index II enriched"
        if any(txt(r[c]) for c in ["consideration_amount","market_value","rent_amount"])
        else "IGR metadata",
        axis=1,
    )

    def rate(r):
        if txt(r.rate_per_sqft):
            return r.rate_per_sqft
        try:
            a = float(str(r.area_sqft).replace(",", ""))
            v = float(str(r.consideration_amount).replace(",", ""))
            return round(v / a, 2) if a > 0 and v > 0 else ""
        except Exception:
            return ""

    out["rate_per_sqft"] = out.apply(rate, axis=1)
    out = out[PUBLIC_COLS]
    out.to_csv(OUT, index=False, encoding="utf-8-sig")

    counts = out.groupby("year").size().to_dict()
    cov = []
    for y in range(2014, datetime.now().year + 1):
        status = "Pending"
        notes = "Historical backfill pending"
        if str(y) in counts:
            status = "Partial"
            notes = "Records loaded; completeness depends on backfill status"
        if y == 2026 and int(counts.get("2026", 0)) >= 198:
            status = "Partial"
            notes = "Anik / 1A/1 metadata loaded; Mumbai-wide backfill still pending"
        cov.append({
            "year": y,
            "status": status,
            "records": int(counts.get(str(y), 0)),
            "notes": notes,
        })

    pd.DataFrame(cov).to_csv(COVERAGE, index=False, encoding="utf-8-sig")
    payload = {
        "last_built_at": datetime.now().astimezone().strftime("%d %b %Y, %H:%M"),
        "summary": f"{len(out):,} sanitized records loaded",
        "quality_label": "Historical backfill in progress",
        "records": len(out),
    }
    STATUS.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Wrote", len(out), "public rows to", OUT)

if __name__ == "__main__":
    main()
