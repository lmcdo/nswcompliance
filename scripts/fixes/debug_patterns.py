#!/usr/bin/env python3
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
import os
import psycopg2

SECTION_OFFSETS = {
    '2_10_Parking': 4,
    '2_11_Fencing': 4,
    '2_12_Signs_and_Advertising': 4,
    '2_13_Biodiversity': 4,
    '2_14_Unique_Environmental_': 4,
    '2_16_Energy_Efficiency': 4,
    '2_1_Urban_Design': 4,
    '2_5_Equity_of_Access_and_M': 4,
    '2_6_Acoustic_and_Visual_Pr': 4,
    '2_7_Solar_Access_and_Overs': 4,
    '2_8_Social_Impact_Assessme': 4,
    '2_9_Community_Safety': 4,
    '4.1_Low_Density_Residentia': 6,
    '4_2_Multi_Dwelling_Housing': 4,
    '4_3_Boarding_Houses': 4,
    '5_0_Commercial_and_Mixed_U': 4,
    '6_0_Industrial_Development': 4,
    '7.3_Sex_Industry_and_Adult': 4,
    '7_1_childcare_centres_-_wi': 6,
    '8.0_Heritage': -48,
    '8.0_Heritage_-_Part1_(page': 14,
    '8.0_Heritage_-_Part2_(page': -48,
    '8.0_Heritage_-_Part4_(page': 7,
    '2_17_Water_Sensitive_Urban': 4,
    '2_25_Stormwater_management': 4,
    '2_3_Site_Context_Analysis': 4,
    '3_0Part3Subdivision,_Amalg': 4,
}

conn = psycopg2.connect(os.environ['DATABASE_URL'])
cur = conn.cursor()

cur.execute("""
    SELECT DISTINCT pdf_page_image_url
    FROM regulatory_provisions
    WHERE document_id LIKE '%Marrickville%'
      AND pdf_page_image_url LIKE '%page_5.%'
    LIMIT 30
""")

print('Checking URL patterns for page_5:')
for (url,) in cur.fetchall():
    matched = False
    for pattern in SECTION_OFFSETS:
        if pattern in url:
            matched = True
            print(f'  MATCHED: {pattern}')
            break
    if not matched:
        print(f'  NO MATCH: {url[-60:]}')

conn.close()
