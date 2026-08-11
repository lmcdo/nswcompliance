-- Migration 042b: Seed initial disclaimer versions for all satellite products.
-- These are the v1 disclaimers active from launch. When disclaimers change,
-- insert a new version row and set superseded_at on the old one.
-- Date: 2026-05-18
--
-- HISTORICAL RECORD — do not edit the rows below; they are what was seeded.
-- Superseded since:
--   shadow-v1 -> shadow-v2 in migrations/064_shadow_disclaimer_v2_pvlib_removal.sql
--     (2026-08-06): the shadow source_attributions here name pvlib, which the
--     running code has never imported. Read 064, not this file, for the
--     current shadow attribution.

INSERT INTO disclaimer_versions (pipeline_name, version, headline_disclaimer, limitations_text, source_attributions)
VALUES

-- BUSHFIRE
('bushfire', 'bushfire-v1',
 'This report is an indicative pre-screen only and does not constitute a formal Bushfire Attack Level (BAL) assessment, planning advice, or bushfire safety recommendation. A formal BAL assessment by an accredited practitioner is required before any development application or construction.',
 'Limitations: (1) BAL band is estimated from vegetation category mapping — actual BAL depends on slope, vegetation structure, and distance to classified vegetation measured on site. (2) The RFS Bush Fire Prone Land Map is updated periodically and may not reflect recent changes. (3) Cross-overlay data (flood, heritage, zone) is sourced from spatial databases that may not be current. (4) This screening does not assess compliance with AS 3959 construction standards. (5) Clearing entitlement distances are indicative only — actual entitlements depend on vegetation type and local council requirements.',
 'NSW Rural Fire Service Bush Fire Prone Land Map (ArcGIS REST, mapprod3.environment.nsw.gov.au). The RFS states: "This map is provided as a guide only. Users should verify information with their local council." PostGIS spatial_overlays derived from NSW Planning Portal and SEED datasets.'),

-- SOLAR YIELD
('solar-yield', 'solar-yield-v1',
 'This report provides an estimate of rooftop solar potential based on automated analysis of aerial imagery and irradiance data. It is not a professional solar assessment or installation quote. Actual solar yield depends on installation quality, panel selection, shading conditions, weather variability, and other factors not captured in this analysis.',
 'Limitations: (1) Roof geometry is derived from Google Solar API aerial imagery — imagery date and resolution may not reflect current roof condition. (2) Panel count and layout are modelled, not measured. (3) Annual kWh yield is an estimate based on historical irradiance data and assumed panel efficiency — actual generation varies year to year. (4) ROI calculations use assumed electricity prices and self-consumption ratios that may not match your actual usage. (5) Heritage constraints are checked against available data but heritage conservation areas may not be fully mapped.',
 'Google Solar API (solar.googleapis.com). Google states: "Solar API data is provided as-is. Actual solar performance depends on many factors." Heritage data from NSW Planning Portal regulatory provisions.'),

-- FLOOD
('flood', 'flood-v1',
 'This report aggregates publicly available flood data from multiple independent sources. It is not a formal flood study, flood risk assessment, or substitute for a Section 10.7 planning certificate. The composite flood signal is derived by PlotDetect from government data sources and does not represent an official government designation.',
 'Limitations: (1) Not all areas of NSW have comprehensive flood study coverage — absence of data does not mean absence of flood risk. (2) EPI flood overlays cover approximately 11 LGAs with polygon data. (3) Satellite-based flood detection (JRC, DEA WOfS, Sentinel-1) operates at 10-30m resolution and may not detect localised flooding. (4) BoM gauge data depends on proximity to the nearest gauge — distant gauges may not reflect conditions at the subject property. (5) Copernicus EMS activations only cover declared emergencies, not all flood events. (6) The flood signal confidence level is our own composite metric, not an official standard.',
 'NSW SEED EPI Flood Planning WFS (mapprod3.environment.nsw.gov.au). Copernicus Emergency Management Service (emergency.copernicus.eu). JRC Global Surface Water (global-surface-water.appspot.com). Geoscience Australia DEA Water Observations from Space (ows.dea.ga.gov.au). Bureau of Meteorology Water Data Online. Each source has its own accuracy limitations — see the full report for per-source details.'),

