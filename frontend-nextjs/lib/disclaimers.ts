/**
 * Consolidated disclaimer strings — single source of truth.
 *
 * Update this file when legal language changes. All layouts, PDF reports,
 * interactive tools, and payment flows import from here.
 */

// ---------------------------------------------------------------------------
// Base fragments (compose into full disclaimers)
// ---------------------------------------------------------------------------

/** Core "indicative only" statement used almost everywhere. */
export const INDICATIVE_ONLY =
  'Results are indicative only and do not constitute planning, legal, or financial advice.';

/** Standard professional verification call-to-action. */
export const VERIFY_WITH_PROFESSIONAL =
  'Always consult a qualified professional before making decisions.';

/** Certifier/planner-specific verification. */
export const VERIFY_WITH_CERTIFIER =
  'Confirm with a registered certifier or town planner.';

/** Government data accuracy caveat. */
export const DATA_ACCURACY =
  'Government data sources may contain errors or lag behind recent amendments to planning instruments.';

// ---------------------------------------------------------------------------
// Layout footer disclaimers
// ---------------------------------------------------------------------------

/** Footer text for the (tools) layout — includes copyright. */
export const TOOLS_LAYOUT_FOOTER =
  `\u00A9 ${new Date().getFullYear()} PlotDetect \u2014 NSW planning data only. ${INDICATIVE_ONLY} ${VERIFY_WITH_CERTIFIER}`;

/** Footer text for the /reports layout. */
export const REPORTS_LAYOUT_FOOTER =
  `${INDICATIVE_ONLY} Always consult a registered town planner or certifier before making any planning or property decision.`;

// ---------------------------------------------------------------------------
// Interactive tool disclaimers (shown below results in the UI)
// ---------------------------------------------------------------------------

export const TOOL_DISCLAIMERS = {
  granny_flat:
    'DCP setback, height, floor space ratio, and landscaping controls not assessed here. This check is indicative only \u2014 verify with a qualified town planner before lodging a DA or CDC.',
  solar:
    'Screening tool \u2014 not financial advice. Actual savings depend on consumption, tariff, and system performance. Get installer quotes before committing.',
  shadow:
    'This is a worst-case envelope model \u2014 not a design-specific shadow study. A formal shadow impact assessment by a qualified town planner or architect is required for DA submission.',
  flood:
    'Screening tool \u2014 not a legal flood determination. Obtain a Section 10.7 certificate from council for conveyancing.',
  bushfire:
    'This is an indicative pre-screen only and does not constitute a formal BAL assessment. For development applications on bushfire prone land, a formal bushfire assessment by a qualified practitioner listed in the RFS directory is required.',
  threat_radar:
    'DA and CDC data sourced from the NSW ePlanning Portal. Application details may be incomplete or delayed. This is not a formal property search \u2014 obtain a Section 10.7 certificate for conveyancing.',
  conveyancing:
    'Results are indicative only and do not constitute planning or legal advice. Always engage a registered town planner or conveyancer.',
  pre_da_history:
    'This report is for preliminary due diligence only. It does not constitute planning, legal, or engineering advice. Satellite analysis cannot detect changes smaller than ~30m\u00B2. Interior renovations are not visible.',
} as const;

// ---------------------------------------------------------------------------
// PDF report disclaimers
// ---------------------------------------------------------------------------

/** Generic PDF disclaimer — used in reports that don't have tool-specific language. */
export const PDF_GENERIC_DISCLAIMER =
  `This report is indicative only and does not constitute legal, planning, or financial advice. ${DATA_ACCURACY} Always verify with a qualified town planner or private certifier before lodging a development application or complying development certificate.`;

