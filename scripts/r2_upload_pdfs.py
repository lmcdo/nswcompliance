#!/usr/bin/env python3
"""
R2 PDF Upload + Chapter Registry Initialisation
================================================
Uploads all council DCP chapter PDFs to Cloudflare R2 under source-pdfs/
and populates the dcp_chapter_registry table with baseline content hashes.

Source priority:
  1. Local _origin.pdf from archive/2026-01-pipeline-outputs/output/
     (the exact files provisions were extracted from — v1.0-baseline)
  2. Local files in downloads/ (amended chapters)
  3. Download from council website (chapters with no local copy)

This is a ONE-TIME setup script. After it runs, the weekly monitor
(r2_monitor.py) takes over change detection.

Usage:
    python3 scripts/r2_upload_pdfs.py                    # all councils
    python3 scripts/r2_upload_pdfs.py --council marrickville
    python3 scripts/r2_upload_pdfs.py --council leichhardt
    python3 scripts/r2_upload_pdfs.py --council ashfield
    python3 scripts/r2_upload_pdfs.py --council local    # SEPP/ADG local files
    python3 scripts/r2_upload_pdfs.py --dry-run          # show plan without downloading
    python3 scripts/r2_upload_pdfs.py --skip-upload      # DB only, assume already in R2

Requirements (already in requirements.txt):
    boto3, requests, psycopg2-binary, python-dotenv
"""

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path
from typing import Optional

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import psycopg2
import requests
from botocore.exceptions import ClientError
from dotenv import load_dotenv
from psycopg2.extras import execute_values

# ─── Configuration ────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID      = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME     = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID   = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL       = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT        = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"
SOURCE_PDF_PREFIX  = "source-pdfs"  # top-level R2 prefix for raw PDFs

INNER_WEST_BASE    = "https://www.innerwest.nsw.gov.au"
VERSION_LABEL      = "v1.0-baseline"

# Request headers that help avoid bot-detection on council sites
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "application/pdf,*/*",
}

# ─── Chapter Manifests ─────────────────────────────────────────────────────────
# Format per entry:
#   chapter_key   : stable slug (never changes even if label/URL changes)
#   chapter_label : human-readable label shown in logs
#   url_path      : path relative to INNER_WEST_BASE (or full URL for non-council sources)
#   doc_type      : 'dcp' | 'map' | 'sepp' | 'lep' | 'adg'
#   sort_order    : integer for display ordering
#   local_path    : relative to project root (for local-only files, no download needed)

