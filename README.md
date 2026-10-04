# Mumbai Real Estate Tracker

Public GitHub Pages dashboard and local Maharashtra IGR data pipeline for Mumbai property registrations.

The public repository contains only a sanitized dataset. Raw IGR inputs can contain seller/purchaser names and remain local and git-ignored.

## Current scope

- Historical coverage framework: 2014 onward
- Current seeded data: 2026, Anik, Property / CTS `1A/1`
- Filters: year, village, property / CTS, document group and document type
- Metrics: registrations, sales / agreements, rent / licence, consideration, market value, rate per sq ft and rent when extracted
- Local Windows pipeline for metadata backfill, dedupe, sanitation and publishing

## Local setup (Windows)

Clone this repository into:

`D:\Animesh Docs\Google Drive\Personal Projects\Real Estate Tracker\Real-Estate`

Then run `run_build.bat`. It scans the existing local `downloads` tree for `metadata.csv`, builds a sanitized master dataset and updates the dashboard files.

## Fast historical backfill

Run:

`python scripts\igr_metadata_block_scraper.py`

The script asks for year, starting page, village and property number. Complete the IGR search/CAPTCHA and navigate to the first page of a pagination block. The script collects metadata only for the visible numeric pages and stops before the next pagination ellipsis. It does not open every Index II document.

## Publishing

Run `run_publish.bat` after new local data has been collected. It rebuilds the sanitized CSV, commits the public dataset files and pushes them to GitHub.

## GitHub Pages

One-time repository setting: **Settings -> Pages -> Deploy from a branch -> `main` -> `/ (root)`**.

The public site will then be available at:

`https://projectdwister.github.io/Real-Estate/`

## Privacy

Seller and purchaser name columns are never included in `data/master_transactions.csv`. Raw metadata, downloaded Index II files, HTML, screenshots and Excel files are excluded by `.gitignore`.

## Daily updates

The project is designed so the only source-side human step is completing any CAPTCHA/search challenge required by the Maharashtra IGR portal. After the results page is available, the local pipeline can collect, sanitize, deduplicate and publish the update. GitHub Pages refreshes automatically after each push.
