import type { Metadata } from 'next';
import Link from 'next/link';
import { TrackedLink } from '@/components/marketing/TrackedLink';
import { query } from '@/lib/database/pool-manager';
import { DatasetJsonLd } from '@/lib/json-ld';
import { BlogDisclaimer } from '@/components/blog/BlogDisclaimer';

export const revalidate = 86400; // ISR: revalidate daily

export const metadata: Metadata = {
  title: 'NSW Housing SEPP Standards — Numeric Requirements by Development Type | PlotDetect',
  description:
    'Numeric development standards from SEPP (Housing) 2021 and the Apartment Design Guide. Height limits, lot sizes, floor area, site coverage, parking, and setbacks for secondary dwellings, duplexes, manor houses, townhouses, and apartments in NSW.',
  openGraph: {
    title: 'NSW Housing SEPP Standards — Numeric Requirements',
    description:
      'Structured numeric standards from SEPP Housing 2021 and the ADG with clause references.',
    url: 'https://verify.plotdetect.com.au/planning-standards',
    siteName: 'plotdetect.com.au',
    type: 'website',
  },
};

/* ─── Types ─── */

interface SeppStandard {
  development_type: string;
  standard_type: string;
  numeric_value: string;
  unit: string;
  applicable_zones: string[] | null;
  requires_lmr_area: boolean;
  source_clause: string;
  source_document: string;
  legislation_url: string | null;
  effective_date: string | null;
}

interface AdgRequirement {
  section_code: string;
  section_name: string;
  criteria_id: string;
  requirement_summary: string | null;
  requirement_text: string;
  has_numeric_standard: boolean;
  numeric_value: string | null;
  numeric_unit: string | null;
  numeric_comparator: string | null;
  secondary_value: string | null;
  secondary_unit: string | null;
  metric_category: string | null;
  applies_to: string[] | null;
  building_height_category: string | null;
  source_url: string | null;
  authority_reference: string | null;
}

/* ─── Data fetching ─── */

async function fetchSeppStandards(): Promise<SeppStandard[]> {
  try {
    const result = await query(
      `SELECT development_type, standard_type, numeric_value, unit,
              applicable_zones, requires_lmr_area, source_clause,
              source_document, legislation_url, effective_date
       FROM housing_sepp_standards
       ORDER BY development_type, standard_type`,
      []
    );
    return result.rows as SeppStandard[];
  } catch (error) {
    console.error('[Planning Standards] Failed to fetch SEPP standards:', error);
    return [];
  }
}

async function fetchAdgRequirements(): Promise<AdgRequirement[]> {
  try {
    const result = await query(
      `SELECT section_code, section_name, criteria_id,
              requirement_summary, requirement_text,
              has_numeric_standard, numeric_value, numeric_unit, numeric_comparator,
              secondary_value, secondary_unit, metric_category,
              applies_to, building_height_category, source_url, authority_reference
       FROM sepp_adg_requirements
       WHERE requirement_type = 'design_criteria'
       ORDER BY section_code, criteria_number`,
      []
    );
    return result.rows as AdgRequirement[];
  } catch (error) {
    console.error('[Planning Standards] Failed to fetch ADG requirements:', error);
    return [];
  }
}

/* ─── Display helpers ─── */

const DEV_TYPE_LABELS: Record<string, string> = {
  secondary_dwelling: 'Secondary Dwelling (Granny Flat)',
  dual_occupancy: 'Dual Occupancy (Duplex)',
  manor_house: 'Manor House',
  multi_dwelling: 'Multi-Dwelling Housing (Townhouses)',
  multi_dwelling_housing: 'Multi-Dwelling Housing (Townhouses)',
  terraces: 'Terrace Housing',
  terrace_house: 'Terrace Housing',
  residential_flat_r1r2: 'Low-Rise Apartments (R1/R2)',
  residential_flat_r3r4_inner: 'Mid-Rise Apartments (within 400m of station)',
  residential_flat_r3r4_outer: 'Mid-Rise Apartments (400–800m from station)',
};

function formatStandardType(raw: string): string {
  return raw
    .replace(/_/g, ' ')
    .replace(/\blot\b/gi, 'lot')
    .replace(/\bunder\b/gi, '<')
    .replace(/\bover\b/gi, '>')
    .replace(/\bto\b/gi, '–')
    .replace(/^./, c => c.toUpperCase());
}

function formatValue(value: string, unit: string): string {
  const num = parseFloat(value);
  if (unit === '%') return `${num}%`;
  if (unit === 'spaces') return `${num} space${num !== 1 ? 's' : ''}`;
  return `${num} ${unit}`;
}