MARRICKVILLE_CHAPTERS = [
    # ── Table of Contents / Cover ──────────────────────────────────────────────
    {
        "chapter_key":   "toc",
        "chapter_label": "Table of Contents",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%20Contents%20Nov%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    1,
    },
    {
        "chapter_key":   "da-guidelines",
        "chapter_label": "Development Application Guidelines",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%20Development%20Application%20Guidelines%20with%20IWLEP%202022%20amendments%20Nov%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    2,
    },
    # ── Part 1 ─────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part1-statutory-info",
        "chapter_label": "Part 1 · Statutory Information",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%201%20-%20Statutory%20Information%20with%20IWLEP%202022%20amendments%20Nov%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    10,
    },
    # ── Part 2 Generic Provisions ──────────────────────────────────────────────
    {
        "chapter_key":   "part2-s01-urban-design",
        "chapter_label": "Part 2 · 2.1 Urban Design",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%201%20Urban%20Design.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    21,
    },
    {
        "chapter_key":   "part2-s03-site-context-analysis",
        "chapter_label": "Part 2 · 2.3 Site and Context Analysis",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%203%20Site%20Context%20Analysis.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    23,
    },
    {
        "chapter_key":   "part2-s05-equity-access-mobility",
        "chapter_label": "Part 2 · 2.5 Equity of Access and Mobility",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%205%20Equity%20of%20Access%20and%20Mobility.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    25,
    },
    {
        "chapter_key":   "part2-s06-privacy",
        "chapter_label": "Part 2 · 2.6 Acoustic and Visual Privacy",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%206%20Acoustic%20and%20Visual%20Privacy.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    26,
    },
    {
        "chapter_key":   "part2-s07-solar-access",
        "chapter_label": "Part 2 · 2.7 Solar Access and Overshadowing",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%207%20Solar%20Access%20and%20Overshadowing.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    27,
    },
    {
        "chapter_key":   "part2-s08-social-impact",
        "chapter_label": "Part 2 · 2.8 Social Impact Assessment",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%208%20Social%20Impact%20Assessment.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    28,
    },
    {
        "chapter_key":   "part2-s09-community-safety",
        "chapter_label": "Part 2 · 2.9 Community Safety",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%209%20Community%20Safety.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    29,
    },
    {
        "chapter_key":   "part2-s10-parking",
        "chapter_label": "Part 2 · 2.10 Parking",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2010%20Parking.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    30,
    },
    {
        "chapter_key":   "part2-s11-fencing",
        "chapter_label": "Part 2 · 2.11 Fencing",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2011%20Fencing.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    31,
    },
    {
        "chapter_key":   "part2-s12-signs",
        "chapter_label": "Part 2 · 2.12 Signs and Advertising Structures",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2012%20Signs%20and%20Advertising%20Structures.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    32,
    },
    {
        "chapter_key":   "part2-s13-biodiversity",
        "chapter_label": "Part 2 · 2.13 Biodiversity",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2013%20Biodiversity.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    33,
    },
    {
        "chapter_key":   "part2-s14-unique-env-features",
        "chapter_label": "Part 2 · 2.14 Unique Environmental Features",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2014%20Unique%20Environmental%20Features.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    34,
    },
    {
        "chapter_key":   "part2-s16-energy-efficiency",
        "chapter_label": "Part 2 · 2.16 Energy Efficiency",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2016%20Energy%20Efficiency.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    36,
    },
    {
        "chapter_key":   "part2-s17-water-sensitive",
        "chapter_label": "Part 2 · 2.17 Water Sensitive Urban Design",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2017%20Water%20Sensitive%20Urban%20Design.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    37,
    },
    {
        "chapter_key":   "part2-s18-landscaping",
        "chapter_label": "Part 2 · 2.18 Landscaping and Open Spaces",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2018%20Landscaping%20and%20Open%20Spaces.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    38,
    },
    {
        "chapter_key":   "part2-s20-tree-management",
        "chapter_label": "Part 2 · 2.20 Tree Management",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2020%20Tree%20Management%20-%20updated%2028%20March%202023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    40,
    },
    {
        "chapter_key":   "part2-s21-site-facilities-waste",
        "chapter_label": "Part 2 · 2.21 Site Facilities and Waste Management",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2021%20-%20Site%20Facilities%20Waste%20Management%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    41,
    },
    {
        "chapter_key":   "part2-s22-flood-management",
        "chapter_label": "Part 2 · 2.22 Flood Management",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2022%20Flood%20Management%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    42,
    },
    {
        "chapter_key":   "part2-s23-acid-sulfate",
        "chapter_label": "Part 2 · 2.23 Acid Sulfate Soils",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2023%20Acid%20Sulfate%20Soils%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    43,
    },
    {
        "chapter_key":   "part2-s24-contaminated-land",
        "chapter_label": "Part 2 · 2.24 Contaminated Land",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2024%20Contaminated%20Land%20Amd.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    44,
    },
    {
        "chapter_key":   "part2-s25-stormwater",
        "chapter_label": "Part 2 · 2.25 Stormwater Management",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%202%2025%20Stormwater%20Management.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    45,
    },
    {
        "chapter_key":   "part2-s26-entertainment-precincts",
        "chapter_label": "Part 2 · 2.26 Special Entertainment Precincts",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20Section%202.26.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    46,
    },
    # ── Part 3 ─────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part3-subdivision",
        "chapter_label": "Part 3 · Subdivision, Amalgamation and Movement Networks",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%203%200%20Subdivision,%20Amalgation,%20Movement%20Network%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    50,
    },
    # ── Part 4 Residential ─────────────────────────────────────────────────────
    {
        "chapter_key":   "part4-s1-low-density",
        "chapter_label": "Part 4 · 4.1 Low Density Residential Development",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%204.1%20Low%20Density%20Residential%20Development.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    61,
    },
    {
        "chapter_key":   "part4-s2-multi-dwelling",
        "chapter_label": "Part 4 · 4.2 Multi Dwelling Housing and Residential Flat Buildings",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%204%202%20Multi%20Dwelling%20Housing%20and%20RFBs%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    62,
    },
    {
        "chapter_key":   "part4-s3-boarding-houses",
        "chapter_label": "Part 4 · 4.3 Boarding Houses",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%204%203%20boarding%20houses.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    63,
    },
    # ── Part 5 ─────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part5-commercial-mixed-use",
        "chapter_label": "Part 5 · Commercial and Mixed Use Development",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%205%200%20Commercial%20and%20Mixed%20Use%20Development%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    70,
    },
    # ── Part 6 ─────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part6-industrial",
        "chapter_label": "Part 6 · Industrial Development",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%206%200%20Industrial%20Development%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    80,
    },
    # ── Part 7 ─────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part7-s1-childcare",
        "chapter_label": "Part 7 · 7.1 Child Care Centres",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%207%201%20childcare%20centres%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    91,
    },
    {
        "chapter_key":   "part7-s3-sex-industry",
        "chapter_label": "Part 7 · 7.3 Sex Industry and Adult Business Premises",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%207.3%20Sex%20Industry%20and%20Adult%20Business%20Premises.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    93,
    },
    # ── Part 8 Heritage ────────────────────────────────────────────────────────
    {
        "chapter_key":   "part8-heritage",
        "chapter_label": "Part 8 · Heritage",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%208.0%20Heritage.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    100,
    },
    # ── Part 9 Strategic Context / Precincts ───────────────────────────────────
    {
        "chapter_key":   "part9-intro",
        "chapter_label": "Part 9 · Introduction",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%200%20Introduction.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    110,
    },
    {
        "chapter_key":   "part9-p01-lewisham-north",
        "chapter_label": "Part 9 · Precinct 1 · Lewisham North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%201%20Lewisham%20North%20Precinct%201.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    111,
    },
    {
        "chapter_key":   "part9-p02-petersham-north",
        "chapter_label": "Part 9 · Precinct 2 · Petersham North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%202%20Petersham%20North%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    112,
    },
    {
        "chapter_key":   "part9-p03-stanmore-north",
        "chapter_label": "Part 9 · Precinct 3 · Stanmore North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%203%20Stanmore%20North%20Precinct%203.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    113,
    },
    {
        "chapter_key":   "part9-p04-newtown-north",
        "chapter_label": "Part 9 · Precinct 4 · Newtown North and Camperdown",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%204%20Newtown%20North%20and%20Camperdown.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    114,
    },
    {
        "chapter_key":   "part9-p05-lewisham-south",
        "chapter_label": "Part 9 · Precinct 5 · Lewisham South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%205%20Lewisham%20South%20Precinct%205.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    115,
    },
    {
        "chapter_key":   "part9-p06-petersham-south",
        "chapter_label": "Part 9 · Precinct 6 · Petersham South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%206%20Petersham%20South%20Precinct%206.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    116,
    },
    {
        "chapter_key":   "part9-p07-stanmore-south",
        "chapter_label": "Part 9 · Precinct 7 · Stanmore South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%207%20Stanmore%20South.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    117,
    },
    {
        "chapter_key":   "part9-p08-enmore-north",
        "chapter_label": "Part 9 · Precinct 8 · Enmore North and Newtown Central",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%208%20Enmore%20North%20and%20Newtown%20Central%20Precinct%208.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    118,
    },
    {
        "chapter_key":   "part9-p09-newington",
        "chapter_label": "Part 9 · Precinct 9 · Newington",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%209%20Newington.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    119,
    },
    {
        "chapter_key":   "part9-p10-dulwich-hill-north",
        "chapter_label": "Part 9 · Precinct 10 · Dulwich Hill North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2010%20Dulwich%20Hill%20North.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    120,
    },
    {
        "chapter_key":   "part9-p11-hoskins-park",
        "chapter_label": "Part 9 · Precinct 11 · Hoskins Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2011%20Hoskins%20Park%20Precinct%2011.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    121,
    },
    {
        "chapter_key":   "part9-p12-marrickville-park",
        "chapter_label": "Part 9 · Precinct 12 · Marrickville Park and Morton Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2012%20Marrickville%20Park%20and%20Morton%20Park.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    122,
    },
    {
        "chapter_key":   "part9-p13-henson-park",
        "chapter_label": "Part 9 · Precinct 13 · Henson Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2013%20Henson%20Park.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    123,
    },
    {
        "chapter_key":   "part9-p14-camdenville",
        "chapter_label": "Part 9 · Precinct 14 · Camdenville",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2014%20Camdenville%20Precinct%2014.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    124,
    },
    {
        "chapter_key":   "part9-p15-enmore-park",
        "chapter_label": "Part 9 · Precinct 15 · Enmore Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2015%20Enmore%20Park.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    125,
    },
    {
        "chapter_key":   "part9-p16-abergeldie",
        "chapter_label": "Part 9 · Precinct 16 · Abergeldie Estate",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2016%20Abergeldie%20Estate.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    126,
    },
    {
        "chapter_key":   "part9-p17-new-canterbury-rd",
        "chapter_label": "Part 9 · Precinct 17 · New Canterbury Road West",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2017%20New%20Canterbury%20Road%20West.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    127,
    },
    {
        "chapter_key":   "part9-p18-dulwich-hill-stn-north",
        "chapter_label": "Part 9 · Precinct 18 · Dulwich Hill Station North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2018%20Dulwich%20Hill%20Station%20North.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    128,
    },
    {
        "chapter_key":   "part9-p19-marrickville-rd-central",
        "chapter_label": "Part 9 · Precinct 19 · Marrickville Road Central",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2019%20Marrickville%20Road,%20Central.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    129,
    },
    {
        "chapter_key":   "part9-p20-marrickville-tc-north",
        "chapter_label": "Part 9 · Precinct 20 · Marrickville Town Centre North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2020%20Marrickville%20Town%20Centre%20North.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    130,
    },
    {
        "chapter_key":   "part9-p21-ness-park",
        "chapter_label": "Part 9 · Precinct 21 · Ness Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2021%20Ness%20Park.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    131,
    },
    {
        "chapter_key":   "part9-p22-dulwich-hill-stn-south",
        "chapter_label": "Part 9 · Precinct 22 · Dulwich Hill Station South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2022%20Dulwich%20Hill%20Station%20South%20Precinct%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    132,
    },
    {
        "chapter_key":   "part9-p23-marrickville-stn-west",
        "chapter_label": "Part 9 · Precinct 23 · Marrickville Station West",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2023%20Marrickville%20Station%20West%20Precinct%2023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    133,
    },
    {
        "chapter_key":   "part9-p24-marrickville-tc-south",
        "chapter_label": "Part 9 · Precinct 24 · Marrickville Town Centre South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2024%20Marrickville%20Town%20Centre%20South.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    134,
    },
    {
        "chapter_key":   "part9-p25-st-peters-triangle",
        "chapter_label": "Part 9 · Precinct 25 · St Peters Triangle",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2025%20St%20Peters%20Triangle%20Precinct%2025.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    135,
    },
    {
        "chapter_key":   "part9-p26-barwon-park",
        "chapter_label": "Part 9 · Precinct 26 · Barwon Park",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2026%20Barwon%20Park.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    136,
    },
    {
        "chapter_key":   "part9-p27-barwon-park-south",
        "chapter_label": "Part 9 · Precinct 27 · Barwon Park South",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2027%20Barwon%20Park%20South.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    137,
    },
    {
        "chapter_key":   "part9-p28-cooks-river-west",
        "chapter_label": "Part 9 · Precinct 28 · Cooks River West",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2028%20Cooks%20River%20West.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    138,
    },
    {
        "chapter_key":   "part9-p29-sw-marrickville",
        "chapter_label": "Part 9 · Precinct 29 · South Western Marrickville",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2029%20South%20Western%20Marrickville.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    139,
    },
    {
        "chapter_key":   "part9-p30-the-warren",
        "chapter_label": "Part 9 · Precinct 30 · The Warren",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2030%20The%20Warren.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    140,
    },
    {
        "chapter_key":   "part9-p31-unwins-bridge",
        "chapter_label": "Part 9 · Precinct 31 · Unwins Bridge Road",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2031%20Unwins%20Bridge%20Road.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    141,
    },
    {
        "chapter_key":   "part9-p32-cooks-river-east",
        "chapter_label": "Part 9 · Precinct 32 · Cooks River East",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2032%20Cooks%20River%20East.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    142,
    },
    {
        "chapter_key":   "part9-p33-princes-highway",
        "chapter_label": "Part 9 · Precinct 33 · Princes Highway",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2033%20Princes%20Highway.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    143,
    },
    {
        "chapter_key":   "part9-p34-tempe-reserve",
        "chapter_label": "Part 9 · Precinct 34 · Tempe Reserve",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2034%20Tempe%20Reserve.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    144,
    },
    {
        "chapter_key":   "part9-p35-parramatta-rd",
        "chapter_label": "Part 9 · Precinct 35 · Parramatta Road (Commercial)",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2035%20Parramatta%20Road.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    145,
    },
    {
        "chapter_key":   "part9-p36-petersham-commercial",
        "chapter_label": "Part 9 · Precinct 36 · Petersham (Commercial)",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2036%20Petersham%20Commercial%20Precinct%2036%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    146,
    },
    {
        "chapter_key":   "part9-p37-king-st-enmore",
        "chapter_label": "Part 9 · Precinct 37 · King Street and Enmore Road (Commercial)",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2037%20King%20Street%20and%20Enmore%20Road%20Commercial%20Precinct.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    147,
    },
    {
        "chapter_key":   "part9-p38-dulwich-hill-commercial",
        "chapter_label": "Part 9 · Precinct 38 · Dulwich Hill (Commercial)",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2038%20Dulwich%20Hill%20Commercial%20Precinct%2038%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    148,
    },
    {
        "chapter_key":   "part9-p39-marrickville-metro",
        "chapter_label": "Part 9 · Precinct 39 · Marrickville Metro",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2039%20Marrickville%20Metro.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    149,
    },
    {
        "chapter_key":   "part9-p40-marrickville-tc-commercial",
        "chapter_label": "Part 9 · Precinct 40 · Marrickville Town Centre (Commercial)",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2040%20Marrickville%20Town%20Centre%20Comm%20Precinct%2040%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    150,
    },
    {
        "chapter_key":   "part9-p41-bridge-road",
        "chapter_label": "Part 9 · Precinct 41 · Bridge Road",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2041%20Bridge%20Road.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    151,
    },
    {
        "chapter_key":   "part9-p42-camperdown-north",
        "chapter_label": "Part 9 · Precinct 42 · Camperdown North",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2042%20Camperdown%20North.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    152,
    },
    {
        "chapter_key":   "part9-p43-sydney-steel",
        "chapter_label": "Part 9 · Precinct 43 · Sydney Steel",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209.43%20Sydney%20Steel%20Precinct%2043.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    153,
    },
    {
        "chapter_key":   "part9-p44-carrington-road",
        "chapter_label": "Part 9 · Precinct 44 · Carrington Road",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2044%20Carrington%20Road.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    154,
    },
    {
        "chapter_key":   "part9-p45-mcgill-st",
        "chapter_label": "Part 9 · Precinct 45 · McGill Street",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2045%20McGill%20Street%20Precinct%2045.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    155,
    },
    {
        "chapter_key":   "part9-p46-tempe-lands",
        "chapter_label": "Part 9 · Precinct 46 · Tempe Lands",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2046%20Tempe%20Lands%20Precinct.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    156,
    },
    {
        "chapter_key":   "part9-p47-victoria-road",
        "chapter_label": "Part 9 · Precinct 47 · Victoria Road",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209%2047%20Victoria%20Road.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    157,
    },
    {
        "chapter_key":   "part9-p48-mary-robert-edith",
        "chapter_label": "Part 9 · Precinct 48 · Mary, Robert and Edith Street",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%209.48%20Mary%20Robert%20and%20Edith%20Street%20Nov%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    158,
    },
    # ── Part 10 ────────────────────────────────────────────────────────────────
    {
        "chapter_key":   "part10-definitions",
        "chapter_label": "Part 10 · Definitions",
        "url_path":      "/ArticleDocuments/740/Marrickville%20DCP%202011%20-%2010.0%20Definitions.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    200,
    },
]

