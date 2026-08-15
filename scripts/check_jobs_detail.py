import os, pathlib, json
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break
import hyp3_sdk as sdk
from hyp3_sdk import Batch
hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])

ids = [
    ("parramatta_test",    "a01d59d4-9372-412e-909a-1da798e07eee"),
    ("hills_district",     "37148a8b-5ae0-4f7b-b959-3c0257218aab"),
    ("inner_west",         "ae3475f2-71e8-4139-9381-ec497a058cf5"),
]

OUTPUT_DIR = pathlib.Path(__file__).parent.parent / "validation_output"

for name, jid in ids:
    j = hyp3.get_job_by_id(jid)
    print(f"\n{'='*50}")
    print(f"Site: {name}  |  Status: {j.status_code}")
    if j.status_code == "FAILED":
        print(f"  Failure reason: {getattr(j, 'status_message', 'N/A')}")
        # Print full job dict for debugging
        jdict = j.__dict__ if hasattr(j, '__dict__') else str(j)
        print(f"  Job detail: {jdict}")
    elif j.status_code == "SUCCEEDED":
        print(f"  Files available: {[f.get('filename') for f in (j.files or [])]}")
        # Download
        site_dir = OUTPUT_DIR / name
        site_dir.mkdir(parents=True, exist_ok=True)
        print(f"  Downloading to {site_dir}...")
        try:
            Batch([j]).download_files(location=str(site_dir))
            all_files = [f.name for f in site_dir.rglob("*") if f.is_file()]
            print(f"  Downloaded: {all_files}")
        except Exception as e:
            print(f"  Download error: {e}")
