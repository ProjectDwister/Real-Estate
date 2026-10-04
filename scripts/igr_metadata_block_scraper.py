"""Fast metadata-only Maharashtra IGR scraper.

This script does not bypass CAPTCHA. Complete the IGR search/CAPTCHA manually and
navigate to the first page of a visible pagination block. The script collects
metadata only (no Index II popups/screenshots) across the visible numeric pages
and deliberately stops before an ellipsis boundary.
"""
import re
import time
from pathlib import Path
from datetime import datetime
import pandas as pd
from playwright.sync_api import sync_playwright

BASE_URL = "https://freesearchigrservice.maharashtra.gov.in/"
PROJECT = Path(r"D:\Animesh Docs\Google Drive\Personal Projects\Real Estate Tracker")

def ask(prompt, default):
    value = input(f"{prompt} [{default}]: ").strip()
    return value or str(default)

def cell(row, i):
    try:
        return row.locator("td").nth(i).inner_text(timeout=2000).strip()
    except Exception:
        return ""

def row_indexes(page):
    out = []
    rows = page.locator("table tr")
    for i in range(rows.count()):
        r = rows.nth(i)
        if r.locator("td").count() < 9:
            continue
        if (
            re.search(r"\d+", cell(r, 0))
            and re.search(r"\d{1,2}/\d{1,2}/\d{4}", cell(r, 2))
            and re.search(r"\d+", cell(r, 7))
        ):
            out.append(i)
    return out

def signature(page):
    ids = row_indexes(page)
    return "|".join(cell(page.locator("table tr").nth(i), 0) for i in ids)

def click_page(page, label):
    old = signature(page)
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    time.sleep(0.4)
    ok = page.evaluate(
        """(t)=>{
          const xs=[...document.querySelectorAll('a,button,span')]
            .filter(e=>(e.innerText||e.textContent||'').trim()===t &&
                       e.getBoundingClientRect().height>0);
          if(!xs.length)return false;
          xs.sort((a,b)=>b.getBoundingClientRect().top-a.getBoundingClientRect().top);
          xs[0].click();
          return true;
        }""",
        str(label),
    )
    if not ok:
        return False
    for _ in range(20):
        time.sleep(0.3)
        now = signature(page)
        if now and now != old:
            return True
    return False

def main():
    year = ask("Year", 2024)
    start = int(ask("Start result page", 1))
    maxpages = int(ask("Pages in this block", 10))
    village = ask("Village", "Anik")
    prop = ask("Property / CTS no.", "1A/1")

    outdir = PROJECT / "metadata_backfill"
    outdir.mkdir(parents=True, exist_ok=True)
    out = outdir / (
        f"{year}_{village}_{prop.replace('/', '_')}_pages_"
        f"{start}_{start+maxpages-1}_{datetime.now():%Y%m%d_%H%M%S}.csv"
    )

    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1500, "height": 950})
        page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)

        print(
            f"Complete Property Details search for Year {year}, Village {village}, "
            f"Property {prop}. Solve CAPTCHA and manually navigate to page {start}."
        )
        input("When the correct result page is visible, press ENTER here...")

        current = start
        for n in range(maxpages):
            ids = row_indexes(page)
            print(f"Page {current}: {len(ids)} rows")
            if not ids:
                break

            for local, i in enumerate(ids, 1):
                r = page.locator("table tr").nth(i)
                records.append(
                    {
                        "result_page": current,
                        "local_row_on_page": local,
                        "search_year": year,
                        "search_village": village,
                        "search_property_no": prop,
                        "doc_no": cell(r, 0),
                        "document_name": cell(r, 1),
                        "registration_date": cell(r, 2),
                        "sro_name": cell(r, 3),
                        "seller_name": cell(r, 4),
                        "purchaser_name": cell(r, 5),
                        "property_description": cell(r, 6),
                        "sro_code": cell(r, 7),
                        "status": cell(r, 8),
                    }
                )

            pd.DataFrame(records).to_csv(out, index=False, encoding="utf-8-sig")

            if n == maxpages - 1:
                break
            if not click_page(page, current + 1):
                print(
                    f"Page {current+1} is not a visible numeric page or did not change. "
                    "Stopping before pagination ellipsis."
                )
                break
            current += 1

        print("Saved", len(records), "metadata rows to", out)
        input("Press ENTER to close browser...")
        browser.close()

if __name__ == "__main__":
    main()
