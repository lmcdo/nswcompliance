/**
 * Render all 7 satellite report PDFs with comprehensive dummy data.
 * Usage: npx tsx scripts/render-all-pdfs.tsx
 *
 * Fetches a real aerial tile from SIX Maps and uses a realistic lot polygon.
 * Saves to ~/Downloads/.
 */

import { renderToBuffer } from '@react-pdf/renderer';
import React from 'react';
import fs from 'fs';
import path from 'path';

// Reports
import { SolarYieldReportDocument, type SolarYieldReportData } from '../lib/pdf/solar-yield-report';
import { ShadowReportDocument, type ShadowReportData } from '../lib/pdf/shadow-report';
import { FloodTruthReportDocument, type FloodReportData } from '../lib/pdf/flood-truth-report';
import { BushfireReportDocument, type BushfireReportData } from '../lib/pdf/bushfire-report';
import { GrannyFlatReportDocument, type GrannyFlatReportData } from '../lib/pdf/granny-flat-report';
import { ThreatRadarReportDocument, type ThreatRadarReportData } from '../lib/pdf/threat-radar-report';
import { PreDAHistoryReportDocument, type PreDAHistoryReportData } from '../lib/pdf/pre-da-history-report';

// Helpers
import { fetchAerialTileBase64 } from '../lib/pdf/aerial-tile';
import { getLogoBase64 } from '../lib/pdf/logo';

const OUT_DIR = path.join(process.env.USERPROFILE || process.env.HOME || '.', 'Downloads');

// 16 O'Connor St Haberfield — realistic lot polygon (approx)
const LAT = -33.8791;
const LNG = 151.1389;
const ADDRESS = "16 O'Connor Street, Haberfield NSW 2045";
const RUN_DATE = '2026-05-12';

// Realistic lot polygon for Haberfield (small rectangular lot ~15m x 40m)
const LOT_POLYGON = {
  type: 'Polygon',
  coordinates: [[
    [151.13875, -33.87895],
    [151.13905, -33.87895],
    [151.13905, -33.87925],
    [151.13875, -33.87925],
    [151.13875, -33.87895],
  ]],
};