export const PDF_DISCLAIMERS = {
  granny_flat: PDF_GENERIC_DISCLAIMER,
  solar:
    'This report contains indicative estimates only and does not constitute financial or energy advice. Actual savings depend on household consumption patterns, tariff structure, system orientation, shading, and future energy prices.',
  shadow:
    'This is a worst-case envelope model \u2014 not a design-specific shadow study. A formal shadow impact assessment by a qualified town planner or architect is required for DA submission.',
  flood:
    'This report is an indicative cross-reference of publicly available flood data sources only. It does not constitute a formal Section 10.7 Planning Certificate, a flood engineering assessment, or legal advice.',
  flood_extended:
    'Flood hazard determination for development applications, conveyancing, or insurance purposes requires a formal flood study or certificate issued by council under the Environmental Planning and Assessment Act 1979.',
  bushfire:
    'This is an indicative pre-screen only and does not constitute a formal BAL assessment. For development applications on bushfire prone land, a formal bushfire assessment by a qualified practitioner listed in the RFS directory is required. Data sourced from the NSW Rural Fire Service Bush Fire Prone Land Map and PostGIS spatial overlays.',
  threat_radar:
    'DA and CDC data sourced from the NSW ePlanning Portal. Application details, lodgement dates, and determination outcomes may be incomplete or delayed. This report does not constitute a formal property search or Section 10.7 Planning Certificate.',
  pre_da_history:
    'This report is for preliminary due diligence only. It does not constitute planning, legal, or engineering advice. Satellite analysis cannot detect changes smaller than ~30m\u00B2. Interior renovations are not visible. DA data before July 2021 may be incomplete.',
} as const;

// ---------------------------------------------------------------------------
// SharedReportPage disclaimer (interactive report result pages)
// ---------------------------------------------------------------------------

export const SHARED_REPORT_DISCLAIMER =
  `This report is indicative only and does not constitute planning, legal, or financial advice. Always consult a qualified professional before making decisions.`;

// ---------------------------------------------------------------------------
// PDF "About" page disclaimer (shared-components.tsx AboutPage)
// ---------------------------------------------------------------------------

export const ABOUT_PAGE_DISCLAIMER =
  'PlotDetect reports are designed to complement \u2014 not replace \u2014 formal certificates, professional advice, and council searches. Always verify critical findings with a qualified professional before making financial or legal decisions.';

// ---------------------------------------------------------------------------
// Payment / Stripe checkout
// ---------------------------------------------------------------------------

/** Shown above or below the "Buy" button before Stripe redirect. */
export const PAYMENT_TOS_ACCEPTANCE =
  'By purchasing you agree to our Terms of Service. Reports are indicative only and do not constitute professional advice.';

/** Terms link path (relative). */
export const TERMS_PATH = '/terms';

/** Privacy link path (relative). */
export const PRIVACY_PATH = '/privacy';

// ---------------------------------------------------------------------------
// Data currency
// ---------------------------------------------------------------------------

/** Shown alongside data currency indicators (assessment/Verify page). */
export const DATA_CURRENCY_NOTE =
  'Verified = last confirmed match to source. Not a guarantee of currency. Always check council and legislation.nsw.gov.au before issuing advice.';

/**
 * Data provenance lines for interactive tool footers.
 * Describes source + update cadence rather than a query date,
 * so users don't perceive normal API lag as staleness.
 */
export const DATA_PROVENANCE = {
  flood:
    'Data sourced live from NSW Planning Portal and PostGIS spatial overlays. Satellite rasters updated annually. Not a formal certificate.',
  solar:
    'Solar data from Google Solar API, queried live. Tariff and rebate assumptions may not reflect your retailer. Not a formal quote.',
  shadow:
    'Building height from NSW Planning Portal (live). Shadow geometry computed at request time. Not a formal shadow impact assessment.',
  bushfire:
    'Bush Fire Prone Land mapping from NSW RFS (updated by RFS). Spatial overlays updated monthly. Not a formal BAL assessment.',
  threat_radar:
    'DA and CDC data sourced live from NSW ePlanning Portal. Application details may lag lodgement by 1\u20133 business days.',
  conveyancing:
    'Data sourced live from NSW Planning Portal, PostGIS spatial overlays, and NSW Valuer General. Spatial overlays updated monthly.',
  granny_flat:
    'Data sourced live from NSW Planning Portal. Spatial overlays (flood, heritage, biodiversity, acid sulfate) updated monthly.',
  pre_da_history:
    'Satellite imagery from Sentinel-2 (annual snapshots 2017\u20132024). DA data from NSW ePlanning Portal, queried live.',
} as const;

/** Generic "report generated" line for PDF footers. */
export function pdfGeneratedLine(runDate: string): string {
  return `Report generated by PlotDetect \u00B7 plotdetect.com.au \u00B7 ${runDate}`;
}
