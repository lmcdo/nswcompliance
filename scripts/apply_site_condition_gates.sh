#!/usr/bin/env bash
# Site-condition gate rules: Ku-ring-gai 16 bushfire, Marrickville 2.23 acid sulfate, Ku-ring-gai 17
# riparian. RUN ONLY AFTER the page change that sends these facts is deployed (PR feat/hazard-gates):
# before that the condition layer is shown to no house. Backups in data/db_rollback_backups/.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/derive_precinct_keys.py --council ku_ring_gai --apply --only krg_16_bushfire_condition,krg_17_riparian
python scripts/derive_precinct_keys.py --council marrickville --apply --only marrickville_2_23_acid_sulfate

python scripts/dq_probe_live.py --id DQ-143 || true   # informational: still open by design
python scripts/dq_probe_live.py --id DQ-146           # must read 0, or this script fails
