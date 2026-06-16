"""
FJC IDB (Federal Judicial Center Integrated Database) Verdict Scraper
Downloads cumulative civil/criminal case files from FJC and filters for
personal injury cases by Nature of Suit (NOS) codes.

Data source: https://www.fjc.gov/research/idb
The IDB contains federal civil and criminal case filings, terminations,
and pending cases from all U.S. district and appellate courts.

Usage:
    python cds_fjc_idb.py --output fjc_pi_cases.csv
    python cds_fjc_idb.py --year 2023 --state FL --output fl_pi_2023.csv
"""

import argparse
import csv
import json
import sys
from pathlib import Path
from zipfile import ZipFile

import requests

IDB_BASE = "https://www.fjc.gov/sites/default/files/idb/textfiles"
CIVIL_CUMULATIVE = "https://www.fjc.gov/sites/default/files/idb/textfiles/cv88on.zip"
CRIMINAL_CUMULATIVE = "https://www.fjc.gov/sites/default/files/idb/textfiles/cr88on.zip"

NOS_PI_LABELS = {
    310: "Airplane PI",
    315: "Airplane product liability",
    320: "Assault, libel, slander",
    330: "Federal employers liability",
    340: "Marine PI",
    345: "Marine product liability",
    350: "Motor vehicle PI",
    355: "Motor vehicle product liability",
    360: "Other personal injury",
    362: "Medical malpractice",
    365: "Product liability",
    368: "Asbestos PI product liability",
    370: "Other fraud",
    371: "Truth in lending",
    380: "Other personal property damage",
    385: "Property damage product liability",
}


def civil_by_year(y: int) -> str:
    return f"{IDB_BASE}/cv{y:02d}.zip"


def criminal_by_year(y: int) -> str:
    return f"{IDB_BASE}/cr{y:02d}.zip"


def download(url: str, out_path: str, timeout: int = 180) -> bool:
    resp = requests.get(url, stream=True, timeout=timeout)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
    return True


def extract_zip(zip_path: str, dest_dir: str):
    Path(dest_dir).mkdir(parents=True, exist_ok=True)
    with ZipFile(zip_path, "r") as zf:
        zf.extractall(dest_dir)


def filter_pi(in_path: str, out_path: str, state: str = None):
    """Filter a tab-delimited IDB civil file to PI cases (optionally by court state prefix)."""
    pi_nos = set(NOS_PI_LABELS.keys())

    with open(in_path, "r", encoding="latin-1") as fin, open(out_path, "w", newline="", encoding="utf-8") as fout:
        reader = csv.reader(fin, delimiter="\t")
        writer = csv.writer(fout, delimiter="\t")

        header = next(reader, None)
        if header:
            writer.writerow(header)

        nos_idx = None
        for i, col in enumerate(header or []):
            if col.strip() in ("NOS", "JURIS", "DISTRICT"):
                nos_idx = i
                break

        for row in reader:
            if nos_idx is not None and len(row) > nos_idx:
                try:
                    nos = int(row[nos_idx])
                except (ValueError, IndexError):
                    continue
                if nos in pi_nos:
                    writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(description="FJC IDB PI case scraper")
    parser.add_argument("--year", type=int, help="Single year to download")
    parser.add_argument("--cumulative", action="store_true", help="Download cumulative files")
    parser.add_argument("--state", help="Filter by court state prefix")
    parser.add_argument("--output", "-o", default="fjc_pi_cases.csv", help="Output CSV path")
    parser.add_argument("--work-dir", default="fjc_data", help="Working directory for downloads")
    args = parser.parse_args()

    work = Path(args.work_dir)
    work.mkdir(parents=True, exist_ok=True)

    if args.cumulative:
        years = ["cumulative"]
        urls = [CIVIL_CUMULATIVE]
    elif args.year:
        y = args.year % 100
        years = [str(args.year)]
        urls = [civil_by_year(y)]
    else:
        print("Specify --year or --cumulative")
        sys.exit(1)

    for label, url in zip(years, urls):
        zip_path = work / f"cv_{label}.zip"
        print(f"Downloading {url} ...")
        download(url, str(zip_path))
        print(f"Extracting {zip_path} ...")
        extract_zip(str(zip_path), str(work / label))
        txt_file = next(work.glob(f"{label}/*.txt"), None) or next(work.glob(f"{label}/*"), None)
        if txt_file:
            print(f"Filtering PI cases from {txt_file} ...")
            filter_pi(str(txt_file), args.output, args.state)
            print(f"Output: {args.output}")


if __name__ == "__main__":
    main()
