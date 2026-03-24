-- Migration 011: Normalize dcp_table_of_contents.document_id for Marrickville
-- Purpose: Update TOC document_ids from the old section-numbering format to the
--          new-clean provision format used by regulatory_provisions.
--          Before this migration, enrichWithTocSections returns 0% TOC matches
--          for provisions with new-clean document_ids (Marrickville_DCP_2011__part*).
--          After this migration, the exact JOIN condition in enrichWithTocSections
--          matches directly without any normalization needed.
--
-- Direction: TOC → provision format (provisions are the authoritative source of record).
-- Safe to re-run: each UPDATE is idempotent (WHERE clause targets the old value).
--
-- Verified against provision document_ids in regulatory_provisions table 2026-03-21.

BEGIN;

-- ─────────────────────────────────────────────────────────────────
-- Part 1 — Statutory Information
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents
SET document_id = 'Marrickville_DCP_2011__part1_statutory_info'
WHERE document_id = 'Marrickville_DCP_2011__1__Statutory_Information_with_IWLEP_2022_amendments_Nov_22';

-- ─────────────────────────────────────────────────────────────────
-- Part 2 — General Controls (individual sections)
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s01_urban_design'
WHERE document_id = 'Marrickville_DCP_2011__2_1_Urban_Design';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s03_site_context_analysis'
WHERE document_id = 'Marrickville_DCP_2011__2_3_Site_Context_Analysis';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s05_equity_access_mobility'
WHERE document_id = 'Marrickville_DCP_2011__2_5_Equity_of_Access_and_Mobility';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s06_privacy'
WHERE document_id = 'Marrickville_DCP_2011__2_6_Acoustic_and_Visual_Privacy';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s07_solar_access'
WHERE document_id = 'Marrickville_DCP_2011__2_7_Solar_Access_and_Overshadowing';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s08_social_impact'
WHERE document_id = 'Marrickville_DCP_2011__2_8_Social_Impact_Assessment';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s09_community_safety'
WHERE document_id = 'Marrickville_DCP_2011__2_9_Community_Safety';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s10_parking'
WHERE document_id = 'Marrickville_DCP_2011__2_10_Parking';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s11_fencing'
WHERE document_id = 'Marrickville_DCP_2011__2_11_Fencing';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s12_signs'
WHERE document_id = 'Marrickville_DCP_2011__2_12_Signs_and_Advertising_Structures';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s13_biodiversity'
WHERE document_id = 'Marrickville_DCP_2011__2_13_Biodiversity';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s14_unique_env_features'
WHERE document_id = 'Marrickville_DCP_2011__2_14_Unique_Environmental_Features';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s16_energy_efficiency'
WHERE document_id = 'Marrickville_DCP_2011__2_16_Energy_Efficiency';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s17_water_sensitive'
WHERE document_id = 'Marrickville_DCP_2011__2_17_Water_Sensitive_Urban_Design';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s18_landscaping'
WHERE document_id = 'Marrickville_DCP_2011__2_18_Landscaping_and_Open_Spaces';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part2_s25_stormwater'
WHERE document_id = 'Marrickville_DCP_2011__2_25_Stormwater_management';

-- ─────────────────────────────────────────────────────────────────
-- Part 3 — Subdivision
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part3_subdivision'
WHERE document_id = 'Marrickville_DCP_2011__3_0Part3Subdivision_Amalgation_Movement_Network__with_IWLEP_2022_amendments';

-- ─────────────────────────────────────────────────────────────────
-- Part 4 — Residential Development
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part4_s1_low_density'
WHERE document_id = 'Marrickville_DCP_2011__4.1_Low_Density_Residential_Development';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part4_s2_multi_dwelling'
WHERE document_id = 'Marrickville_DCP_2011__4_2_Multi_Dwelling_Housing_and_RFBs__with_IWLEP_2022_amendments';

-- Note: two TOC entries map to the same provision chapter (duplicate upload).
-- Both are updated to the same target — page ranges won't conflict as they cover
-- different sections within the same chapter.
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part4_s3_boarding_houses'
WHERE document_id IN (
  'Marrickville_DCP_2011__4_3_Boarding_Houses',
  'Marrickville_DCP_2011__4_3_boarding_houses_(1)'
);

