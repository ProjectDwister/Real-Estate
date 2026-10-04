# Mumbai Real Estate Tracker

GitHub Pages dashboard and local Maharashtra IGR data pipeline for Mumbai property-registration analysis.

## Live site

https://projectdwister.github.io/Real-Estate/

## Data currently loaded

- **2025:** 265 sanitized, Index II-enriched Bhakti Park / Anik records
- **2026:** 198 unique IGR metadata records for the current Anik / 1A/1 collection, with 169 Index II-enriched records layered over them
- **2014–2024:** historical backfill runner is ready; these years remain marked Pending until collected from IGR

The site deliberately labels incomplete years as **Partial/Pending** rather than treating missing backfill as zero transaction activity.

## Public dashboard

The website provides filters for year, village, Property/CTS, document group and document type, plus searchable transaction records. Available fields include registration/execution date, document number/type, CTS/property reference, building, wing, unit, floor, area, consideration, market value, rate per sq ft, rent, deposit, SRO and data-quality status.

## Privacy

Raw IGR result tables may contain seller and purchaser names. They stay in `data/input_metadata/`, which is git-ignored.

The public CSV and enriched datasets do **not** publish seller or purchaser fields.

## Historical backfill: 2014–2024

Run:

```bat
run_backfill_2014_2024.bat
```

The browser will open once and the script will walk through 2024 down to 2014. For each year:

1. Select **Property Details**
2. Select **Mumbai**
3. Select the year shown in the terminal
4. District: **Mumbai Suburban**
5. Village: **Anik**
6. Property / CTS: **1A/1**
7. Complete the CAPTCHA/search
8. Leave the browser on result page 1
9. Press Enter in the terminal

After that the script traverses result pages automatically, including the **forward/right-hand ellipsis** after each 10-page pagination block. It saves metadata only, so this is much faster than opening every Index II.

CAPTCHA is not bypassed.

## Current-year refresh

Run:

```bat
run_daily_update.bat
```

Complete the IGR CAPTCHA/search once. The script collects current-year metadata, rebuilds the sanitized public files, commits changes and pushes them to GitHub.

## Index II enrichment

The metadata backfill is intentionally separate from Index II enrichment. Metadata is collected for every registration first. Sale/Agreement and Rent/Licence records can then be prioritized for deeper Index II extraction of consideration, market value, area, ₹/sq ft, rent and deposit.

## Local folder

Recommended clone location:

```text
D:\Animesh Docs\Google Drive\Personal Projects\Real Estate Tracker\Real-Estate
```

## Main files

- `index.html`, `styles.css`, `app.js` — GitHub Pages dashboard
- `data/master_transactions.csv` — sanitized base metadata
- `data/enriched/*.csv` — sanitized Index II-enriched monthly records
- `data/data_manifest.json` — files loaded by the website
- `data/coverage.csv` — historical coverage status
- `scripts/igr_metadata_year_scraper.py` — multi-year metadata collector
- `scripts/build_master_transactions.py` — sanitization/dedupe/public build
- `run_backfill_2014_2024.bat` — historical runner
- `run_daily_update.bat` — current-year refresh/publish

## Scope

The current populated dataset is **Bhakti Park / Anik**, centered on Property/CTS search **1A/1**. The codebase is designed to add more Mumbai villages/CTS searches later, but the dashboard must not be interpreted as Mumbai-wide coverage until those searches are actually backfilled.