async function main() {
  console.log('Fetching aerial tile and logo...');
  const [tile_b64, logo_b64] = await Promise.all([
    fetchAerialTileBase64(LAT, LNG, 'property'),
    Promise.resolve(getLogoBase64()),
  ]);
  console.log(`Tile: ${tile_b64 ? `${(tile_b64.length / 1024).toFixed(0)}KB` : 'MISSING'}, Logo: ${logo_b64 ? 'OK' : 'MISSING'}`);

  const common = { address: ADDRESS, run_date: RUN_DATE, lat: LAT, lng: LNG, tile_b64, logo_b64 };

  // ---- 1. Solar Yield ----
  const solarData: SolarYieldReportData = {
    ...common,
    lga_name: 'Inner West',
    max_panels: 24,
    max_panel_area_m2: 39.4,
    annual_kwh_estimate: 9120,
    sunshine_hours_per_year: 1752,
    best_pitch_deg: 22,
    best_azimuth_deg: 15,
    roof_area_m2: 185,
    is_heritage: false,
    is_commercial_scale: false,
    imagery_date: '2024-11-15',
    coverage_available: true,
    annual_saving_aud: 2190,
    system_cost_aud: 9600,
    payback_years: 4.4,
    ten_year_return_aud: 12300,
    system_kw: 9.6,
    solar_grade: 'A',
    solar_grade_reason: 'Excellent solar potential',
    sensitivity: [
      { feed_in_rate: 0.04, annual_saving: 1822, payback_years: 5.3 },
      { feed_in_rate: 0.06, annual_saving: 2190, payback_years: 4.4 },
      { feed_in_rate: 0.10, annual_saving: 2445, payback_years: 3.9 },
    ],
    monthly_kwh: [904, 821, 830, 721, 620, 529, 593, 675, 748, 821, 866, 994],
    neighbour_max_height_m: 8.5,
    is_paid: true,
    confidence: 'high',
    data_sources: ['Google Solar API', 'NSW SIX Maps', 'BOM solar irradiance'],
    shareable_url: 'https://canibuildit.com.au/reports/solar-yield/demo-123',
    firm_name: 'Demo Property Advisory',
  };

  // ---- 2. Shadow ----
  const shadowData: ShadowReportData = {
    ...common,
    zone: 'R2 Low Density Residential',
    lga_name: 'Inner West',
    height_m: 8.5,
    height_source: 'LEP (Inner West) 2022 — Height of Buildings Map',
    lep_name: 'Inner West LEP 2022',
    scenarios: [
      { scenario: 'jun21_9am', label: '21 Jun 9am', date: '2026-06-21', time_local: '09:00', shadow_length_m: 14.2, shadow_overlap_fraction: 0.35, shadow_direction_deg: 285, overlaps_subject_lot: true },
      { scenario: 'jun21_12pm', label: '21 Jun 12pm', date: '2026-06-21', time_local: '12:00', shadow_length_m: 8.1, shadow_overlap_fraction: 0.12, shadow_direction_deg: 0, overlaps_subject_lot: false },
      { scenario: 'jun21_3pm', label: '21 Jun 3pm', date: '2026-06-21', time_local: '15:00', shadow_length_m: 14.8, shadow_overlap_fraction: 0.28, shadow_direction_deg: 75, overlaps_subject_lot: true },
      { scenario: 'sep21_12pm', label: '21 Sep 12pm', date: '2026-09-21', time_local: '12:00', shadow_length_m: 5.2, shadow_overlap_fraction: 0.05, shadow_direction_deg: 0, overlaps_subject_lot: false },
      { scenario: 'dec21_12pm', label: '21 Dec 12pm', date: '2026-12-21', time_local: '12:00', shadow_length_m: 2.8, shadow_overlap_fraction: 0.0, shadow_direction_deg: 0, overlaps_subject_lot: false },
    ],
    construction_change_score: 0.72,
    construction_change_detected: true,
    adg_compliant: false,
    worst_case_scenario: 'jun21_9am',
    confidence: 'high',
    data_sources: ['Sentinel-2 change detection', 'NSW SIX Maps', 'LEP Height of Buildings', 'Solar geometry model'],
    warnings: ['North-facing lot boundary used as proxy — actual neighbour footprint may differ.'],
    lot_polygon: LOT_POLYGON as any,
    north_proxy_polygon: {
      type: 'Polygon',
      coordinates: [[
        [151.13875, -33.87860],
        [151.13905, -33.87860],
        [151.13905, -33.87895],
        [151.13875, -33.87895],
        [151.13875, -33.87860],
      ]],
    } as any,
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/shadow/demo-456',
    firm_name: 'Demo Property Advisory',
  };

  // ---- 3. Flood Truth ----
  const floodData: FloodReportData = {
    ...common,
    lga_name: 'Inner West',
    epi_flood_class: 'flood_planning_area',
    epi_flood_label: 'Flood Planning Area',
    sar_flood_detected: false,
    sar_confidence: 'high',
    sar_analysis_date: '2026-04-28',
    ems_flood_detected: true,
    ems_activations: [
      { activation_id: 'EMSR-2022-001', event_name: 'Eastern Australia Floods March 2022', event_date: '2022-03-08', flood_type: 'Riverine' },
      { activation_id: 'EMSR-2021-014', event_name: 'NSW Floods March 2021', event_date: '2021-03-20', flood_type: 'Flash flooding' },
    ],
    jrc_water_occurrence_pct: 3.2,
    jrc_data_year: 2021,
    dea_wofs_frequency_pct: 1.8,
    bom_gauge_name: 'Parramatta River at Silverwater',
    bom_gauge_distance_km: 4.2,
    bom_last_major_flood_date: '2022-03-09',
    bom_last_major_flood_peak_m: 4.85,
    bom_flood_history: [
      { date: '2022-03-09', peak_m: 4.85, ari_category: '1-in-50 year' },
      { date: '2021-03-22', peak_m: 3.92, ari_category: '1-in-20 year' },
      { date: '2016-06-05', peak_m: 3.15, ari_category: '1-in-10 year' },
    ],
    flood_study_name: 'Parramatta River Flood Study 2020',
    flood_study_date: '2020',
    ground_elevation_m_ahd: 6.8,
    in_100yr_flood_zone: true,
    flood_studies: [
      {
        study_key: 'parramatta_river_2020',
        study_name: 'Parramatta River Flood Study',
        source: 'Inner West Council / NSW SES flooddata.ses.nsw.gov.au',
        design: {
          '1% AEP': { depth_m: 1.2, level_m_ahd: 8.0 },
          '0.5% AEP': { depth_m: 1.8, level_m_ahd: 8.6 },
          '0.2% AEP': { depth_m: 2.4, level_m_ahd: 9.2 },
          'PMF': { depth_m: 4.1, level_m_ahd: 10.9 },
        },
        historical: {
          'March 2022': { depth_m: 0.8, level_m_ahd: 7.6 },
        },
      },
    ],
    s1_gap_warning: null,
    data_currency: '2026-04-28',
    flood_signal: 'elevated',
    confidence: 'high',
    data_sources: ['Sentinel-1 SAR', 'Copernicus EMS', 'JRC Global Surface Water', 'DEA WOfS', 'BOM flood gauge', 'NSW EPI overlay', 'SES Flood Studies'],
    warnings: ['Property is within 1% AEP flood extent.', 'EMS activated for this area twice in the last 5 years.'],
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/flood/demo-789',
    firm_name: 'Demo Property Advisory',
  };

  // ---- 4. Bushfire ----
  const bushfireData: BushfireReportData = {
    ...common,
    is_bushfire_prone: true,
    designation_source: 'NSW RFS Bushfire Prone Land Map (GDA2020)',
    designation_category: 'Vegetation Category 1',
    designation_guideline: 'AS 3959:2018 — Construction of buildings in bushfire-prone areas',
    estimated_bal_band: 'BAL-29',
    bal_assessment_likely_required: true,
    bal_formal_assessment_cost_range: '$2,500–$5,000',
    bal_assessor_directory_url: 'https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/find-a-practitioner',
    fire_signal: 'elevated',
    compliance: {
      state_legislation: 'Environmental Planning and Assessment Regulation 2021 (cl 45)',
      rfs_referral_required: true,
      rfs_referral_triggers: ['New dwelling', 'Additions > 50m²', 'Change of use to residential', 'Subdivision creating additional lots'],
      cdc_pathway_available: false,
      clearing_10_50_entitled: true,
      clearing_10_50_exceptions: 'Heritage items, threatened species habitat',
      cross_overlays: [
        { type: 'Heritage Conservation Area', value: 'Haberfield Heritage Conservation Area', source: 'Inner West LEP 2022' },
        { type: 'Acid Sulfate Soils', value: 'Class 4', source: 'Inner West LEP 2022' },
      ],
      estimated_consultant_costs: '$2,500–$5,000 for BAL assessment, $800–$1,500 for bushfire report',
      zone: 'R2 Low Density Residential',
      compliance_depth: 'full',
      legislation_url: 'https://legislation.nsw.gov.au/view/html/inforce/current/sl-2021-0759#sec.45',
    },
    data_currency: '2026-05-01',
    confidence: 'high',
    data_sources: ['NSW RFS Bushfire Prone Land Map (GDA2020)', 'Inner West LEP 2022', 'NSW ePlanning Portal'],
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/bushfire/demo-abc',
    firm_name: 'Demo Property Advisory',
  };

  // ---- 5. Granny Flat ----
  const grannyFlatData: GrannyFlatReportData = {
    ...common,
    lot_area_m2: 557,
    main_dwelling_area_m2: 180,
    confirmed_structure_count: 1,
    granny_flat_buildable: true,
    max_floor_area_m2: 60,
    estimated_weekly_rent_aud: 550,
    rental_yield_annual_pct: 7.2,
    assumed_build_cost_aud: 180000,
    confidence: 'high',
    confidence_reason: 'Lot area, zone, and structure count confirmed via spatial data.',
    warnings: [],
    data_sources: ['NSW ePlanning Portal', 'SEPP (Exempt and Complying Development Codes) 2008', 'SIX Maps'],
    lot_polygon: LOT_POLYGON as any,
    lga_name: 'Inner West',
    lga_slug: 'inner-west',
    dcp_sd_setbacks: [
      { type: 'Front setback', value: '3m minimum', source: 'Inner West DCP 2022, Part C, cl 4.3' },
      { type: 'Side setback', value: '0.9m minimum', source: 'Inner West DCP 2022, Part C, cl 4.3' },
      { type: 'Rear setback', value: '3m minimum', source: 'Inner West DCP 2022, Part C, cl 4.3' },
      { type: 'Max wall height', value: '3.8m', source: 'SEPP (E&C) 2008, Div 2, cl 3.2' },
      { type: 'Max overall height', value: '4.8m', source: 'SEPP (E&C) 2008, Div 2, cl 3.2' },
    ],
    dcp_name: 'Inner West DCP 2022',
    dcp_url: 'https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/development-control-plans',
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/granny-flat/demo-def',
    firm_name: 'Demo Property Advisory',
  };

  // ---- 6. Threat Radar ----
  const threatRadarData: ThreatRadarReportData = {
    ...common,
    council_name: 'Inner West',
    applications: [
      {
        PlanningPortalApplicationNumber: 'DA/2026/0142',
        ApplicationType: 'DA',
        DevelopmentType: 'Residential - Alterations & additions to dwelling houses',
        ApplicationDescription: 'Demolition of existing rear structures and construction of a two-storey addition to the rear of the dwelling house including new garage, internal alterations, landscaping, and associated works.',
        LodgementDate: '2026-04-15',
        Status: 'Under Assessment',
        PropertyAddress: '22 O\'Connor Street, Haberfield NSW 2045',
        CostOfDevelopment: 485000,
        NumberOfNewDwellings: 0,
        _distance_m: 45,
        Latitude: -33.8794,
        Longitude: 151.1392,
        NumberOfStoreys: 2,
        EpiVariationProposedFlag: 'No',
      },
      {
        PlanningPortalApplicationNumber: 'DA/2026/0098',
        ApplicationType: 'DA',
        DevelopmentType: 'Residential - Multi dwelling housing',
        ApplicationDescription: 'Demolition of existing dwelling and construction of a three-storey residential flat building containing 6 apartments, basement parking for 8 vehicles, landscaping, and stormwater management.',
        LodgementDate: '2026-03-22',
        DeterminationDate: '2026-05-01',
        Status: 'Approved',
        PropertyAddress: '148 Ramsay Street, Haberfield NSW 2045',
        CostOfDevelopment: 3200000,
        NumberOfNewDwellings: 6,
        _distance_m: 180,
        Latitude: -33.8778,
        Longitude: 151.1401,
        NumberOfStoreys: 3,
        DemolitionDwellings: 1,
        EpiVariationProposedFlag: 'Yes',
        SubdivisionProposedFlag: 'Yes',
      },
      {
        PlanningPortalApplicationNumber: 'CDC/2026/0055',
        ApplicationType: 'CDC',
        DevelopmentType: 'Residential - Secondary dwelling (granny flat)',
        ApplicationDescription: 'Construction of a secondary dwelling (granny flat) at the rear of the existing dwelling house.',
        LodgementDate: '2026-04-02',
        DeterminationDate: '2026-04-18',
        Status: 'Approved',
        PropertyAddress: '8 Waratah Street, Haberfield NSW 2045',
        CostOfDevelopment: 195000,
        NumberOfNewDwellings: 1,
        _distance_m: 220,
        Latitude: -33.8803,
        Longitude: 151.1375,
      },
      {
        PlanningPortalApplicationNumber: 'DA/2025/0891',
        ApplicationType: 'DA',
        DevelopmentType: 'Residential - New dwelling house',
        ApplicationDescription: 'Demolition of existing dwelling and construction of a new two-storey dwelling house with swimming pool, landscaping, and new driveway.',
        LodgementDate: '2025-12-10',
        DeterminationDate: '2026-03-15',
        Status: 'Approved',
        PropertyAddress: '31 Dalhousie Street, Haberfield NSW 2045',
        CostOfDevelopment: 1850000,
        NumberOfNewDwellings: 1,
        _distance_m: 310,
        Latitude: -33.8810,
        Longitude: 151.1370,
        NumberOfStoreys: 2,
        DemolitionDwellings: 1,
      },
      {
        PlanningPortalApplicationNumber: 'DA/2026/0167',
        ApplicationType: 'DA',
        DevelopmentType: 'Residential - Alterations & additions to dwelling houses',
        ApplicationDescription: 'First-floor addition to existing single-storey dwelling including 2 bedrooms, bathroom, and balcony. New rear deck at ground level.',
        LodgementDate: '2026-04-28',
        Status: 'Under Assessment',
        PropertyAddress: '5 Rogers Avenue, Haberfield NSW 2045',
        CostOfDevelopment: 320000,
        NumberOfNewDwellings: 0,
        _distance_m: 380,
        Latitude: -33.8775,
        Longitude: 151.1365,
        NumberOfStoreys: 2,
      },
      {
        PlanningPortalApplicationNumber: 'DA/2026/0121',
        ApplicationType: 'DA',
        DevelopmentType: 'Commercial - Shop fit-out',
        ApplicationDescription: 'Internal fit-out of existing ground-floor commercial tenancy for use as a cafe including mechanical ventilation, grease trap, and signage.',
        LodgementDate: '2026-04-05',
        Status: 'Under Assessment',
        PropertyAddress: '154 Ramsay Street, Haberfield NSW 2045',
        CostOfDevelopment: 95000,
        NumberOfNewDwellings: 0,
        _distance_m: 420,
        Latitude: -33.8776,
        Longitude: 151.1405,
      },
    ],
    window_days: 180,
    radius_m: 500,
    is_paid: true,
    firm_name: 'Demo Property Advisory',
  };

  // ---- 7. Pre-DA History ----
  const preDaData: PreDAHistoryReportData = {
    address: ADDRESS,
    run_date: RUN_DATE,
    lat: LAT,
    lon: LNG,
    council: 'Inner West',
    heritage_flag: true,
    heritage_note: 'Haberfield Heritage Conservation Area (Item I120) — Inner West LEP 2022, Schedule 5',
    timeline: [
      { year: 2017, level: 'stable', label: 'No significant change', similarity: 0.95 },
      { year: 2018, level: 'stable', label: 'No significant change', similarity: 0.93 },
      { year: 2019, level: 'minor', label: 'Rear addition constructed', similarity: 0.82, change_type: 'construction', explanation: 'Ground-floor extension to rear of dwelling.', da_events: [{ pan: 'DA/2019/0432', status: 'Approved', app_type: 'DA', dev_type: 'Residential - Alterations & additions', date: '2019-08-15' }] },
      { year: 2020, level: 'stable', label: 'No significant change', similarity: 0.91 },
      { year: 2021, level: 'stable', label: 'No significant change', similarity: 0.94 },
      { year: 2022, level: 'minor', label: 'Landscaping change detected', similarity: 0.85, change_type: 'vegetation', explanation: 'Tree removal and replanting visible in imagery.', ndvi_delta: -0.15 },
      { year: 2023, level: 'stable', label: 'No significant change', similarity: 0.92 },
      { year: 2024, level: 'stable', label: 'No significant change', similarity: 0.96 },
      { year: 2025, level: 'stable', label: 'No significant change', similarity: 0.94 },
    ],
    wayback_ssim: { '2017': 0.95, '2018': 0.93, '2019': 0.82, '2020': 0.91, '2021': 0.94, '2022': 0.85, '2023': 0.92, '2024': 0.96, '2025': 0.94 },
    data_quality_note: 'Sentinel-2 imagery available for all years. NSW Planning Portal DA records matched.',
    logo_b64: logo_b64,
    is_paid: true,
    shareable_url: 'https://canibuildit.com.au/reports/pre-da-history/demo-ghi',
    firm_name: 'Demo Property Advisory',
  };

  // Render all
  const reports: Array<{ name: string; filename: string; element: React.ReactElement }> = [
    { name: 'Solar Yield', filename: 'solar-yield-report-demo.pdf', element: React.createElement(SolarYieldReportDocument, { data: solarData }) },
    { name: 'Shadow', filename: 'shadow-report-demo.pdf', element: React.createElement(ShadowReportDocument, { data: shadowData }) },
    { name: 'Flood Truth', filename: 'flood-truth-report-demo.pdf', element: React.createElement(FloodTruthReportDocument, { data: floodData }) },
    { name: 'Bushfire', filename: 'bushfire-report-demo.pdf', element: React.createElement(BushfireReportDocument, { data: bushfireData }) },
    { name: 'Granny Flat', filename: 'granny-flat-report-demo.pdf', element: React.createElement(GrannyFlatReportDocument, { data: grannyFlatData }) },
    { name: 'Threat Radar', filename: 'threat-radar-report-demo.pdf', element: React.createElement(ThreatRadarReportDocument, { data: threatRadarData }) },
    { name: 'Pre-DA History', filename: 'pre-da-history-report-demo.pdf', element: React.createElement(PreDAHistoryReportDocument, { data: preDaData }) },
  ];

  for (const r of reports) {
    try {
      console.log(`Rendering ${r.name}...`);
      const buf = await renderToBuffer(r.element as any);
      const outPath = path.join(OUT_DIR, r.filename);
      fs.writeFileSync(outPath, buf);
      console.log(`  -> ${outPath} (${(buf.length / 1024).toFixed(0)} KB)`);
    } catch (err) {
      console.error(`  FAILED: ${r.name}`, err);
    }
  }

  console.log('\nDone!');
}

main().catch(console.error);
