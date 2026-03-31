-- Migration 025: Leichhardt Distinctive Neighbourhood chapters -- TOC catch-all entries
--
-- Problem: 28 Part C Section 2 Distinctive Neighbourhood sub-chapters had no
--          dcp_table_of_contents entries. 210 provisions were unmatched (6% of total).
--          These chapters use absolute page numbers from a large combined PDF.
--
-- Fix: depth=0 catch-all per chapter, page_start/page_end = min/max pdf_page
--      from regulatory_provisions. Each chapter is one neighbourhood section.

BEGIN;

INSERT INTO dcp_table_of_contents
  (document_id, section_number, section_title, page_start, page_end, depth)
VALUES
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_1_Young_Street_Distinctive_Neighbourhood', 'C2.2.1.1', 'Young Street Distinctive Neighbourhood', 19, 25, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_2_Annandale_Street_Distinctive_Neighbourhood', 'C2.2.1.2', 'Annandale Street Distinctive Neighbourhood', 26, 31, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_3_Johnston_Street_Distinctive_Neighbourhood', 'C2.2.1.3', 'Johnston Street Distinctive Neighbourhood', 32, 39, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_4_Booth_Street_Distinctive_Neighbourhood', 'C2.2.1.4', 'Booth Street Distinctive Neighbourhood', 21, 43, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_5_Trafalgar_Street_Distinctive_Neighbourhood', 'C2.2.1.5', 'Trafalgar Street Distinctive Neighbourhood', 44, 49, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_6_Nelson_Street_Distinctive_Neighbourhood', 'C2.2.1.6', 'Nelson Street Distinctive Neighbourhood', 50, 59, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_7_Parramatta_Road_Commercial_Distinctive_Neighbourhood', 'C2.2.1.7', 'Parramatta Road Commercial Distinctive Neighbourhood', 21, 60, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_8_Camperdown_Distinctive_Neighbourhood', 'C2.2.1.8', 'Camperdown Distinctive Neighbourhood', 61, 63, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_1_Darling_Street_Distinctive_Neighbourhood', 'C2.2.2.1', 'Darling Street Distinctive Neighbourhood', 66, 75, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_2_Balmain_East_Distinctive_Neighbourhood', 'C2.2.2.2', 'Balmain East Distinctive Neighbourhood', 21, 134, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_3_Gladstone_Park_Distinctive_Neighbourhood', 'C2.2.2.3', 'Gladstone Park Distinctive Neighbourhood', 86, 90, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_4_The_Valley_Balmain_Distinctive_Neighbourhood', 'C2.2.2.4', 'The Valley Balmain Distinctive Neighbourhood', 21, 96, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_5_Mort_Bay_Distinctive_Neighbourhood', 'C2.2.2.5', 'Mort Bay Distinctive Neighbourhood', 21, 104, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_1_Excelsior_Estate_Distinctive_Neighbourhood', 'C2.2.3.1', 'Excelsior Estate Distinctive Neighbourhood', 115, 121, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_2_West_Leichhardt_Distinctive_Neighbourhood', 'C2.2.3.2', 'West Leichhardt Distinctive Neighbourhood', 123, 131, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_3_Piperston_Distinctive_Neighbourhood', 'C2.2.3.3', 'Piperston Distinctive Neighbourhood', 132, 137, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_4_Helsarmel_Distinctive_Neighbourhood', 'C2.2.3.4', 'Helsarmel Distinctive Neighbourhood', 139, 142, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_3_5_Leichhardt_Commercial_Distinctive_Neighbourhood', 'C2.2.3.5', 'Leichhardt Commercial Distinctive Neighbourhood', 143, 157, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_4_1_Catherine_Street_Distinctive_Neighbourhood', 'C2.2.4.1', 'Catherine Street Distinctive Neighbourhood', 160, 173, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_4_2_Nanny_Goat_Hill_Distinctive_Neighbourhood', 'C2.2.4.2', 'Nanny Goat Hill Distinctive Neighbourhood', 174, 184, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_4_3_Leichhardt_Park_Distinctive_Neighbourhood', 'C2.2.4.3', 'Leichhardt Park Distinctive Neighbourhood', 185, 193, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_4_4_Iron_Cove_Parklands_Distinctive_Neighbourhood', 'C2.2.4.4', 'Iron Cove Parklands Distinctive Neighbourhood', 194, 196, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_1_The_Valley_‘Rozelle’_Distinctive_Neighbourhood', 'C2.2.5.1', 'The Valley ‘Rozelle’ Distinctive Neighbourhood', 200, 205, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_2_Easton_Park_Distinctive_Neighbourhood', 'C2.2.5.2', 'Easton Park Distinctive Neighbourhood', 207, 209, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_3_Callan_Park_Distinctive_Neighbourhood', 'C2.2.5.3', 'Callan Park Distinctive Neighbourhood', 211, 212, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_4_Iron_Cove_Distinctive_Neighbourhood', 'C2.2.5.4', 'Iron Cove Distinctive Neighbourhood', 214, 215, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_5_Rozelle_Commercial_Distinctive_Neighbourhood', 'C2.2.5.5', 'Rozelle Commercial Distinctive Neighbourhood', 216, 223, 0),
  ('Leichhardt_DCP_2013_Part_C_Section_2_C2_2_5_6_Robert_Street_Industrial_Distinctive_Neighbourhood', 'C2.2.5.6', 'Robert Street Industrial Distinctive Neighbourhood', 225, 226, 0)
ON CONFLICT DO NOTHING;

COMMIT;
