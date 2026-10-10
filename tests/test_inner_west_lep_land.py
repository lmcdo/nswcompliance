"""DQ-140: each land-gated Inner West LEP clause gets the land its own words name.

The real-lot checks (10 Norton St, 45 Victoria Rd) call the served filter in
frontend-nextjs/__tests__/api/lep-land-condition.test.ts; these cover how conditions are built.
"""
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from enrichment.config.inner_west_lep_land import (  # noqa: E402
    LAND_GATED_CLAUSES, VERIFIED_LAYERS, clause_condition, condition_from_quote, row_conditions,
    schedule5_items,
)

ROOT = Path(__file__).resolve().parents[1]


def test_every_land_gated_clause_gets_a_condition():
    for key in LAND_GATED_CLAUSES:
        if key.startswith('Schedule'):
            continue
        cond = clause_condition(key)
        assert cond['source'], key
        if cond['layer'] is None:
            assert cond['verified'] is False, key


@pytest.mark.parametrize('key,layer,labels,zones', [
    ('6.17', 'Key Sites Map', ['Area 5'], None),
    ('6.21', 'Key Sites Map', ['Area 19'], ['E3', 'E4']),  # noqa: zone-codes -- cl 6.21's own words, a test expectation
    ('6.22', 'Key Sites Map', ['Area 20'], ['E3']),
    ('4.3C', 'Key Sites Map', ['Area 1'], ['R1']),
    ('6.23', 'Key Sites Map', ['Area 10', 'Area 11', 'Area 12', 'Area 8', 'Area 9'], None),
    ('4.4A', 'Floor Space Ratio Map', ['Area 1'], None),
    ('6.4', 'Terrestrial Biodiversity Map', ['Biodiversity'], None),
    ('6.20', 'Heritage Map', ['C54'], None),
    ('7.3', 'Key Sites Map', ['Area 14'], None),
    ('4.1', 'Lot Size Map', None, None),
])
def test_conditions_come_from_the_clause_words(key, layer, labels, zones):
    cond = clause_condition(key)
    assert (cond['layer'], cond['labels'], cond['zones']) == (layer, labels, zones)


def test_unseen_layers_are_never_verified():
    assert clause_condition('6.5')['verified'] is False   # Foreshore Building Line Map not seen
    assert clause_condition('6.33')['verified'] is False  # Bays West label not seen
    assert clause_condition('6.8')['layer'] is None       # ANEF is not a layerintersect layer


def test_a_shared_label_is_flagged():
    assert clause_condition('6.26')['label_not_unique']
    assert 'label_not_unique' not in clause_condition('6.17')


def test_a_map_name_outside_the_table_fails_loudly():
    with pytest.raises(ValueError):
        condition_from_quote("land identified as 'Area 1' on the Made Up Map")


def test_schedule5_reads_the_ocr_I_as_1():
    html = '<table><tr><td>Ashfield</td><td>Crocodile Farm Hotel</td><td>Local</td><td>1269</td></tr>' \
           '<tr><td>Leichhardt</td><td>6 Lords Road</td><td>11123</td></tr><tr><td>A18</td></tr></table>'
    assert schedule5_items(html) == ['A18', 'I1123', 'I269']


def _row(i, header, text, ref=None):
    return {'id': i, 'section_header': header, 'ref_number': ref, 'provision_text': text}


def test_schedule1_items_follow_document_order_and_ignore_a_wrong_heading():
    rows = [
        _row(1, 'Schedule 1 Additional permitted uses', "(1) This clause applies to ... identified as "
             "“45” on the Additional Permitted Uses Map."),
        _row(2, None, '46 Use of certain land for advertising structures'),
        _row(3, None, '(1) This clause applies to land identified as “46” on the Additional '
             'Permitted Uses Map.'),
        _row(4, '7.4 Additional permitted uses', '(2) Development for the following purposes ...'),
        _row(5, 'Schedule 1 Additional permitted uses', '(1) This clause applies to land identified as '
             '" 47 " on the Additional Permitted Uses Map.'),
    ]
    c = row_conditions(rows)
    assert c[1]['labels'] == ['45']
    assert c[4]['labels'] == ['46'] and c[4]['layer'] == 'Additional Permitted Uses Map'
    assert c[5]['labels'] == ['47']
    assert 2 not in c and 3 not in c  # headings are not served rules


def test_a_part_6_clause_is_not_swallowed_by_schedule1_refs():
    rows = [
        _row(1, 'Schedule 1 Additional permitted uses', 'The following ...', ref='Clause 32'),
        _row(2, '6.26 Development at Trafalgar Street', "This clause applies to ... identified as "
             "‘46’ on the Additional Permitted Use Map.", ref='Clause 6.26'),
        _row(3, '6.25 Development at Balmain Road', 'text', ref='Clause 6.25'),
        _row(4, 'Schedule 1 Additional permitted uses', 'Development consent must not ...', ref='Clause 32(3)'),
    ]
    c = row_conditions(rows)
    assert c[1]['labels'] == ['32'] and c[4]['labels'] == ['32']
    assert c[2] == clause_condition('6.26')  # its own clause, not "Schedule 1 item 6"
    assert c[3]['labels'] == ['Area 15']


def test_dq140_probe_lists_the_same_clauses():
    src = (ROOT / 'scripts' / 'dq_probe_live.py').read_text(encoding='utf-8')
    block = src[src.index('"DQ-140": ('):src.index('"DQ-141": (')]
    listed = re.findall(r"'((?:Schedule \d+)|(?:\d+\.\d+[A-Z]{0,2}))'", block.split(' IN (')[1])
    assert tuple(listed) == LAND_GATED_CLAUSES


def test_verified_layers_are_portal_names():
    assert 'Natural Resource-Biodiversity Map' not in VERIFIED_LAYERS
    assert 'Terrestrial Biodiversity Map' in VERIFIED_LAYERS
