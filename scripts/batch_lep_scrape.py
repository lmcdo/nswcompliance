#!/usr/bin/env python3
"""
Batch scrape LEP land use tables for all supported LGAs.
Downloads full LEP HTML from legislation.nsw.gov.au, then parses zone land use tables.

Usage:
    python scripts/batch_lep_scrape.py --dry-run
    python scripts/batch_lep_scrape.py
    python scripts/batch_lep_scrape.py --only Waverley,Woollahra
"""
import subprocess
import sys
import os
import time

sys.stdout.reconfigure(encoding='utf-8')

# Correct EPI IDs verified against NSW Planning Portal API (2026-05-12)
# Format: LGA display name → (EPI ID, local HTML filename slug)
LGAS = {
    'Bayside': ('epi-2021-0498', 'bayside-lep-2021'),
    'Waverley': ('epi-2012-0540', 'waverley-lep'),
    'Woollahra': ('epi-2015-0020', 'woollahra-lep'),
    'Ku-Ring-Gai': ('epi-2015-0134', 'ku-ring-gai-lep'),
    'Blacktown': ('epi-2015-0239', 'blacktown-lep'),
    'Campbelltown': ('epi-2015-0754', 'campbelltown-lep'),
    'Canterbury-Bankstown': ('epi-2023-0252', 'canterbury-bankstown-lep'),
    'Cumberland': ('epi-2021-0651', 'cumberland-lep'),
    'Georges River': ('epi-2021-0587', 'georges-river-lep'),
    'Hornsby': ('epi-2013-0569', 'hornsby-lep'),
    'Liverpool': ('epi-2008-0403', 'liverpool-lep'),
    'Northern Beaches': ('epi-2011-0649', 'northern-beaches-lep'),   # Warringah LEP 2011
    'Parramatta': ('epi-2023-0117', 'parramatta-lep'),
    'Penrith': ('epi-2010-0540', 'penrith-lep'),
    'Randwick': ('epi-2013-0036', 'randwick-lep'),
    'Sutherland Shire': ('epi-2015-0319', 'sutherland-shire-lep'),
    'Ryde': ('epi-2014-0608', 'ryde-lep'),
    'Strathfield': ('epi-2013-0115', 'strathfield-lep'),
    'The Hills Shire': ('epi-2019-0596', 'the-hills-shire-lep'),
    'Camden': ('epi-2010-0514', 'camden-lep'),
    'Canada Bay': ('epi-2013-0389', 'canada-bay-lep'),
    'Burwood': ('epi-2012-0550', 'burwood-lep'),
    'Fairfield': ('epi-2013-0213', 'fairfield-lep'),
    'Sydney': ('epi-2012-0628', 'sydney-lep'),
}

MAX_RETRIES = 3
RETRY_DELAY = 10  # seconds between retries (403s are intermittent)


def main():
    dry_run = '--dry-run' in sys.argv

    # --only filter
    only = None
    for arg in sys.argv:
        if arg.startswith('--only='):
            only = arg.split('=', 1)[1].split(',')
        elif arg == '--only' and sys.argv.index(arg) + 1 < len(sys.argv):
            only = sys.argv[sys.argv.index(arg) + 1].split(',')

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scrape_lep_land_use.py')
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'lep-html')
    os.makedirs(data_dir, exist_ok=True)

    results = []
    failed = []

    for lga_name, (epi_id, slug) in LGAS.items():
        if only and lga_name not in only:
            continue

        print(f"\n{'='*60}")
        print(f"  {lga_name} ({epi_id})")
        print(f"{'='*60}")

        # Check for local HTML file first
        local_file = os.path.join(data_dir, f"{slug}.html")

        for attempt in range(1, MAX_RETRIES + 1):
            cmd = [sys.executable, script, '--epi', epi_id, '--lga', lga_name]
            if os.path.exists(local_file):
                cmd.extend(['--file', local_file])
            if dry_run:
                cmd.append('--dry-run')

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}
            )
            print(result.stdout)
            if result.stderr:
                print(f"  STDERR: {result.stderr[:300]}")

            # Check if it succeeded (look for TOTAL in output)
            success = False
            for line in result.stdout.split('\n'):
                if 'TOTAL:' in line:
                    results.append((lga_name, line.strip()))
                    success = True
                    break

            if success:
                break

            # Check for 403/fetch failure
            if 'curl failed' in result.stdout or 'curl failed' in result.stderr or result.returncode != 0:
                if attempt < MAX_RETRIES:
                    print(f"  Attempt {attempt}/{MAX_RETRIES} failed, retrying in {RETRY_DELAY}s...")
                    time.sleep(RETRY_DELAY)
                else:
                    print(f"  FAILED after {MAX_RETRIES} attempts")
                    failed.append(lga_name)
            else:
                # No TOTAL but also no error — parser found 0 zones
                if '0 zones' in result.stdout:
                    failed.append(lga_name)
                break

        # Be nice to the server
        time.sleep(3)

    print(f"\n{'='*60}")
    print("  SUMMARY")
    print(f"{'='*60}")
    for lga, total in results:
        print(f"  {lga:25s}  {total}")
    if failed:
        print(f"\n  FAILED ({len(failed)}): {', '.join(failed)}")


if __name__ == '__main__':
    main()