LEICHHARDT_CHAPTERS = [
    {
        "chapter_key":   "cover",
        "chapter_label": "Cover Page",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%201%20-%20Cover%20-%20Amdt%2018%20-%20March%2023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    1,
    },
    {
        "chapter_key":   "toc",
        "chapter_label": "Contents Page",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%20Contents%20Page%20Amdt%20No%2019%20-%20November%202023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    2,
    },
    {
        "chapter_key":   "part-a-introduction",
        "chapter_label": "Part A · Introduction",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%203%20-%20Part%20A%20%20Introduction%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    10,
    },
    {
        "chapter_key":   "part-b-connections",
        "chapter_label": "Part B · Connections",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%204%20-%20Part%20B%20Connections%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    20,
    },
    {
        "chapter_key":   "part-c-s1-general",
        "chapter_label": "Part C · Section 1 · General Provisions",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%205%20-%20%20Part%20C%20Place%20Section%201%20-%20with%20IWLEP%202022%20amendments%20March%2023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    31,
    },
    {
        "chapter_key":   "part-c-s2-urban-character",
        "chapter_label": "Part C · Section 2 · Urban Character",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%206%20-%20Part%20C%20Place%20Section%202%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    32,
    },
    {
        "chapter_key":   "part-c-s3-residential",
        "chapter_label": "Part C · Section 3 · Residential Provisions",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%207%20-%20Part%20C%20Place%20Section%203%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    33,
    },
    {
        "chapter_key":   "part-c-s4-non-residential",
        "chapter_label": "Part C · Section 4 · Non-Residential Provisions",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%208%20-%20Part%20C%20Place%20Section%204%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    34,
    },
    {
        "chapter_key":   "part-c-s5-entertainment-precincts",
        "chapter_label": "Part C · Section 5 · Special Entertainment Precincts",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20Part%20C%20Section%205.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    35,
    },
    {
        "chapter_key":   "part-d-energy",
        "chapter_label": "Part D · Energy",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%209%20-%20Part%20D%20Energy%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    40,
    },
    {
        "chapter_key":   "part-e-water",
        "chapter_label": "Part E · Water",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2010%20-%20Part%20E%20Water%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    50,
    },
    {
        "chapter_key":   "part-f-food",
        "chapter_label": "Part F · Food",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2011%20-%20Part%20F%20Food%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    60,
    },
    {
        "chapter_key":   "part-g-s1-site-specific",
        "chapter_label": "Part G · Site Specific Controls (Sections 1–12)",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2012%20-%20Part%20G%20Section%201-12%20-%20Amdt%2019%20-%20Nov%202023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    71,
    },
    {
        "chapter_key":   "part-g-s13-pyrmont-bridge-rd",
        "chapter_label": "Part G · Section 13 · Pyrmont Bridge Road",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2012%20-%20Part%20G%20Section%2013%20-%20Amdt%2019%20-%20Pyrmont%20Bridge%20Road%20Nov%202023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    72,
    },
    {
        "chapter_key":   "appendix-a-glossary",
        "chapter_label": "Appendix A · Glossary",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2013%20-%20Appendix%20A%20Glossary%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    80,
    },
    {
        "chapter_key":   "appendix-b-building-typologies",
        "chapter_label": "Appendix B · Building Typologies",
        "url_path":      "/ArticleDocuments/739/Leichhardt%20DCP%202013%20-%2014%20-%20Appendix%20B%20Building%20Typologies%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    81,
    },
]

