"""Railway startup script: download the Tweed and Wollongong flood grids from R2.

prior-art-checked: reuse not viable as a shared module, and the reason is in the
prior art itself. scripts/download_hawkesbury_rasters.py and
scripts/download_redbank_rasters.py were both read in full and are deliberately
mirrored: each hardcodes its own file list, R2 prefix, env var and destination,
and each is COPY'd standalone into Dockerfile.python where no shared module is
importable. Two studies are combined in ONE script here rather than adding two
more near-copies, because they ship together and neither can answer the 1% AEP
question without the other's council being separately configured.

WHY THIS EXISTS
---------------
Tweed and Wollongong were declared in FLOOD_STUDIES and their rasters could
never reach the container: data/flood_studies is untracked, Dockerfile.python
does not copy data/, and unlike Hawkesbury and Redbank they had no download
script. The runtime noticed and wrote a log line nobody read, and until #892
the 1% AEP verdict for those councils came back "no" rather than "not assessed".
This is the other half of that fix — the half that produces an actual answer.

Called by Dockerfile.python before uvicorn starts. Downloads to
/tmp/tweed_rasters and /tmp/wollongong_rasters, matching TWEED_RASTER_DIR and
WOLLONGONG_RASTER_DIR in services/flood_truth.py. Skips files already present
at the correct size, so restarts are fast.

Exits 0 always. A missing raster degrades to "not assessed" in flood_truth.py
rather than crashing — and, since #892, never to "not in a flood zone".
"""
import logging
import base64
import hashlib
import os
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

R2_ACCOUNT_ID        = os.environ.get("R2_ACCOUNT_ID") or ""
R2_ACCESS_KEY_ID     = os.environ.get("R2_ACCESS_KEY_ID") or ""
R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY") or ""
R2_BUCKET_NAME       = os.environ.get("R2_BUCKET_NAME") or ""

# Relative paths mirror the FLOOD_STUDIES templates in services/flood_truth.py
# exactly. If a template changes there, it must change here or the study goes
# quiet — which is now visible, because flood_study_raster_availability() checks
# the 1% grid specifically and warns at import.
_TWEED_DESIGN = ["20p", "5p", "1p", "1in500", "PMP"]
_TWEED_HIST   = ["1989", "2017", "2020", "2022"]

TWEED_FILES = [
    f"design/Tweed_001_{event}_{t}_Max.tif"
    for event in _TWEED_DESIGN for t in ("d", "h")
] + [
    f"calibration/Tweed_001_{year}_{t}_Max.tif"
    for year in _TWEED_HIST for t in ("d", "h")
]

_WOLLONGONG_DESIGN = ["20pct", "10pct", "5pct", "2pct", "1pct", "PMF"]

WOLLONGONG_FILES = [
    f"design/Wollongong_{event}_{t}_Max.asc"
    for event in _WOLLONGONG_DESIGN for t in ("d", "h")
]

STUDIES = [
    ("tweed", "tweed-rasters", Path(os.environ.get("TWEED_RASTER_DIR", "/tmp/tweed_rasters")), TWEED_FILES),
    ("wollongong", "wollongong-rasters", Path(os.environ.get("WOLLONGONG_RASTER_DIR", "/tmp/wollongong_rasters")), WOLLONGONG_FILES),
]


def _local_md5(path: Path) -> str:
    """MD5 of a local file, streamed. Used only to compare against R2's ETag."""
    h = hashlib.md5()  # noqa: S324 — matching S3's ETag, not a security digest
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _local_sha256_b64(path: Path) -> str:
    """Base64 SHA-256, the encoding S3/R2 uses for ChecksumSHA256."""
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return base64.b64encode(h.digest()).decode()


def _matches_remote(dest: Path, head: dict, tag: str, rel_path: str) -> bool:
    """Is the local raster the same OBJECT as the remote one?

    Size alone cannot answer this. A stale raster from a previous container, or
    a corrupted-but-readable GeoTIFF, keeps its byte length and was being
    skipped as "already present" — then served as authoritative 1% AEP flood
    data with no warning anywhere.

    S3/R2 already hands us a checksum for free in the same head_object call:
    for a single-part upload the ETag IS the MD5. For a MULTIPART upload it is
    a digest-of-digests with a "-N" suffix that cannot be reproduced without
    knowing the part size, so it is not comparable — in that case we say so
    rather than pretending the size check verified anything.
    """
    if dest.stat().st_size != head["ContentLength"]:
        return False

    # R2 can carry an explicit SHA-256 when the object was uploaded with
    # additional checksums enabled. Prefer it: it is comparable regardless of
    # how the object was uploaded.
    # A COMPOSITE checksum is not a full-object digest. S3-compatible stores
    # expose multipart checksums as a digest-of-digests with a "-N" suffix,
    # which can never equal a locally computed full-file SHA-256. Comparing
    # them would discard a perfectly good raster on every boot and leave the
    # council reported as not assessed forever — a check that always fails is
    # as useless as one that always passes, and harder to notice.
    remote_sha = head.get("ChecksumSHA256")
    composite = bool(remote_sha) and (
        "-" in remote_sha or head.get("ChecksumType") == "COMPOSITE"
    )
    if remote_sha and not composite:
        return _local_sha256_b64(dest) == remote_sha

    etag = (head.get("ETag") or "").strip('"')
    if etag and "-" not in etag:
        # Single-part upload: the ETag IS the MD5.
        if _local_md5(dest) == etag:
            return True
        log.warning(
            f"[{tag}-dl] {rel_path}: SAME SIZE but MD5 differs from the remote "
            f"object — local copy is stale or corrupt. Re-downloading."
        )
        return False

    # Multipart or absent ETag and no checksum: the contents CANNOT be
    # verified from what R2 told us. Returning true here would have accepted a
    # same-size stale or corrupt raster and served it as authoritative 1% AEP
    # flood data — size is not integrity, and a warning is not a check.
    #
    # So the local copy is not trusted: it is re-fetched, which at least
    # guarantees the bytes came from R2 this boot. That does not protect
    # against R2 itself holding a corrupt object; nothing available here can,
    # and the honest position is to say so rather than imply the size check
    # covered it.
    log.warning(
        f"[{tag}-dl] {rel_path}: remote ETag is multipart and no ChecksumSHA256 "
        f"is set, so the local contents cannot be verified. Re-downloading "
        f"rather than trusting file size. (A corrupt object in R2 would still "
        f"pass — that is outside what this check can see.)"
    )
    return False


