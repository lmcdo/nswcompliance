"""Publish refuses a chapter whose new version would lose its area links (scripts/dcp_area_link_guard.py).

prior-art-checked: new module; pure judge plus a fake cursor, no database.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import dcp_area_link_guard as g  # noqa: E402


def test_keeping_nine_tenths_of_the_links_passes():
    assert g.judge(100, 90) and g.judge(100, 150)


def test_losing_more_than_a_tenth_of_the_links_is_refused():
    assert not g.judge(89, 4)            # Waverley pilot: 4 of 89 Part E links
    assert not g.judge(1009, 124)        # Leichhardt C2 before the C2.2.1.4 heading fix


def test_a_chapter_with_few_links_is_not_judged():
    assert g.judge(4, 0)


def test_enforce_raises_and_the_override_lets_one_named_chapter_through(monkeypatch):
    monkeypatch.setattr(g, "relinkable_count", lambda cur, c, k: g.Linked(4, 4))
    with pytest.raises(g.AreaLinkLossRefused, match="--allow-area-link-loss waverley/waverley-dcp-2022"):
        g.enforce(None, "waverley", "waverley-dcp-2022", g.Linked(89, 0))
    assert g.enforce(None, "waverley", "waverley-dcp-2022", g.Linked(89, 0),
                     frozenset({"waverley/waverley-dcp-2022"})) == g.Linked(4, 4)


def test_both_publish_paths_run_the_guard_before_they_commit():
    """PR #1285 review: the direct-to-live path (dcp_extract_changed) published without it."""
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "scripts"
    for name in ("dcp_commit_approved.py", "dcp_extract_changed.py"):
        src = (root / name).read_text(encoding="utf-8")
        assert "area_links.linked_count(cur, council, chapter_key)" in src, name
        guard = src.index("area_links.enforce(cur, council, chapter_key")
        assert "conn.commit()" in src[guard:guard + 400] or name == "dcp_commit_approved.py", name


class _Cur:
    """Records UPDATEs; returns the canned SELECT rows once."""

    def __init__(self, rows):
        self.rows, self.updates = rows, []

    def execute(self, sql, params=None):
        if sql.lstrip().startswith("UPDATE"):
            self.updates.append(params)

    def fetchall(self):
        out, self.rows = self.rows, []
        return out


class _Tagger:
    def tag(self, doc, text):
        return ("precinct", "E6" if "Bondi" in text else None, None)


def test_fill_parts_gives_new_rows_the_part_enrichment_would():
    """2026-10-15: inside the publish no new Waverley row had a Part yet, so the guard predicted 0 of 126 links
    while the published version carries 1,028 Part E rows. The Part is filled first, with the same tagger."""
    cur = _Cur([(1, "d", "Bondi Junction controls ..."), (2, "d", "General controls ...")])
    assert g.fill_parts(cur, "waverley", "waverley-dcp-2022", tagger=_Tagger()) == 1
    assert cur.updates == [("E6", 1)]          # a row the tagger gives no Part is left alone


def test_both_publish_paths_fill_the_part_before_the_guard():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1] / "scripts"
    for name in ("dcp_commit_approved.py", "dcp_extract_changed.py"):
        src = (root / name).read_text(encoding="utf-8")
        fill = src.index("area_links.fill_parts(cur, council, chapter_key)")
        assert fill < src.index("area_links.enforce(cur, council, chapter_key"), name


class _ZoneTagger:
    """Stands in for ApplicabilityTagger.tag_with_provenance."""

    def tag_with_provenance(self, text, doc, part=None, pdf_page=None):
        if "config" in text:
            return ["R2", "R3"], ["ALL"], {"zone_source": "config_specific"}  # noqa: zone-codes (test fixture)
        if "prose" in text:
            return ["R4"], ["ALL"], {"zone_source": "text_regex"}
        return ["ALL"], ["ALL"], {"zone_source": "config_all"}


def test_config_zones_count_and_zones_read_from_prose_do_not():
    """Campbelltown Part 3, 2026-10-18: enrichment re-applied its zones from the chapter config to all 504 rules, but the
    guard predicted only precinct/gate links and refused. A zone read from the rule's own words is not counted."""
    cur = _Cur([(1, "d", "config row", None, 3), (2, "d", "prose row", None, 3), (3, "d", "everywhere", None, 4)])
    assert g.config_zoned_ids(cur, "campbelltown", "part3", tagger=_ZoneTagger()) == {1}


