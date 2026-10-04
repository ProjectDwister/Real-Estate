"""Collect local IGR metadata.csv files from the user's downloads tree into
one private, git-ignored input CSV.

Usage:
  python scripts\sync_local_downloads.py
  python scripts\sync_local_downloads.py "D:\\Animesh Docs\\Google Drive\\Personal Projects\\Real Estate Tracker\\downloads"
"""
import sys
from pathlib import Path
import pandas as pd

DEFAULT = Path(r"D:\Animesh Docs\Google Drive\Personal Projects\Real Estate Tracker\downloads")
ROOT = Path(__file__).resolve().parents[1]
base = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
files = list(base.rglob("metadata.csv"))

if not files:
    raise SystemExit(f"No metadata.csv files found under {base}")

frames = []
for p in files:
    try:
        x = pd.read_csv(p, dtype=str, encoding="utf-8-sig")
        x["_source_folder"] = p.parent.name
        frames.append(x)
        print("Read", p)
    except Exception as e:
        print("Skip", p, e)

df = pd.concat(frames, ignore_index=True)
out = ROOT / "data" / "input_metadata" / "local_igr_metadata_all.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False, encoding="utf-8-sig")
print("Wrote", len(df), "raw rows to", out)