def _download_study(s3, tag: str, prefix: str, dest_dir: Path, files: list[str]) -> int:
    present = 0
    for rel_path in files:
        dest = dest_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        key = f"{prefix}/{rel_path}"

        try:
            head = s3.head_object(Bucket=R2_BUCKET_NAME, Key=key)
            remote_size = head["ContentLength"]
        except Exception as e:  # noqa: BLE001
            log.warning(f"[{tag}-dl] {rel_path}: head_object failed — {e}")
            continue

        if dest.exists() and _matches_remote(dest, head, tag, rel_path):
            log.info(f"[{tag}-dl] {rel_path} already present ({remote_size / 1_048_576:.1f} MB) — skip")
            present += 1
            continue

        log.info(f"[{tag}-dl] downloading {rel_path} ({remote_size / 1_048_576:.1f} MB)...")
        try:
            s3.download_file(R2_BUCKET_NAME, key, str(dest))
            # Verify what actually LANDED, not what we asked for. A truncated
            # or mid-flight-corrupted download is worse than a missing file:
            # missing is visible, wrong is served. Skipped when the object is
            # unverifiable by construction (multipart ETag, no checksum) —
            # otherwise a fresh, correct download would be discarded on every
            # boot by a check that can never pass.
            _sha = head.get("ChecksumSHA256")
            verifiable = (bool(_sha) and "-" not in _sha
                          and head.get("ChecksumType") != "COMPOSITE") or (
                (head.get("ETag") or "").strip('"') and "-" not in (head.get("ETag") or "")
            )
            if verifiable and not _matches_remote(dest, head, tag, rel_path):
                log.warning(f"[{tag}-dl] {rel_path}: downloaded copy failed verification — discarding")
                dest.unlink(missing_ok=True)
                continue
            if not verifiable and dest.stat().st_size != head["ContentLength"]:
                log.warning(f"[{tag}-dl] {rel_path}: downloaded copy is the wrong size — discarding")
                dest.unlink(missing_ok=True)
                continue
            present += 1
        except Exception as e:  # noqa: BLE001
            log.warning(f"[{tag}-dl] {rel_path}: download failed — {e}")
            if dest.exists():
                dest.unlink()  # never leave a partial raster where one is expected
    return present


def main():
    if not all([R2_ACCOUNT_ID, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET_NAME]):
        log.warning("[flood-dl] R2 env vars not set — skipping Tweed/Wollongong download")
        return

    try:
        import boto3
    except ImportError:
        log.warning("[flood-dl] boto3 not installed — skipping")
        return

    # Every other failure path in this script warns and returns, because it
    # runs in the Docker startup chain: a non-zero exit means uvicorn never
    # starts. Client construction was the one uncaught call, so an invalid
    # endpoint or account id would have taken the whole container down instead
    # of serving those councils as visibly not assessed.
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
            aws_access_key_id=R2_ACCESS_KEY_ID,
            aws_secret_access_key=R2_SECRET_ACCESS_KEY,
            region_name="auto",
        )
    except Exception as e:  # noqa: BLE001
        log.warning(f"[flood-dl] could not construct the R2 client — skipping: {e}")
        return

    for tag, prefix, dest_dir, files in STUDIES:
        got = _download_study(s3, tag, prefix, dest_dir, files)
        log.info(f"[{tag}-dl] {got}/{len(files)} raster files ready in {dest_dir}")
        # The 1% grid is the one the served verdict depends on. Say plainly
        # whether it arrived — a partial study is not a working study.
        one_pct = [f for f in files if "_1p_" in f or "_1pct_" in f]
        missing_1pct = [f for f in one_pct if not (dest_dir / f).exists()]
        if missing_1pct:
            log.warning(
                f"[{tag}-dl] 1%% AEP grid NOT present ({missing_1pct}) — every 1%% "
                f"answer for this council will be 'not assessed', never 'no'"
            )


if __name__ == "__main__":
    main()
