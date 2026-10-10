"""Inner West LEP 2022: the LAND each site-specific clause names, as a condition the portal can check (DQ-140).

prior-art-checked: lib/nsw-planning-portal.ts already reads the Key Sites and Additional Permitted Uses
layers, but only to list clause numbers in a side card; nothing gated the served rule rows on them.
enrichment/config/inner_west_lep_config.py holds each clause's own words (scope_evidence) and is the
only source read here. lib/dcp-land-application.ts is the same idea for a DCP's Land Application Map.

WHY. 67 of 88 clauses were recorded `scope_declined` because their reach is a map area the zone and
development-type labels cannot hold, and `config_declined` serves to ALL. So clause 6.17 ("168 Norton
Street, Leichhardt, identified as 'Area 5' on the Key Sites Map") was shown on every Inner West lot.

WHAT DECIDES IT. The Planning Portal `layerintersect` answer for the lot names the same map areas the
clauses name. Measured live 2026-10-11:
  10 Norton St Leichhardt  (propId 3268260) Key Sites Label 'Area 1'; APU Code '46'; FSR Additional
                                            Controls 'Area 1'; Acid Sulfate Class 'Class 5'
  45 Victoria Rd Rozelle   (propId 2830578) Key Sites 'Area 1' and 'Area 19'; no APU layer
  168 Norton St Leichhardt (propId 4256724) Key Sites 'Area 5' and 'Area 1'; Heritage Item Number 'C60'
  15 Dalhousie St Haberfield               Heritage Item Number 'C54'; Lot Size Map '500 m2'
  262 Liverpool Rd Ashfield                Heritage 'I269'; Height of Buildings Additional Controls 'Area 1'
  20 Smidmore St Marrickville              APU Code '44' and '49'
  1 Bedford Cres Dulwich Hill              layer 'Terrestrial Biodiversity Map', Class 'Biodiversity'

A condition is {layer, labels, zones, verified, source}:
  layer    the layerintersect layer name, or None when no portal layer holds the land (tidal land,
           the flood planning area, ANEF contours) -- those can never be confirmed and say so
  labels   map labels that satisfy it; None = any answer on that layer
  zones    zone codes the clause ALSO requires ("land in Zone E3 ... and identified as 'Area 20'")
  verified True when the portal has been SEEN returning this layer with labels. Only then does the
           layer's absence from a lot's answer mean "not this land"; otherwise absence is "could not
           confirm this land" and the rule stays visible.
No model reads anything: every condition comes from the clause's quoted words by regex, or from an
override below that quotes the words it rests on.
"""
import re
from typing import Iterable, Optional

from enrichment.config.inner_west_lep_config import INNER_WEST_LEP_CLAUSES, clause_key

#: The LEP's map name, as the clause words it -> the layer name layerintersect returns.
MAP_LAYER = {
    'key sites map': 'Key Sites Map',
    'additional permitted uses map': 'Additional Permitted Uses Map',
    'additional permitted use map': 'Additional Permitted Uses Map',  # cl 6.26 drops the 's'
    'lot size map': 'Lot Size Map',
    'height of buildings map': 'Height of Buildings Map',
    'floor space ratio map': 'Floor Space Ratio Map',
    'land reservation acquisition map': 'Land Reservation Acquisition Map',
    'heritage map': 'Heritage Map',
    'acid sulfate soils map': 'Acid Sulfate Soils Map',
    'natural resource-biodiversity map': 'Terrestrial Biodiversity Map',
    'foreshore building line map': 'Foreshore Building Line Map',
    'land application map': 'Land Application Map',
}

#: Layers the portal was seen returning, with labels, on a real Inner West lot (the module docstring
#: lists each). Foreshore Building Line, Land Reservation Acquisition and the Bays West label on the
#: Land Application Map were not seen: a lot without them reads "could not confirm", never "not here".
VERIFIED_LAYERS = frozenset({
    'Key Sites Map', 'Additional Permitted Uses Map', 'Heritage Map', 'Floor Space Ratio Map',
    'Height of Buildings Map', 'Lot Size Map', 'Acid Sulfate Soils Map', 'Terrestrial Biodiversity Map',
})