function formatComparator(comp: string | null): string {
  if (comp === 'min') return 'Minimum';
  if (comp === 'max') return 'Maximum';
  if (comp === 'exactly') return 'Exactly';
  return '';
}

/* ─── Page ─── */

export default async function PlanningStandardsPage() {
  const [seppStandards, adgRequirements] = await Promise.all([
    fetchSeppStandards(),
    fetchAdgRequirements(),
  ]);

  // Group SEPP standards by development type
  const byDevType = new Map<string, SeppStandard[]>();
  for (const std of seppStandards) {
    const list = byDevType.get(std.development_type) || [];
    list.push(std);
    byDevType.set(std.development_type, list);
  }

  // Group ADG by section
  const bySection = new Map<string, AdgRequirement[]>();
  for (const req of adgRequirements) {
    const list = bySection.get(req.section_code) || [];
    list.push(req);
    bySection.set(req.section_code, list);
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <DatasetJsonLd
        name="NSW Housing SEPP Numeric Standards"
        description="Structured numeric development standards from SEPP (Housing) 2021 and the NSW Apartment Design Guide. Includes height limits, lot sizes, floor areas, site coverage, parking rates, and setbacks by development type."
        url="https://verify.plotdetect.com.au/planning-standards"
        spatialCoverage="New South Wales, Australia"
        variableMeasured={[
          'Maximum building height',
          'Minimum lot size',
          'Maximum floor area',
          'Maximum site coverage',
          'Minimum private open space',
          'Parking rates',
          'Solar access hours',
          'Building separation distances',
        ]}
        license="Derived from NSW Government legislative instruments"
      />

      {/* Header */}
      <div className="mb-10">
        <div className="flex items-center gap-2 mb-4">
          <Link
            href="/blog"
            className="text-xs text-slate-400 hover:text-teal-600 transition-colors"
          >
            Insights
          </Link>
          <span className="text-xs text-slate-300">/</span>
          <span className="text-xs text-slate-500">Planning Standards</span>
        </div>
        <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight mb-4">
          NSW Housing SEPP development standards
        </h1>
        <p className="text-lg text-slate-500 leading-relaxed max-w-2xl">
          Numeric requirements from SEPP (Housing) 2021 and the Apartment Design
          Guide. {seppStandards.length} standards across{' '}
          {byDevType.size} development types, plus {adgRequirements.length} ADG
          design criteria. All values sourced from legislative instruments with
          clause references.
        </p>
      </div>

      {/* Headline stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-10">
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">SEPP standards</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{seppStandards.length}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">Development types</p>
          <p className="text-2xl font-bold text-slate-900 mt-1">{byDevType.size}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">ADG criteria</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">{adgRequirements.length}</p>
        </div>
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-xs text-slate-500 uppercase tracking-wider font-medium">ADG sections</p>
          <p className="text-2xl font-bold text-teal-700 mt-1">{bySection.size}</p>
        </div>
      </div>

      {/* SEPP Housing Standards by development type */}
      <h2 className="text-xl font-bold text-slate-900 mb-6">
        SEPP (Housing) 2021 — standards by development type
      </h2>

      {Array.from(byDevType.entries()).map(([devType, standards]) => (
        <div key={devType} className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 sm:p-6 mb-6">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            {DEV_TYPE_LABELS[devType] || devType}
          </h3>
          {standards[0]?.applicable_zones && (
            <p className="text-xs text-slate-500 mb-4">
              Applicable zones: {standards[0].applicable_zones.join(', ')}
              {standards[0].requires_lmr_area && ' (LMR reform area required)'}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2.5 pr-3 font-semibold text-slate-700">Standard</th>
                  <th className="text-right py-2.5 px-3 font-semibold text-teal-700">Value</th>
                  <th className="text-left py-2.5 px-3 font-semibold text-slate-700 hidden sm:table-cell">Source clause</th>
                  <th className="text-left py-2.5 pl-3 font-semibold text-slate-700 hidden md:table-cell">Instrument</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                {standards.map(std => (
                  <tr key={`${devType}-${std.standard_type}`} className="border-b border-slate-100">
                    <td className="py-2.5 pr-3">{formatStandardType(std.standard_type)}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-teal-700">
                      {formatValue(std.numeric_value, std.unit)}
                    </td>
                    <td className="py-2.5 px-3 hidden sm:table-cell">
                      {std.legislation_url ? (
                        <a
                          href={std.legislation_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-teal-600 hover:text-teal-800 underline underline-offset-2"
                        >
                          {std.source_clause}
                        </a>
                      ) : (
                        std.source_clause
                      )}
                    </td>
                    <td className="py-2.5 pl-3 text-xs text-slate-500 hidden md:table-cell">
                      {std.source_document.replace('State Environmental Planning Policy ', 'SEPP ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* ADG Design Criteria */}
      <h2 className="text-xl font-bold text-slate-900 mt-12 mb-6">
        Apartment Design Guide — design criteria
      </h2>
      <p className="text-sm text-slate-500 mb-6 max-w-2xl">
        Numeric design criteria from the NSW Apartment Design Guide (March 2023),
        which applies to residential flat buildings, shop top housing, and mixed-use
        development under SEPP (Housing) 2021.
      </p>

      {Array.from(bySection.entries()).map(([sectionCode, requirements]) => (
        <div key={sectionCode} className="rounded-2xl border border-slate-200 bg-slate-50/50 p-4 sm:p-6 mb-6">
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-1">
            {sectionCode} — {requirements[0]?.section_name}
          </h3>
          {requirements[0]?.building_height_category && requirements[0].building_height_category !== 'all' && (
            <p className="text-xs text-slate-500 mb-4">
              Building height: {requirements[0].building_height_category.replace(/_/g, ' ')}
            </p>
          )}
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-2.5 pr-3 font-semibold text-slate-700">Criteria</th>
                  <th className="text-left py-2.5 px-3 font-semibold text-slate-700">Requirement</th>
                  <th className="text-right py-2.5 pl-3 font-semibold text-teal-700 hidden sm:table-cell">Standard</th>
                </tr>
              </thead>
              <tbody className="text-slate-700">
                {requirements.map(req => (
                  <tr key={req.criteria_id} className="border-b border-slate-100">
                    <td className="py-2.5 pr-3 font-medium text-slate-900 whitespace-nowrap">
                      {req.criteria_id}
                    </td>
                    <td className="py-2.5 px-3 text-slate-600">
                      {req.requirement_summary || req.requirement_text}
                    </td>
                    <td className="py-2.5 pl-3 text-right font-bold text-teal-700 whitespace-nowrap hidden sm:table-cell">
                      {req.has_numeric_standard && req.numeric_value != null ? (
                        <>
                          {formatComparator(req.numeric_comparator)}{' '}
                          {parseFloat(req.numeric_value)} {req.numeric_unit?.replace('_', ' ')}
                          {req.secondary_value != null && (
                            <> @ {parseFloat(req.secondary_value)} {req.secondary_unit?.replace('_', ' ')}</>
                          )}
                        </>
                      ) : (
                        <span className="text-slate-400">Qualitative</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Source attribution */}
      <p className="text-xs text-slate-400 mt-8 mb-10">
        Standards sourced from SEPP (Housing) 2021 and the NSW Apartment Design
        Guide (March 2023). Clause references link to the NSW Legislation website.
        These are state-level standards — individual councils may have additional
        DCP controls. Values are extracted from legislative instruments and
        cross-referenced against the NSW Planning Portal. Last checked: 2026-05-31.
      </p>

      {/* CTA */}
      <div className="rounded-2xl border border-teal-200 bg-teal-50/50 p-6 sm:p-8 mb-6">
        <h2 className="text-lg font-bold text-slate-900 mb-2">
          Check how these standards apply to your property
        </h2>
        <p className="text-sm text-slate-600 mb-4">
          Enter an address to check zoning, lot size, overlays, and which SEPP
          Housing development types are eligible for your site.
        </p>
        <TrackedLink
          href="/assessment"
          page="planning-standards"
          cta="run_compliance_check"
          className="inline-flex items-center gap-2 rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
        >
          Run compliance check
        </TrackedLink>
      </div>

      {/* Related links */}
      <div className="mt-8">
        <p className="text-xs text-slate-400 font-medium uppercase tracking-wide mb-3">
          Related resources
        </p>
        <div className="flex flex-wrap gap-2">
          <Link href="/glossary" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Planning Glossary
          </Link>
          <Link href="/blog/granny-flat" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Granny Flat Statistics
          </Link>
          <Link href="/blog/can-i-build-a-granny-flat-nsw" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            Granny Flat Eligibility Guide
          </Link>
          <Link href="/blog/nsw-housing-sepp-low-mid-rise-reforms" className="text-xs px-3 py-1.5 rounded-full border border-slate-200 text-slate-600 hover:border-teal-400 hover:text-teal-700 transition-colors">
            LMR Reform Explainer
          </Link>
        </div>
      </div>

      <BlogDisclaimer />
    </div>
  );
}