ASHFIELD_CHAPTERS = [
    {
        "chapter_key":   "preliminary",
        "chapter_label": "Section 1 · Preliminary and Table of Contents",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20%20-%20Preliminary,%20Notification%20and%20Advertising%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    1,
    },
    {
        "chapter_key":   "chapter-a-miscellaneous",
        "chapter_label": "Chapter A · Miscellaneous",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20A%20-%20Miscellaneous%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    10,
    },
    {
        "chapter_key":   "chapter-b-public-domain",
        "chapter_label": "Chapter B · Public Domain",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20B%20-%20Public%20Domain%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    20,
    },
    {
        "chapter_key":   "chapter-c-sustainability",
        "chapter_label": "Chapter C · Sustainability",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20C%20-%20Sustainability%20IWLEP%202022%20amends%20-%2028%20Mar%2023.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    30,
    },
    {
        "chapter_key":   "chapter-d-precinct-guidelines",
        "chapter_label": "Chapter D · Precinct Guidelines",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20D%20-%20Precinct%20Guidelines%20with%20IWLEP%202022%20amendments%20Nov%2022.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    40,
    },
    {
        "chapter_key":   "chapter-e1-heritage",
        "chapter_label": "Chapter E1 · All Heritage Items and Conservation Areas (except Haberfield)",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20E1-%20Heritage%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    51,
    },
    {
        "chapter_key":   "chapter-e2-haberfield",
        "chapter_label": "Chapter E2 · Haberfield Neighbourhood",
        "url_path":      "/ArticleDocuments/737/Chapter%20E2%20Haberfield%20Neighbourhood.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    52,
    },
    {
        "chapter_key":   "chapter-f-dev-category",
        "chapter_label": "Chapter F · Development Category Guidelines",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20F%20-%20Development%20Category%20with%20IWLEP%202022%20amendment.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    60,
    },
    {
        "chapter_key":   "chapter-g-definitions",
        "chapter_label": "Chapter G · Definitions",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20G%20-%20Definitions%20-%20with%20IWLEP%202022%20amendments.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    70,
    },
    {
        "chapter_key":   "chapter-h-amendments",
        "chapter_label": "Chapter H · Amendments",
        "url_path":      "/ArticleDocuments/737/Inner%20West%20Ashfield%20DCP%202016%20-%20Chapter%20H%20-%20with%20IWLEP%202022%20amendments%20Apr%2024.pdf.aspx",
        "doc_type":      "dcp",
        "sort_order":    80,
    },
]

# Local-only files (already on disk, no council URL to poll for changes)
# These are uploaded once. For SEPP/LEP changes, the RSS monitor handles re-download.
PROJECT_ROOT    = Path(__file__).parent.parent
_ARCHIVE_ROOT   = PROJECT_ROOT / "archive" / "2026-01-pipeline-outputs" / "output"
_DOWNLOADS_DIR  = PROJECT_ROOT / "downloads"

def _arch(folder: str) -> Path:
    """Return the _origin.pdf path for a chapter inside the archive output tree."""
    return _ARCHIVE_ROOT / folder / "auto" / f"{folder}_origin.pdf"

def _dl(filename: str) -> Path:
    """Return path to a file in the downloads/ directory."""
    return _DOWNLOADS_DIR / filename

LOCAL_FILES = [
    {
        "council":       "state",
        "dcp_name":      "State Environmental Planning Policy (Housing) 2021",
        "chapter_key":   "sepp-housing-2021",
        "chapter_label": "SEPP Housing 2021",
        "doc_type":      "sepp",
        "sort_order":    1,
        "local_path":    PROJECT_ROOT / "scripts" / "sepp_housing_2021.pdf",
        "council_url":   "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0624",
    },
    {
        "council":       "state",
        "dcp_name":      "State Environmental Planning Policy (Resilience and Hazards) 2021",
        "chapter_key":   "sepp-resilience-hazards-2021",
        "chapter_label": "SEPP Resilience and Hazards 2021",
        "doc_type":      "sepp",
        "sort_order":    2,
        "local_path":    PROJECT_ROOT / "frontend-nextjs" / "sepp_resilience_hazards_2021.pdf",
        "council_url":   "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0620",
    },
    {
        "council":       "state",
        "dcp_name":      "Apartment Design Guide Part 3",
        "chapter_key":   "adg-part3",
        "chapter_label": "Apartment Design Guide Part 3",
        "doc_type":      "adg",
        "sort_order":    1,
        "local_path":    PROJECT_ROOT / "docs" / "adg" / "adg-part-3.pdf",
        "council_url":   None,  # No council URL - manual update
    },
    {
        "council":       "state",
        "dcp_name":      "Apartment Design Guide (full)",
        "chapter_key":   "apartment-design-guide",
        "chapter_label": "Apartment Design Guide",
        "doc_type":      "adg",
        "sort_order":    2,
        "local_path":    PROJECT_ROOT / "docs" / "adg" / "apartment-design-guide.pdf",
        "council_url":   None,
    },
    {
        "council":       "state",
        "dcp_name":      "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008",
        "chapter_key":   "sepp-exempt-complying-2008",
        "chapter_label": "SEPP Exempt and Complying Development Codes 2008",
        "doc_type":      "sepp",
        "sort_order":    3,
        # Extraction origin — page numbers in regulatory_provisions match this version
        "local_path":    PROJECT_ROOT / "archive" / "2026-01-extraction-outputs" / "extraction_outputs" / "sepps" / "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation" / "auto" / "State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation_origin.pdf",
        "council_url":   "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572",
    },
]

# ─── Council lookup ────────────────────────────────────────────────────────────

