"""Maharashtra IGR metadata backfill runner for the Mumbai Real Estate Tracker.

Purpose
-------
Collect the *result-table metadata* quickly for one or more years without opening
every Index II document. CAPTCHA/search challenges are intentionally completed
by the user in the visible browser. After the results table is visible, this
script handles numeric pagination and the forward "..." control.

Default historical run:
    python scripts/igr_metadata_year_scraper.py --years 2024-2014

Current-year refresh:
    python scripts/igr_metadata_year_scraper.py --years 2026

Output is written to data/input_metadata/, which is git-ignored because raw IGR
metadata can contain seller/purchaser names. The public build strips those fields.
"""
from __future__ import annotations

import argparse
import re
import time
from pathlib import Path

import pandas as pd
from playwright.sync_api import sync_playwright

BASE_URL = "https://freesearchigrservice.maharashtra.gov.in/"
ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "data" / "input_metadata"
INPUT_DIR.mkdir(parents=True, exist_ok=True)


def parse_years(spec: str) -> list[int]:
    spec = spec.strip()
    if "-" in spec and "," not in spec:
        a, b = [int(x.strip()) for x in spec.split("-", 1)]
        step = -1 if a > b else 1
        return list(range(a, b + step, step))
    return [int(x.strip()) for x in spec.split(",") if x.strip()]


def clean(v) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def cell(row, idx: int) -> str:
    try:
        return clean(row.locator("td").nth(idx).inner_text(timeout=2500))
    except Exception:
        return ""


def result_row_indexes(page) -> list[int]:
    out = []
    rows = page.locator("table tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        try:
            if row.locator("td").count() < 9:
                continue
            doc = cell(row, 0)
            date = cell(row, 2)
            sro = cell(row, 7)
            if (
                re.search(r"\d+", doc)
                and re.search(r"\d{1,2}/\d{1,2}/\d{4}", date)
                and re.search(r"\d+", sro)
            ):
                out.append(i)
        except Exception:
            pass
    return out


def page_signature(page) -> str:
    ids = result_row_indexes(page)
    return "|".join(
        f"{cell(page.locator('table tr').nth(i),0)}:{cell(page.locator('table tr').nth(i),2)}"
        for i in ids
    )


def wait_for_signature_change(page, old: str, seconds: float = 12.0) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        time.sleep(0.35)
        new = page_signature(page)
        if new and new != old:
            return True
    return False


def click_bottom_rightmost_exact(page, text_value: str) -> bool:
    """Click exact text in the bottom-most pager; on ties choose right-most.

    Choosing the right-most ellipsis is important because IGR commonly shows
    both a backward and a forward ellipsis after page 10.
    """
    try:
        return bool(
            page.evaluate(
                """
                (target) => {
                  const els=[...document.querySelectorAll('a,button,span,td,div')]
                    .map(el=>{
                      const r=el.getBoundingClientRect();
                      const s=getComputedStyle(el);
                      return {el,r,t:(el.innerText||el.textContent||'').trim(),s};
                    })
                    .filter(x=>x.t===target && x.r.width>0 && x.r.height>0 &&
                               x.s.display!=='none' && x.s.visibility!=='hidden');
                  if(!els.length) return false;
                  const maxTop=Math.max(...els.map(x=>x.r.top));
                  const bottom=els.filter(x=>x.r.top>=maxTop-12);
                  bottom.sort((a,b)=>b.r.left-a.r.left);
                  bottom[0].el.scrollIntoView({block:'center'});
                  bottom[0].el.click();
                  return true;
                }
                """,
                text_value,
            )
        )
    except Exception:
        return False


def visible_exact(page, text_value: str) -> bool:
    try:
        return bool(
            page.evaluate(
                """
                (target)=>[...document.querySelectorAll('a,button,span,td,div')]
                  .some(el=>{
                    const r=el.getBoundingClientRect(), s=getComputedStyle(el);
                    return (el.innerText||el.textContent||'').trim()===target &&
                           r.width>0 && r.height>0 && s.display!=='none' &&
                           s.visibility!=='hidden';
                  })
                """,
                text_value,
            )
        )
    except Exception:
        return False


def go_forward(page, current_page: int) -> bool:
    """Move exactly one results page forward, including across an ellipsis."""
    target = current_page + 1
    old = page_signature(page)

    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.4)

    # Normal visible numeric page.
    if visible_exact(page, str(target)):
        if click_bottom_rightmost_exact(page, str(target)) and wait_for_signature_change(page, old):
            return True

    # Cross a 10-page block using the RIGHT-MOST ellipsis.
    if visible_exact(page, "..."):
        if click_bottom_rightmost_exact(page, "..."):
            if wait_for_signature_change(page, old):
                return True
            # Some paginator implementations only reveal the next block first.
            time.sleep(0.8)
            if visible_exact(page, str(target)):
                if click_bottom_rightmost_exact(page, str(target)) and wait_for_signature_change(page, old):
                    return True

    return False


