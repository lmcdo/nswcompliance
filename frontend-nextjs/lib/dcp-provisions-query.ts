/**
 * The /api/provisions/for-property query the assessment page sends.
 *
 * prior-art-checked: reuse not viable -- hooks/useFullPropertyData.ts builds a similar query and
 * already sends land_facts, but nothing mounts that hook. The page users see
 * (app/assessment/page.tsx -> ProvisionsByTocStructure) built its own query inline and never sent
 * land_facts, so the DQ-140 land gate (PR #1259) reached the route but not the page: every Inner
 * West lot was still shown the site-only LEP rules, marked "could not confirm this land".
 * Measured 2026-10-11 on origin/main. Kept pure so a test can see exactly what is sent.
 */
import { encodeLandApplication, type LandApplicationInstrument } from '@/lib/dcp-land-application';
import { encodeLandFacts, type LandFacts } from '@/lib/lep-land-condition';

export interface ForPropertyQueryInput {
  formerCouncil?: string | null;
  zone?: string | null;
  heritage?: boolean;
  hcaName?: string | null;
  precinctId?: string | null;
  landApplicationInstruments?: LandApplicationInstrument[] | null;
  landFacts?: LandFacts | null;
}

export function buildForPropertyParams(input: ForPropertyQueryInput): URLSearchParams {
  const params = new URLSearchParams();
  params.set('groupBy', 'toc');
  if (input.formerCouncil) params.set('former_council', input.formerCouncil);
  if (input.zone) params.set('zone', input.zone);
  if (input.heritage !== undefined) params.set('heritage', String(input.heritage));
  if (input.hcaName) params.set('hca', input.hcaName);
  if (input.precinctId) params.set('precinct_id', input.precinctId);
  // DQ-120: the Land Application Map answer decides whether this council's DCP covers the
  // property. Not sent = the route treats it as unknown.
  const landApplication = encodeLandApplication(input.landApplicationInstruments);
  if (landApplication) params.set('land_application', landApplication);
  // DQ-140: the lot's own portal layers decide whether a site-specific LEP rule (a key site, a
  // Schedule 1 item) is this land's. Not sent = every such rule is kept as "unconfirmed".
  const landFacts = encodeLandFacts(input.landFacts);
  if (landFacts) params.set('land_facts', landFacts);
  // dev_types intentionally excluded -- provisions are property-specific, not dev-type-specific.
  return params;
}
