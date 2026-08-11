// "Data sources" footer provenance for the Intelligence Brief — pure helpers
// extracted from page.tsx so the per-run derivation is unit-testable.
//
// The footer must describe THIS run, not a static union (issue #753): a source
// is listed only when at least one populated DataField in the received sections
// cites it (value present, not null). Sources cited only by null-valued fields
// (a pipeline that did not run, or returned nothing for the address) stay off
// the list, and labels dedupe case-insensitively after normalisation so two
// internal slugs naming the same real-world source render once, keeping the
// latest as-at stamp seen for that source.

// Internal source slugs -> the real-world data source, so the brief can list
// "every figure traced to its source" honestly at the bottom.
const SOURCE_LABELS: Record<string, string> = {
  postgis_overlays: 'NSW planning overlays (PostGIS)',
  live_protection_overlay: 'NSW Planning Portal — Protection layers',
  planning_portal_protection: 'NSW Planning Portal — Protection layers',
  cadastre_strata: 'NSW cadastre (strata/lot)',
  postgis_heritage: 'NSW heritage (PostGIS)',
  anef_zones: 'ANEF aircraft-noise contours',
  planning_portal: 'NSW Planning Portal',
  bushfire_prescreen: 'NSW RFS Bushfire Prone Land map',
  flood_truth: 'Flood screening (JRC / WOfS / BoM)',
  housing_sepp_standards: 'SEPP (Housing) 2021 standards',
  constraint_arithmetic_engine: 'Computed — constraint engine',
  terrain_analysis: 'Computed — 5 m DEM terrain',
  granny_flat_detect: 'Satellite imagery + structure detection',
  vg_valuation: 'NSW Valuer General',
  nsw_spatial_services: 'NSW Spatial Services',
  epa_contaminated_sites: 'NSW EPA contaminated-land register',
  plotdetect_dcp: 'Council DCP (extracted controls)',
  da_tracking_mapserver: 'NSW DA tracking extract',
  eplanning_da_api: 'NSW ePlanning DA feed',
  nsw_valuation_service: 'NSW Valuer General',
  nsw_valuer_general: 'NSW Valuer General',
  nsw_valuer_general_sales: 'NSW Valuer General sales records',
  lep_land_use_table: 'LEP land use table',
  sepp_resilience_hazards: 'SEPP (Resilience and Hazards) 2021',
  shadow_detector: 'Computed — shadow model',
  google_solar: 'Google Solar API',
};

export function humanizeSource(slug: string): string {
  if (slug in SOURCE_LABELS) return SOURCE_LABELS[slug];
  return slug.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

export interface BriefProvenance {
  sources: { label: string; asAt?: string }[];
  links: { label: string; url: string }[];
}

// Fallback link-label formatter — page.tsx passes its richer formatKey.
function defaultLinkLabel(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

// Walk the streamed sections and collect the data sources this run actually
// used, plus any legislation/source URL, so the brief footer lists per-run
// provenance rather than every source the pipeline knows about.
export function collectSources(
  sections: { data: { data: unknown } }[],
  formatLinkLabel: (key: string) => string = defaultLinkLabel,
): BriefProvenance {
  // Keyed on the lower-cased normalised label so distinct internal slugs for
  // the same real-world source (and any label-case drift) collapse to one row.
  const srcMap = new Map<string, { label: string; asAt?: string }>();
  const linkMap = new Map<string, string>();
  const walk = (v: unknown) => {
    if (!v || typeof v !== 'object') return;
    if (Array.isArray(v)) { v.forEach(walk); return; }
    const o = v as Record<string, unknown>;
    // Count a citation only when the field carrying it populated on this run:
    // the object must have a `value` key and that value must be non-null. A
    // DataField whose value is null (did not run / nothing at this address)
    // does not put its source on the list.
    if (typeof o.source === 'string' && o.source && 'value' in o && o.value != null) {
      const label = humanizeSource(o.source);
      const key = label.toLowerCase();
      const asAt = typeof o.as_at === 'string' ? o.as_at : undefined;
      const existing = srcMap.get(key);
      if (!existing) {
        srcMap.set(key, { label, asAt });
      } else if (asAt && (!existing.asAt || asAt > existing.asAt)) {
        // Keep the latest as-at stamp seen for this source across fields.
        existing.asAt = asAt;
      }
    }
    for (const [k, val] of Object.entries(o)) {
      if (/url$/i.test(k) && typeof val === 'string' && val.startsWith('http')) {
        if (!linkMap.has(val)) linkMap.set(val, formatLinkLabel(k.replace(/_url$/i, '')) || 'Source');
      }
      walk(val);
    }
  };
  sections.forEach((s) => walk(s.data.data));
  return {
    sources: [...srcMap.values()].sort((a, b) => a.label.localeCompare(b.label)),
    links: [...linkMap.entries()].map(([url, label]) => ({ label, url })),
  };
}
