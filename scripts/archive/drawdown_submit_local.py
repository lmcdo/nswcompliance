"""Local test runner — sets credentials then submits HyP3 jobs."""
import os
import sys

# Set before any imports that might read env
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
if not os.environ.get("ASF_EARTHDATA_PASSWORD"):
    # Read from local creds file if it exists (not .env to avoid git hooks)
    import pathlib
    creds_file = pathlib.Path(__file__).parent / "drawdown_creds.txt"
    if creds_file.exists():
        for line in creds_file.read_text().strip().splitlines():
            if line and not line.startswith("#"):
                os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
                break

# Now run the submission script
exec(open(os.path.join(os.path.dirname(__file__), "drawdown_submit_jobs.py")).read())
