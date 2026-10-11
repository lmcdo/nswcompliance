#!/usr/bin/env bash
# DQ-146 production write, approved by the user 2026-10-11 ("yes"). Each step backs up first
# (data/db_rollback_backups/) and prints what it changed. Stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . "$(git rev-parse --path-format=absolute --git-common-dir)/../.env"; set +a

python scripts/import_woollahra_b2_union.py --commit
python scripts/derive_precinct_keys.py --council woollahra --apply --only \
woollahra_b2_2,woollahra_b2_3,woollahra_b2_4,woollahra_b2_5,woollahra_b2_6,woollahra_b2_7,woollahra_b2_8,woollahra_b2_9,woollahra_b2_10,woollahra_b2_11,woollahra_b2_12,woollahra_b2_all_eleven,woollahra_c1_paddington,woollahra_e2_3_flood,woollahra_e2_whole_council,woollahra_e4_whole_council
python scripts/derive_precinct_keys.py --council wollongong --apply --only wollongong_e11_heritage
python scripts/derive_precinct_keys.py --council ashfield --apply --only ashfield_e1_heritage
python scripts/derive_precinct_keys.py --council waverley --apply --only waverley_b8_heritage

python scripts/dq_probe_live.py --id DQ-146 | head -2 || true
python scripts/dq_probe_live.py --id DQ-143 | head -2 || true
