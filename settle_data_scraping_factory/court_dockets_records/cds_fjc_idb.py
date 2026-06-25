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

# Federal Nature-of-Suit (NOS) codes that are genuine *bodily-injury* personal injury.
# Deliberately EXCLUDES non-PI matters the civil cover sheet groups nearby but that are
# not personal-injury settlements — the false-positive analog to the criminal/enforcement
# mislabeling fixed in _common/extract.py:
#   320 (assault/libel/slander — defamation), 370 (other fraud), 371 (truth in lending),
#   380 / 385 (property damage). Including those would mislabel non-PI cases as PI.
NOS_PI_LABELS = {
    310: "Airplane PI",
    315: "Airplane product liability",
    330: "Federal employers' liability (FELA)",
    340: "Marine PI",
    345: "Marine product liability",
    350: "Motor vehicle PI",
    355: "Motor vehicle product liability",
    360: "Other personal injury",
    362: "Medical malpractice",
    365: "Product liability",
    368: "Asbestos PI product liability",
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

        # Locate the Nature-of-Suit column specifically. (Previously this matched the
        # first of NOS/JURIS/DISTRICT — but real IDB files list DISTRICT before NOS, so it
        # filtered on the wrong column and let non-PI cases through. Match "NOS" exactly.)
        nos_idx = None
        for i, col in enumerate(header or []):
            if col.strip().upper() == "NOS":
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


def selftest() -> int:
    import tempfile

    failures = []

    def check(name, cond):
        print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
        if not cond:
            failures.append(name)

    print("NOS-code precision (only bodily-injury PI; non-PI matters excluded):")
    pi = set(NOS_PI_LABELS)
    check("keeps motor vehicle PI (350)", 350 in pi)
    check("keeps medical malpractice (362)", 362 in pi)
    check("keeps product liability (365)", 365 in pi)
    for code, label in [(320, "assault/libel/slander"), (370, "other fraud"),
                        (371, "truth in lending"), (380, "property damage"),
                        (385, "property damage product liability")]:
        check(f"excludes non-PI NOS {code} ({label})", code not in pi)

    print("filter_pi keeps only PI-NOS rows, using the NOS column (not DISTRICT/JURIS):")
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "idb.txt"
        dst = Path(tmp) / "out.txt"
        # DISTRICT deliberately placed BEFORE NOS to catch the old wrong-column bug.
        rows = [
            ["CASEID", "DISTRICT", "NOS", "JURIS"],
            ["1", "350", "350", "FL"],   # NOS 350 motor vehicle PI -> keep
            ["2", "370", "362", "CA"],   # NOS 362 med mal -> keep (DISTRICT 370 must be ignored)
            ["3", "350", "370", "FL"],   # NOS 370 fraud -> drop (DISTRICT 350 must be ignored)
            ["4", "999", "385", "CA"],   # NOS 385 property damage -> drop
            ["5", "999", "899", "FL"],   # NOS 899 unrelated -> drop
        ]
        src.write_text("\n".join("\t".join(r) for r in rows), encoding="utf-8")
        filter_pi(str(src), str(dst))
        out = [l for l in dst.read_text(encoding="utf-8").splitlines() if l.strip()]
        kept_nos = {l.split("\t")[2] for l in out[1:]}  # NOS column index 2
        check("kept exactly the 2 PI rows (350, 362)", kept_nos == {"350", "362"})
        check("did not filter on DISTRICT/JURIS column", "370" not in kept_nos and "385" not in kept_nos)

    if failures:
        print(f"\nRESULT: FAILED ({len(failures)}) -> {failures}")
        return 1
    print("\nRESULT: ALL CHECKS PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="FJC IDB PI case scraper")
    parser.add_argument("--year", type=int, help="Single year to download")
    parser.add_argument("--cumulative", action="store_true", help="Download cumulative files")
    parser.add_argument("--state", help="Filter by court state prefix")
    parser.add_argument("--output", "-o", default="fjc_pi_cases.csv", help="Output CSV path")
    parser.add_argument("--work-dir", default="fjc_data", help="Working directory for downloads")
    parser.add_argument("--selftest", action="store_true", help="Run offline self-checks")
    args = parser.parse_args()

    if args.selftest:
        return selftest()

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
