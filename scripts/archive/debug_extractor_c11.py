#!/usr/bin/env python3
import os, sys
sys.path.insert(0, '.')
from enrichment.extractors.numeric_extractor import NumericExtractor

text = """
ii. Side setback for new, detached secondary dwellings
a. For attached secondary dwellings the side setback controls
are the same as prescribed for attached dwellings, dwelling
houses and semi-attached dwellings at C10ii; and
b. For detached secondary dwellings where the secondary
dwelling is located at the rear, a minimum of 1.5 metres side
setback from allotment's side boundaries must be maintained
for the secondary dwelling.
iv. Rear setback for new, detached secondary dwellings
a. Where there is no rear lane, the rear setback controls are the
same as prescribed for attached dwellings, dwelling houses
and semi-attached dwellings at C10iii; and
v. The distance between a new detached secondary dwelling and
principal dwelling must:
a. Maintain a minimum separation distance of 4 metres between
the dwellings where the secondary dwelling is located at the
rear; and
b. Maintain a minimum separation distance of 1.8 metres
between the dwellings where the secondary dwelling is
located at the side.
vi. The height of a new, detached secondary dwelling, including the
conversion of an existing detached garage or other structure, is
limited to maximum two storeys in height
"""

extractor = NumericExtractor()
result = extractor.extract(text)
print('has_numeric:', result['has_numeric'])
print('values:')
for v in result['values']:
    print(' ', v)
