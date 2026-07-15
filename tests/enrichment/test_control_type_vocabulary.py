"""Tests for the canonical control_type vocabulary + its enforcement.

Guards the single source of truth (enrichment/config/control_type_vocabulary.py)
against the drift that hid DCP controls from the capacity engine and mis-grouped
them in the UI: variant slugs (landscaped_area_min, site_coverage_max, ...) must
normalise to canonical, the SQL CHECK constraint must stay in sync with the
Python set, the extractors must not emit non-canonical slugs, and no row in the
DB may carry a slug outside the vocabulary.

Run with: pytest tests/enrichment/test_control_type_vocabulary.py -v
"""
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from enrichment.config.control_type_vocabulary import (  # noqa: E402
    CANONICAL_CONTROL_TYPES,
    CANONICAL_SET,
    CONTROL_TYPE_ALIASES,
    MAXIMUM_CONTROL_TYPES,
    UnknownControlTypeError,
    is_maximum,
    normalize_control_type,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestNormalize:
    def test_canonical_passes_through(self):
        for ct in CANONICAL_SET:
            assert normalize_control_type(ct) == ct

    def test_every_alias_maps_to_a_canonical_slug(self):
        # This is the drift we are eliminating — each alias must resolve to a
        # real canonical slug, never to another alias or an unknown.
        for variant, canon in CONTROL_TYPE_ALIASES.items():
            assert normalize_control_type(variant) == canon
            assert canon in CANONICAL_SET

    def test_known_drifts_specifically(self):
        assert normalize_control_type("landscaped_area_min") == "landscaping_min"
        assert normalize_control_type("communal_open_space") == "communal_open_space_min"
        assert normalize_control_type("site_coverage_max") == "max_site_coverage"
        assert normalize_control_type("height_max") == "max_height"
        assert normalize_control_type("height_storeys_max") == "max_height"
        assert normalize_control_type("floor_area_max") == "max_floor_area"

    def test_none_is_passthrough(self):
        assert normalize_control_type(None) is None

    def test_whitespace_is_stripped(self):
        assert normalize_control_type("  front_setback  ") == "front_setback"

    def test_unknown_raises_in_strict_mode(self):
        with pytest.raises(UnknownControlTypeError):
            normalize_control_type("totally_new_slug")

    def test_unknown_returns_none_when_not_strict(self):
        assert normalize_control_type("totally_new_slug", strict=False) is None


class TestMaximumClassification:
    def test_maxima_are_ceilings(self):
        assert is_maximum("max_height")
        assert is_maximum("max_site_coverage")
        assert is_maximum("site_coverage_max")  # via alias

    def test_minima_are_not_maxima(self):
        assert not is_maximum("front_setback")
        assert not is_maximum("landscaping_min")

    def test_maximum_set_is_subset_of_canonical(self):
        assert MAXIMUM_CONTROL_TYPES <= CANONICAL_SET


class TestConstraintStaysInSync:
    """The SQL CHECK constraint and the Python vocabulary must not drift apart."""

    def _constraint_slugs(self):
        path = os.path.join(_ROOT, "migrations", "enforce_control_type_vocabulary.sql")
        sql = open(path, encoding="utf-8").read()
        # slugs inside the CHECK (... control_type IN ( '...' , ... ) ...)
        check = sql[sql.index("control_type IN"):]
        return set(re.findall(r"'([a-z_]+)'", check))

    def test_migration_matches_python_vocabulary(self):
        assert self._constraint_slugs() == CANONICAL_SET


class TestExtractorsEmitCanonical:
    """The extractors must not reintroduce the *_max suffix drift."""

    def test_no_noncanonical_max_literals_in_extractors(self):
        bad = ("'height_max'", "'site_coverage_max'", "'floor_area_max'", "'height_storeys_max'")
        ext_dir = os.path.join(_ROOT, "enrichment", "extractors")
        for name in os.listdir(ext_dir):
            if not name.startswith("extract_secondary_setbacks") or not name.endswith(".py"):
                continue
            src = open(os.path.join(ext_dir, name), encoding="utf-8").read()
            for token in bad:
                assert token not in src, f"{name} still emits {token}"


@pytest.mark.database
class TestNoDriftInDatabase:
    def test_every_db_control_type_is_canonical(self):
        import psycopg2

        url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
        if not url:
            pytest.skip("no DATABASE_URL")
        conn = psycopg2.connect(url)
        try:
            cur = conn.cursor()
            cur.execute("SELECT DISTINCT control_type FROM dcp_setback_controls")
            existing = {r[0] for r in cur.fetchall()}
        finally:
            conn.close()
        drift = existing - CANONICAL_SET
        assert not drift, f"non-canonical control_type in DB: {drift}"
