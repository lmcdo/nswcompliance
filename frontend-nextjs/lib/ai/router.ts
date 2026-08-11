/**
 * Data Router for AI Assistant
 *
 * Routes classified questions to the appropriate data endpoints.
 * No content generation - only fetches precomputed data.
 */

import { ClassificationResult, PropertyContext, QuestionCategory } from './classifier';

// Base URL for API calls (server-side)
// Must resolve correctly in both local dev and Vercel production
function getApiBase(): string {
  // Production: use the canonical domain
  if (process.env.VERCEL_ENV === 'production') {
    return 'https://verify.plotdetect.com.au';
  }
  // Preview deployments: use VERCEL_URL
  if (process.env.VERCEL_URL) {
    return `https://${process.env.VERCEL_URL}`;
  }
  // Custom base URL if set
  if (process.env.NEXT_PUBLIC_BASE_URL) {
    return process.env.NEXT_PUBLIC_BASE_URL;
  }
  // Local development
  return 'http://localhost:3003';
}

const API_BASE = getApiBase();

// Response from data endpoints
export interface DataResponse {
  success: boolean;
  category: QuestionCategory;
  data: unknown;
  sources: Citation[];
  error?: string;
  refusalMessage?: string;
}

// Citation for source attribution
export interface Citation {
  source: string;
  document?: string;
  clause?: string;
  url?: string;
  page?: number;
}

/**
 * Route a classified question to the appropriate endpoint
 */
export async function routeQuestion(
  classification: ClassificationResult,
  propertyContext?: PropertyContext
): Promise<DataResponse> {
  const { category, extractedParams } = classification;

  // Handle interpretation questions (refuse with helpful data)
  if (category === 'interpretation') {
    return handleInterpretationRefusal(extractedParams.originalQuestion, propertyContext);
  }

  // Check if property context is required but missing
  const contextRequiredCategories: QuestionCategory[] = [
    'factual_lookup',
    'permissibility',
    'housing_sepp',
    'constraint_check',
    'synthesis'
  ];

  if (contextRequiredCategories.includes(category) && !propertyContext?.address) {
    return {
      success: false,
      category,
      data: null,
      sources: [],
      error: 'This question requires a property to be selected. Please enter an address above to get specific requirements.',
    };
  }

  // Route to appropriate handler
  switch (category) {
    case 'definition':
      return handleDefinitionLookup(extractedParams.term || extractedParams.originalQuestion);

    case 'procedural':
      return handleProceduralQuestion(extractedParams.originalQuestion);

    case 'guide':
      return handleGuideQuestion(extractedParams.originalQuestion);

    case 'factual_lookup':
      return handleFactualLookup(extractedParams.controlType || 'all', propertyContext!);

    case 'permissibility':
      return handlePermissibilityCheck(extractedParams.developmentType || '', propertyContext!);

    case 'housing_sepp':
      return handleHousingSeppCheck(propertyContext!);

    case 'constraint_check':
      return handleConstraintCheck(propertyContext!);

    case 'synthesis':
      return handleSynthesis(extractedParams.originalQuestion, propertyContext!);

    default:
      return {
        success: false,
        category,
        data: null,
        sources: [],
        error: 'Unable to process this question. Please try rephrasing.',
      };
  }
}

/**
 * Handle definition lookup from /api/definitions
 */
