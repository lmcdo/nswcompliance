#!/usr/bin/env bash
# DQ-143 / DQ-146: Canterbury-Bankstown heritage chapters. Loads the seven HCA outlines chapter 4.3
# names (+ their union) from the NSW heritage layer, keys 4.3 (section 21 -> Ashbury, rest -> all
# seven), gives 4.2 the heritage marker, and moves 4.4's unread-layer rows to the generic layer.
# Backups in data/db_rollback_backups/.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/import_cb_heritage_areas.py --commit
python scripts/derive_precinct_keys.py --council canterbury_bankstown --apply \
  --only cb_4_3_ashbury,cb_4_3_all_seven,cb_4_2_heritage_items,cb_4_4_vicinity_generic

python scripts/dq_probe_live.py --id DQ-146 | head -2 || true
python scripts/dq_probe_live.py --id DQ-143 | head -2 || true
