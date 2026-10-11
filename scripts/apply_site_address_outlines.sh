#!/usr/bin/env bash
# DQ-143 address-only single sites. Loads ONLY sites whose proofs pass (Brighton Ave, Roberts Rd,
# Boorea Ave, 47 Warrane Rd), then keys their chapters. Backups in data/db_rollback_backups/.
# Held: Milton St (171 not in register), Chullora (353), Screen Australia (101 Eton Rd),
# Leichhardt George St (area 6,297 vs 14,662; nearest-outline fallback reaches 112 lots), Milperra (area).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/build_site_boundaries.py --addresses --commit --only 11.11,11.3,11.8,14M
python scripts/derive_precinct_keys.py --council canterbury_bankstown --apply --only canterbury_bankstown_lot_list_sites
python scripts/derive_precinct_keys.py --council ku_ring_gai --apply --only ku_ring_gai_part14_single_site

python scripts/dq_probe_live.py --id DQ-143 | head -2 || true
