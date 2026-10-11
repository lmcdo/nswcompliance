#!/usr/bin/env bash
# DQ-143 address-only single sites. Loads ONLY sites whose proofs pass, including check 6 (the
# chapter's own site map): Brighton Ave, Milton St, Chullora, Roberts Rd, Boorea Ave, 47 Warrane Rd
# (4 lots, as the map draws), Milperra. Backups in data/db_rollback_backups/.
# Held: Leichhardt George St (map 0.317), Screen Australia (no register address to anchor it).
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/build_site_boundaries.py --addresses --commit --only 11.11,11.1,11.10,11.3,11.8,14M,11.13
python scripts/derive_precinct_keys.py --council canterbury_bankstown --apply --only canterbury_bankstown_lot_list_sites
python scripts/derive_precinct_keys.py --council ku_ring_gai --apply --only ku_ring_gai_part14_single_site

python scripts/dq_probe_live.py --id DQ-143 | head -2 || true
