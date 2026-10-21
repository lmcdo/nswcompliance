"""Upload data/may_apply_maps/*.png to R2 under may-apply-maps/<area_id>.png. Dry-run unless --commit.

prior-art-checked: same boto3/R2 pattern as scripts/add_new_chapter.py (R2_* env vars, put_object).
After a real upload, set MAP_BASE_URL in scripts/export_may_apply_areas.py to the public R2 base and re-run the export.
Usage: python scripts/upload_may_apply_maps.py [--commit]
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "data" / "may_apply_maps"
PREFIX = "may-apply-maps"


def planned() -> list[tuple[Path, str]]:
    index = json.loads((MAPS / "index.json").read_text(encoding="utf-8"))
    return [(MAPS / v["file"], f"{PREFIX}/{v['file']}") for _, v in sorted(index.items()) if v.get("file")]


def main(commit: bool) -> int:
    items = planned()
    bucket = os.environ.get("R2_BUCKET_NAME", "nsw-planning-pdfs")
    total = sum(p.stat().st_size for p, _ in items)
    print(f"{'UPLOAD' if commit else 'DRY RUN'}: {len(items)} files, {total // 1024} KB -> r2://{bucket}/{PREFIX}/")
    if not commit:
        for p, key in items:
            print(f"  would upload {p.name} -> {key}")
        return 0
    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    for p, key in items:
        s3.put_object(Bucket=bucket, Key=key, Body=p.read_bytes(), ContentType="image/png")
        print(f"  uploaded {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main("--commit" in sys.argv))
