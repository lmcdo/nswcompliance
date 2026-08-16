"""Check status of all ground truth HyP3 jobs."""
import os, pathlib, json

os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import hyp3_sdk as sdk

hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])

jobs_file = pathlib.Path(__file__).parent.parent / "validation_output" / "ground_truth" / "gt_jobs.json"
records = json.loads(jobs_file.read_text())

counts = {"SUCCEEDED": 0, "RUNNING": 0, "FAILED": 0, "PENDING": 0}
total = 0

for rec in records:
    all_jobs = rec["pre_jobs"] + rec["post_jobs"]
    statuses = []
    for j in all_jobs:
        status = hyp3.get_job_by_id(j["job_id"]).status_code
        statuses.append(status)
        counts[status] = counts.get(status, 0) + 1
        total += 1
    summary = {s: statuses.count(s) for s in set(statuses)}
    print(f"{rec['pan'][-8:]}  {rec['address'][:40]:<40}  {summary}")

print(f"\nTotal jobs: {total}")
print(f"SUCCEEDED: {counts.get('SUCCEEDED',0)}  RUNNING: {counts.get('RUNNING',0)}  FAILED: {counts.get('FAILED',0)}  PENDING: {counts.get('PENDING',0)}")
print(f"Credits remaining: {hyp3.check_credits()}")