def test_zone_only_links_re_applied_by_config_pass(monkeypatch):
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set())
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(504)))
    assert g.enforce(None, "campbelltown", "part3", g.Linked(0, 193)) == g.Linked(0, 504)


def test_config_zones_cannot_hide_lost_precinct_links(monkeypatch):
    """The two kinds are judged apart: a chapter that loses its precinct links is refused even when every row will
    get config zones, so the zone count can never stand in for the precincts."""
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set(range(10)))
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(500)))
    with pytest.raises(g.AreaLinkLossRefused, match="100 rules linked to a precinct or marker"):
        g.enforce(None, "c", "k", g.Linked(100, 50))


def test_lost_zone_only_links_are_still_refused(monkeypatch):
    monkeypatch.setattr(g, "relinkable_ids", lambda cur, c, k: set())
    monkeypatch.setattr(g, "config_zoned_ids", lambda cur, c, k: set(range(20)))
    with pytest.raises(g.AreaLinkLossRefused):
        g.enforce(None, "c", "k", g.Linked(0, 193))


# ---------------------------------------------------------------------------
# rederive_after_publish: both publish paths re-make the precinct keys
# ---------------------------------------------------------------------------

def _fake_derive(monkeypatch, behaviour):
    calls = []
    mod = type(sys)("derive_precinct_keys")

    def run(council, apply, validate):
        calls.append((council, apply, validate))
        return behaviour(council)

    mod.run = run
    mod.RULES = []
    mod.DATABASE_URL = None
    mod._derive = lambda strategy, row: None
    monkeypatch.setattr(g, "withhold_unkeyed", lambda dpk, council: 0)
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", mod)
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", mod)
    return calls


def test_rederive_runs_once_per_council_named_and_applies(monkeypatch):
    calls = _fake_derive(monkeypatch, lambda c: 0)
    g.rederive_after_publish(["ku_ring_gai", "campbelltown", "ku_ring_gai"])
    assert calls == [("campbelltown", True, False), ("ku_ring_gai", True, False)]


def test_rederive_does_nothing_on_a_dry_run_or_with_no_council(monkeypatch):
    calls = _fake_derive(monkeypatch, lambda c: 0)
    g.rederive_after_publish(["ku_ring_gai"], dry_run=True)
    g.rederive_after_publish(set())
    assert calls == []


def test_one_council_failing_warns_and_the_next_still_runs(monkeypatch, capsys):
    def boom(c):
        if c == "ashfield":
            raise RuntimeError("fingerprint mismatch")
        return 0
    calls = _fake_derive(monkeypatch, boom)
    g.rederive_after_publish(["ashfield", "ku_ring_gai"])
    assert [c[0] for c in calls] == ["ashfield", "ku_ring_gai"]
    assert "derive_precinct_keys.py --council ashfield --apply" in capsys.readouterr().out


def test_the_direct_to_live_path_rederives_after_enrichment():
    """2026-10-18: Ku-ring-gai 14A/14H went live through dcp_extract_changed with 0 of 112 / 0 of 37 rows keyed,
    because only dcp_commit_approved re-derived. The call must come after enrichment (layer tagging would
    otherwise overwrite the derived 'precinct' layer) and outside the quality-gate branch."""
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts" / "dcp_extract_changed.py").read_text(encoding="utf-8")
    call = src.index("area_links.alert_precinct_keys(published_councils, args.dry_run, _precinct_alert_sender())")
    assert src.index("results = run_standard_enrichment(batch_size=500)") < call < src.rindex("sys.exit(2)")
    line = src[src.rindex("\n", 0, call) + 1:call]
    assert line == "    ", "must not sit inside the quality-gate branch"
    # only chapters this run wrote live -- not review or dry-run chapters
    assert "elif not args.review and not args.dry_run:\n                published_councils.add(chapter[\"council\"])" in src


def test_the_commit_path_uses_the_same_rederive():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "scripts" / "dcp_commit_approved.py").read_text(encoding="utf-8")
    assert "area_links.alert_precinct_keys(committed_councils, False, _precinct_alert_sender())" in src



# ---------------------------------------------------------------------------
# Fails closed: a rule a precinct rule should have keyed is withheld, not served council-wide
# (Sol back-review of #1344, 2026-10-20)
# ---------------------------------------------------------------------------