COUNCIL_CONFIGS = {
    "marrickville": {
        "dcp_name":        "Marrickville DCP 2011",
        "council_page_url": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/marrickville-dcp",
        "chapters":        MARRICKVILLE_CHAPTERS,
    },
    "leichhardt": {
        "dcp_name":        "Leichhardt DCP 2013",
        "council_page_url": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp",
        "chapters":        LEICHHARDT_CHAPTERS,
    },
    "ashfield": {
        "dcp_name":        "Inner West Ashfield DCP 2016",
        "council_page_url": "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-controls-lep-and-dcp/development-control-plans-dcp/ashfield-dcp",
        "chapters":        ASHFIELD_CHAPTERS,
    },
}

# ─── Local baseline PDF mapping ───────────────────────────────────────────────
# Maps (council, chapter_key) → local Path of the _origin.pdf that was used for
# the original extraction.  These become the v1.0-baseline content hashes.
# Chapters not listed here fall back to downloading from council_url.

_LOCAL_PATHS: dict[tuple[str, str], Path] = {
    # ── Marrickville ─────────────────────────────────────────────────────────
    ("marrickville", "da-guidelines"):                    _arch("Marrickville DCP 2011 - Development Application Guidelines with IWLEP 2022 amendments Nov 22"),
    ("marrickville", "part1-statutory-info"):             _arch("Marrickville DCP 2011 - 1 - Statutory Information with IWLEP 2022 amendments Nov 22"),
    ("marrickville", "part2-s01-urban-design"):           _arch("Marrickville DCP 2011 - 2 1 Urban Design"),
    ("marrickville", "part2-s03-site-context-analysis"):  _arch("Marrickville DCP 2011 - 2 3 Site Context Analysis"),
    ("marrickville", "part2-s05-equity-access-mobility"): _arch("Marrickville DCP 2011 - 2 5 Equity of Access and Mobility"),
    ("marrickville", "part2-s06-privacy"):                _arch("Marrickville DCP 2011 - 2 6 Acoustic and Visual Privacy"),
    ("marrickville", "part2-s07-solar-access"):           _arch("Marrickville DCP 2011 - 2 7 Solar Access and Overshadowing"),
    ("marrickville", "part2-s08-social-impact"):          _arch("Marrickville DCP 2011 - 2 8 Social Impact Assessment"),
    ("marrickville", "part2-s09-community-safety"):       _arch("Marrickville DCP 2011 - 2 9 Community Safety"),
    ("marrickville", "part2-s10-parking"):                _arch("Marrickville DCP 2011 - 2 10 Parking"),
    ("marrickville", "part2-s11-fencing"):                _arch("Marrickville DCP 2011 - 2 11 Fencing"),
    ("marrickville", "part2-s12-signs"):                  _arch("Marrickville DCP 2011 - 2 12 Signs and Advertising Structures"),
    ("marrickville", "part2-s13-biodiversity"):           _arch("Marrickville DCP 2011 - 2 13 Biodiversity"),
    ("marrickville", "part2-s14-unique-env-features"):    _arch("Marrickville DCP 2011 - 2 14 Unique Environmental Features"),
    ("marrickville", "part2-s16-energy-efficiency"):      _arch("Marrickville DCP 2011 - 2 16 Energy Efficiency"),
    ("marrickville", "part2-s17-water-sensitive"):        _arch("Marrickville DCP 2011 - 2 17 Water Sensitive Urban Design"),
    ("marrickville", "part2-s18-landscaping"):            _arch("Marrickville DCP 2011 - 2 18 Landscaping and Open Spaces"),
    ("marrickville", "part2-s20-tree-management"):        _dl("marrickville_dcp_updates/Marrickville_DCP_2011_Section_2.20_Tree_Management_March_2023.pdf"),
    ("marrickville", "part2-s25-stormwater"):             _arch("Marrickville DCP 2011 - 2 25 Stormwater management"),
    ("marrickville", "part2-s26-entertainment-precincts"):_dl("marrickville_dcp_updates/Marrickville_DCP_2011_Section_2.26_Special_Entertainment_Precincts.pdf"),
    ("marrickville", "part3-subdivision"):                _arch("Marrickville DCP 2011 - 3 0Part3Subdivision, Amalgation, Movement Network - with IWLEP 2022 amendments"),
    ("marrickville", "part4-s1-low-density"):             _arch("Marrickville DCP 2011 - 4.1 Low Density Residential Development"),
    ("marrickville", "part4-s2-multi-dwelling"):          _arch("Marrickville DCP 2011 - 4 2 Multi Dwelling Housing and RFBs - with IWLEP 2022 amendments"),
    ("marrickville", "part4-s3-boarding-houses"):         _arch("Marrickville DCP 2011 - 4 3 Boarding Houses"),
    ("marrickville", "part5-commercial-mixed-use"):       _arch("Marrickville DCP 2011 - 5 0 Commercial and Mixed Use Development - with IWLEP 2022 amendments"),
    ("marrickville", "part6-industrial"):                 _arch("Marrickville DCP 2011 - 6 0 Industrial Development - with IWLEP 2022 amendments"),
    ("marrickville", "part7-s1-childcare"):               _arch("Marrickville DCP 2011 - 7 1 childcare centres - with IWLEP 2022 amendments"),
    ("marrickville", "part7-s3-sex-industry"):            _arch("Marrickville DCP 2011 - 7.3 Sex Industry and Adult Business Premises"),
    ("marrickville", "part8-heritage"):                   _arch("Marrickville DCP 2011 - 8.0 Heritage"),
    ("marrickville", "part9-intro"):                      _arch("Marrickville DCP 2011 - 9 0 Introduction"),
    ("marrickville", "part9-p01-lewisham-north"):         _arch("Marrickville DCP 2011 - 9 1 Lewisham North Precinct 1"),
    ("marrickville", "part9-p02-petersham-north"):        _arch("Marrickville DCP 2011 - 9 2 Petersham North - with IWLEP 2022 amendments"),
    ("marrickville", "part9-p03-stanmore-north"):         _arch("Marrickville DCP 2011 - 9 3 Stanmore North Precinct 3"),
    ("marrickville", "part9-p04-newtown-north"):          _arch("Marrickville DCP 2011 - 9 4 Newtown North and Camperdown"),
    ("marrickville", "part9-p05-lewisham-south"):         _arch("Marrickville DCP 2011 - 9 5 Lewisham South Precinct 5"),
    ("marrickville", "part9-p06-petersham-south"):        _arch("Marrickville DCP 2011 - 9 6 Petersham South Precinct 6"),
    ("marrickville", "part9-p07-stanmore-south"):         _arch("Marrickville DCP 2011 - 9 7 Stanmore South"),
    ("marrickville", "part9-p08-enmore-north"):           _arch("Marrickville DCP 2011 - 9 8 Enmore North and Newtown Central Precinct 8"),
    ("marrickville", "part9-p09-newington"):              _arch("Marrickville DCP 2011 - 9 9 Newington"),
    ("marrickville", "part9-p10-dulwich-hill-north"):     _arch("Marrickville DCP 2011 - 9 10 Dulwich Hill North"),
    ("marrickville", "part9-p11-hoskins-park"):           _arch("Marrickville DCP 2011 - 9 11 Hoskins Park Precinct 11"),
    ("marrickville", "part9-p12-marrickville-park"):      _arch("Marrickville DCP 2011 - 9 12 Marrickville Park and Morton Park"),
    ("marrickville", "part9-p13-henson-park"):            _arch("Marrickville DCP 2011 - 9 13 Henson Park"),
    ("marrickville", "part9-p14-camdenville"):            _arch("Marrickville DCP 2011 - 9 14 Camdenville Precinct 14"),
    ("marrickville", "part9-p15-enmore-park"):            _arch("Marrickville DCP 2011 - 9 15 Enmore Park"),
    ("marrickville", "part9-p16-abergeldie"):             _arch("Marrickville DCP 2011 - 9 16 Abergeldie Estate"),
    ("marrickville", "part9-p17-new-canterbury-rd"):      _arch("Marrickville DCP 2011 - 9 17 New Canterbury Road West"),
    ("marrickville", "part9-p18-dulwich-hill-stn-north"): _arch("Marrickville DCP 2011 - 9 18 Dulwich Hill Station North"),
    ("marrickville", "part9-p19-marrickville-rd-central"):_arch("Marrickville DCP 2011 - 9 19 Marrickville Road, Central"),
    ("marrickville", "part9-p20-marrickville-tc-north"):  _arch("Marrickville DCP 2011 - 9 20 Marrickville Town Centre North"),
    ("marrickville", "part9-p21-ness-park"):              _arch("Marrickville DCP 2011 - 9 21 Ness Park"),
    ("marrickville", "part9-p22-dulwich-hill-stn-south"): _arch("Marrickville DCP 2011 - 9 22 Dulwich Hill Station South Precinct 22"),
    ("marrickville", "part9-p23-marrickville-stn-west"):  _arch("Marrickville DCP 2011 - 9 23 Marrickville Station West Precinct 23"),
    ("marrickville", "part9-p24-marrickville-tc-south"):  _arch("Marrickville DCP 2011 - 9 24 Marrickville Town Centre South"),
    ("marrickville", "part9-p25-st-peters-triangle"):     _arch("Marrickville DCP 2011 - 9 25 St Peters Triangle Precinct 25"),
    ("marrickville", "part9-p26-barwon-park"):            _arch("Marrickville DCP 2011 - 9 26 Barwon Park"),
    ("marrickville", "part9-p27-barwon-park-south"):      _arch("Marrickville DCP 2011 - 9 27 Barwon Park South"),
    ("marrickville", "part9-p28-cooks-river-west"):       _arch("Marrickville DCP 2011 - 9 28 Cooks River West"),
    ("marrickville", "part9-p29-sw-marrickville"):        _arch("Marrickville DCP 2011 - 9 29 South Western Marrickville"),
    ("marrickville", "part9-p30-the-warren"):             _arch("Marrickville DCP 2011 - 9 30 The Warren"),
    ("marrickville", "part9-p31-unwins-bridge"):          _arch("Marrickville DCP 2011 - 9 31 Unwins Bridge Road"),
    ("marrickville", "part9-p32-cooks-river-east"):       _arch("Marrickville DCP 2011 - 9 32 Cooks River East"),
    ("marrickville", "part9-p33-princes-highway"):        _arch("Marrickville DCP 2011 - 9 33 Princes Highway"),
    ("marrickville", "part9-p34-tempe-reserve"):          _arch("Marrickville DCP 2011 - 9 34 Tempe Reserve"),
    ("marrickville", "part9-p35-parramatta-rd"):          _arch("Marrickville DCP 2011 - 9 35 Parramatta Road"),
    ("marrickville", "part9-p36-petersham-commercial"):   _arch("Marrickville DCP 2011 - 9 36 Petersham Commercial Precinct 36 - with IWLEP 2022 amendments"),
    ("marrickville", "part9-p37-king-st-enmore"):         _arch("Marrickville DCP 2011 - 9 37 King Street and Enmore Road Commercial Precinct"),
    ("marrickville", "part9-p38-dulwich-hill-commercial"):_arch("Marrickville DCP 2011 - 9 38 Dulwich Hill Commercial Precinct 38 - with IWLEP 2022 amendments"),
    ("marrickville", "part9-p39-marrickville-metro"):     _arch("Marrickville DCP 2011 - 9 39 Marrickville Metro"),
    ("marrickville", "part9-p40-marrickville-tc-commercial"):_arch("Marrickville DCP 2011 - 9 40 Marrickville Town Centre Comm Precinct 40 - with IWLEP 2022 amendments"),
    ("marrickville", "part9-p41-bridge-road"):            _arch("Marrickville DCP 2011 - 9 41 Bridge Road"),
    ("marrickville", "part9-p42-camperdown-north"):       _arch("Marrickville DCP 2011 - 9 42 Camperdown North"),
    ("marrickville", "part9-p43-sydney-steel"):           _arch("Marrickville DCP 2011 - 9.43 Sydney Steel Precinct 43"),
    ("marrickville", "part9-p44-carrington-road"):        _arch("Marrickville DCP 2011 - 9 44 Carrington Road"),
    ("marrickville", "part9-p45-mcgill-st"):              _arch("Marrickville DCP 2011 - 9 45 McGill Street Precinct 45"),
    ("marrickville", "part9-p46-tempe-lands"):            _arch("Marrickville DCP 2011 - 9 46 Tempe Lands Precinct"),
    ("marrickville", "part9-p47-victoria-road"):          _arch("Marrickville DCP 2011 - 9 47 Victoria Road"),
    ("marrickville", "part9-p48-mary-robert-edith"):      _arch("Marrickville DCP 2011 - 9.48 Mary Robert and Edith Street Nov 22"),
    ("marrickville", "part10-definitions"):               _arch("Marrickville DCP 2011 - 10.0 Definitions"),

    # ── Leichhardt ───────────────────────────────────────────────────────────
    ("leichhardt", "part-a-introduction"):          _arch("Leichhardt DCP 2013 - 3 - Part A  Introduction - with IWLEP 2022 amendments"),
    ("leichhardt", "part-b-connections"):           _arch("Leichhardt DCP 2013 - 4 - Part B Connections - with IWLEP 2022 amendments"),
    ("leichhardt", "part-c-s1-general"):            _arch("Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23"),
    ("leichhardt", "part-c-s2-urban-character"):    _arch("Leichhardt DCP 2013 - 6 - Part C Place Section 2 - with IWLEP 2022 amendments"),
    ("leichhardt", "part-c-s3-residential"):        _arch("Leichhardt DCP 2013 - 7 - Part C Place Section 3 - with IWLEP 2022 amendments"),
    ("leichhardt", "part-c-s4-non-residential"):    _arch("Leichhardt DCP 2013 - 8 - Part C Place Section 4 - with IWLEP 2022 amendments"),
    ("leichhardt", "part-c-s5-entertainment-precincts"): _arch("Leichhardt DCP 2013 Part C Section 5"),
    ("leichhardt", "part-d-energy"):                _arch("Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments"),
    ("leichhardt", "part-e-water"):                 _arch("Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments"),
    ("leichhardt", "part-f-food"):                  _arch("Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments"),
    # Part G was split into 3 during extraction; use first part as the local baseline.
    # Monitor will use the full-document URL on the council website.
    ("leichhardt", "part-g-s1-site-specific"):      _arch("Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023-1-50"),
    ("leichhardt", "part-g-s13-pyrmont-bridge-rd"): _arch("Leichhardt DCP 2013 - 12 - Part G Section 13 - Amdt 19 - Pyrmont Bridge Road Nov 2023"),
    ("leichhardt", "appendix-a-glossary"):          _arch("Leichhardt DCP 2013 - 13 - Appendix A Glossary - with IWLEP 2022 amendments"),
    ("leichhardt", "appendix-b-building-typologies"):_arch("Leichhardt DCP 2013 - 14 - Appendix B Building Typologies - with IWLEP 2022 amendments"),

    # ── Ashfield ─────────────────────────────────────────────────────────────
    ("ashfield", "preliminary"):              _arch("Inner West Ashfield DCP 2016  - Preliminary, Notification and Advertising - with IWLEP 2022 amendments"),
    ("ashfield", "chapter-a-miscellaneous"):  _arch("Inner West Ashfield DCP 2016 - Chapter A - Miscellaneous - with IWLEP 2022 amendments"),
    ("ashfield", "chapter-b-public-domain"):  _arch("Inner West Ashfield DCP 2016 - Chapter B - Public Domain - with IWLEP 2022 amendments"),
    ("ashfield", "chapter-c-sustainability"): _arch("Inner West Ashfield DCP 2016 - Chapter C - Sustainability IWLEP 2022 amends - 28 Mar 23"),
    ("ashfield", "chapter-d-precinct-guidelines"): _arch("Inner West Ashfield DCP 2016 - Chapter D - Precinct Guidelines with IWLEP 2022 amendments Nov 22"),
    ("ashfield", "chapter-e1-heritage"):      _arch("Inner West Ashfield DCP 2016 - Chapter E1- Heritage with IWLEP 2022 amendments"),
    ("ashfield", "chapter-e2-haberfield"):    _arch("Chapter E2 Haberfield Neighbourhood"),
    ("ashfield", "chapter-f-dev-category"):   _arch("Inner West Ashfield DCP 2016 - Chapter F - Development Category with IWLEP 2022 amendment"),
    ("ashfield", "chapter-g-definitions"):    _arch("Inner West Ashfield DCP 2016 - Chapter G - Definitions - with IWLEP 2022 amendments"),
    ("ashfield", "chapter-h-amendments"):     _arch("Inner West Ashfield DCP 2016 - Chapter H - with IWLEP 2022 amendments Apr 24"),
}

