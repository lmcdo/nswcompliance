"""One council key, two readers: services/council_key.py must give what lga-slug.ts gives."""
import json
from pathlib import Path

import pytest

from services.council_key import _RENAMES_PATH, to_council_key


@pytest.mark.parametrize("raw,key", [
    ("city_of_parramatta", "parramatta"), ("CITY OF PARRAMATTA", "parramatta"),
    ("the_hills_shire", "the_hills"), ("The Hills Shire", "the_hills"),
    ("Canterbury-Bankstown", "canterbury_bankstown"), ("Ashfield", "ashfield"),
    ("Marrickville", "marrickville"), ("Woollahra", "woollahra"), ("canada_bay", "canada_bay"),
    ("City of Canada Bay", "canada_bay"), ("Sydney", "city_of_sydney"),
    ("Strathfield Municipal", "strathfield"), ("Ku-ring-gai", "ku_ring_gai"),
])
def test_keys(raw, key):
    assert to_council_key(raw) == key


@pytest.mark.parametrize("raw", [None, "", "   ", "!!!"])
def test_empty_is_none_never_blank(raw):
    assert to_council_key(raw) is None


def test_renames_file_is_the_one_the_ts_reader_imports():
    ts = (Path(__file__).resolve().parents[1] / "frontend-nextjs" / "lib" / "lga-slug.ts").read_text(encoding="utf-8")
    assert "from './lga-slug-renames.json'" in ts
    assert "city_of_parramatta: 'parramatta'" not in ts  # no second copy in the TS file
    data = json.loads(_RENAMES_PATH.read_text(encoding="utf-8"))
    assert data["city_of_parramatta"] == "parramatta"


def test_yield_box_queries_with_the_key(monkeypatch):
    """The DCP fetch receives 'parramatta' when the page sends 'city_of_parramatta'."""
    import sys
    from services import constraint_arithmetic as ca
    seen = {}

    class FakeConn:
        autocommit = True
        def close(self): pass

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import conveyancing_db
    monkeypatch.setattr(conveyancing_db, "fetch_dcp_setbacks",
                        lambda conn, lga, zone: seen.setdefault("lga", lga) and None)
    monkeypatch.setattr(conveyancing_db, "fetch_sepp_housing_standards", lambda conn, **k: [])
    monkeypatch.setenv("DATABASE_URL", "postgres://x")
    import psycopg2
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: FakeConn())
    ca._fetch_constraint_data_from_db(lga="city_of_parramatta", zone="R2", lot_area_m2=600.0,
                                      lep_height_str="9", lep_fsr_str="0.5")
    assert seen.get("lga") == "parramatta"