def scrape_current_results(page, year: int, village: str, property_no: str) -> pd.DataFrame:
    output = INPUT_DIR / f"{year}_{village}_{property_no.replace('/', '_')}_metadata.csv"
    records: list[dict] = []
    seen_signatures: set[str] = set()
    page_no = 1

    while True:
        sig = page_signature(page)
        if not sig:
            print("No result rows found; stopping.")
            break
        if sig in seen_signatures:
            print(f"Duplicate result page detected at logical page {page_no}; stopping to avoid a loop.")
            break
        seen_signatures.add(sig)

        ids = result_row_indexes(page)
        print(f"Year {year} | page {page_no} | {len(ids)} rows")

        for local, i in enumerate(ids, 1):
            row = page.locator("table tr").nth(i)
            records.append(
                {
                    "result_page": page_no,
                    "local_row_on_page": local,
                    "search_year": str(year),
                    "search_district": "Mumbai Suburban",
                    "search_village": village,
                    "search_property_no": property_no,
                    "doc_no": cell(row, 0),
                    "document_name": cell(row, 1),
                    "registration_date": cell(row, 2),
                    "sro_name": cell(row, 3),
                    "seller_name": cell(row, 4),
                    "purchaser_name": cell(row, 5),
                    "property_description": cell(row, 6),
                    "sro_code": cell(row, 7),
                    "status": cell(row, 8),
                }
            )

        # Continuous checkpoint; safe to stop with Ctrl+C.
        pd.DataFrame(records).to_csv(output, index=False, encoding="utf-8-sig")

        if not go_forward(page, page_no):
            print(f"No validated forward page after page {page_no}. Year {year} complete or pager ended.")
            break

        page_no += 1

    df = pd.DataFrame(records)
    if not df.empty:
        # Remove exact duplicates caused by any portal quirks.
        key = ["doc_no", "registration_date", "sro_code", "document_name"]
        df = df.drop_duplicates(key, keep="first")
        df.to_csv(output, index=False, encoding="utf-8-sig")
    print(f"Saved {len(df):,} unique rows to {output}")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", default="2024-2014", help="e.g. 2024-2014 or 2026 or 2024,2023")
    ap.add_argument("--village", default="Anik")
    ap.add_argument("--property", default="1A/1", dest="property_no")
    args = ap.parse_args()
    years = parse_years(args.years)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport={"width": 1500, "height": 950})
        page = context.new_page()

        for n, year in enumerate(years, 1):
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            print("\n" + "=" * 96)
            print(f"BACKFILL {n}/{len(years)} — YEAR {year}")
            print(f"Search: Property Details | Mumbai | {year} | Mumbai Suburban | {args.village} | {args.property_no}")
            print("Complete the search and CAPTCHA in the browser. Leave the browser on RESULT PAGE 1.")
            print("=" * 96)
            input("When page 1 results are visible, press ENTER here... ")

            scrape_current_results(page, year, args.village, args.property_no)

            if n != len(years):
                print(f"Year {year} saved. The browser will now return to the search page for the next year.")

        input("\nBackfill run finished. Press ENTER to close Chrome... ")
        browser.close()


if __name__ == "__main__":
    main()
