#!/usr/bin/env python3
"""
Multi-study flood shapefile ingest into spatial_overlays.

Downloads, inspects, and ingests flood extent shapefiles from the NSW Flood
Data Portal (flooddata.ses.nsw.gov.au) for priority Greater Sydney LGAs.
Also ingests locally available shapefiles (e.g. Hawkesbury FPA from Nona Ruddell).

Studies covered:
  hawkesbury_fpa -- Hawkesbury FRMSP 2025 Flood Planning Area (binary FPA mask)
  campbelltown   -- Campbelltown Design Flood Extents (Campbelltown / Camden)
  narellan       -- Narellan Creek Flood Study Extents (Camden)
  greendale      -- Greendale Creek Flood Study GIS Layers (Northern Beaches)
  south_creek_hc -- Updated South Creek Flood Study Hydraulic Categories (Penrith)

Usage:
  python scripts/ingest_flood_studies.py --inspect              # show column names only
  python scripts/ingest_flood_studies.py --study all            # ingest all studies
  python scripts/ingest_flood_studies.py --study hawkesbury_fpa # single study
  python scripts/ingest_flood_studies.py --study campbelltown   # single study
  python scripts/ingest_flood_studies.py --dry-run --study all  # parse without DB insert

AEP column detection (in priority order):
  Column names containing AEP, ARI, FLOOD_CAT, SCENARIO, CATEGORY, CLASS are inspected.
  If a study has one shapefile per AEP scenario (Hawkesbury pattern), scenario is
  parsed from the filename instead.
  aep_source="fixed" uses the fixed_scenario value directly (e.g. for FPA binary masks).

  Campbelltown filename convention: 0p2AEP_Extent.shp (p = decimal point).

download_type options:
  "zip"   -- single ZIP file; all .shp files inside are candidates
  "local" -- shapefile already downloaded; local_path must point to the .shp file

Adding new studies:
  Register a download_type="zip" entry in STUDIES with the direct /download/<file> URL
  from flooddata.ses.nsw.gov.au. Resource page URLs (without /download/) return HTML
  and require portal authentication -- only uploaded files have working direct URLs.
  For locally available data use download_type="local" with an absolute local_path.
"""

import argparse
import json
import os
import re
import sys
import time
import zipfile
from datetime import date
from pathlib import Path
from typing import Optional

import geopandas as gpd
import psycopg2
import requests
from dotenv import load_dotenv
from psycopg2.extras import execute_values

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
load_dotenv()