#: Clauses whose reach is a map area or a listed site. Every served row of these must carry a condition;
#: scripts/dq_probe_live.py DQ-140 counts the ones that do not. The rest of the 67 declined clauses
#: (2.6, 2.9, 3.1, 3.2, 5.4, 5.8, 5.12, 5.19, 5.20, 6.2, 6.7, 6.10-6.13, Schedules 2, 3, 6) are limited by
#: development type only, so showing them on every lot is right by land.
LAND_GATED_CLAUSES = (
    '2.5', '4.1', '4.1A', '4.3A', '4.3B', '4.3C', '4.4A', '5.1', '5.1A', '5.7', '5.10', '5.21', '5.22',
    '6.1', '6.4', '6.5', '6.6', '6.8', '6.14', '6.15', '6.16', '6.17', '6.18', '6.19', '6.20', '6.21',
    '6.22', '6.23', '6.24', '6.25', '6.26', '6.27', '6.30', '6.31', '6.33', '6.34', '7.2', '7.3', '7.4',
    '7.5', '8.2', 'Schedule 1', 'Schedule 5',
)

_DULWICH_GROVE = "Dulwich Grove land means the land identified as 'Area 14' on the Key Sites Map. (cl 7.1)"
_NO_LAYER = {
    '5.7': 'tidal land below mean high water mark is not a layerintersect layer',
    '5.21': 'the flood planning area is decided by the consent authority, not a map layer',
    '5.22': 'the flood planning area is decided by the consent authority, not a map layer',
    '6.8': 'ANEF contours are not in the layerintersect answer',
}

#: Clauses whose quote does not itself name the map, with the words the condition rests on instead.
_OVERRIDE = {
    '2.5': ('Additional Permitted Uses Map', None, None,
            'Development on particular land that is described or referred to in Schedule 1 (cl 2.5); '
            'Schedule 1 land is identified on the Additional Permitted Uses Map'),
    '5.10': ('Heritage Map', None, None,
             'a building, work, relic or tree within a heritage conservation area (cl 5.10); heritage items '
             'and conservation areas are identified on the Heritage Map'),
    '6.6': ('Foreshore Building Line Map', ['Foreshore Area'], None,
            "development in the foreshore area (cl 6.6); land identified as 'Foreshore Area' on the "
            'Foreshore Building Line Map (cl 6.5)'),
    '7.2': ('Key Sites Map', ['Area 14'], None, _DULWICH_GROVE),
    '7.3': ('Key Sites Map', ['Area 14'], None, _DULWICH_GROVE),
    '7.4': ('Key Sites Map', ['Area 14'], None, _DULWICH_GROVE),
    '7.5': ('Key Sites Map', ['Area 14'], None, _DULWICH_GROVE),
}

#: Read but not seen in a portal answer. 6.33's Land Application Map is verified, its Bays West label is not.
_UNVERIFIED_CLAUSES = frozenset({'6.33'})

#: Clauses whose map label does not identify the land on its own. Cl 6.26 names two Trafalgar St, Petersham
#: lots "identified as '46' on the Additional Permitted Use Map", but the portal returns APU '46' on
#: 10 Norton St, Leichhardt too (Schedule 1 item 46 covers E1 land widely). A label hit is therefore only
#: "could not confirm"; a lot without the label is still "not here". Proper fix: match the named Lot/DP.
_LABEL_NOT_UNIQUE = {
    '6.26': "APU '46' is also Schedule 1 item 46's label; the clause's land is Lot 1 DP 1208130 and "
            'Lot 10 DP 1004198 (287-309 Trafalgar St, Petersham), which the portal answer does not name',
}

_QUOTED = re.compile(r"[‘'“\"]\s*([^‘’'“”\"]+?)\s*[’'”\"]")
_MAP = re.compile(r'on the ([A-Z][A-Za-z ‐-―-]*?Map)\b')
_ZONE = re.compile(r'\bZone ([A-Z]{1,3}\d?)\b')


def _norm_map(name: str) -> str:
    return re.sub(r'\s+', ' ', re.sub(r'[‐-―]', '-', name)).strip().lower()


def condition(layer: Optional[str], labels: Optional[Iterable[str]], zones: Optional[Iterable[str]],
              source: str, verified: Optional[bool] = None) -> dict:
    """One land condition, in the shape stored on regulatory_provisions.v2_land_condition."""
    return {
        'layer': layer,
        'labels': sorted(set(labels)) if labels else None,
        'zones': sorted(set(zones)) if zones else None,
        'verified': bool(layer in VERIFIED_LAYERS) if verified is None else verified,
        'source': source,
    }


def condition_from_quote(quote: str) -> Optional[dict]:
    """The map, labels and zones a clause's own words name. None when the words name no map."""
    m = _MAP.search(quote or '')
    if not m:
        return None
    layer = MAP_LAYER.get(_norm_map(m.group(1)))
    if layer is None:
        raise ValueError(f'map not in MAP_LAYER: {m.group(1)!r}')
    before = quote[:m.start()]
    labels = _QUOTED.findall(before)
    zones = _ZONE.findall(before) if re.search(r'\bland in Zone\b', before) else []
    return condition(layer, labels or None, zones or None, quote)