async function handleDefinitionLookup(term: string): Promise<DataResponse> {
  try {
    const response = await fetch(`${API_BASE}/api/definitions?term=${encodeURIComponent(term)}&limit=5`);
    const data = await response.json();

    if (!data.success || data.count === 0) {
      return {
        success: false,
        category: 'definition',
        data: null,
        sources: [],
        error: `No definition found for "${term}". Try searching for a different term.`,
      };
    }

    const definitions = data.definitions;
    const sources: Citation[] = definitions.map((def: any) => ({
      source: def.source_document,
      clause: def.source_clause,
      page: def.pdf_page,
    }));

    return {
      success: true,
      category: 'definition',
      data: {
        term: definitions[0].term,
        definitions: definitions.map((def: any) => ({
          text: def.definition_text,
          summary: def.definition_summary,
          source: def.source_document,
          clause: def.source_clause,
          legislationType: def.legislation_type,
        })),
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] Definition lookup error:', error);
    return {
      success: false,
      category: 'definition',
      data: null,
      sources: [],
      error: 'Unable to look up definition. Please try again.',
    };
  }
}

/**
 * Handle procedural questions from /api/procedural
 */
async function handleProceduralQuestion(question: string): Promise<DataResponse> {
  try {
    const q = question.toLowerCase();

    // Determine query type: checklist vs Q&A guidance
    const isChecklistQuestion = /document|checklist|what do i need|what documents|what forms|paperwork/i.test(q);
    const isPathwayQuestion = /\bvs\b|versus|which pathway|should i use|difference between|compare|\bor da\b|\bor cdc\b|cdc or da|da or cdc/i.test(q);

    // Extract pathway (CDC or DA) - but only use it for filtering if asking for checklists
    let pathway: string | null = null;
    if (q.includes('cdc') || q.includes('complying development')) {
      pathway = 'CDC';
    }
    if (q.includes(' da ') || q.includes(' da?') || q.includes(' da,') || q.includes('development application')) {
      // If both CDC and DA mentioned, it's a comparison question
      if (pathway === 'CDC') {
        pathway = null; // Don't filter by pathway for comparison questions
      } else {
        pathway = 'DA';
      }
    }

    // Map question keywords to development_type for checklist lookups
    const devTypeMap: Record<string, string> = {
      'residential': 'residential',
      'granny flat': 'secondary_dwelling',
      'secondary dwelling': 'secondary_dwelling',
      'dual occ': 'dual_occupancy',
      'dual occupancy': 'dual_occupancy',
      'duplex': 'dual_occupancy',
      'two storey': 'two_storey_addition',
      'two-storey': 'two_storey_addition',
      'second storey': 'two_storey_addition',
      'pool': 'swimming_pool',
      'swimming pool': 'swimming_pool',
      'garage': 'garage_carport',
      'carport': 'garage_carport',
      'deck': 'deck_pergola',
      'pergola': 'deck_pergola',
      'commercial': 'commercial_fitout',
      'fitout': 'commercial_fitout',
      'fit-out': 'commercial_fitout',
      'heritage': 'heritage',
      'flood': 'flood_zone',
      'bushfire': 'bushfire_prone',
    };

    let developmentType: string | null = null;
    for (const [keyword, dbValue] of Object.entries(devTypeMap)) {
      if (q.includes(keyword)) {
        developmentType = dbValue;
        break;
      }
    }

    // Build query params
    const params = new URLSearchParams();
    params.set('question', question);
    params.set('limit', '10');

    // Decide what to fetch based on question type
    if (isChecklistQuestion) {
      params.set('type', 'checklist');
      if (pathway) params.set('pathway', pathway);
      if (developmentType) params.set('development_type', developmentType);
    } else if (isPathwayQuestion) {
      params.set('type', 'guidance');
      params.set('category', 'pathway'); // Search pathway category for comparison questions
    } else {
      params.set('type', 'guidance');
    }

    let response = await fetch(`${API_BASE}/api/procedural?${params.toString()}`);
    let data = await response.json();

    // Fallback: if no guidance found for pathway question, search by category
    if (isPathwayQuestion && (!data.guidance?.items?.length)) {
      const fallbackParams = new URLSearchParams();
      fallbackParams.set('category', 'pathway');
      fallbackParams.set('type', 'guidance');
      fallbackParams.set('limit', '5');
      response = await fetch(`${API_BASE}/api/procedural?${fallbackParams.toString()}`);
      data = await response.json();
    }

    if (!data.success) {
      return {
        success: false,
        category: 'procedural',
        data: null,
        sources: [],
        error: 'Unable to find procedural guidance.',
      };
    }

    const sources: Citation[] = [];

    if (data.guidance?.items?.length > 0) {
      for (const item of data.guidance.items.slice(0, 2)) {
        sources.push({
          source: item.source_document,
          url: item.source_url || 'https://www.planningportal.nsw.gov.au/',
        });
      }
    }

    // Add checklist sources with correct URL
    if (data.checklist?.items?.length > 0) {
      const seenChecklists = new Set<string>();
      for (const item of data.checklist.items) {
        if (!seenChecklists.has(item.checklist_name)) {
          seenChecklists.add(item.checklist_name);
          sources.push({
            source: item.checklist_name,
            url: 'https://www.planningportal.nsw.gov.au/onlinecdc',
          });
        }
      }
    }

    return {
      success: true,
      category: 'procedural',
      data: {
        guidance: data.guidance?.items || [],
        checklist: data.checklist?.items || [],
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] Procedural lookup error:', error);
    return {
      success: false,
      category: 'procedural',
      data: null,
      sources: [],
      error: 'Unable to fetch procedural guidance. Please try again.',
    };
  }
}

/**
 * Handle guide questions from /api/guides
 */
async function handleGuideQuestion(question: string): Promise<DataResponse> {
  try {
    // Map question keywords to guide slugs
    const guideKeywordMap: Record<string, string> = {
      'granny flat': 'build-granny-flat',
      'secondary dwelling': 'build-granny-flat',
      'second storey': 'add-second-storey',
      'second story': 'add-second-storey',
      'two storey': 'add-second-storey',
      'two story': 'add-second-storey',
      'upstairs': 'add-second-storey',
      'duplex': 'build-duplex',
      'dual occupancy': 'build-duplex',
      'dual occ': 'build-duplex',
      'knock down': 'knock-down-rebuild',
      'knockdown': 'knock-down-rebuild',
      'rebuild': 'knock-down-rebuild',
      'subdivide': 'subdivide-property',
      'subdivision': 'subdivide-property',
    };

    const q = question.toLowerCase();
    let slug: string | null = null;

    // Find matching guide based on keywords
    for (const [keyword, guideSlug] of Object.entries(guideKeywordMap)) {
      if (q.includes(keyword)) {
        slug = guideSlug;
        break;
      }
    }

    // Fetch guide by slug or search
    const url = slug
      ? `${API_BASE}/api/guides?slug=${encodeURIComponent(slug)}`
      : `${API_BASE}/api/guides?search=${encodeURIComponent(question)}&limit=3`;

    const response = await fetch(url);
    const data = await response.json();

    if (!data.success || data.count === 0) {
      // Fallback to listing all guides
      const allGuidesResponse = await fetch(`${API_BASE}/api/guides?limit=5`);
      const allGuidesData = await allGuidesResponse.json();

      if (allGuidesData.success && allGuidesData.count > 0) {
        return {
          success: true,
          category: 'guide',
          data: {
            guides: allGuidesData.guides,
            isListing: true,
          },
          sources: [{
            source: 'NSW Planning Portal',
            url: 'https://www.planningportal.nsw.gov.au/',
          }],
        };
      }

      return {
        success: false,
        category: 'guide',
        data: null,
        sources: [],
        error: 'No guides found. Try asking about granny flats, second storeys, duplexes, or subdivision.',
      };
    }

    const sources: Citation[] = data.guides.map((guide: any) => ({
      source: guide.source_document || 'NSW Planning Portal Guides',
      url: guide.source_url || 'https://www.planningportal.nsw.gov.au/',
    }));

    return {
      success: true,
      category: 'guide',
      data: {
        guides: data.guides,
        isListing: data.count > 1,
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] Guide lookup error:', error);
    return {
      success: false,
      category: 'guide',
      data: null,
      sources: [],
      error: 'Unable to fetch guide. Please try again.',
    };
  }
}

/**
 * Handle factual lookups from /api/capacity/calculate or /api/provisions/for-property
 * Uses provisions API for parking/landscaping to get actual DCP provisions
 */
async function handleFactualLookup(
  controlType: string,
  context: PropertyContext
): Promise<DataResponse> {
  try {
    // For height and FSR, use values from Planning Portal (already in context)
    // For all other DCP topics, query the DCP provisions API (same source as DCP tab)
    if (controlType !== 'height' && controlType !== 'fsr' && controlType !== 'all') {
      return handleDcpProvisionLookup(controlType, context);
    }

    // Use Planning Portal data directly from context (no API call needed)
    const capacity: any = {};
    if (context.maxHeight) {
      capacity.maxHeight = context.maxHeight;
      // Estimate storeys: ~3m per storey
      capacity.approxStoreys = Math.floor(context.maxHeight / 3);
    }
    if (context.maxFsr && context.lotSize) {
      capacity.maxFSR = context.maxFsr;
      capacity.maxGFA = context.lotSize * context.maxFsr;
      capacity.lotArea = context.lotSize;
    }

    // Filter to requested control type
    let filteredData: any = { capacity };
    if (controlType === 'height') {
      filteredData.capacity = {
        maxHeight: capacity.maxHeight,
        approxStoreys: capacity.approxStoreys
      };
    } else if (controlType === 'fsr') {
      filteredData.capacity = {
        maxFSR: capacity.maxFSR,
        maxGFA: capacity.maxGFA,
        lotArea: capacity.lotArea
      };
    }

    const sources: Citation[] = [{
      source: 'NSW Planning Portal',
      url: 'https://www.planningportal.nsw.gov.au/',
    }];

    return {
      success: true,
      category: 'factual_lookup',
      data: filteredData,
      sources,
    };
  } catch (error) {
    console.error('[Router] Capacity lookup error:', error);
    return {
      success: false,
      category: 'factual_lookup',
      data: null,
      sources: [],
      error: 'Unable to fetch development controls. Please try again.',
    };
  }
}

/**
 * Handle DCP topic lookups from /api/provisions/for-property
 * Uses the same DCP provisions source as the DCP tab
 * Supports all DCP topics: parking, landscaping, setbacks, waste, stormwater, etc.
 */
async function handleDcpProvisionLookup(
  topic: string,
  context: PropertyContext
): Promise<DataResponse> {
  try {
    // DQ-31, same class as the Housing SEPP handler below: this sent
    // `context.zone || 'R2'`, so when the zone was unknown the AI answered with
    // R2's DCP provisions and presented them as this property's.
    //
    // Omitting the param is NOT sufficient either — cross-review caught that.
    // Without a zone the endpoint applies no zone filter, so zone-specific rows
    // for OTHER zones come back and get presented as applicable here. That is the
    // same fabrication with a wider net.
    //
    // An unknown zone means the question cannot be answered for this property, so
    // say that, exactly as the Housing SEPP handler does.
    // Zone AND council scope are both required. Cross-review caught that zone
    // alone is not enough: without a council the endpoint can return another
    // council's provisions for the same zone, and they read as applicable here.
    //
    // Written as explicit guards rather than a collected list so TypeScript
    // narrows `context.zone` to a string below.
    const hasCouncil = Boolean(context.lga || context.formerCouncil);
    if (!context.zone || !hasCouncil) {
      const missingScope = [!context.zone && 'zone', !hasCouncil && 'council']
        .filter(Boolean).join(' and ');
      return {
        success: false,
        category: 'factual_lookup',
        data: null,
        sources: [],
        error: `The ${missingScope} for this property is not known, and DCP `
          + `provisions are scoped by both. Not assessed — this is not a finding `
          + `that no ${topic} provisions apply.`,
      };
    }

    const params = new URLSearchParams({
      zone: context.zone,
      topic: topic, // Topics match v2_topic in regulatory_provisions
    });
    if (context.lga) params.set('lga', context.lga);
    if (context.formerCouncil) params.set('former_council', context.formerCouncil);

    // Add heritage params if property is heritage-listed
    if (context.constraints?.heritage) {
      params.set('heritage', 'true');
      // Pass HCA code if available for HCA-specific provisions
      if (context.constraints.hca) {
        params.set('hca', context.constraints.hca);
      }
    }

    // Add precinct ID if available
    if (context.precinctId) {
      params.set('precinct_id', context.precinctId);
    }

    const response = await fetch(`${API_BASE}/api/provisions/for-property?${params.toString()}`);
    const data = await response.json();

    if (!data.success || !data.data?.by_layer) {
      return {
        success: false,
        category: 'factual_lookup',
        data: null,
        sources: [],
        error: `Unable to find ${topic} requirements.`,
      };
    }

    // Collect provisions from all layers
    const allProvisions: any[] = [];
    for (const layer of data.data.by_layer) {
      allProvisions.push(...layer.provisions);
    }

    if (allProvisions.length === 0) {
      return {
        success: false,
        category: 'factual_lookup',
        data: null,
        sources: [],
        error: `No ${topic} requirements found for this property.`,
      };
    }

    // Format all provisions for display (no truncation - show everything)
    const formattedProvisions = allProvisions.map((p: any) => ({
      text: p.provision_text,
      source: p.document_id,
      section: p.toc_section_title || p.v2_dcp_part,
      page: p.pdf_page,
    }));

    // Build sources from unique documents
    const uniqueDocs = new Set(allProvisions.map((p: any) => p.document_id).filter(Boolean));
    const sources: Citation[] = Array.from(uniqueDocs).slice(0, 3).map(doc => ({
      source: (doc as string).replace(/_/g, ' '),
      url: 'https://www.planningportal.nsw.gov.au/',
    }));

    return {
      success: true,
      category: 'factual_lookup',
      data: {
        dcpProvisions: formattedProvisions,
        topic: topic,
        totalCount: allProvisions.length,
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] DCP provision lookup error:', error);
    return {
      success: false,
      category: 'factual_lookup',
      data: null,
      sources: [],
      error: `Unable to fetch ${topic} requirements. Please try again.`,
    };
  }
}

/**
 * Handle permissibility check from /api/permissibility/check
 */
async function handlePermissibilityCheck(
  developmentType: string,
  context: PropertyContext
): Promise<DataResponse> {
  try {
    // Map common terms to LEP terminology
    const devTypeMap: Record<string, string> = {
      'duplex': 'dual_occupancy',
      'dual occupancy': 'dual_occupancy',
      'granny flat': 'secondary_dwelling',
      'secondary dwelling': 'secondary_dwelling',
      'townhouse': 'multi_dwelling_housing',
      'townhouses': 'multi_dwelling_housing',
      'apartment': 'residential_flat_building',
      'apartments': 'residential_flat_building',
      'house': 'dwelling_house',
      'dwelling': 'dwelling_house',
    };

    const normalizedType = devTypeMap[developmentType.toLowerCase()] || developmentType;

    const response = await fetch(`${API_BASE}/api/permissibility/check`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        address: context.address,
        developmentType: normalizedType,
      }),
    });

    const data = await response.json();

    // Use zone from API response, fallback to context
    const displayZone = data.zone_name || data.zone || context.zone || 'this zone';

    const sources: Citation[] = [{
      source: `Inner West LEP 2022 - ${displayZone}`,
    }];

    // API returns success:false for prohibited, but we still want to show the result
    return {
      success: true,
      category: 'permissibility',
      data: {
        developmentType: normalizedType, // Include for display formatting
        permitted: data.permitted ?? false,
        permissibility: data.permissibility || 'prohibited',
        zone: data.zone || context.zone,
        zoneName: data.zone_name || context.zone,
        reason: data.reason,
        summary: data.summary,
        lepControls: data.lep_controls,
        alternatives: data.alternative_options,
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] Permissibility check error:', error);
    return {
      success: false,
      category: 'permissibility',
      data: null,
      sources: [],
      error: 'Unable to check permissibility. Please try again.',
    };
  }
}

/**
 * Handle Housing SEPP eligibility from /api/housing-sepp/eligibility
 */
async function handleHousingSeppCheck(context: PropertyContext): Promise<DataResponse> {
  try {
    // DQ-31. This previously sent `zone || 'R2'`, `lotSize || 450`,
    // `lotWidth || 12` and a hardcoded `isLMRArea: true`. Every one of those is a
    // measurement of a SPECIFIC SITE, and every one was invented when the real
    // value was missing — so an answer was produced for a property whose zone, lot
    // size, width and LMR status were all unknown, and the LMR gate (the input the
    // whole result turns on) was asserted in the claimant's favour.
    //
    // Missing inputs now stop the check instead of being filled in. An answer the
    // user cannot act on is better than a confident one derived from defaults.
    const missing = [
      !context.zone && 'zone',
      context.lotSize == null && 'lot size',
      context.lotWidth == null && 'lot width',
    ].filter(Boolean) as string[];

    if (missing.length > 0) {
      return {
        success: false,
        category: 'housing_sepp',
        data: null,
        sources: [],
        error: `Housing SEPP eligibility needs ${missing.join(', ')} for this property. `
          + `Not assessed — this is not a finding that the property is ineligible.`,
      };
    }

    const response = await fetch(`${API_BASE}/api/housing-sepp/eligibility`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        zoneCode: context.zone,
        lotSize: context.lotSize,
        lotWidth: context.lotWidth,
        // Omitted deliberately: this handler has no LMR-area source. The endpoint
        // now treats an absent value as NOT ASSESSED rather than as `true`.
      }),
    });

    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        category: 'housing_sepp',
        data: null,
        sources: [],
        error: data.error || 'Unable to check Housing SEPP eligibility.',
      };
    }

    const sources: Citation[] = [{
      source: 'SEPP (Housing) 2021',
      url: 'https://legislation.nsw.gov.au/view/html/inforce/current/epi-2021-0714',
    }];

    return {
      success: true,
      category: 'housing_sepp',
      data: {
        eligibleTypes: data.data.eligibleTypes,
        propertyInfo: data.data.propertyInfo,
        eligibleCount: data.data.eligibleCount,
        totalChecked: data.data.totalChecked,
      },
      sources,
    };
  } catch (error) {
    console.error('[Router] Housing SEPP check error:', error);
    return {
      success: false,
      category: 'housing_sepp',
      data: null,
      sources: [],
      error: 'Unable to check Housing SEPP eligibility. Please try again.',
    };
  }
}

