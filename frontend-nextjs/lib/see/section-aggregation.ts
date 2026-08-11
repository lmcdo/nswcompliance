// Computation layer for the SEE PDF document.
// Transforms raw SEEDocumentData into all derived values consumed by page components.
// Pure function — no React, no side effects, unit-testable.

import { PropertyContext, ProvisionForPDF, ProvisionGroup } from '@/lib/pdf/types';
import { SEEDocumentData, SectionAssessment, PathwayDetermination, SeppAssessableControl, LepAssessableStandard, TopicAssertion, ChapterAssertion } from '@/lib/see/types';
import { parseSectionKey } from '@/lib/see/sectionKey';
import type { IntakeAnswers } from '@/lib/see/intake';
import { groupProvisionsByTopic } from '@/lib/pdf/formatProvisions';
import { ANCILLARY_WORKS, AncillaryWork } from '@/lib/see/ancillaryWorks';
import { determineDevelopmentPathway } from '@/lib/pdf/see-helpers';
import { HOUSING_SEPP_ZONES } from '@/lib/regulatory-constants';

// ---------------------------------------------------------------------------
// Computed data shape — all derived values for SEE page components
// ---------------------------------------------------------------------------

export interface SEEComputedData {
  // Development description (normalised)
  devDesc: string;

  // Original data fields
  property: PropertyContext;
  see_intro: string | undefined;
  annotated_provisions: ProvisionForPDF[];
  all_provisions: ProvisionForPDF[];
  generated_date: string;
  intake_answers: IntakeAnswers | undefined;
  client_ref: string | undefined;
  prepared_by: string | undefined;
  pathway_determination: PathwayDetermination | undefined;
  sepp_assessable_controls: SeppAssessableControl[] | undefined;
  lep_assessable_standards: LepAssessableStandard[] | undefined;
  topic_assertions: TopicAssertion[] | undefined;
  chapter_assertions: ChapterAssertion[] | undefined;
  ancillary_works: string[] | undefined;
  council_pdf_url: string | undefined;
  section_responses: SectionAssessment[] | undefined;
  section_scope: { section_key: string; section_title: string | null }[] | undefined;

  // Destructured from property for convenience
  heritage_status: PropertyContext['heritage_status'];
  lot_dimensions: PropertyContext['lot_dimensions'];
  lep_controls: PropertyContext['lep_controls'];
  environmental_constraints: PropertyContext['environmental_constraints'];
  additional_local_provisions: PropertyContext['additional_local_provisions'];
  planning_portal_layers: PropertyContext['planning_portal_layers'];

  // Pathway derived from determineDevelopmentPathway
  zoneCode: string;
  pathway: string;
  reason: string;
  housingSeppApplies: boolean;

  // DCP provision buckets
  unannotatedProvisions: ProvisionForPDF[];
  variesProvisions: ProvisionForPDF[];
  compliesProvisions: ProvisionForPDF[];
  naIntakeProvisions: ProvisionForPDF[];
  naManualProvisions: ProvisionForPDF[];
  variesGroups: ProvisionGroup[];
  compliesGroups: ProvisionGroup[];
  naManualGroups: ProvisionGroup[];
  naIntakeGroups: ProvisionGroup[];
  ancillaryWorksWithNoProvisions: AncillaryWork[];

  // Provision counts
  annotatedCount: number;
  totalCount: number;
  unannotatedCount: number;

  // Compliance percentages (provision-level model)
  compliesPct: number;
  variesPct: number;
  naPct: number;
  assessedPct: number;

  // Section-level model
  useSectionModel: boolean;
  secVaries: SectionAssessment[];
  secComplies: SectionAssessment[];
  secNA: SectionAssessment[];
  secFlagged: SectionAssessment[];
  secScopeTotal: number;
  secAssessedTotal: number;
  secUnassessedTotal: number;
  secAssessedPct: number;
  secSortedParts: [string, SectionAssessment[]][];
  secUnassessedList: { section_key: string; section_title: string | null }[];

  // Document identifiers
  docRef: string;
  siteSuitabilityText: string;
  footerRef: string;
}

// ---------------------------------------------------------------------------
// Builder
// ---------------------------------------------------------------------------

