"""A council's new chapter file is STAGED until its reviewed rules are published (migration 125).

prior-art-checked: reuse not viable because the guard's matches are pip/setuptools internals and a
lot-width TS helper; the registry has no staging concept (44 columns read 2026-11-10, none staged_*).

Live columns (r2_current_path, r2_public_pdf_url, content_hash, r2_version_label) say what the live
page links and proofs point at. Moving r2_current_path fires the proof-clearing triggers (078/079/111/112),
so intake must not move it. Everything that READS the new file during an update (extractor, approver,
commit worker) uses the EFFECTIVE_* fragments below; only publish_staged() moves the live columns.
"""
from __future__ import annotations

# Use in SQL against dcp_chapter_registry (unaliased). Swap into a SELECT list under the live column's
# own name so the code that reads the row does not change.
EFFECTIVE_PATH = "COALESCE(staged_r2_path, r2_current_path)"
EFFECTIVE_HASH = "COALESCE(staged_content_hash, content_hash)"
EFFECTIVE_VERSION = "COALESCE(staged_version_label, r2_version_label)"


def effective(alias: str | None = None) -> dict[str, str]:
    """The three fragments qualified with a table alias (e.g. 'reg')."""
    p = f"{alias}." if alias else ""
    return {
        "path": f"COALESCE({p}staged_r2_path, {p}r2_current_path)",
        "hash": f"COALESCE({p}staged_content_hash, {p}content_hash)",
        "version": f"COALESCE({p}staged_version_label, {p}r2_version_label)",
    }


def stage_file(cur, chapter_id: int, *, r2_path: str, version: str, public_url: str,
               content_hash: str, content_length: int | None) -> None:
    """Hold a new file to one side. Live columns are not touched."""
    cur.execute(
        """UPDATE dcp_chapter_registry
              SET staged_r2_path = %s, staged_version_label = %s, staged_public_pdf_url = %s,
                  staged_content_hash = %s, staged_url_content_length = %s, staged_at = now()
            WHERE id = %s""",
        (r2_path, version, public_url, content_hash, content_length, chapter_id))


def publish_staged(cur, council: str, chapter_key: str) -> bool:
    """Make the staged file live and clear the staging. Call inside the transaction that publishes the
    reviewed rules. Returns False when nothing was staged. The live-path change fires the proof-clearing
    triggers by design: the proofs were judged on the old file."""
    cur.execute(
        """UPDATE dcp_chapter_registry
              SET r2_current_path = staged_r2_path,
                  r2_version_label = staged_version_label,
                  r2_public_pdf_url = staged_public_pdf_url,
                  content_hash = staged_content_hash,
                  url_content_length = COALESCE(staged_url_content_length, url_content_length),
                  staged_r2_path = NULL, staged_version_label = NULL, staged_public_pdf_url = NULL,
                  staged_content_hash = NULL, staged_url_content_length = NULL, staged_at = NULL
            WHERE council = %s AND chapter_key = %s AND staged_r2_path IS NOT NULL""",
        (council, chapter_key))
    return cur.rowcount > 0