# Populate local_path into each chapter entry
for _council, _config in COUNCIL_CONFIGS.items():
    for _chap in _config["chapters"]:
        _lp = _LOCAL_PATHS.get((_council, _chap["chapter_key"]))
        if _lp is not None:
            _chap["local_path"] = _lp

# ─── Helpers ───────────────────────────────────────────────────────────────────

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def download_pdf(url: str, retries: int = 3) -> tuple[bytes, dict]:
    """
    Download a PDF from a URL.
    Returns (content_bytes, response_headers).
    Follows redirects automatically (handles Inner West .aspx handler).
    """
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=60, allow_redirects=True)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and len(resp.content) < 1000:
                raise ValueError(f"Response doesn't look like a PDF (Content-Type: {content_type})")
            return resp.content, dict(resp.headers)
        except Exception as exc:
            print(f"    [attempt {attempt}/{retries}] {exc}")
            if attempt < retries:
                time.sleep(2 * attempt)
    raise RuntimeError(f"Failed to download after {retries} attempts: {url}")


def r2_key(council: str, version: str, chapter_key: str) -> str:
    """Build the R2 object key for a source PDF."""
    return f"{SOURCE_PDF_PREFIX}/dcps/{council}/{version}/{chapter_key}.pdf"


def r2_key_state(doc_type: str, version: str, chapter_key: str) -> str:
    """Build the R2 object key for state-level documents (SEPP, ADG)."""
    return f"{SOURCE_PDF_PREFIX}/{doc_type}s/{version}/{chapter_key}.pdf"


