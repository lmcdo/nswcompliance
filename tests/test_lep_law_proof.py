"""lep_law_proof: registry title -> instrument mapping, and the apply script's scope guard."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import apply_state_law_proof as A  # noqa: E402
import lep_law_proof as L  # noqa: E402

REG = [("Inner West Local Environmental Plan 2022", "epi-2022-0457"),
       ("Woollahra Local Environmental Plan 2014", "epi-2015-0020")]
TM = L.build_title_map(REG)


def test_chunked_lep_document_maps():
    assert L.lep_for("Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50", TM) == "epi-2022-0457"
    assert L.lep_for("Inner_West_Local_Environmental_Plan_2022__NSW_Legislation", TM) == "epi-2022-0457"


def test_dcp_and_sepp_documents_do_not_map():
    assert L.lep_for("Inner_West_Ashfield_DCP_2016__chapter_e1_heritage", TM) is None
    assert L.lep_for("State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation", TM) is None
    assert L.lep_for("Woollahra_DCP_2015__chapter_c1_paddington_hca", TM) is None
    assert L.lep_for(None, TM) is None


def test_word_boundary_required():
    assert L.lep_for("Inner_West_Local_Environmental_Plan_2022X_foo", TM) is None


def test_longest_title_wins():
    tm = L.build_title_map([("Foo LEP", "a"), ("Foo LEP 2020 Amendment", "b")])
    assert L.lep_for("Foo_LEP_2020_Amendment_part", tm) == "b"


def test_scope_default_is_state_only():
    assert A.scope_clause({}, False) == "source_council IS NULL"


def test_registry_plan_needs_flag():
    with pytest.raises(SystemExit):
        A.scope_clause({"scope": "registry_lep"}, False)
    assert A.scope_clause({"scope": "registry_lep"}, True) == "source_council IS NOT NULL"


def test_flag_does_not_widen_state_plan():
    with pytest.raises(SystemExit):
        A.scope_clause({}, True)