CACHE_DIR = project_root / "data" / "flood_studies"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Study manifest
# ---------------------------------------------------------------------------
# download_type:
#   "zip"       -- single ZIP file; all .shp files inside are candidates
#   "shp_parts" -- individual SHP component files (SHP + SHX + DBF + PRJ + CPG)
#
# aep_source:
#   "column"    -- AEP scenario stored in a column (col name = aep_col)
#   "filename"  -- one shapefile per AEP scenario; parse from filename
#
# Note: only direct /download/<filename> URLs work without auth.
# Resource page URLs (no /download/) return HTML -- those studies are marked
# with a comment and will fail gracefully.
# ---------------------------------------------------------------------------
STUDIES = {
    "hawkesbury_fpa": {
        "label": "Hawkesbury FRMSP 2025 — Flood Planning Area (binary mask)",
        "lga_names": ["HAWKESBURY"],
        "currency_date": date(2025, 1, 1),
        "instrument_prefix": "HFRMS_2025",
        # Shapefile provided directly by NSW Reconstruction Authority (Nona Ruddell).
        # 188 features, EPSG:7856, VALUE=1.0 binary mask (no AEP breakdown).
        # Place at: data/flood_studies/hawkesbury_fpa/FPL_clipped_LGA_mapping_extent.shp
        # Or point local_path to the original download location.
        "download_type": "local",
        "local_path": "C:/Users/lawre/Downloads/ses flood data/hfrms2025-fpa/FPL_clipped_LGA_mapping_extent.shp",
        # Fixed scenario — the whole shapefile is the FPA boundary (no per-polygon AEP)
        "aep_source": "fixed",
        "fixed_scenario": "flood_planning_area",
        "fixed_ari": None,
    },
    "epi_statewide": {
        "label": "NSW EPI Statewide Flood Layer (OEH BIS Data Broker, 30 Apr 2026)",
        # 10 LGAs: Bathurst, Clarence Valley, Forbes, Hornsby, Mid-Western Regional,
        # Tamworth, Wentworth, Wingecarribee, Wollongong, Yass Valley.
        # Not a complete NSW dataset — ~10 LGAs not covered by EPI REST Layer 1.
        # LAY_CLASS values vary: "Flood Planning Area", "Flood Prone and Major Creeks Land",
        # "1 in 100 AEP Flood Extent", "Level of Probable Maximum Flood", etc.
        # LGA_NAME comes from each row, not a single config value.
        "lga_names": ["MULTIPLE"],  # placeholder — actual LGA read from each row
        "currency_date": None,      # read from CURRENCY_D column per row
        "instrument_prefix": "EPI_STATEWIDE",
        "download_type": "local",
        "local_path": "C:/Users/lawre/Downloads/ses flood data/All_EPI_Data_Shapefile_GDA2020_30042026/All_EPI_Data_Shapefile_GDA2020_30042026/EPI_Flood.shp",
        # Each row has its own LAY_CLASS and LGA_NAME — use specialised ingest path
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "campbelltown": {
        "label": "Campbelltown Design Flood Extents",
        "lga_names": ["CAMPBELLTOWN", "CAMDEN"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "CTFS_2023",
        "download_type": "zip",
        # Direct download confirmed working (no auth required)
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/7a412d28-4699-456c-b7d0-98b28f11ba29/resource/b5675efa-b0d0-4ac4-b8f2-173b1ef409a0/download/flood-extents.zip",
        # One shapefile per AEP: 0p2AEP_Extent.shp, 1AEP_Extent.shp, PMF_Extent.shp
        "aep_source": "filename",
        "aep_col": None,
    },
    "narellan": {
        "label": "Narellan Creek Flood Study Flood Extents (Camden)",
        "lga_names": ["CAMDEN", "CAMPBELLTOWN"],
        "currency_date": date(2023, 9, 1),
        "instrument_prefix": "NCFS_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login, will fail with HTML error
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/14509edb-c3df-4099-8d09-af60d9930d81/resource/acd7362b-d57c-48d6-bb4e-da3b72578119",
        "aep_source": "filename",
        "aep_col": None,
    },
    "greendale": {
        "label": "Greendale Creek Flood Study GIS Layers (Northern Beaches)",
        "lga_names": ["NORTHERN BEACHES"],
        "currency_date": date(2023, 9, 1),
        "instrument_prefix": "GCFS_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/0756443e-b207-4120-9d8a-8a00cebe8820/resource/b66856ce-003a-4898-821b-892b40009a23",
        "aep_source": "filename",
        "aep_col": None,
    },
    "south_creek_hc": {
        "label": "Updated South Creek Flood Study Hydraulic Categories (Penrith)",
        "lga_names": ["PENRITH", "HAWKESBURY", "BLACKTOWN"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "SCFS_HC_2023",
        "download_type": "zip",
        # Resource page URL -- requires portal login
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/b0576482-7d66-4788-b4fa-cf612cb996c8/resource/19a8343c-50d2-4cb5-978b-6131af0fff8e",
        "aep_source": "column",
        "aep_col": None,
    },

    # -------------------------------------------------------------------------
    # ArcGIS FeatureServer studies — free public services, no auth required.
    # outSR=4326 requested so server reprojects to WGS84 before returning.
    # Run: python scripts/ingest_flood_studies.py --study <key> --inspect-featureserver
    # to preview layer field names before committing to full ingest.
    # All URLs confirmed anonymous-queryable May 2026.
    # -------------------------------------------------------------------------

    # Byron Shire — ras_byron account, anonymous-queryable.
    # Only one layer (id=3): FPL at 1:100 ARI + 0.5m freeboard + CC to 2100.
    # Fields: OBJECTID, Id, Shape__Area, Shape__Length — binary FPA mask, no AEP col.
    # GIS_GISDATA_flood service is identical data — skip it.
    "byron_fpa": {
        "label": "Byron Shire — Future Flood Planning Level FPA (ArcGIS FeatureServer)",
        "lga_names": ["BYRON"],
        "currency_date": None,
        "instrument_prefix": "BYRON_FPA",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services7.arcgis.com/SqbRuGmmUbhRpdi1/arcgis/rest/services/Flood_Planning_Area/FeatureServer",
        "layer_id": 3,          # confirmed: only layer in service
        "aep_source": "fixed",
        "fixed_scenario": "flood_planning_area",
        "fixed_ari": None,
    },

    # Tweed Shire — gis_tweed account.
    # FloodingData service: 12 layers.
    #   Layers 1/6/11 are "Inundation Areas" with LOWER/UPPER flood level bands (m AHD),
    #   NOT discrete AEP scenarios — contour-band polygons showing inundation depth ranges.
    #   Layer 8 = "ARI 100 year (AEP 1%) flood" — the directly useful FPA/flood extent.
    #   Fields: Object_ID, LOWER, UPPER, Shape__Area, Shape__Length.
    # tweed_dcp_flood: Design Flood Inundation Areas (layer 1) — same LOWER/UPPER structure.
    #   "Design Flood" = 1% AEP per NSW DCP standard (Tweed DCP TV09 + Coastal Creeks 2010).
    "tweed_flood": {
        "label": "Tweed Shire — ARI 100yr (1%AEP) flood extent (ArcGIS FeatureServer)",
        "lga_names": ["TWEED"],
        "currency_date": None,
        "instrument_prefix": "TWEED_1PCT",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services1.arcgis.com/KURAxOhGWn5RdCPg/arcgis/rest/services/FloodingData/FeatureServer",
        "layer_id": 8,          # confirmed: 'ARI 100 year (AEP 1%) flood'
        "aep_source": "fixed",
        "fixed_scenario": "1%AEP",
        "fixed_ari": 100,
    },
    "tweed_dcp_flood": {
        "label": "Tweed Shire — DCP Design Flood Inundation Areas TV09/CC10 (ArcGIS FeatureServer)",
        "lga_names": ["TWEED"],
        "currency_date": None,
        "instrument_prefix": "TWEED_DCP",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services1.arcgis.com/KURAxOhGWn5RdCPg/arcgis/rest/services/Flooding_ExistingDCP_TV09_CC10/FeatureServer",
        "layer_id": 1,          # confirmed: 'Design Flood Inundation Areas'
        "aep_source": "fixed",
        # "Design flood" in Tweed DCP TV09/CC10 = 1%AEP per NSW planning standard.
        "fixed_scenario": "design_flood",
        "fixed_ari": 100,
    },

    # Port Macquarie-Hastings — confirmed public, council-authored.
    # Data broker: Jennifer Lang <jennifer.lang@pmhc.nsw.gov.au>
    # Contact before commercial use to confirm licence terms.
    # Two layers: layer 0 = FPA (binary), layer 1 = PMF (binary).
    # Both have no AEP column — binary masks only.
    "pmhc_flood": {
        "label": "Port Macquarie-Hastings — Flood Planning Area layer 0 (ArcGIS FeatureServer)",
        "lga_names": ["PORT MACQUARIE-HASTINGS"],
        "currency_date": None,
        "instrument_prefix": "PMHC_FPA",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services5.arcgis.com/apQoc7QtDZkPPGVg/arcgis/rest/services/Flood_Planning_Info/FeatureServer",
        "layer_id": 0,          # confirmed: 'Flood Planning Area'
        "aep_source": "fixed",
        "fixed_scenario": "flood_planning_area",
        "fixed_ari": None,
    },
    "pmhc_pmf": {
        "label": "Port Macquarie-Hastings — Probable Maximum Flood layer 1 (ArcGIS FeatureServer)",
        "lga_names": ["PORT MACQUARIE-HASTINGS"],
        "currency_date": None,
        "instrument_prefix": "PMHC_PMF",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services5.arcgis.com/apQoc7QtDZkPPGVg/arcgis/rest/services/Flood_Planning_Info/FeatureServer",
        "layer_id": 1,          # confirmed: 'Probable Maximum Flood'
        "aep_source": "fixed",
        "fixed_scenario": "PMF",
        "fixed_ari": None,
    },

    # Hawkesbury City Council — hsc_dave account.
    # HSC_Flooding_LAYERS: layer 1 = 1%AEP categorized extent (confirmed: FID, Join_Count, Evaluated).
    # No AEP column — the scenario is the layer itself.
    # Also has CSIRO sea level rise scenarios (layers 4-6) and 2010 flood event (layer 7).
    # Complements hawkesbury_fpa (FPA boundary shapefile from Nona Ruddell).
    "hawkesbury_council_flood": {
        "label": "Hawkesbury City Council — 1%AEP Flood Extent Categorized (ArcGIS FeatureServer)",
        "lga_names": ["HAWKESBURY"],
        "currency_date": None,
        "instrument_prefix": "HAWK_1PCT",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services6.arcgis.com/VKqP0BP08pVXloHq/arcgis/rest/services/HSC_Flooding_LAYERS/FeatureServer",
        "layer_id": 1,          # confirmed: '1pc_AEP_Flood_Extent_Categorized'
        "aep_source": "fixed",
        "fixed_scenario": "1%AEP",
        "fixed_ari": 100,
    },

    # NSW Flood Risk EPI overlay — same field structure as EPI_Flood.shp from OEH data broker.
    # Fields: EPI_NAME, LGA_CODE, LGA_NAME, LAY_CLASS, CURRENCY_D — routed to _ingest_epi_statewide().
    # Filtered by where_clause per LGA (single FeatureServer covers all NSW EPI flood areas).
    "lismore_epi_flood": {
        "label": "Lismore — NSW EPI Flood Risk (ArcGIS FeatureServer, filtered by LGA)",
        "lga_names": ["LISMORE"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_LISMORE",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='LISMORE'",
        # Field structure identical to EPI shapefile — use same ingest path.
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "ballina_epi_flood": {
        "label": "Ballina — NSW EPI Flood Risk (ArcGIS FeatureServer, filtered by LGA)",
        "lga_names": ["BALLINA"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_BALLINA",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='BALLINA'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },

    # ---------------------------------------------------------------------------
    # NSW_Flood_Risk FeatureServer — batch expansion (confirmed 2026-05-01)
    # Same service as Lismore/Ballina above. 70 LGAs in layer 0.
    # Each entry filters by LGA_NAME. Field structure: EPI_NAME, LGA_NAME, LAY_CLASS, CURRENCY_D.
    # All routed to _ingest_epi_statewide(). Polygon counts from statistics query.
    # LGAs already ingested via EPI shapefile or other FeatureServers are excluded.
    # ---------------------------------------------------------------------------
    "shoalhaven_epi_flood": {
        "label": "Shoalhaven — NSW EPI Flood Risk FeatureServer (862 polygons)",
        "lga_names": ["SHOALHAVEN"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_SHOALHAVEN",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='SHOALHAVEN'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "lake_macquarie_epi_flood": {
        "label": "Lake Macquarie — NSW EPI Flood Risk FeatureServer (530 polygons)",
        "lga_names": ["LAKE MACQUARIE"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_LAKE_MACQUARIE",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='LAKE MACQUARIE'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "woollahra_epi_flood": {
        "label": "Woollahra — NSW EPI Flood Risk FeatureServer (370 polygons)",
        "lga_names": ["WOOLLAHRA"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_WOOLLAHRA",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='WOOLLAHRA'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "georges_river_epi_flood": {
        "label": "Georges River — NSW EPI Flood Risk FeatureServer (191 polygons)",
        "lga_names": ["GEORGES RIVER"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_GEORGES_RIVER",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='GEORGES RIVER'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "midcoast_epi_flood": {
        "label": "MidCoast — NSW EPI Flood Risk FeatureServer (152 polygons)",
        "lga_names": ["MID-COAST"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_MIDCOAST",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='MID-COAST'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "inner_west_epi_flood": {
        "label": "Inner West — NSW EPI Flood Risk FeatureServer (115 polygons)",
        "lga_names": ["INNER WEST"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_INNER_WEST",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='INNER WEST'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "hilltops_epi_flood": {
        "label": "Hilltops — NSW EPI Flood Risk FeatureServer (74 polygons)",
        "lga_names": ["HILLTOPS"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_HILLTOPS",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='HILLTOPS'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "canterbury_bankstown_epi_flood": {
        "label": "Canterbury-Bankstown — NSW EPI Flood Risk FeatureServer (55 polygons)",
        "lga_names": ["CANTERBURY-BANKSTOWN"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_CANTERBURY_BANKSTOWN",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='CANTERBURY-BANKSTOWN'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "sutherland_epi_flood": {
        "label": "Sutherland Shire — NSW EPI Flood Risk FeatureServer (51 polygons)",
        "lga_names": ["SUTHERLAND SHIRE"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_SUTHERLAND",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='SUTHERLAND SHIRE'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "ryde_epi_flood": {
        "label": "Ryde — NSW EPI Flood Risk FeatureServer (42 polygons)",
        "lga_names": ["RYDE"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_RYDE",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='RYDE'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "cumberland_epi_flood": {
        "label": "Cumberland — NSW EPI Flood Risk FeatureServer (42 polygons)",
        "lga_names": ["CUMBERLAND"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_CUMBERLAND",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='CUMBERLAND'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "maitland_epi_flood": {
        "label": "Maitland — NSW EPI Flood Risk FeatureServer (23 polygons)",
        "lga_names": ["MAITLAND"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_MAITLAND",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='MAITLAND'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "parramatta_epi_flood": {
        "label": "City of Parramatta — NSW EPI Flood Risk FeatureServer (22 polygons)",
        "lga_names": ["CITY OF PARRAMATTA"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_PARRAMATTA",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='CITY OF PARRAMATTA'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "dungog_epi_flood": {
        "label": "Dungog — NSW EPI Flood Risk FeatureServer (11 polygons)",
        "lga_names": ["DUNGOG"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_DUNGOG",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='DUNGOG'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "liverpool_epi_flood": {
        "label": "Liverpool — NSW EPI Flood Risk FeatureServer (9 polygons)",
        "lga_names": ["LIVERPOOL"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_LIVERPOOL",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='LIVERPOOL'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "sydney_epi_flood": {
        "label": "City of Sydney — NSW EPI Flood Risk FeatureServer (6 polygons)",
        "lga_names": ["SYDNEY"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_SYDNEY",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='SYDNEY'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "queanbeyan_epi_flood": {
        "label": "Queanbeyan-Palerang Regional — NSW EPI Flood Risk FeatureServer (6 polygons)",
        "lga_names": ["QUEANBEYAN-PALERANG REGIONAL"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_QUEANBEYAN",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='QUEANBEYAN-PALERANG REGIONAL'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "singleton_epi_flood": {
        "label": "Singleton — NSW EPI Flood Risk FeatureServer (3 polygons)",
        "lga_names": ["SINGLETON"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_SINGLETON",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='SINGLETON'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },
    "penrith_epi_flood": {
        "label": "Penrith — NSW EPI Flood Risk FeatureServer (1 polygon; SES portal ZIPs are 403-gated)",
        "lga_names": ["PENRITH"],
        "currency_date": None,
        "instrument_prefix": "NSW_FLOOD_RISK_PENRITH",
        "download_type": "arcgis_featureserver",
        "base_url": "https://services-ap1.arcgis.com/s047i49VH0D2nqIM/arcgis/rest/services/NSW_Flood_Risk/FeatureServer",
        "layer_id": 0,
        "where_clause": "LGA_NAME='PENRITH'",
        "aep_source": "epi_statewide",
        "aep_col": "LAY_CLASS",
    },

    # Penrith South Creek — SES portal downloads.
    # Both URLs return 403 (portal requires login even for direct /download/ links).
    # Manual workaround: download via browser, drop ZIP in data/flood_studies/penrith_fpa/
    # and data/flood_studies/penrith_extents/, then re-run with --study penrith_fpa.
    "penrith_fpa": {
        "label": "Penrith South Creek — Flood Planning Area (SES portal, manual download required)",
        "lga_names": ["PENRITH"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "PENRITH_FPA",
        "download_type": "zip",
        # 403 Forbidden — portal requires auth. Download manually and drop ZIP here.
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/bbced83f-2a91-4983-b773-2efeb0709a5d/resource/406c8e42-ded2-428c-b73a-1a1375586ea4/download/flood-planning-area.zip",
        "aep_source": "fixed",
        "fixed_scenario": "flood_planning_area",
        "fixed_ari": None,
    },
    "penrith_extents": {
        "label": "Penrith South Creek — GIS Flood Extents (SES portal, manual download required)",
        "lga_names": ["PENRITH", "HAWKESBURY", "BLACKTOWN"],
        "currency_date": date(2023, 9, 12),
        "instrument_prefix": "PENRITH_EXTENTS",
        "download_type": "zip",
        # 403 Forbidden — portal requires auth. Download manually and drop ZIP here.
        "zip_url": "https://flooddata.ses.nsw.gov.au/dataset/bbced83f-2a91-4983-b773-2efeb0709a5d/resource/4617fafc-a32b-4a4d-bc6a-29aab141ba7d/download/gis-extents.zip",
        "aep_source": "filename",
        "aep_col": None,
    },
}

# AEP numeric (%) -> ARI (years) lookup for value_numeric field
AEP_TO_ARI = {
    "50": 2, "20": 5, "10": 10, "5": 20,
    "2": 50, "1": 100, "0.5": 200, "0.2": 500,
    "0.1": 1000,
}

# Column name patterns indicating AEP scenario (checked case-insensitively)
AEP_COL_PATTERNS = ["aep", "ari", "flood_cat", "scenario", "category", "class", "rp", "recurrence"]

_AEP_CLEAN = re.compile(r"(\d+(?:\.\d+)?)\s*%?\s*(?:AEP|aep)?", re.IGNORECASE)


def _normalise_aep(raw: str) -> tuple[str, Optional[float]]:
    """
    Normalise AEP raw value to (label, ari_years).

    Input forms:
      "PMF"        -> ("PMF", None)
      "100AEP"     -> ARI=100yr -> ("1.0%AEP", 100)   [Hawkesbury: ARI-based]
      "1AEP"       -> AEP%=1%  -> ("1%AEP", 100)       [Campbelltown: already AEP%]
      "0.2AEP"     -> ("0.2%AEP", 500)
      "1% AEP"     -> ("1%AEP", 100)

    Disambiguation: values >= 50 treated as ARI; values < 50 as AEP%.
    """
    raw = str(raw).strip()
    if "pmf" in raw.lower() or "probable" in raw.lower():
        return "PMF", None
    # Pass through non-AEP fixed scenarios (e.g. "flood_planning_area")
    if re.match(r"^[a-z_]+$", raw.lower()) and not re.search(r"\d", raw):
        return raw, None
    # Match XAEp or X.XAEP (normalised internal form from filename parsing)
    m = re.match(r"^(\d+(?:\.\d+)?)AEP$", raw, re.IGNORECASE)
    if m:
        val = float(m.group(1))
        if val >= 50:
            # ARI-based (Hawkesbury): ARI=val, pct=100/val
            ari = val
            pct = round(100.0 / ari, 4)
        else:
            # AEP%-based (Campbelltown): pct=val, ARI=100/val
            pct = val
            ari = round(100.0 / pct, 1) if pct > 0 else None
        return f"{pct}%AEP", ari
    # Handle "1% AEP", "1%AEP", "1 AEP" (column values)
    m = _AEP_CLEAN.match(raw)
    if m:
        pct = m.group(1)
        ari = AEP_TO_ARI.get(pct)
        return f"{pct}%AEP", float(ari) if ari else None
    return raw, None


def _detect_aep_col(gdf) -> Optional[str]:
    cols = [c for c in gdf.columns if c.lower() != "geometry"]
    for pat in AEP_COL_PATTERNS:
        for col in cols:
            if pat in col.lower():
                return col
    return None


def _query_featureserver(base_url: str, layer_id: int, where: str, bbox: Optional[list] = None) -> list[dict]:
    """Single query to a FeatureServer, with optional spatial bbox filter.

    Returns raw GeoJSON feature list. Retries up to 3 times on HTTP 500.
    Spatial filter uses inSR=4326 (WGS84 bbox coordinates).
    """
    params: dict = {
        "where": where,
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "resultOffset": 0,
        "resultRecordCount": 1000,
        "f": "geojson",
    }
    if bbox is not None:
        params.update({
            "geometry": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
            "geometryType": "esriGeometryEnvelope",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
        })
    url = f"{base_url}/{layer_id}/query"
    for attempt in range(3):
        r = requests.get(url, params=params, timeout=60)
        if r.status_code == 500:
            wait = 10 * (attempt + 1)
            print(f"    [warn] 500 from FeatureServer (attempt {attempt + 1}/3) — retrying in {wait}s ...")
            time.sleep(wait)
            continue
        r.raise_for_status()
        return r.json().get("features", [])
    print(f"    [skip] 500 after 3 retries — bbox={bbox}")
    return []


def _bbox_from_features(features: list[dict]) -> Optional[list[float]]:
    """Compute WGS84 bounding box from GeoJSON feature list (used to seed bbox-split)."""
    lngs: list[float] = []
    lats: list[float] = []
    for f in features:
        geom = f.get("geometry") or {}
        gtype = geom.get("type", "")
        coords = geom.get("coordinates") or []
        try:
            rings = coords if gtype == "MultiPolygon" else [coords]
            for poly in rings:
                for pt in (poly[0] if poly else []):
                    lngs.append(float(pt[0]))
                    lats.append(float(pt[1]))
        except (IndexError, TypeError, ValueError):
            continue
    if not lngs:
        return None
    pad = 0.05  # ~5 km
    return [min(lngs) - pad, min(lats) - pad, max(lngs) + pad, max(lats) + pad]


def _fetch_all_bbox(base_url: str, layer_id: int, where: str,
                    bbox: Optional[list] = None, depth: int = 0) -> list[dict]:
    """Recursively fetch all features via bbox quadrant-split when server caps at 1000.

    ArcGIS Online free tier silently truncates at 1000 features per query without
    setting exceededTransferLimit. This recursively splits the bbox into quadrants
    until each quadrant returns < 1000 features, guaranteeing full coverage.

    Max recursion depth = 8 (2^8 = 256 quadrants → handles datasets up to ~250k features).
    """
    features = _query_featureserver(base_url, layer_id, where, bbox=bbox)

    if len(features) < 1000:
        return features  # This quadrant is complete

    if depth >= 8:
        print(f"    [warn] bbox-split depth limit — quadrant has {len(features)} (may be incomplete)")
        return features

    # Capped — derive or use existing bbox and split into 4 quadrants
    if bbox is None:
        bbox = _bbox_from_features(features)
        if bbox is None:
            return features  # can't split without coordinates

    mx = (bbox[0] + bbox[2]) / 2.0
    my = (bbox[1] + bbox[3]) / 2.0
    quadrants = [
        [bbox[0], bbox[1], mx,      my     ],  # SW
        [mx,      bbox[1], bbox[2], my     ],  # SE
        [bbox[0], my,      mx,      bbox[3]],  # NW
        [mx,      my,      bbox[2], bbox[3]],  # NE
    ]
    result: list[dict] = []
    for q in quadrants:
        chunk = _fetch_all_bbox(base_url, layer_id, where, bbox=q, depth=depth + 1)
        result.extend(chunk)
    if depth == 0:
        print(f"    [bbox-split] completed: {len(result)} raw features before dedup")
    return result


def _download_featureserver(study: dict, cache_file: Path) -> None:
    """Fetch all features from a FeatureServer layer and save as a GeoJSON cache file.

    Uses bbox quadrant-split to bypass ArcGIS Online's silent 1000-feature cap.
    Deduplicates by OBJECTID/FID so quadrant-boundary features are not double-counted.
    Respects the optional ``where_clause`` study field (e.g. "LGA_NAME='LISMORE'").
    """
    base_url = study["base_url"]
    layer_id = study["layer_id"]
    where = study.get("where_clause", "1=1")

    where_desc = f" WHERE {where}" if where != "1=1" else ""
    print(f"  [fetch] ArcGIS FeatureServer {base_url}/{layer_id}{where_desc} ...")

    all_features = _fetch_all_bbox(base_url, layer_id, where)

    if not all_features:
        raise RuntimeError(f"FeatureServer returned 0 features for {base_url}/{layer_id}")

    # Deduplicate by OBJECTID / Object_ID / FID (bbox boundaries produce duplicates)
    _OID_FIELDS = ("OBJECTID", "Object_ID", "FID", "OBJECTID_1", "objectid")
    sample_props = (all_features[0].get("properties") or {}) if all_features else {}
    oid_field = next((f for f in _OID_FIELDS if f in sample_props), None)
    if oid_field:
        seen: set = set()
        deduped = []
        for f in all_features:
            oid = (f.get("properties") or {}).get(oid_field)
            if oid not in seen:
                seen.add(oid)
                deduped.append(f)
        dropped = len(all_features) - len(deduped)
        if dropped:
            print(f"  [dedup] {dropped} duplicate features removed (by {oid_field})")
        all_features = deduped

    geojson: dict = {
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "EPSG:4326"}},
        "features": all_features,
    }
    with open(cache_file, "w") as fh:
        json.dump(geojson, fh)
    print(f"  [cache] saved {len(all_features)} features -> {cache_file.name}")


def _inspect_featureserver(study_key: str, study: dict) -> None:
    """Fetch service metadata + first record to show available layers and field names."""
    base_url = study["base_url"]
    layer_id = study["layer_id"]

    # 1. Show all layers in the service (useful for multi-layer services)
    meta_r = requests.get(base_url, params={"f": "json"}, timeout=30)
    if meta_r.ok:
        meta = meta_r.json()
        layers = meta.get("layers", []) or meta.get("tables", [])
        if layers:
            print(f"\n  Available layers in {study_key}:")
            for lyr in layers:
                print(f"    id={lyr.get('id')}  name={lyr.get('name')!r}  type={lyr.get('type')!r}")
        else:
            print(f"  (no layers metadata returned)")

    # 2. Fetch one record — prefer first available layer_id from metadata over config
    if meta_r.ok:
        meta = meta_r.json()
        available_ids = [lyr.get("id") for lyr in (meta.get("layers") or []) if lyr.get("id") is not None]
        if available_ids and layer_id not in available_ids:
            print(f"  [warn] configured layer_id={layer_id} not in service — using id={available_ids[0]}")
            layer_id = available_ids[0]
    where = study.get("where_clause", "1=1")
    url = f"{base_url}/{layer_id}/query"
    params = {
        "where": where,
        "outFields": "*",
        "returnGeometry": "false",
        "resultOffset": 0,
        "resultRecordCount": 1,
        "f": "geojson",
    }
    r = requests.get(url, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()
    features = data.get("features", [])
    if not features:
        print(f"  [empty] no features returned for layer {layer_id} (where: {where})")
        return
    props = features[0].get("properties") or features[0].get("attributes") or {}
    print(f"\n  Field names for {study_key} layer {layer_id}:")
    for k, v in props.items():
        print(f"    {k!r}: {v!r}")


def _download_file(url: str, dest: Path, label: str = "") -> None:
    if dest.exists():
        print(f"  [cache] {dest.name}")
        return
    print(f"  [dl] {label or dest.name} ...")
    r = requests.get(url, timeout=120, stream=True, allow_redirects=True)
    r.raise_for_status()
    content_type = r.headers.get("content-type", "")
    if "html" in content_type.lower():
        raise RuntimeError(
            f"Got HTML response (auth required?) for {url}\n"
            f"Content-Type: {content_type}"
        )
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)
    print(f"  [dl] done ({dest.stat().st_size // 1024} KiB)")


def _prepare_study(study_key: str, study: dict) -> list[Path]:
    study_dir = CACHE_DIR / study_key
    study_dir.mkdir(exist_ok=True)

    dl_type = study["download_type"]

    if dl_type == "local":
        local_path = Path(study["local_path"])
        if not local_path.exists():
            raise FileNotFoundError(
                f"local_path not found: {local_path}\n"
                f"Place the shapefile at that path or update the study config."
            )
        return [local_path]

    elif dl_type == "shp_parts":
        stem = None
        for ext, url in study["shp_urls"].items():
            fname = url.split("/download/")[-1]
            if ext == ".shp":
                stem = fname[: -len(".shp")]
            dest = study_dir / fname
            _download_file(url, dest, label=fname)
        if not stem:
            raise RuntimeError("No .shp URL found in study config")
        return [study_dir / f"{stem}.shp"]

    elif dl_type == "arcgis_featureserver":
        cache_file = study_dir / f"{study_key}.geojson"
        if not cache_file.exists():
            _download_featureserver(study, cache_file)
        else:
            print(f"  [cache] {cache_file.name}")
        return [cache_file]

    elif dl_type == "zip":
        zip_url = study["zip_url"]
        zip_name = zip_url.split("/download/")[-1] if "/download/" in zip_url else f"{study_key}.zip"
        zip_path = study_dir / zip_name
        _download_file(zip_url, zip_path, label=zip_name)
        extract_dir = study_dir / "extracted"
        if not extract_dir.exists():
            print(f"  [extract] {zip_name} ...")
            with zipfile.ZipFile(zip_path) as zf:
                zf.extractall(extract_dir)
        return sorted(extract_dir.rglob("*.shp"))

    else:
        raise NotImplementedError(f"Unknown download_type: {dl_type}")


def _ingest_epi_statewide(study: dict, shp_paths: list[Path], conn, dry_run: bool) -> int:
    """
    Specialised ingest for EPI statewide shapefile where each row has its own
    LGA_NAME, LAY_CLASS (flood class), and CURRENCY_D (currency date).
    Uses LGA_CODE + LAY_CLASS sanitised string as the instrument_key.
    """
    cur = conn.cursor()
    total = 0
    instrument_prefix = study["instrument_prefix"]

    for shp_path in shp_paths:
        print(f"\n  [shp] {shp_path.name}")
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            print(f"  [skip] cannot read: {e}")
            continue

        if len(gdf) == 0:
            print(f"  [skip] empty")
            continue

        print(f"  rows={len(gdf)}, CRS={gdf.crs}")
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        rows_to_insert = []
        for idx, row in gdf.iterrows():
            geom = row.geometry
            if geom is None or geom.is_empty:
                continue
            lga_name = str(row.get("LGA_NAME") or "UNKNOWN").strip().upper()
            lga_code = int(row.get("LGA_CODE") or 0)
            lay_class = str(row.get("LAY_CLASS") or "flood_planning_area").strip()
            # Sanitise for instrument_key
            key_class = re.sub(r"[^a-zA-Z0-9]+", "_", lay_class).strip("_").upper()
            instrument_key = f"{instrument_prefix}_{lga_code}_{key_class}"
            # Currency date from row CURRENCY_D (Timestamp or date)
            raw_date = row.get("CURRENCY_D")
            if hasattr(raw_date, "date"):
                currency_date = raw_date.date()
            elif isinstance(raw_date, str):
                try:
                    from datetime import datetime
                    currency_date = datetime.strptime(raw_date[:10], "%Y-%m-%d").date()
                except Exception:
                    currency_date = date(2026, 4, 30)
            else:
                currency_date = date(2026, 4, 30)

            rows_to_insert.append((
                instrument_key,
                lga_name,
                "flood",
                lay_class,
                None,           # value_numeric: no ARI for EPI class labels
                currency_date,
                int(idx) + 1,
                geom.wkt,
            ))

        if not rows_to_insert:
            print(f"  [skip] no valid rows")
            continue

        print(f"  Prepared {len(rows_to_insert)} features")

        if dry_run:
            print(f"  [dry-run] would upsert {len(rows_to_insert)} features")
            total += len(rows_to_insert)
            continue

        execute_values(
            cur,
            """
            INSERT INTO spatial_overlays
                (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
            VALUES %s
            ON CONFLICT (instrument_key, layer_type, source_oid) DO UPDATE
                SET value = EXCLUDED.value,
                    value_numeric = EXCLUDED.value_numeric,
                    currency_date = EXCLUDED.currency_date,
                    geom = EXCLUDED.geom,
                    synced_at = now()
            """,
            rows_to_insert,
            template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())",
        )
        conn.commit()
        print(f"  Upserted {len(rows_to_insert)} features")
        total += len(rows_to_insert)

    cur.close()
    return total


def _ingest_study(study_key: str, study: dict, shp_paths: list[Path], conn, dry_run: bool) -> int:
    cur = conn.cursor()
    total = 0
    instrument_prefix = study["instrument_prefix"]
    lga_primary = study["lga_names"][0]
    currency_date = study["currency_date"]

    for shp_path in shp_paths:
        print(f"\n  [shp] {shp_path.name}")
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            print(f"  [skip] cannot read: {e}")
            continue

        if len(gdf) == 0:
            print(f"  [skip] empty")
            continue

        print(f"  rows={len(gdf)}, CRS={gdf.crs}")
        if gdf.crs is None:
            gdf = gdf.set_crs("EPSG:4326")
        elif gdf.crs.to_epsg() != 4326:
            gdf = gdf.to_crs("EPSG:4326")

        aep_col = study.get("aep_col") or _detect_aep_col(gdf)
        print(f"  columns={list(gdf.columns)}")

        aep_source = study.get("aep_source", "column")
        if aep_source == "fixed":
            # Binary mask or FPA-type study — every feature shares one fixed scenario.
            unique_scenarios = [study["fixed_scenario"]]
            aep_col = None
        elif aep_source == "filename":
            stem = shp_path.stem
            if re.search(r"PMF", stem, re.IGNORECASE):
                scenario_raw = "PMF"
            else:
                # Hawkesbury: DesignXXXAEP
                m = re.search(r"Design(\d+(?:p\d+)?AEP)", stem, re.IGNORECASE)
                if not m:
                    # Campbelltown: 0p2AEP, 1AEP, 20AEP
                    m = re.search(r"(\d+(?:p\d+)?)AEP", stem, re.IGNORECASE)
                if m:
                    raw = m.group(1).replace("p", ".")
                    scenario_raw = f"{raw}AEP"
                else:
                    scenario_raw = "UNKNOWN"
            unique_scenarios = [scenario_raw]
        elif aep_col and aep_col in gdf.columns:
            unique_scenarios = sorted(gdf[aep_col].dropna().unique().tolist())
            print(f"  aep_col={aep_col}, unique_values={unique_scenarios[:10]}")
        else:
            print(f"  [warn] no AEP column found -- ingesting as 'FLOOD_EXTENT'")
            aep_col = None
            unique_scenarios = ["FLOOD_EXTENT"]

        rows_to_insert = []
        for scenario_raw in unique_scenarios:
            subset = gdf[gdf[aep_col] == scenario_raw] if aep_col else gdf
            if len(subset) == 0:
                continue
            norm_label, ari = _normalise_aep(str(scenario_raw))
            instrument_key = f"{instrument_prefix}_{norm_label.replace('%', 'pct').replace('.', '_')}"

            for idx, row in subset.iterrows():
                geom = row.geometry
                if geom is None or geom.is_empty:
                    continue
                rows_to_insert.append((
                    instrument_key,
                    lga_primary,
                    "flood",
                    norm_label,
                    float(ari) if ari is not None else None,
                    currency_date,
                    int(idx) + 1,
                    geom.wkt,
                ))

        if not rows_to_insert:
            print(f"  [skip] no valid rows")
            continue

        print(f"  Prepared {len(rows_to_insert)} features")

        if dry_run:
            print(f"  [dry-run] would upsert {len(rows_to_insert)} features")
            total += len(rows_to_insert)
            continue

        execute_values(
            cur,
            """
            INSERT INTO spatial_overlays
                (instrument_key, lga_name, layer_type, value, value_numeric, currency_date, source_oid, geom, synced_at)
            VALUES %s
            ON CONFLICT (instrument_key, layer_type, source_oid) DO UPDATE
                SET value = EXCLUDED.value,
                    value_numeric = EXCLUDED.value_numeric,
                    currency_date = EXCLUDED.currency_date,
                    geom = EXCLUDED.geom,
                    synced_at = now()
            """,
            rows_to_insert,
            template="(%s, %s, %s, %s, %s, %s, %s, ST_Multi(ST_GeomFromText(%s, 4326)), now())",
        )
        conn.commit()
        print(f"  Upserted {len(rows_to_insert)} features")
        total += len(rows_to_insert)

    cur.close()
    return total


def _inspect_study(study_key: str, study: dict, shp_paths: list[Path]) -> None:
    print(f"\n{'=' * 60}")
    print(f"STUDY: {study_key} -- {study['label']}")
    for shp_path in shp_paths:
        print(f"\n  SHP: {shp_path.name}")
        try:
            gdf = gpd.read_file(shp_path)
        except Exception as e:
            print(f"  ERROR: {e}")
            continue
        print(f"  rows={len(gdf)}, CRS={gdf.crs}")
        print(f"  columns: {[c for c in gdf.columns if c != 'geometry']}")
        for col in gdf.columns:
            if col.lower() == "geometry":
                continue
            if any(pat in col.lower() for pat in AEP_COL_PATTERNS):
                unique_vals = gdf[col].dropna().unique().tolist()[:20]
                print(f"  >>> {col}: {unique_vals}")


def _verify_db(conn, study_key: str, instrument_prefix: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT value, COUNT(*) FROM spatial_overlays "
            "WHERE layer_type='flood' AND instrument_key LIKE %s "
            "GROUP BY value ORDER BY value",
            (f"{instrument_prefix}%",),
        )
        rows = cur.fetchall()
        print(f"\n[{study_key}] flood rows in DB:")
        for r in rows:
            print(f"  {r[0]}: {r[1]} polygons")


def main():
    all_keys = list(STUDIES.keys())
    parser = argparse.ArgumentParser()
    parser.add_argument("--study", default="all", nargs="+",
                        help=f"Study key(s): all | {' | '.join(all_keys)}")
    parser.add_argument("--inspect", action="store_true",
                        help="Print column info from local files only -- no DB insert")
    parser.add_argument("--inspect-featureserver", action="store_true",
                        help="Fetch 1 record from FeatureServer studies and print field names")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and validate but skip DB insert")
    args = parser.parse_args()

    study_arg = args.study if isinstance(args.study, list) else [args.study]
    target_keys = all_keys if study_arg == ["all"] else study_arg
    for k in target_keys:
        if k not in STUDIES:
            print(f"ERROR: unknown study '{k}'. Valid: {all_keys}")
            sys.exit(1)

    database_url = os.getenv("DATABASE_URL")
    if not database_url and not args.inspect and not args.inspect_featureserver and not args.dry_run:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    for study_key in target_keys:
        study = STUDIES[study_key]
        print(f"\n{'=' * 60}")
        print(f"Processing: {study_key} -- {study['label']}")

        # FeatureServer field inspection — no local file needed
        if args.inspect_featureserver:
            if study.get("download_type") == "arcgis_featureserver":
                _inspect_featureserver(study_key, study)
            else:
                print(f"  [skip] not an arcgis_featureserver study")
            continue

        try:
            shp_paths = _prepare_study(study_key, study)
        except Exception as e:
            print(f"  ERROR preparing study: {e}")
            continue

        if not shp_paths:
            print(f"  ERROR: no files found after download")
            continue

        print(f"  Found {len(shp_paths)} file(s)")

        if args.inspect:
            _inspect_study(study_key, study, shp_paths)
            continue

        conn = psycopg2.connect(database_url)
        try:
            aep_source = study.get("aep_source")
            if aep_source == "epi_statewide":
                total = _ingest_epi_statewide(study, shp_paths, conn, dry_run=args.dry_run)
            else:
                total = _ingest_study(study_key, study, shp_paths, conn, dry_run=args.dry_run)
            if not args.dry_run:
                _verify_db(conn, study_key, study["instrument_prefix"])
            print(f"\n[{study_key}] Total features: {total}")
        except Exception as e:
            conn.rollback()
            print(f"  ERROR: {e}")
            raise
        finally:
            conn.close()

    print("\n[DONE]")


if __name__ == "__main__":
    main()