def clause_condition(key: str) -> dict:
    """The land condition for one land-gated clause. Raises if the clause cannot be given one."""
    if key in _NO_LAYER:
        quote = INNER_WEST_LEP_CLAUSES[key]['scope_evidence'].get('applicable_zones', '')
        return condition(None, None, None, f'{quote} -- {_NO_LAYER[key]}', verified=False)
    if key in _OVERRIDE:
        layer, labels, zones, source = _OVERRIDE[key]
        return condition(layer, labels, zones, source)
    quote = INNER_WEST_LEP_CLAUSES[key]['scope_evidence'].get('applicable_zones', '')
    cond = condition_from_quote(quote)
    if cond is None:
        raise ValueError(f'clause {key}: its quote names no map and it has no override')
    if key in _UNVERIFIED_CLAUSES:
        cond['verified'] = False
    if key in _LABEL_NOT_UNIQUE:
        cond['label_not_unique'] = _LABEL_NOT_UNIQUE[key]
    return cond


# --- rows -----------------------------------------------------------------------------------------

_SCH1_HEADING = re.compile(r'^\s*(\d{1,2})\s+Use of certain land\b')
_SCH1_IDENTIFIED = re.compile(r'identified as\W{0,4}(\d{1,2})\W{0,4}on the Additional Permitted')
_SCH1_REF = re.compile(r'^(?:Schedule 1, )?Clause (\d{1,2})(?![.\d])')
_SCH5_CELL = re.compile(r'<td[^>]*>\s*([IA1]\d{2,5})\s*</td>')


def schedule5_items(table_html: str) -> list:
    """Heritage item numbers in one Schedule 5 table row, as the portal's Heritage Map names them.

    The stored tables are OCR of the PDF, which reads the 'I' that starts every item number as '1':
    the table's 1269 and 11123 are the portal's I269 (262 Liverpool Rd) and I1123 (6 Lords Rd).
    """
    out = []
    for cell in _SCH5_CELL.findall(table_html or ''):
        out.append('I' + cell[1:] if cell[0] == '1' else cell)
    return sorted(set(out))


def row_conditions(rows: list) -> dict:
    """{row id: condition} for one document's rows.

    `rows` are dicts with id, section_header, ref_number, provision_text -- ALL current rows of the
    document, served or not, because the Schedule 1 item headings are themselves not served. They are
    walked in id order, which is document order within one load.

    A Schedule 1 row takes its item from its own words when it has them ("identified as '46' on the
    Additional Permitted Uses Map"), else from its reference ("Clause 32(3)"), else from the nearest item
    heading above it ("46 Use of certain land ..."). A row whose nearest headed neighbours on BOTH sides
    are Schedule 1 is Schedule 1 whatever its own heading: row 23689 is item 46's list of uses but carries
    clause 7.4's heading. Unheaded rows (the item headings) only move the item while inside Schedule 1.
    """
    rows = sorted(rows, key=lambda r: r['id'])
    keys = [clause_key(r.get('section_header')) for r in rows]
    headed = [i for i, k in enumerate(keys) if k is not None]
    eff = list(keys)
    for n, i in enumerate(headed):
        if 0 < n < len(headed) - 1 and keys[i] != 'Schedule 1' \
                and keys[headed[n - 1]] == 'Schedule 1' and keys[headed[n + 1]] == 'Schedule 1':
            eff[i] = 'Schedule 1'

    out = {}
    item = None
    last = None
    for i, r in enumerate(rows):
        text = r.get('provision_text') or ''
        key = eff[i]
        if key is not None:
            if key != 'Schedule 1':
                item = None
            last = key
        if key == 'Schedule 1' or (key is None and last == 'Schedule 1'):
            m = (_SCH1_HEADING.match(text) or _SCH1_IDENTIFIED.search(text)
                 or _SCH1_REF.match(r.get('ref_number') or ''))
            if m:
                item = m.group(1)
        if key == 'Schedule 1':
            if item is None:
                out[r['id']] = condition(None, None, None,
                                         'Schedule 1 row whose item number could not be read', verified=False)
            else:
                out[r['id']] = condition('Additional Permitted Uses Map', [item], None,
                                         f'Schedule 1 item {item}: land identified as "{item}" on the '
                                         'Additional Permitted Uses Map')
            continue
        if key == 'Schedule 5':
            items = schedule5_items(text)
            out[r['id']] = condition('Heritage Map', items or None, None,
                                     'Schedule 5 heritage items ' + (', '.join(items) if items else
                                     '(no item number legible in this row): land on the Heritage Map'))
        elif key in LAND_GATED_CLAUSES:
            out[r['id']] = clause_condition(key)
    return out
