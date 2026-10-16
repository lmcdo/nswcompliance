"""state_law_proof2: stronger normaliser and the verbatim / amended / paraphrase classifier."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import state_law_proof2 as P  # noqa: E402

TODAY = ("A fence must be no higher than 1.8 m above ground level and the floor area must not exceed 60 m 2 "
         "for a secondary dwelling. Landscaped area must be provided along the boundaries adjoining roads.")
OLDER = "The maximum floor area for a secondary dwelling is 45 m 2 where the lot is under the stated size."


def doc(text):
    return P.Doc([text])


def test_superscript_matches_spaced_digit():
    assert P.squash2("60 m\u00b2") == P.squash2("60 m 2") == P.squash2("60 m\u00a02")


def test_html_table_stripped_to_cell_text():
    assert P.squash2("<table><tr><td>Lot area</td><td>10%</td></tr></table>") == P.squash2("Lot area 10%")


def test_dash_quote_markdown_folded():
    assert P.squash2("**the\u2019s** \u2013 a | b") == P.squash2("the's - a b")
    assert P.squash2("a \* b") == P.squash2("a * b")


def test_words2_ignores_punctuation_and_case():
    assert P.words2("Max. 60m\u00b2, (a)") == ["max", "60m2", "a"]


def test_verbatim_with_superscript_is_proven():
    t = "the floor area must not exceed 60 m\u00b2 for a secondary dwelling"
    assert P.classify(t, doc(TODAY), None)["status"] == "proven"


def test_short_verbatim_is_not_proof():
    assert P.classify("above ground level", doc(TODAY), None)["status"] == "short_unproven"


def test_older_version_verbatim_is_amended():
    t = "The maximum floor area for a secondary dwelling is 45 m 2 where the lot is under the stated size."
    assert P.classify(t, doc(TODAY), doc(OLDER))["status"] == "amended"
    assert P.classify(t, doc(TODAY), None)["status"] != "amended"


def test_paraphrase_below_half():
    t = "Parking spaces must remain the same as before the works started on this site"
    c = P.classify(t, doc(TODAY), doc(OLDER))
    assert c["status"] == "paraphrase" and c["share"] < P.PARAPHRASE_BELOW


def test_threshold_boundaries():
    # law has runs for 'w1..w10'; a 10-word text has 6 five-word runs
    law = doc("w1 w2 w3 w4 w5 w6 w7 w8 w9 w10")
    half = "w1 w2 w3 w4 w5 w6 zz1 zz2 zz3 zz4 w10"  # runs: w1-5 yes, w2-6 yes, others no -> 2/7
    assert P.classify(half, law, None)["status"] == "paraphrase"
    mid = "w1 w2 w3 w4 w5 w6 w7 xx w8 w9 w10 yy"  # runs hit: 3 of 8 (<0.5) -> sanity on direction below
    assert P.classify(mid, law, None)["share"] < 0.5
    # 4 hit of 6 runs = 0.667 -> partial_unresolved
    t = "w1 w2 w3 w4 w5 w6 w7 w8 q1 q2 q3 q4"
    c = P.classify(t, law, None)
    assert 0.5 <= c["share"] < 0.9 and c["status"] == "partial_unresolved"


def test_high_share_not_verbatim_is_partial_high_never_proven():
    law = doc("w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12 w13 w14 w15 w16 w17 w18 w19 w20")
    t = "w1 w2 w3 w4 w5 w6 w7 w8 w9 w10 w11 w12 w13 w14 w15 w16 w17 w18 w19 w20 extra"  # not a substring; 16 of 17 runs hit
    c = P.classify(t, law, None)
    assert c["status"] == "partial_high" and c["share"] >= P.PARTIAL_HIGH_AT


def test_empty_text_is_paraphrase_not_proven():
    assert P.classify("# heading only", doc(TODAY), None)["status"] == "paraphrase"
