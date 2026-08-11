"""
Fetch NSW rental bond lodgement data and extract median weekly rent by postcode.

Source: NSW Government Residential Rental Bond Lodgements
URL: https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data

XLSX columns: Lodgement Date | Postcode | Dwelling Type | Bedrooms | Weekly Rent
Data starts row 4 (row 3 = headers, rows 1-2 = title).

Usage:
    python -m services.scripts.update_rental_data

Output:
    services/data/nsw_rental_by_postcode.json
"""

import io
import json
import logging
import sys
from collections import defaultdict
from pathlib import Path
from statistics import median

import requests

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Annual file — update URL each January when new year file is published
# Check: https://www.nsw.gov.au/housing-and-construction/rental-forms-surveys-and-data/rental-bond-data
DATA_URL = "https://www.nsw.gov.au/sites/default/files/noindex/2026-01/rentalbond_lodgements_year_2025.xlsx"
DATA_PERIOD = "2025"

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "data" / "nsw_rental_by_postcode.json"


def run():
    logger.info(f"Downloading: {DATA_URL}")
    try:
        resp = requests.get(
            DATA_URL,
            headers={"User-Agent": "PlotDetect/1.0"},
            timeout=90,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"Download failed: {e}")
        sys.exit(1)

    logger.info(f"Downloaded {len(resp.content):,} bytes — parsing XLSX...")

    try:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(resp.content), read_only=True, data_only=True)
        ws = wb.active
    except Exception as e:
        logger.error(f"Failed to open XLSX: {e}")
        sys.exit(1)

    # Columns: Lodgement Date | Postcode | Dwelling Type | Bedrooms | Weekly Rent
    # Data starts row 4
    rents: dict[tuple, list] = defaultdict(list)  # (postcode, bedrooms) → [weekly_rent, ...]
    rows_parsed = 0
    rows_skipped = 0

    for i, row in enumerate(ws.iter_rows(min_row=4, values_only=True)):
        if not row or row[1] is None:
            continue
        try:
            postcode = str(row[1]).strip().zfill(4)
            if len(postcode) != 4 or not postcode.isdigit():
                rows_skipped += 1
                continue

            bedrooms_raw = row[3]
            if bedrooms_raw is None:
                rows_skipped += 1
                continue
            bedrooms = int(float(str(bedrooms_raw)))
            if bedrooms not in (1, 2, 3):
                rows_skipped += 1
                continue

            rent_raw = row[4]
            if rent_raw is None:
                rows_skipped += 1
                continue
            rent = float(str(rent_raw).replace(",", ""))
            if rent <= 0 or rent > 5000:  # sanity bounds
                rows_skipped += 1
                continue

            rents[(postcode, bedrooms)].append(rent)
            rows_parsed += 1
        except (ValueError, TypeError):
            rows_skipped += 1
            continue

    wb.close()
    logger.info(f"Parsed {rows_parsed:,} rows, skipped {rows_skipped:,}")

    # Aggregate by postcode
    result: dict[str, dict] = {}
    for (postcode, bedrooms), rent_list in rents.items():
        if not rent_list:
            continue
        med = round(median(rent_list), 2)
        if postcode not in result:
            result[postcode] = {
                "postcode": postcode,
                "median_weekly_rent_1br_aud": None,
                "median_weekly_rent_2br_aud": None,
                "median_weekly_rent_3br_aud": None,
                "sample_size_1br": 0,
                "sample_size_2br": 0,
                "sample_size_3br": 0,
                "period": DATA_PERIOD,
                "source": "NSW Government Residential Rental Bond Lodgements",
            }
        result[postcode][f"median_weekly_rent_{bedrooms}br_aud"] = med
        result[postcode][f"sample_size_{bedrooms}br"] = len(rent_list)

    logger.info(f"Aggregated {len(result):,} postcodes")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(result, f, indent=2, sort_keys=True)

    logger.info(f"Written to {OUTPUT_PATH}")

    # Spot-check Inner West
    for pc in ["2040", "2041", "2042", "2045", "2204"]:
        entry = result.get(pc)
        if entry:
            logger.info(
                f"  {pc}: 1br ${entry.get('median_weekly_rent_1br_aud')}/wk "
                # `or 0`, not a .get default: the key can be present AND None,
                # in which case the default is never applied and this logs "n=None".
                f"(n={entry.get('sample_size_1br') or 0}), "
                f"2br ${entry.get('median_weekly_rent_2br_aud')}/wk"
            )
        else:
            logger.warning(f"  {pc}: no data")


if __name__ == "__main__":
    run()
