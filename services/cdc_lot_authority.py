"""Authority loader for the CDC Housing Code lot-requirements screen.

prior-art-checked: reuse not viable because services/cdc_screen.py's
load_cdc_standards checks only the standards row (manual_verified/is_active) and
never resolves the cited provisions, their text, the source URL or the PDF page.
This module reads the SAME table (cdc_eligibility_standards) and the SAME cited
regulatory_provisions rows; it adds no new source of regulatory values.

The lot-requirements screen may produce a result only from a ValidatedAuthority,
and a ValidatedAuthority exists only when, for every standard the screen uses:

  1. exactly one active, manually verified, non-stale standards row exists, and its
     value is well formed;
  2. every cited provision ID resolves to a current row with non-empty text;
  3. the standard's source quote is contained in that provision text;
  4. the standard's value appears in its source quote;
  5. the provision's document carries an authoritative source URL
     (legislation.nsw.gov.au) and a PDF, and every provision carries a PDF page.

Any failure returns the list of failures and NO authority: the caller must then
return UNAVAILABLE and make no determination. Nothing here falls back to a default.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Optional

CODE_NAME = "housing_code"

# The four standards this screen evaluates, keyed by the standard_type column.
REQUIRED_STANDARDS = ("eligible_zones", "min_lot_size", "min_lot_width", "acid_sulfate_max_class")

AUTHORITATIVE_URL_PREFIX = "https://legislation.nsw.gov.au/"

_ZONE_RE = re.compile(r"^[A-Z]{1,3}[0-9]{0,2}[A-Z]?$")


def normalise_for_match(text: str) -> str:
    """Lowercase alphanumerics only, so a quote matches its provision regardless
    of whitespace, dashes, line breaks or a PDF-split superscript ("200 m2" vs
    "200m2"). Words and numbers must still match exactly."""
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


@dataclass(frozen=True)
class ProvisionEvidence:
    provision_id: int
    pdf_page: int
    document_id: str


@dataclass(frozen=True)
class StandardAuthority:
    """One validated standard: the value the screen may use plus its evidence."""

    standard_id: int
    standard_type: str
    clause: str
    value: object  # frozenset[str] for zones, float for thresholds, int for class
    source_quote: str
    provisions: tuple[ProvisionEvidence, ...]
    source_url: str
    pdf_url: str
    verified_by: Optional[str]
    verified_at: Optional[str]


@dataclass(frozen=True)
class ValidatedAuthority:
    standards: dict  # standard_type -> StandardAuthority (all REQUIRED_STANDARDS)

    def get(self, standard_type: str) -> StandardAuthority:
        return self.standards[standard_type]  # noqa: bracket-access — construction guarantees every REQUIRED_STANDARDS key


@dataclass(frozen=True)
class AuthorityOutcome:
    authority: Optional[ValidatedAuthority]
    failures: tuple[str, ...]


def _value_for(standard_type: str, row: dict) -> tuple[object, Optional[str]]:
    """Parse and validate a standard's value. Returns (value, failure)."""
    if standard_type == "eligible_zones":
        zones = row.get("applicable_zones")
        if not isinstance(zones, (list, tuple)) or not zones:
            return None, "eligible_zones has no zones"
        cleaned = set()
        for z in zones:
            if not isinstance(z, str) or not _ZONE_RE.match(z.strip()):
                return None, f"eligible_zones contains an invalid zone code {z!r}"
            cleaned.add(z.strip())
        return frozenset(cleaned), None
    raw = row.get("numeric_value")
    try:
        num = float(raw)
    except (TypeError, ValueError):
        return None, f"{standard_type} has no numeric value"
    if not math.isfinite(num) or num <= 0:
        return None, f"{standard_type} value {raw!r} is not a finite positive number"
    if standard_type == "acid_sulfate_max_class":
        if num != int(num) or not 1 <= int(num) <= 5:
            return None, f"acid_sulfate_max_class {raw!r} is not a class 1-5"
        return int(num), None
    return num, None


def _value_in_quote(standard_type: str, value: object, quote: str) -> bool:
    """The threshold the screen uses must be the one the quote states."""
    q = normalise_for_match(quote)
    if standard_type == "eligible_zones":
        tokens = set(re.findall(r"\b[A-Z]{1,3}[0-9]{1,2}[A-Z]?\b", quote or ""))
        return set(value) <= tokens  # type: ignore[arg-type]
    if standard_type == "acid_sulfate_max_class":
        return f"class{value}" in q
    num = float(value)  # type: ignore[arg-type]
    shown = str(int(num)) if num == int(num) else f"{num:g}"
    return normalise_for_match(shown) in q