class _WCur:
    """Rows of the rule: `unkeyed` ids are live with no key; `keyed` ids already carry a key."""
    def __init__(self, unkeyed, keyed=()):
        self.unkeyed, self.keyed, self.sql, self.description, self.rowcount = unkeyed, keyed, [], None, 0
    def execute(self, sql, args=None):
        self.sql.append((sql, args))
        if sql.lstrip().startswith("SELECT"):
            self.description = [("id",), ("document_id",), ("ref_number",), ("pdf_page",), ("source_chapter_key",),
                                ("v2_precinct_id",), ("v2_dcp_layer",), ("v2_dcp_part",), ("provision_text",),
                                ("v2_is_actionable",)]
        else:
            self.rowcount = len(args[0])
    def fetchall(self):
        return ([(i, "d", "r", 1, "k", None, None, None, "t", True) for i in self.unkeyed]
                + [(i, "d", "r", 1, "k", "P1", "precinct", None, "t", True) for i in self.keyed])


class _WConn:
    def __init__(self, cur):
        self.cur, self.committed = cur, False
    def cursor(self): return self.cur
    def commit(self): self.committed = True
    def rollback(self): pass
    def close(self): pass


def _dpk(rules):
    mod = type(sys)("dpk")
    mod.RULES, mod.DATABASE_URL = rules, "postgres://x"
    mod._derive = lambda strategy, row: "P1"
    return mod