def upload_to_r2(s3: object, content: bytes, key: str, dry_run: bool = False) -> bool:
    """Upload bytes to R2. Returns True if uploaded, False if already exists."""
    if dry_run:
        print(f"    [dry-run] would upload → r2://{R2_BUCKET_NAME}/{key}")
        return True
    try:
        # Check if already exists with same size (skip re-upload)
        try:
            existing = s3.head_object(Bucket=R2_BUCKET_NAME, Key=key)
            if existing["ContentLength"] == len(content):
                print(f"    [skip] already in R2 (same size): {key}")
                return False
        except ClientError as e:
            if e.response["Error"]["Code"] != "404":
                raise
        # Upload
        s3.put_object(
            Bucket=R2_BUCKET_NAME,
            Key=key,
            Body=content,
            ContentType="application/pdf",
        )
        print(f"    [upload] {key} ({len(content):,} bytes)")
        return True
    except Exception as exc:
        print(f"    [ERROR] upload failed for {key}: {exc}")
        raise


def upsert_registry(cur, row: dict, dry_run: bool = False):
    """Insert or update a row in dcp_chapter_registry."""
    if dry_run:
        print(f"    [dry-run] would upsert registry: {row['council']}/{row['chapter_key']}")
        return
    cur.execute(
        """
        INSERT INTO dcp_chapter_registry (
            council, dcp_name, doc_type, chapter_key, chapter_label, sort_order,
            council_url, council_page_url,
            r2_current_path, r2_version_label,
            content_hash, url_content_length, url_etag, url_last_modified,
            url_last_checked, url_last_changed,
            is_active, notes
        ) VALUES (
            %(council)s, %(dcp_name)s, %(doc_type)s, %(chapter_key)s, %(chapter_label)s, %(sort_order)s,
            %(council_url)s, %(council_page_url)s,
            %(r2_current_path)s, %(r2_version_label)s,
            %(content_hash)s, %(url_content_length)s, %(url_etag)s, %(url_last_modified)s,
            %(url_last_checked)s, %(url_last_changed)s,
            TRUE, %(notes)s
        )
        ON CONFLICT (council, chapter_key) DO UPDATE SET
            dcp_name          = EXCLUDED.dcp_name,
            chapter_label     = EXCLUDED.chapter_label,
            sort_order        = EXCLUDED.sort_order,
            council_url       = EXCLUDED.council_url,
            council_page_url  = EXCLUDED.council_page_url,
            r2_current_path   = EXCLUDED.r2_current_path,
            r2_version_label  = EXCLUDED.r2_version_label,
            content_hash      = EXCLUDED.content_hash,
            url_content_length = EXCLUDED.url_content_length,
            url_etag          = EXCLUDED.url_etag,
            url_last_modified = EXCLUDED.url_last_modified,
            url_last_checked  = EXCLUDED.url_last_checked,
            url_last_changed  = EXCLUDED.url_last_changed,
            updated_at        = NOW()
        """,
        row,
    )


# ─── Main processing ───────────────────────────────────────────────────────────

