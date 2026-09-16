"""
One-time migration tool: converts the already-rendered certificates in
sorted_certificates/ (plus Name/Phone/CertNo data from the xlsx) into the
bucket-ready folder structure the static site expects:

    gcs_upload/
      certs/<random-id>-<certno-lower>.jpg
      index/by-name/<hash>.json
      index/by-phone/<hash>.json
      index/by-certno/<hash>.json

This script only READS the local xlsx and sorted_certificates/*.jpg. It never
uploads anything and never touches credentials/gcs_key.json. Upload the
resulting gcs_upload/ folder to the GCS bucket yourself (gsutil or Console).

Usage:
    pip install openpyxl        # already installed in this environment
    python tools/bootstrap_bucket.py --dry-run --limit 5   # sanity check first
    python tools/bootstrap_bucket.py                       # full run
"""

import argparse
import hashlib
import json
import re
import secrets
import shutil
from collections import defaultdict
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
XLSX_PATH = ROOT / "2025 TEM - CERTIFICATE ISSUE_SORTED_WITH_BATCH_CODES.xlsx"
CERTS_DIR = ROOT / "sorted_certificates"
OUT_DIR = ROOT / "gcs_upload"

# MUST match public/assets/config.js exactly. If you change the SALT there,
# change it here too and re-run this script, then re-upload gcs_upload/.
SALT = "s5nF3nbmO9rbo6azJFqnmXPBhuVaDVop"

# Column indices in Sheet1 (0-based), confirmed against the actual xlsx:
# 0 SL NO | 1 SHEET NAME | 2 CATEGORY | 3 NAME | 4 PHONE NUM | 5 PHONE NUM
# (duplicate header, two phone numbers per row) | 6 CERTIFICATE NO | 7 BATCH PDF
COL_NAME = 3
COL_PHONE1 = 4
COL_PHONE2 = 5
COL_CERT_NO = 6


def normalize_name(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def normalize_phone(s: str) -> str:
    # Digits only, kept to the last 10 digits — tolerates a leading country
    # code (e.g. "+91..."), matching normalizePhone() in public/assets/config.js.
    digits = re.sub(r"\D+", "", s)
    return digits[-10:] if len(digits) > 10 else digits


def normalize_certno(s: str) -> str:
    return s.strip().upper()


def sha256_hex(s: str) -> str:
    # UTF-8 encoding must match TextEncoder().encode(...) on the JS side.
    return hashlib.sha256((SALT + s).encode("utf-8")).hexdigest()


def random_id() -> str:
    return secrets.token_hex(6)  # 12 hex chars, same shape as crypto.getRandomValues(6) in JS


def cell_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report counts only, write nothing.")
    parser.add_argument("--limit", type=int, default=None, help="Process only the first N data rows.")
    args = parser.parse_args()

    if not XLSX_PATH.exists():
        raise SystemExit(f"Missing input file: {XLSX_PATH}")
    if not CERTS_DIR.exists():
        raise SystemExit(f"Missing input folder: {CERTS_DIR}")

    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb.active
    print(f"Reading sheet '{ws.title}' from {XLSX_PATH.name}")

    by_name = defaultdict(list)
    by_phone = defaultdict(list)
    by_certno = defaultdict(list)

    remaining_jpgs = {p.stem for p in CERTS_DIR.glob("*.jpg")}
    missing_jpgs = []
    skipped_blank = 0
    processed = 0

    rows = ws.iter_rows(min_row=2, values_only=True)
    for row in rows:
        if args.limit is not None and processed >= args.limit:
            break

        name = cell_str(row[COL_NAME])
        phone1 = cell_str(row[COL_PHONE1])
        phone2 = cell_str(row[COL_PHONE2])
        cert_no = cell_str(row[COL_CERT_NO])

        if not name or not cert_no:
            skipped_blank += 1
            continue

        cert_no_upper = normalize_certno(cert_no)
        src = CERTS_DIR / f"{cert_no_upper}.jpg"
        if not src.exists():
            missing_jpgs.append(cert_no_upper)
            continue
        remaining_jpgs.discard(cert_no_upper)

        rid = random_id()
        new_filename = f"{rid}-{cert_no_upper.lower()}.jpg"
        dest = OUT_DIR / "certs" / new_filename

        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)  # copy, never mutate the original

        record = {"name": name, "cert_no": cert_no_upper, "file": f"certs/{new_filename}"}

        by_name[sha256_hex(normalize_name(name))].append(record)
        by_certno[sha256_hex(normalize_certno(cert_no))].append(record)

        for raw_phone in {phone1, phone2}:  # set() de-dupes identical phone1==phone2 rows
            np = normalize_phone(raw_phone)
            if np:
                by_phone[sha256_hex(np)].append(record)

        processed += 1

    write_index_tree(OUT_DIR / "index" / "by-name", by_name, args.dry_run)
    write_index_tree(OUT_DIR / "index" / "by-phone", by_phone, args.dry_run)
    write_index_tree(OUT_DIR / "index" / "by-certno", by_certno, args.dry_run)

    print()
    print(f"{'[DRY RUN] ' if args.dry_run else ''}Processed: {processed}")
    print(f"Skipped (blank name/certno): {skipped_blank}")
    print(f"Missing jpg for xlsx row (cert number with no matching file): {len(missing_jpgs)}")
    if missing_jpgs:
        print("  e.g.:", missing_jpgs[:20])
    if args.limit is None:
        print(f"Orphan jpg (file exists, no matching xlsx row processed): {len(remaining_jpgs)}")
        if remaining_jpgs:
            print("  e.g.:", list(remaining_jpgs)[:20])
    else:
        print(f"(orphan-jpg check skipped because --limit={args.limit} was used)")

    if not args.dry_run:
        print(f"\nOutput written to: {OUT_DIR}")
        print("Next: upload its contents to the GCS bucket, preserving folder structure.")


def write_index_tree(dirpath: Path, buckets: dict, dry_run: bool):
    if dry_run:
        print(f"[DRY RUN] Would write {len(buckets)} file(s) to {dirpath}")
        return
    dirpath.mkdir(parents=True, exist_ok=True)
    for h, records in buckets.items():
        (dirpath / f"{h}.json").write_text(
            json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    print(f"Wrote {len(buckets)} file(s) to {dirpath}")


if __name__ == "__main__":
    main()