-- ─────────────────────────────────────────────────────────────────
-- Part 5 — Commercial and Mixed Use
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part5_commercial_mixed_use'
WHERE document_id = 'Marrickville_DCP_2011__5_0_Commercial_and_Mixed_Use_Development__with_IWLEP_2022_amendments';

-- ─────────────────────────────────────────────────────────────────
-- Part 6 — Industrial Development
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part6_industrial'
WHERE document_id = 'Marrickville_DCP_2011__6_0_Industrial_Development__with_IWLEP_2022_amendments';

-- ─────────────────────────────────────────────────────────────────
-- Part 7 — Special Uses
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part7_s1_childcare'
WHERE document_id = 'Marrickville_DCP_2011__7_1_childcare_centres__with_IWLEP_2022_amendments';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part7_s3_sex_industry'
WHERE document_id = 'Marrickville_DCP_2011__7.3_Sex_Industry_and_Adult_Business_Premises';

-- ─────────────────────────────────────────────────────────────────
-- Part 8 — Heritage
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part8_heritage'
WHERE document_id = 'Marrickville_DCP_2011__8.0_Heritage';

-- ─────────────────────────────────────────────────────────────────
-- Part 9 — Precinct Controls (intro + 48 precincts)
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_intro'
WHERE document_id = 'Marrickville_DCP_2011__9_0_Introduction';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p01_lewisham_north'
WHERE document_id = 'Marrickville_DCP_2011__9_1_Lewisham_North_Precinct_1';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p02_petersham_north'
WHERE document_id = 'Marrickville_DCP_2011__9_2_Petersham_North__with_IWLEP_2022_amendments';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p03_stanmore_north'
WHERE document_id = 'Marrickville_DCP_2011__9_3_Stanmore_North_Precinct_3';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p04_newtown_north'
WHERE document_id = 'Marrickville_DCP_2011__9_4_Newtown_North_and_Camperdown';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p05_lewisham_south'
WHERE document_id = 'Marrickville_DCP_2011__9_5_Lewisham_South_Precinct_5';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p06_petersham_south'
WHERE document_id = 'Marrickville_DCP_2011__9_6_Petersham_South_Precinct_6';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p07_stanmore_south'
WHERE document_id = 'Marrickville_DCP_2011__9_7_Stanmore_South';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p08_enmore_north'
WHERE document_id = 'Marrickville_DCP_2011__9_8_Enmore_North_and_Newtown_Central_Precinct_8';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p09_newington'
WHERE document_id = 'Marrickville_DCP_2011__9_9_Newington';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p10_dulwich_hill_north'
WHERE document_id = 'Marrickville_DCP_2011__9_10_Dulwich_Hill_North';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p11_hoskins_park'
WHERE document_id = 'Marrickville_DCP_2011__9_11_Hoskins_Park_Precinct_11';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p12_marrickville_park'
WHERE document_id = 'Marrickville_DCP_2011__9_12_Marrickville_Park_and_Morton_Park';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p13_henson_park'
WHERE document_id = 'Marrickville_DCP_2011__9_13_Henson_Park';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p14_camdenville'
WHERE document_id = 'Marrickville_DCP_2011__9_14_Camdenville_Precinct_14';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p15_enmore_park'
WHERE document_id = 'Marrickville_DCP_2011__9_15_Enmore_Park';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p16_abergeldie'
WHERE document_id = 'Marrickville_DCP_2011__9_16_Abergeldie_Estate';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p17_new_canterbury_rd'
WHERE document_id = 'Marrickville_DCP_2011__9_17_New_Canterbury_Road_West';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p18_dulwich_hill_stn_north'
WHERE document_id = 'Marrickville_DCP_2011__9_18_Dulwich_Hill_Station_North';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p19_marrickville_rd_central'
WHERE document_id = 'Marrickville_DCP_2011__9_19_Marrickville_Road_Central';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p20_marrickville_tc_north'
WHERE document_id = 'Marrickville_DCP_2011__9_20_Marrickville_Town_Centre_North';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p21_ness_park'
WHERE document_id = 'Marrickville_DCP_2011__9_21_Ness_Park';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p22_dulwich_hill_stn_south'
WHERE document_id = 'Marrickville_DCP_2011__9_22_Dulwich_Hill_Station_South_Precinct_22';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p23_marrickville_stn_west'
WHERE document_id = 'Marrickville_DCP_2011__9_23_Marrickville_Station_West_Precinct_23';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p24_marrickville_tc_south'
WHERE document_id = 'Marrickville_DCP_2011__9_24_Marrickville_Town_Centre_South';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p25_st_peters_triangle'
WHERE document_id = 'Marrickville_DCP_2011__9_25_St_Peters_Triangle_Precinct_25';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p26_barwon_park'
WHERE document_id = 'Marrickville_DCP_2011__9_26_Barwon_Park';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p27_barwon_park_south'
WHERE document_id = 'Marrickville_DCP_2011__9_27_Barwon_Park_South';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p28_cooks_river_west'
WHERE document_id = 'Marrickville_DCP_2011__9_28_Cooks_River_West';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p29_sw_marrickville'
WHERE document_id = 'Marrickville_DCP_2011__9_29_South_Western_Marrickville';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p30_the_warren'
WHERE document_id = 'Marrickville_DCP_2011__9_30_The_Warren';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p31_unwins_bridge'
WHERE document_id = 'Marrickville_DCP_2011__9_31_Unwins_Bridge_Road';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p32_cooks_river_east'
WHERE document_id = 'Marrickville_DCP_2011__9_32_Cooks_River_East';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p33_princes_highway'
WHERE document_id = 'Marrickville_DCP_2011__9_33_Princes_Highway';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p34_tempe_reserve'
WHERE document_id = 'Marrickville_DCP_2011__9_34_Tempe_Reserve';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p35_parramatta_rd'
WHERE document_id = 'Marrickville_DCP_2011__9_35_Parramatta_Road';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p36_petersham_commercial'
WHERE document_id = 'Marrickville_DCP_2011__9_36_Petersham_Commercial_Precinct_36__with_IWLEP_2022_amendments';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p37_king_st_enmore'
WHERE document_id = 'Marrickville_DCP_2011__9_37_King_Street_and_Enmore_Road_Commercial_Precinct';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p38_dulwich_hill_commercial'
WHERE document_id = 'Marrickville_DCP_2011__9_38_Dulwich_Hill_Commercial_Precinct_38__with_IWLEP_2022_amendments';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p39_marrickville_metro'
WHERE document_id = 'Marrickville_DCP_2011__9_39_Marrickville_Metro';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p40_marrickville_tc_commercial'
WHERE document_id = 'Marrickville_DCP_2011__9_40_Marrickville_Town_Centre_Comm_Precinct_40__with_IWLEP_2022_amendments';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p41_bridge_road'
WHERE document_id = 'Marrickville_DCP_2011__9_41_Bridge_Road';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p42_camperdown_north'
WHERE document_id = 'Marrickville_DCP_2011__9_42_Camperdown_North';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p43_sydney_steel'
WHERE document_id = 'Marrickville_DCP_2011__9.43_Sydney_Steel_Precinct_43';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p44_carrington_road'
WHERE document_id = 'Marrickville_DCP_2011__9_44_Carrington_Road';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p45_mcgill_st'
WHERE document_id = 'Marrickville_DCP_2011__9_45_McGill_Street_Precinct_45';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p46_tempe_lands'
WHERE document_id = 'Marrickville_DCP_2011__9_46_Tempe_Lands_Precinct';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p47_victoria_road'
WHERE document_id = 'Marrickville_DCP_2011__9_47_Victoria_Road';

UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part9_p48_mary_robert_edith'
WHERE document_id = 'Marrickville_DCP_2011__9.48_Mary_Robert_and_Edith_Street_Nov_22';

-- ─────────────────────────────────────────────────────────────────
-- Part 10 — Definitions
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__part10_definitions'
WHERE document_id = 'Marrickville_DCP_2011__10.0_Definitions';

-- ─────────────────────────────────────────────────────────────────
-- DA Guidelines
-- ─────────────────────────────────────────────────────────────────
UPDATE dcp_table_of_contents SET document_id = 'Marrickville_DCP_2011__da_guidelines'
WHERE document_id = 'Marrickville_DCP_2011__Development_Application_Guidelines_with_IWLEP_2022_amendments_Nov_22';

COMMIT;
