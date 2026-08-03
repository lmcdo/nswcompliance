// prior-art-checked: no existing module words imagery-currency lines (the
// three report PDFs each inlined a bare `Queried ${run_date}` template —
// campaign item 4 census). One source so every surface words the imagery
// claim identically, and so the wording is testable without importing
// @react-pdf (ESM, unloadable under the jest config).
//
// Language rule: the line states only what the run recorded — an acquisition
// date when scene identity exists, an explicit "not recorded"/"not stated"
// when it does not, and never a query date dressed as imagery currency.

/** Sentinel-2 change-detection row (shadow report). */
export function s2ImageryCurrency(
  s2LatestAcquisition: string | null | undefined,
  runDate: string,
): string {
  if (s2LatestAcquisition) {
    return `Imagery acquired ${s2LatestAcquisition}; queried ${runDate}`;
  }
  return `Queried ${runDate}; acquisition dates not recorded for this run`;
}

/** Google Solar API row (solar report) — provider states a capture month.
 * Only a calendar-valid YYYY-MM renders as a provenance claim; any other
 * persisted value (bare year, out-of-range month, absence sentinel) falls to
 * the explicit not-stated wording — malformed data must never become a
 * factual capture claim. */
const CAPTURE_MONTH = /^\d{4}-(0[1-9]|1[0-2])$/;

export function solarImageryCurrency(
  imageryDate: string | null | undefined,
  runDate: string,
): string {
  if (imageryDate && CAPTURE_MONTH.test(imageryDate)) {
    return `Imagery captured ${imageryDate} (month stated by provider); queried ${runDate}`;
  }
  return `Queried ${runDate}; imagery capture date not stated by provider`;
}

/** Sentinel-1 SAR row (flood report) — no S1 analysis has ever run (Phase
 * 3B); 'Most recent pass' implied one had (DQ-44). */
export function sarImageryCurrency(
  sarAnalysisDate: string | null | undefined,
): string {
  return sarAnalysisDate ?? 'Not analysed in this report';
}