/**
 * Handle constraint check from /api/property
 */
async function handleConstraintCheck(context: PropertyContext): Promise<DataResponse> {
  try {
    const response = await fetch(
      `${API_BASE}/api/property?address=${encodeURIComponent(context.address || '')}`
    );
    const data = await response.json();

    if (!data.success) {
      return {
        success: false,
        category: 'constraint_check',
        data: null,
        sources: [],
        error: 'Unable to fetch property constraints.',
      };
    }

    const constraints = data.data.constraints || {};

    return {
      success: true,
      category: 'constraint_check',
      data: {
        heritage: constraints.heritage,
        heritageName: constraints.heritageName,
        hca: constraints.hca,
        flood: constraints.flood,
        bushfire: constraints.bushfire,
        zone: constraints.zone,
        lga: constraints.lga,
        maxHeight: constraints.maxHeight,
        maxFsr: constraints.maxFsr,
      },
      sources: [{
        source: 'NSW Planning Portal',
        url: 'https://www.planningportal.nsw.gov.au/',
      }],
    };
  } catch (error) {
    console.error('[Router] Constraint check error:', error);
    return {
      success: false,
      category: 'constraint_check',
      data: null,
      sources: [],
      error: 'Unable to fetch property constraints. Please try again.',
    };
  }
}

