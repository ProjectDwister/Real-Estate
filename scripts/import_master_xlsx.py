"""Import a merged metadata workbook into the local git-ignored input folder.

Usage:
  python scripts/import_master_xlsx.py "C:\\path\\master_metadata_2026_Anik_1A_1.xlsx"
"""
import sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if len(sys.argv) < 2:
    raise SystemExit("Provide an .xlsx path")

p = Path(sys.argv[1])
df = pd.read_excel(p, sheet_name="Master_Metadata", dtype=str)
out = ROOT / "data" / "input_metadata" / f"{p.stem}.csv"
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False, encoding="utf-8-sig")
print("Imported", len(df), "rows to", out)