def process_council(
    council: str,
    s3,
    conn,
    dry_run: bool = False,
    skip_upload: bool = False,
) -> tuple[int, int, int]:
    """
    Process all chapters for a council.
    Returns (success, skipped, failed).
    """
    config = COUNCIL_CONFIGS[council]
    chapters = config["chapters"]
    dcp_name = config["dcp_name"]
    page_url = config["council_page_url"]

    print(f"\n{'='*60}")
    print(f"Council: {council.upper()} — {dcp_name}")
    print(f"Chapters to process: {len(chapters)}")
    print(f"{'='*60}")

    success, skipped, failed = 0, 0, 0
    cur = conn.cursor()

    for i, chapter in enumerate(chapters, 1):
        chapter_key = chapter["chapter_key"]
        label = chapter["chapter_label"]
        url_path = chapter["url_path"]
        full_url = INNER_WEST_BASE + url_path if url_path.startswith("/") else url_path

        print(f"\n[{i}/{len(chapters)}] {label}")
        print(f"  URL: {full_url}")

        r2_path = r2_key(council, VERSION_LABEL, chapter_key)

        try:
            # Load content — prefer local baseline, fall back to council website download
            local_path = chapter.get("local_path")
            if dry_run:
                source = f"local: {local_path}" if local_path else f"web: {full_url}"
                print(f"  [dry-run] would load from {source}")
                content, headers = b"", {}
                content_hash = "dry-run-hash"
                content_length = 0
                etag = None
                last_modified = None
            elif local_path and local_path.exists():
                print(f"  Reading local baseline: {local_path.name}")
                content = local_path.read_bytes()
                content_hash = sha256(content)
                content_length = len(content)
                etag = None
                last_modified = None
                print(f"  Read {content_length:,} bytes, SHA-256: {content_hash[:16]}...")
            else:
                if local_path:
                    print(f"  [WARN] local_path not found ({local_path}), falling back to download")
                print(f"  Downloading from council website...")
                content, headers = download_pdf(full_url)
                content_hash = sha256(content)
                content_length = len(content)
                etag = headers.get("ETag")
                last_modified = headers.get("Last-Modified")
                print(f"  Downloaded {content_length:,} bytes, SHA-256: {content_hash[:16]}...")

            # Upload to R2
            if not skip_upload:
                upload_to_r2(s3, content, r2_path, dry_run=dry_run)

            # Upsert registry
            from datetime import timezone, datetime
            now = datetime.now(timezone.utc)

            upsert_registry(cur, {
                "council":           council,
                "dcp_name":          dcp_name,
                "doc_type":          chapter.get("doc_type", "dcp"),
                "chapter_key":       chapter_key,
                "chapter_label":     label,
                "sort_order":        chapter.get("sort_order"),
                "council_url":       full_url,
                "council_page_url":  page_url,
                "r2_current_path":   r2_path,
                "r2_version_label":  VERSION_LABEL,
                "content_hash":      content_hash,
                "url_content_length": content_length,
                "url_etag":          etag,
                "url_last_modified": last_modified,
                "url_last_checked":  now,
                "url_last_changed":  now,  # First time = baseline
                "notes":             None,
            }, dry_run=dry_run)

            if not dry_run:
                conn.commit()
            success += 1

        except Exception as exc:
            print(f"  [FAILED] {exc}")
            if not dry_run:
                conn.rollback()
            failed += 1

        # Polite delay between requests to council server
        if not dry_run and i < len(chapters):
            time.sleep(0.5)

    cur.close()
    return success, skipped, failed


def process_local_files(
    s3,
    conn,
    dry_run: bool = False,
    skip_upload: bool = False,
) -> tuple[int, int, int]:
    """Upload local SEPP/ADG files to R2 and register them."""
    print(f"\n{'='*60}")
    print("Local Files (SEPP/ADG)")
    print(f"Files to process: {len(LOCAL_FILES)}")
    print(f"{'='*60}")

    success, skipped, failed = 0, 0, 0
    cur = conn.cursor()

    for i, entry in enumerate(LOCAL_FILES, 1):
        label = entry["chapter_label"]
        local_path = entry["local_path"]
        doc_type = entry["doc_type"]
        chapter_key = entry["chapter_key"]

        print(f"\n[{i}/{len(LOCAL_FILES)}] {label}")
        print(f"  Local: {local_path}")

        if not local_path.exists():
            print(f"  [SKIP] file not found: {local_path}")
            skipped += 1
            continue

        r2_path = r2_key_state(doc_type, VERSION_LABEL, chapter_key)

        try:
            content = local_path.read_bytes() if not dry_run else b""
            content_hash = sha256(content) if not dry_run else "dry-run"
            content_length = len(content)

            if not dry_run:
                print(f"  Read {content_length:,} bytes, SHA-256: {content_hash[:16]}...")

            if not skip_upload:
                upload_to_r2(s3, content, r2_path, dry_run=dry_run)

            from datetime import timezone, datetime
            now = datetime.now(timezone.utc)

            upsert_registry(cur, {
                "council":            entry.get("council", "state"),
                "dcp_name":           entry.get("dcp_name", label),
                "doc_type":           doc_type,
                "chapter_key":        chapter_key,
                "chapter_label":      label,
                "sort_order":         entry.get("sort_order"),
                "council_url":        entry.get("council_url"),
                "council_page_url":   None,
                "r2_current_path":    r2_path,
                "r2_version_label":   VERSION_LABEL,
                "content_hash":       content_hash,
                "url_content_length": content_length,
                "url_etag":           None,
                "url_last_modified":  None,
                "url_last_checked":   now if entry.get("council_url") else None,
                "url_last_changed":   now,
                "notes":              "Uploaded from local file. SEPP/LEP monitored via RSS.",
            }, dry_run=dry_run)

            if not dry_run:
                conn.commit()
            success += 1

        except Exception as exc:
            print(f"  [FAILED] {exc}")
            if not dry_run:
                conn.rollback()
            failed += 1

    cur.close()
    return success, skipped, failed


# ─── Entry point ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Upload council DCP PDFs to R2 and populate dcp_chapter_registry"
    )
    parser.add_argument(
        "--council",
        choices=["marrickville", "leichhardt", "ashfield", "local", "all"],
        default="all",
        help="Which council to process (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without downloading, uploading, or writing to DB",
    )
    parser.add_argument(
        "--skip-upload",
        action="store_true",
        help="Download and register in DB but skip R2 upload (useful for registry-only updates)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("R2 PDF Upload + Chapter Registry Initialisation")
    print("=" * 60)
    if args.dry_run:
        print("DRY RUN — no downloads, uploads, or DB writes will occur")
    print()

    # ── R2 client ─────────────────────────────────────────────────────────────
    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    # ── DB connection ─────────────────────────────────────────────────────────
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    # ── Run migrations ────────────────────────────────────────────────────────
    if not args.dry_run:
        migration_file = Path(__file__).parent.parent / "migrations" / "007_dcp_chapter_registry.sql"
        if migration_file.exists():
            print(f"Running migration: {migration_file.name}")
            cur = conn.cursor()
            cur.execute(migration_file.read_text(encoding="utf-8"))
            conn.commit()
            cur.close()
            print("Migration complete.\n")
        else:
            print(f"Warning: migration file not found at {migration_file}")

    # ── Process ───────────────────────────────────────────────────────────────
    totals = {"success": 0, "skipped": 0, "failed": 0}

    if args.council in ("all", "marrickville"):
        s, sk, f = process_council("marrickville", s3, conn, args.dry_run, args.skip_upload)
        totals["success"] += s; totals["skipped"] += sk; totals["failed"] += f

    if args.council in ("all", "leichhardt"):
        s, sk, f = process_council("leichhardt", s3, conn, args.dry_run, args.skip_upload)
        totals["success"] += s; totals["skipped"] += sk; totals["failed"] += f

    if args.council in ("all", "ashfield"):
        s, sk, f = process_council("ashfield", s3, conn, args.dry_run, args.skip_upload)
        totals["success"] += s; totals["skipped"] += sk; totals["failed"] += f

    if args.council in ("all", "local"):
        s, sk, f = process_local_files(s3, conn, args.dry_run, args.skip_upload)
        totals["success"] += s; totals["skipped"] += sk; totals["failed"] += f

    # ── Summary ───────────────────────────────────────────────────────────────
    conn.close()

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Succeeded : {totals['success']}")
    print(f"  Skipped   : {totals['skipped']}")
    print(f"  Failed    : {totals['failed']}")
    if totals["failed"] > 0:
        print("\n  Some chapters failed. Re-run to retry only failures:")
        print("  python3 scripts/r2_upload_pdfs.py --council <council>")
        sys.exit(1)
    else:
        print("\n  All done. Registry is populated and PDFs are in R2.")
        print("  Next step: run r2_monitor.py on a weekly schedule.")


if __name__ == "__main__":
    main()