/**
 * Handle synthesis questions requiring multiple endpoints
 */
async function handleSynthesis(
  question: string,
  context: PropertyContext
): Promise<DataResponse> {
  // Fetch multiple data sources in parallel
  const [capacityRes, constraintRes] = await Promise.all([
    handleFactualLookup('all', context),
    handleConstraintCheck(context),
  ]);

  // Combine sources
  const allSources = [
    ...capacityRes.sources,
    ...constraintRes.sources,
  ];

  // Check if any succeeded
  if (!capacityRes.success && !constraintRes.success) {
    return {
      success: false,
      category: 'synthesis',
      data: null,
      sources: [],
      error: 'Unable to gather property information. Please try again.',
    };
  }

  return {
    success: true,
    category: 'synthesis',
    data: {
      capacity: capacityRes.success ? capacityRes.data : null,
      constraints: constraintRes.success ? constraintRes.data : null,
    },
    sources: allSources,
  };
}

/**
 * Handle interpretation questions with graceful refusal
 */
async function handleInterpretationRefusal(
  question: string,
  context?: PropertyContext
): Promise<DataResponse> {
  // Even when refusing, provide helpful factual data if property is available
  let factualData = null;
  let sources: Citation[] = [];

  if (context?.address) {
    try {
      const capacityRes = await handleFactualLookup('all', context);
      if (capacityRes.success) {
        factualData = capacityRes.data;
        sources = capacityRes.sources;
      }
    } catch {
      // Ignore errors - this is supplementary
    }
  }

  return {
    success: true,
    category: 'interpretation',
    data: factualData,
    sources,
    refusalMessage: `That question requires professional assessment that I'm unable to provide. I can only give you factual planning requirements.

Here's what I CAN tell you about this property:`,
  };
}