export function buildSEEData(data: SEEDocumentData): SEEComputedData {
  const devDesc = data.development_description?.replace(/\n+/g, ' ').trim() ?? '';

  const {
    property, see_intro, annotated_provisions, all_provisions,
    generated_date, intake_answers, client_ref, prepared_by,
    pathway_determination, sepp_assessable_controls, lep_assessable_standards,
    topic_assertions, chapter_assertions, ancillary_works, council_pdf_url,
    section_responses, section_scope,
  } = data;

  const {
    heritage_status, lot_dimensions, lep_controls, environmental_constraints,
    additional_local_provisions, planning_portal_layers,
  } = property;

  // Unannotated provisions — listed as outstanding
  const annotatedIds = new Set(annotated_provisions.map(p => p.id));
  const unannotatedProvisions = all_provisions.filter(p => !annotatedIds.has(p.id));

  const zoneCode = property.zone?.split(' ')[0] || '';
  const { pathway, reason } = determineDevelopmentPathway(
    property.zone || '',
    heritage_status.in_hca,
    heritage_status.heritage_item || false
  );

  const housingSeppApplies = HOUSING_SEPP_ZONES.includes(zoneCode);

  // DCP Assessment buckets
  const variesProvisions = annotated_provisions.filter(p => p.da_status === 'varies');
  const compliesProvisions = annotated_provisions.filter(p => p.da_status === 'complies');
  const naAllProvisions = annotated_provisions.filter(p => p.da_status === 'not_applicable');
  const naIntakeProvisions = naAllProvisions.filter(p => p.da_response?.startsWith('Excluded by intake:'));
  const naManualProvisions = naAllProvisions.filter(p => !p.da_response?.startsWith('Excluded by intake:'));

  const variesGroups = groupProvisionsByTopic(variesProvisions);
  const compliesGroups = groupProvisionsByTopic(compliesProvisions);
  const naManualGroups = groupProvisionsByTopic(naManualProvisions);
  const naIntakeGroups = groupProvisionsByTopic(naIntakeProvisions);

  // Ancillary works selected but with zero provisions for the dev type
  const allCategoriesInProvisions = new Set(all_provisions.map(p => p.v2_structural_category).filter(Boolean));
  const ancillaryWorksWithNoProvisions = ancillary_works
    ? ANCILLARY_WORKS.filter(w =>
        ancillary_works.includes(w.value) &&
        w.devTypeTag &&
        !allCategoriesInProvisions.has(w.devTypeTag) &&
        !allCategoriesInProvisions.has(w.value)
      )
    : [];

  const annotatedCount = annotated_provisions.length;
  const totalCount = all_provisions.length;
  const unannotatedCount = totalCount - annotatedCount;

  // Section-level model
  const useSectionModel = (section_responses?.length ?? 0) > 0;
  const secVaries    = section_responses?.filter(s => s.status === 'varies') ?? [];
  const secComplies  = section_responses?.filter(s => s.status === 'complies') ?? [];
  const secNA        = section_responses?.filter(s => s.status === 'not_applicable') ?? [];
  const secFlagged   = section_responses?.filter(s => s.status === 'flagged') ?? [];
  const secScopeTotal    = section_scope?.length ?? 0;
  const secAssessedTotal = section_responses?.length ?? 0;
  const secUnassessedTotal = Math.max(0, secScopeTotal - secAssessedTotal);
  const secAssessedPct = secScopeTotal > 0
    ? Math.min(100, Math.round((secAssessedTotal / secScopeTotal) * 100))
    : 0;

  // Sections grouped by part (for per-part tables)
  const secPartMap = new Map<string, SectionAssessment[]>();
  for (const s of (section_responses ?? [])) {
    const { part } = parseSectionKey(s.section_key);
    if (!secPartMap.has(part)) secPartMap.set(part, []);
    secPartMap.get(part)!.push(s);
  }
  const secSortedParts = [...secPartMap.entries()].sort(([a], [b]) =>
    a.localeCompare(b, undefined, { numeric: true })
  );

  // Unassessed sections (in scope but not yet responded to)
  const secAssessedKeys = new Set((section_responses ?? []).map(s => s.section_key));
  const secUnassessedList = (section_scope ?? []).filter(s => !secAssessedKeys.has(s.section_key));

  // Compliance percentages (provision-level)
  const pct = (n: number) => totalCount > 0 ? Math.round((n / totalCount) * 100) : 0;
  const compliesPct = pct(compliesProvisions.length);
  const variesPct   = pct(variesProvisions.length);
  const naPct       = pct(naManualProvisions.length + naIntakeProvisions.length);
  const assessedPct = pct(annotatedCount);

  // Document reference: SEE-YYYYMMDD-XXXX
  const refDate  = new Date().toISOString().split('T')[0].replace(/-/g, '');
  const addrHash = (property.address || 'unknown')
    .split('')
    .reduce((a, c) => ((a << 5) - a + c.charCodeAt(0)) | 0, 0);
  const docRef = `SEE-${refDate}-${Math.abs(addrHash).toString(36).toUpperCase().slice(0, 4).padStart(4, '0')}`;

  // Auto-generated site suitability paragraph
  const siteSuitabilitySentences: string[] = [];
  if (lot_dimensions?.area) {
    const dimParts = [`a total area of ${Math.round(lot_dimensions.area).toLocaleString()} m²`];
    if (lot_dimensions.frontage) dimParts.push(`a ${lot_dimensions.frontage.toFixed(1)} m frontage`);
    if (lot_dimensions.depth)    dimParts.push(`a depth of ${lot_dimensions.depth.toFixed(1)} m`);
    siteSuitabilitySentences.push(`The site at ${property.address} has ${dimParts.join(', ')}.`);
    if (lot_dimensions.is_corner && lot_dimensions.corner_roads?.length) {
      siteSuitabilitySentences.push(
        `It is a corner lot at the intersection of ${lot_dimensions.corner_roads.join(' and ')}.`
      );
    }
  } else {
    siteSuitabilitySentences.push(`The site is located at ${property.address}.`);
  }
  if (environmental_constraints) {
    const activeConstraints: string[] = [];
    if (environmental_constraints.flood_prone)           activeConstraints.push('flood prone land');
    if (environmental_constraints.bushfire_prone)        activeConstraints.push('bushfire prone land');
    if (environmental_constraints.coastal_management)    activeConstraints.push('coastal management area');
    if (environmental_constraints.contaminated_land)     activeConstraints.push('proximity to notified contaminated site');
    if (environmental_constraints.anef_zone)             activeConstraints.push('aircraft noise (ANEF) zone');
    if (environmental_constraints.mine_subsidence)       activeConstraints.push('mine subsidence district');
    if (environmental_constraints.landslide_risk)        activeConstraints.push('landslide risk area');
    if (environmental_constraints.drinking_water_catchment) activeConstraints.push('drinking water catchment');
    if (environmental_constraints.terrestrial_biodiversity) activeConstraints.push('terrestrial biodiversity area');
    if (activeConstraints.length > 0) {
      siteSuitabilitySentences.push(`The site is affected by ${activeConstraints.join(', ')}.`);
    } else {
      siteSuitabilitySentences.push('The site is not affected by any mapped environmental constraints.');
    }
  }
  if (heritage_status.heritage_item) {
    siteSuitabilitySentences.push(
      `The site contains a heritage item${heritage_status.item_number ? ` (${heritage_status.item_number})` : ''} listed under the LEP.`
    );
  } else if (heritage_status.in_hca) {
    siteSuitabilitySentences.push(
      `The site is located within the ${heritage_status.hca_name || 'a'} Heritage Conservation Area.`
    );
  }
  const siteSuitabilityText = siteSuitabilitySentences.join(' ');

  const footerRef = [docRef, client_ref, prepared_by].filter(Boolean).join(' | ');

  return {
    devDesc,
    property,
    see_intro,
    annotated_provisions,
    all_provisions,
    generated_date,
    intake_answers,
    client_ref,
    prepared_by,
    pathway_determination,
    sepp_assessable_controls,
    lep_assessable_standards,
    topic_assertions,
    chapter_assertions,
    ancillary_works,
    council_pdf_url,
    section_responses,
    section_scope,
    heritage_status,
    lot_dimensions,
    lep_controls,
    environmental_constraints,
    additional_local_provisions,
    planning_portal_layers,
    zoneCode,
    pathway,
    reason,
    housingSeppApplies,
    unannotatedProvisions,
    variesProvisions,
    compliesProvisions,
    naIntakeProvisions,
    naManualProvisions,
    variesGroups,
    compliesGroups,
    naManualGroups,
    naIntakeGroups,
    ancillaryWorksWithNoProvisions,
    annotatedCount,
    totalCount,
    unannotatedCount,
    compliesPct,
    variesPct,
    naPct,
    assessedPct,
    useSectionModel,
    secVaries,
    secComplies,
    secNA,
    secFlagged,
    secScopeTotal,
    secAssessedTotal,
    secUnassessedTotal,
    secAssessedPct,
    secSortedParts,
    secUnassessedList,
    docRef,
    siteSuitabilityText,
    footerRef,
  };
}