-- SHADOW
('shadow', 'shadow-v1',
 'This report provides an indicative shadow analysis based on modelled building heights and solar position calculations. It is not a formal shadow study, ADG compliance assessment, or planning advice. The ADG solar access test result is based on modelled scenarios and may differ from a professional shadow analysis using measured building dimensions.',
 'Limitations: (1) Building heights are estimated from LEP height controls or spatial data — actual building heights may differ. (2) Shadow calculations assume flat terrain — sloping sites will produce different shadow patterns. (3) The pybdshadow model uses simplified building geometry (extruded footprints) — actual shadow patterns depend on roof form, setbacks, and architectural detail. (4) Construction change detection via Sentinel-2 spectral analysis operates at 10m resolution and is heuristic. (5) ADG solar access scenarios are modelled for Jun 21 and Sep 21 only — other times of year are not assessed.',
 'pvlib solar position library (NREL-backed, peer-reviewed). pybdshadow shadow casting (open source). Element84 Earth Search Sentinel-2 L2A imagery (ESA Copernicus). NSW Planning Portal LEP height controls.'),

-- GRANNY FLAT
('granny-flat', 'granny-flat-v1',
 'This report provides a preliminary eligibility screening for secondary dwelling (granny flat) construction under SEPP (Housing) 2021. It is not a planning assessment, feasibility study, or development approval. Eligibility for the complying development (CDC) pathway depends on site-specific factors that require professional assessment.',
 'Limitations: (1) Structure detection uses automated aerial imagery analysis (SAM segmentation) at approximately 70-80% accuracy — structures may be missed or incorrectly identified. (2) Aerial imagery date varies and may not reflect current site conditions. (3) This screening checks lot area, zoning, and basic setbacks only — it does not check easements, covenants, stormwater, services, soil conditions, or tree preservation orders. (4) Flood control lot status is checked against available spatial data covering approximately 12 LGAs — status is shown as unknown outside coverage. (5) Rental yield estimates use historical bond data and assumed parameters that may not reflect current market conditions.',
 'NSW SIX Maps 10cm aerial imagery (maps.six.nsw.gov.au, CC-BY). SAM segmentation model (Meta AI, MIT licence). SEPP (Housing) 2021 rule parameters (NSW Legislation). NSW Fair Trading rental bond data. NSW Planning Portal zone and heritage data.'),

-- THREAT RADAR
('threat-radar', 'threat-radar-v1',
 'This report shows development applications (DAs) and complying development certificates (CDCs) lodged near the subject property, sourced from the NSW ePlanning Portal. It does not represent a complete record of all development activity. Not all councils lodge applications on the same timeline, and historical records may be incomplete.',
 'Limitations: (1) The ePlanning Portal dataset is comprehensive from approximately July 2021 — earlier applications may not appear. (2) Not all councils lodge applications at the same speed — there may be a delay between lodgement and appearance in the portal. (3) Distance is calculated from the application coordinates to the subject property coordinates using the Haversine formula — actual proximity depends on lot boundaries, not point distances. (4) Application status reflects the portal data at time of query and may not be current. (5) Some development types (exempt development, internal works) do not require lodgement and will not appear.',
 'NSW ePlanning Portal (api.apps1.nsw.gov.au/eplanning/data/v0). The NSW Department of Planning states: "Information on this site is provided in good faith and is believed to be accurate at the time of publication."'),

-- PRE-DA HISTORY
('pre-da-history', 'pre-da-history-v1',
 'This report combines satellite imagery analysis with planning records to identify physical changes and development applications associated with the subject property. It is not a building inspection, compliance audit, or substitute for professional due diligence. Satellite detection is indicative and may not identify all changes.',
 'Limitations: (1) Sentinel-2 satellite imagery operates at 10m resolution — changes smaller than this (internal renovations, minor works) will not be detected. (2) Spectral change detection (NDVI/NDBI) is heuristic and may produce false positives from seasonal vegetation changes or imagery artefacts. (3) DA records are sourced from the ePlanning Portal — comprehensive from July 2021 only. (4) Heritage status is checked against available spatial data and may not include all heritage items or conservation areas. (5) This analysis covers 2017-2024 only — works before 2017 are not assessed.',
 'Element84 Earth Search Sentinel-2 L2A imagery (ESA Copernicus). NSW ePlanning Portal (api.apps1.nsw.gov.au). NSW Planning Portal heritage spatial data. Esri World Imagery Wayback (conditional, for small lots).')

ON CONFLICT (pipeline_name, version) DO NOTHING;
