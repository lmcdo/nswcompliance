import os, pathlib
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break
import hyp3_sdk as sdk
hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])
ids = [
    ("inner_west",              "ae3475f2-71e8-4139-9381-ec497a058cf5"),
    ("kellyville-early2024",    "a7063991-c00f-4946-a4a2-425ea9437107"),
    ("kellyville-mid2024",      "d9c82ff4-4d07-47ad-a33b-700d00dfb7df"),
    ("kellyville-late2024",     "586b8c59-4873-4c4b-bfaf-b8d1bbf0d9e8"),
    ("kellyville-2022jul",      "2296ffb5-8811-4ea5-ae79-536be0a11483"),
    ("kellyville-2022aug",      "4cf73e66-c52c-4e7a-afea-9d53f4418885"),
    ("kellyville-2022aug2",     "c769fe7d-fa59-443f-94b1-22f059e06b8f"),
    ("tallawong-2023jul-a",     "44745b41-9020-453d-95d3-6e023cb47054"),
    ("tallawong-2023jul-b",     "fae75b19-1593-4d43-87b9-4d30bc903a15"),
    ("tallawong-2023aug",       "ac30786c-479f-44ae-9dab-c217480aa6d2"),
    ("tallawong-2024feb-a",     "8eb536ab-0eb9-4a83-bf63-284825f07ced"),
    ("tallawong-2024feb-b",     "2b83f392-6d5d-480c-9172-34df73bd89ca"),
    ("tallawong-2024mar",       "39e2566f-828b-4f0d-8747-480c31da4004"),
]
for name, jid in ids:
    j = hyp3.get_job_by_id(jid)
    print(f"{name}: {j.status_code}")
print(f"Credits remaining: {hyp3.check_credits()}")