def _validate_one(st: str, rows: list[dict], provisions: dict, documents: dict
                  ) -> tuple[Optional[StandardAuthority], list[str]]:
    if len(rows) != 1:
        return None, [f"{st}: expected exactly one active standard, found {len(rows)}"]
    row = rows[0]  # noqa: bracket-access — length checked above
    sid = row.get("id")
    if row.get("manual_verified") is not True:
        return None, [f"{st}: standard {sid} is not manually verified"]
    if row.get("stale_since"):
        return None, [f"{st}: standard {sid} is marked stale ({row.get('stale_reason') or 'source amended'})"]
    clause = (row.get("ref_number") or "").strip()
    if not clause:
        return None, [f"{st}: standard {sid} has no clause reference"]
    value, err = _value_for(st, row)
    if err:
        return None, [f"{st}: {err}"]
    quote = (row.get("source_quote") or "").strip()
    ids = row.get("source_provision_ids") or []
    if not quote:
        return None, [f"{st}: no source quote"]
    if not ids:
        return None, [f"{st}: no cited provision IDs"]
    if not _value_in_quote(st, value, quote):
        return None, [f"{st}: value {value!r} does not appear in the source quote"]

    failures: list[str] = []
    evidence: list[ProvisionEvidence] = []
    texts: list[str] = []
    doc_ids: set = set()
    for pid in ids:
        p = provisions.get(int(pid))
        if p is None:
            failures.append(f"{st}: cited provision {pid} does not exist")
            continue
        if p.get("is_current") is not True:
            failures.append(f"{st}: cited provision {pid} is not current")
            continue
        text = p.get("provision_text") or ""
        if not text.strip():
            failures.append(f"{st}: cited provision {pid} has no text")
            continue
        page = p.get("pdf_page")
        if not isinstance(page, int) or isinstance(page, bool) or page <= 0:
            failures.append(f"{st}: cited provision {pid} has no PDF page")
            continue
        texts.append(text)
        doc_ids.add(p.get("document_id"))
        evidence.append(ProvisionEvidence(int(pid), page, p.get("document_id")))
    if failures:
        return None, failures
    if len(doc_ids) != 1:
        return None, [f"{st}: cited provisions span {len(doc_ids)} documents, expected one"]
    doc = documents.get(next(iter(doc_ids))) or {}
    source_url = (doc.get("source_url") or "").strip()
    pdf_url = (doc.get("r2_pdf_url") or "").strip()
    if not source_url.startswith(AUTHORITATIVE_URL_PREFIX):
        return None, [f"{st}: source document has no authoritative source URL"]
    if not pdf_url:
        return None, [f"{st}: source document has no PDF"]
    fragments = [f for f in re.split(r"\.\.\.|…", quote) if normalise_for_match(f)]
    joined = normalise_for_match("".join(texts))
    missing = [f.strip()[:60] for f in fragments if normalise_for_match(f) not in joined]
    if missing:
        return None, [f"{st}: source quote not found in cited provision text: {missing}"]
    return StandardAuthority(
        standard_id=int(sid), standard_type=st, clause=clause, value=value,
        source_quote=quote, provisions=tuple(evidence), source_url=source_url,
        pdf_url=pdf_url, verified_by=row.get("verified_by"),
        verified_at=str(row.get("verified_at")) if row.get("verified_at") else None,
    ), []


def validate_authority(standard_rows: list[dict], provision_rows: list[dict],
                       document_rows: list[dict]) -> AuthorityOutcome:
    """Pure validation of already-fetched rows (testable without a database).

    standard_rows: active cdc_eligibility_standards rows for CODE_NAME.
    provision_rows: regulatory_provisions rows for every cited ID.
    document_rows: documents rows for every cited provision's document_id.
    """
    by_type: dict = {}
    for r in standard_rows:
        by_type.setdefault(r.get("standard_type"), []).append(r)
    provisions = {int(p.get("id")): p for p in provision_rows if p.get("id") is not None}
    documents = {d.get("id"): d for d in document_rows}

    failures: list[str] = []
    validated: dict = {}
    for st in REQUIRED_STANDARDS:
        auth, errs = _validate_one(st, by_type.get(st) or [], provisions, documents)
        failures.extend(errs)
        if auth is not None:
            validated[st] = auth
    if failures or set(validated) != set(REQUIRED_STANDARDS):
        return AuthorityOutcome(None, tuple(failures) or ("authority incomplete",))
    return AuthorityOutcome(ValidatedAuthority(validated), ())


def load_authority(conn) -> AuthorityOutcome:
    """Fetch the rows and validate. Any database error is an authority failure."""
    if conn is None:
        return AuthorityOutcome(None, ("no database connection",))
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, standard_type, numeric_value, applicable_zones, ref_number,
                   source_provision_ids, source_quote, manual_verified, verified_by,
                   verified_at, stale_since, stale_reason
            FROM cdc_eligibility_standards
            WHERE code_name = %s AND is_active = TRUE AND standard_type = ANY(%s)
            """,
            (CODE_NAME, list(REQUIRED_STANDARDS)),
        )
        cols = [d[0] for d in cur.description]
        standards = [dict(zip(cols, r)) for r in cur.fetchall()]
        ids = sorted({int(i) for s in standards for i in (s.get("source_provision_ids") or [])})
        provisions: list = []
        documents: list = []
        if ids:
            cur.execute(
                "SELECT id, document_id, provision_text, pdf_page, is_current "
                "FROM regulatory_provisions WHERE id = ANY(%s)",
                (ids,),
            )
            cols = [d[0] for d in cur.description]
            provisions = [dict(zip(cols, r)) for r in cur.fetchall()]
            doc_ids = sorted({p.get("document_id") for p in provisions if p.get("document_id")})
            if doc_ids:
                cur.execute(
                    "SELECT id, source_url, r2_pdf_url FROM documents WHERE id = ANY(%s)",
                    (doc_ids,),
                )
                cols = [d[0] for d in cur.description]
                documents = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
    except Exception as e:  # noqa: BLE001 — every failure is reported as unavailable authority
        try:
            conn.rollback()
        except Exception:  # noqa: BLE001
            pass
        return AuthorityOutcome(None, (f"authority query failed: {type(e).__name__}",))
    return validate_authority(standards, provisions, documents)