def test_rows_the_rule_should_have_keyed_are_withheld(monkeypatch, capsys):
    import psycopg2
    cur = _WCur([11, 12]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    n = g.withhold_unkeyed(_dpk([{"council": "ku_ring_gai", "where": "true", "strategy": "s"}]), "ku_ring_gai")
    assert n == 2 and conn.committed
    upd = [q for q in cur.sql if q[0].startswith("UPDATE")][0]
    assert "v2_is_actionable = FALSE" in upd[0] and "v2_precinct_id IS NULL" in upd[0] and upd[1] == ([11, 12],)
    assert "[WITHHELD] 2 ku_ring_gai" in capsys.readouterr().out


def test_nothing_unkeyed_writes_nothing(monkeypatch):
    import psycopg2
    cur = _WCur([]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    assert g.withhold_unkeyed(_dpk([{"council": "c", "where": "true", "strategy": "s"}]), "c") == 0
    assert not any(q[0].startswith("UPDATE") for q in cur.sql) and not conn.committed


def test_other_councils_rules_are_not_used(monkeypatch):
    import psycopg2
    cur = _WCur([11]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    assert g.withhold_unkeyed(_dpk([{"council": "other", "where": "true", "strategy": "s"}]), "c") == 0


def test_withholding_runs_even_when_derivation_raises_or_succeeds_silently(monkeypatch):
    seen = []
    def boom(c):
        if c == "ashfield":
            raise RuntimeError("fingerprint mismatch")
        return 0
    _fake_derive(monkeypatch, boom)
    monkeypatch.setattr(g, "withhold_unkeyed", lambda dpk, council: seen.append(council) or 0)
    g.rederive_after_publish(["ashfield", "ku_ring_gai"])
    assert seen == ["ashfield", "ku_ring_gai"]



def test_a_check_that_cannot_run_fails_the_run(monkeypatch):
    _fake_derive(monkeypatch, lambda c: 0)
    monkeypatch.setattr(g, "withhold_unkeyed", lambda dpk, council: None if council == "ashfield" else 0)
    with pytest.raises(g.PrecinctKeysUnverified, match="ashfield"):
        g.rederive_after_publish(["ashfield", "ku_ring_gai"])


def test_derivation_that_cannot_load_fails_the_run(monkeypatch):
    monkeypatch.setitem(sys.modules, "scripts.derive_precinct_keys", None)
    monkeypatch.setitem(sys.modules, "derive_precinct_keys", None)
    with pytest.raises(g.PrecinctKeysUnverified, match="could not load"):
        g.rederive_after_publish(["ashfield"])


def test_database_down_during_the_check_is_none_not_zero(monkeypatch):
    import psycopg2
    def down(*a, **k):
        raise psycopg2.OperationalError("down")
    monkeypatch.setattr(psycopg2, "connect", down)
    assert g.withhold_unkeyed(_dpk([{"council": "c", "where": "true", "strategy": "s"}]), "c") is None



def test_alert_sends_withheld_rules_and_never_raises(monkeypatch):
    sent = []
    monkeypatch.setattr(g, "rederive_after_publish", lambda c, dry_run: ["ku_ring_gai: 3 precinct-limited rule(s) withheld"])
    g.alert_precinct_keys(["ku_ring_gai"], False, sent.append)
    assert len(sent) == 1 and "3 precinct-limited rule(s) withheld" in sent[0]


def test_alert_reports_a_check_that_could_not_run(monkeypatch):
    sent = []
    def boom(c, dry_run):
        raise g.PrecinctKeysUnverified("could not check ashfield")
    monkeypatch.setattr(g, "rederive_after_publish", boom)
    g.alert_precinct_keys(["ashfield"], False, sent.append)
    assert sent and "NOT VERIFIED: could not check ashfield" in sent[0]


def test_alert_quiet_when_nothing_needs_attention(monkeypatch):
    sent = []
    monkeypatch.setattr(g, "rederive_after_publish", lambda c, dry_run: [])
    g.alert_precinct_keys(["c"], False, sent.append)
    assert sent == []


def test_rows_on_a_repaginated_pdf_are_withheld_even_when_no_page_derives(monkeypatch):
    """Sol 2026-10-20: a re-paginated PDF fails the page-range fingerprint, the derivation writes no key and
    _derive returns None for the shifted pages, so a check based on _derive alone missed every such row."""
    import psycopg2
    cur = _WCur([21, 22], keyed=[23]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    dpk = _dpk([{"council": "city_of_sydney", "where": "true", "strategy": "page_range", "fingerprint": {"x": 1}}])
    dpk._derive = lambda strategy, row: None
    dpk._fingerprint_reasons = lambda fp, pages, n_none, n_total: ["last keyed page moved"]
    assert g.withhold_unkeyed(dpk, "city_of_sydney") == 2
    upd = [q for q in cur.sql if q[0].startswith("UPDATE")][0]
    assert upd[1] == ([21, 22],)


def test_unbroken_fingerprint_and_no_derivation_withholds_nothing(monkeypatch):
    import psycopg2
    cur = _WCur([21]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    dpk = _dpk([{"council": "c", "where": "true", "strategy": "page_range", "fingerprint": {"x": 1}}])
    dpk._derive = lambda strategy, row: None
    dpk._fingerprint_reasons = lambda fp, pages, n_none, n_total: []
    assert g.withhold_unkeyed(dpk, "c") == 0


def test_an_alert_that_cannot_be_sent_does_not_abort_the_run(monkeypatch, capsys):
    monkeypatch.setattr(g, "rederive_after_publish", lambda c, dry_run: ["c: 1 withheld"])
    def down(msg):
        raise ConnectionError("telegram down")
    g.alert_precinct_keys(["c"], False, down)
    assert "could not send the precinct-key alert" in capsys.readouterr().out


def test_a_row_whose_key_cannot_be_worked_out_is_withheld(monkeypatch):
    import psycopg2
    cur = _WCur([31, 32]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    dpk = _dpk([{"council": "c", "where": "true", "strategy": "s"}])
    def derive(strategy, row):
        if row["id"] == 32:
            raise ValueError("malformed row")
        return "P1"
    dpk._derive = derive
    assert g.withhold_unkeyed(dpk, "c") == 2



def test_a_not_yet_switched_on_row_is_withheld_too(monkeypatch):
    """Sol 2026-10-20: a NULL row is switched on by the next routine enrichment run, unkeyed."""
    import psycopg2
    class Cur(_WCur):
        def fetchall(self):
            return [(41, "d", "r", 1, "k", None, None, None, "t", None)]
    cur = Cur([]); conn = _WConn(cur)
    monkeypatch.setattr(psycopg2, "connect", lambda *a, **k: conn)
    assert g.withhold_unkeyed(_dpk([{"council": "c", "where": "true", "strategy": "s"}]), "c") == 1


def test_withheld_means_false_which_routine_enrichment_leaves_alone():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[1] / "enrichment" / "pipeline.py").read_text(encoding="utf-8")
    assert "WHERE v2_is_actionable IS NULL" in src  # the routine selector: FALSE rows are not picked up
