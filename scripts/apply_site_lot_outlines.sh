#!/usr/bin/env bash
# DQ-143 single sites with a Lot/DP list. Loads ONLY the sites whose proofs pass (445 Canterbury
# Rd, Revesby hospital, Marco Ave), then keys their chapters. Backups in data/db_rollback_backups/.
# Leichhardt George St (lots no longer exist) and Milperra (lot missing, area 10x) are held.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/build_site_boundaries.py --commit --only 11.9,11.12,11.15
python scripts/derive_precinct_keys.py --council canterbury_bankstown --apply --only canterbury_bankstown_lot_list_sites

python scripts/dq_probe_live.py --id DQ-143 | head -2 || true
