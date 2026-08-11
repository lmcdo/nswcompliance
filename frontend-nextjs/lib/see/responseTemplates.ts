/**
 * Context-aware response templates for DA assessment.
 *
 * Templates are looked up by v2_structural_category first, then by
 * keyword matching against topic / section_header / marker.
 * All templates are professional planning language suitable for a SEE.
 */

export type ComplianceStatus = 'complies' | 'varies' | 'not_applicable';

export interface TemplateSet {
  complies: string;
  varies: string;
  not_applicable: string;
}

export interface ProvisionContext {
  category?: string | null;
  topic?: string | null;
  marker?: string | null;
  sectionHeader?: string | null;
}

// ─── Templates by planning topic ─────────────────────────────────────────────

const TEMPLATES: Record<string, TemplateSet> = {
  heritage: {
    complies:
      'The proposed works are sympathetic to the heritage significance of the item/area. The scale, form, materials and detailing respect the identified character of the heritage conservation area and do not diminish the heritage significance of the place.',
    varies:
      'The proposed works vary from this heritage control. [Insert justification addressing the specific heritage significance and demonstrating that the impact is acceptable having regard to the Statement of Heritage Impact.]',
    not_applicable:
      'This heritage control does not apply to the proposed works given the nature and location of the development relative to the identified heritage fabric.',
  },

  height: {
    complies:
      'The proposed building height complies with the maximum height specified in this control.',
    varies:
      'The proposed building height exceeds the control. [Insert height of proposed development, control limit, and justification for the variation including whether a LEP or DCP variation pathway applies.]',
    not_applicable:
      'The height control is not applicable to this element of the proposed development.',
  },

  setbacks: {
    complies:
      'The proposed development maintains setbacks that comply with the minimum requirements. The built form respects the required separation from boundaries and is consistent with the established pattern of development in the streetscape.',
    varies:
      'The proposed setback is less than the standard control. The variation is minor, arises from site constraints, and is consistent with the established setback rhythm of the streetscape. [Insert setback proposed vs required.]',
    not_applicable:
      'Setback controls are not applicable to this element of the proposed works.',
  },

  landscaping: {
    complies:
      'The proposed development retains significant existing vegetation and provides new landscaping consistent with the character of the area. Soft landscaped area and deep soil zone meet the requirements of this control.',
    varies:
      'The proposed landscaping does not fully meet this control. [Insert shortfall details and compensatory measures such as alternative deep soil areas, green roofs, or enhanced planting.] The variation is acceptable having regard to the overall landscape quality achieved.',
    not_applicable:
      'This landscaping control is not applicable to the proposed development.',
  },

  stormwater: {
    complies:
      'Stormwater from the proposed development is managed in accordance with the applicable standards. On-site detention, absorption areas and drainage connections are detailed in the engineering documentation submitted with this application.',
    varies:
      'Stormwater management varies from this control due to site constraints. [Insert engineering justification and alternative measures proposed.] A detailed stormwater management plan is provided.',
    not_applicable:
      'This stormwater control is not applicable to the proposed development.',
  },

  parking: {
    complies:
      'The proposed development provides parking in accordance with the DCP requirements.',
    varies:
      'The number of car spaces provided is less than the standard requirement. [Insert spaces provided vs required, and justification referencing site location, proximity to public transport, or existing parking supply.]',
    not_applicable:
      'Parking controls are not applicable to this component of the proposed development.',
  },

  privacy: {
    complies:
      'The proposed works maintain acceptable levels of visual privacy for adjoining properties. Window placement, screening devices and setbacks limit opportunities for direct overlooking.',
    varies:
      'The proposed development has the potential to impact privacy of adjoining properties. [Insert details of impact and proposed mitigation such as screening, obscure glazing, or reorientation of windows.]',
    not_applicable:
      'This privacy control is not applicable to the proposed development.',
  },

  solar_access: {
    complies:
      'The proposed development does not result in unreasonable additional overshadowing of adjoining properties or private open space. Shadow diagrams confirm compliance with the applicable solar access standard.',
    varies:
      'The proposed development results in some additional overshadowing of adjoining properties. [Insert period and extent of shadow impact from the shadow diagrams, and justification that the impact is acceptable.] The primary private open space of adjoining properties retains the required solar access.',
    not_applicable:
      'This solar access control is not applicable to the proposed development.',
  },

  site_coverage: {
    complies:
      'The proposed site coverage complies with the maximum permitted under this control.',
    varies:
      'The proposed site coverage exceeds the control limit. [Insert proposed coverage percentage vs control limit and justification for the variation.]',
    not_applicable:
      'Site coverage controls are not applicable to this element of the proposed development.',
  },

  materials: {
    complies:
      'The materials proposed are consistent with the character of the area. External finishes are sympathetic to the existing dwelling and surrounding streetscape.',
    varies:
      'The proposed materials vary from those typically found in the area. [Insert material details and justification for the selection, including how heritage or streetscape character is maintained.]',
    not_applicable:
      'This materials control is not applicable to the proposed development.',
  },

  waste: {
    complies:
      'Adequate waste storage and collection areas are provided in accordance with the requirements. Bin storage areas are accessible and screened from public view.',
    varies:
      'Waste management varies from the standard control due to site constraints. [Insert details and proposed alternative arrangements.]',
    not_applicable:
      'This waste management control is not applicable to the proposed development.',
  },

  accessibility: {
    complies:
      'The proposed development provides accessible paths of travel and facilities in accordance with the applicable requirements.',
    varies:
      'Full compliance with the accessibility standard is not achievable due to site constraints. [Insert details and proposed alternative design solutions.]',
    not_applicable:
      'Accessibility controls for this provision are not applicable to the proposed development.',
  },

  retaining_walls: {
    complies:
      'The proposed retaining walls are designed to be structurally sound, will not adversely affect adjoining properties, and incorporate drainage as required. Engineering drawings are provided.',
    varies:
      'The retaining wall design varies from this control. [Insert details of height, location relative to boundary, and justification including geotechnical or engineering advice.]',
    not_applicable:
      'This retaining wall control is not applicable to the proposed works.',
  },
};

// ─── Category and keyword mappings ───────────────────────────────────────────

const CATEGORY_MAP: Record<string, string> = {
  heritage: 'heritage',
  heritage_control: 'heritage',
  building_height: 'height',
  height: 'height',
  setback: 'setbacks',
  setbacks: 'setbacks',
  front_setback: 'setbacks',
  secondary_street_setback: 'setbacks',
  side_setback: 'setbacks',
  rear_setback: 'setbacks',
  landscape: 'landscaping',
  landscaping: 'landscaping',
  deep_soil: 'landscaping',
  tree: 'landscaping',
  stormwater: 'stormwater',
  drainage: 'stormwater',
  flooding: 'stormwater',
  car_parking: 'parking',
  parking: 'parking',
  transport: 'parking',
  privacy: 'privacy',
  solar: 'solar_access',
  solar_access: 'solar_access',
  overshadowing: 'solar_access',
  site_coverage: 'site_coverage',
  coverage: 'site_coverage',
  materials: 'materials',
  finishes: 'materials',
  waste: 'waste',
  accessibility: 'accessibility',
  retaining: 'retaining_walls',
};

const TOPIC_KEYWORDS: Array<[RegExp, string]> = [
  [/heritage|conservation area|curtilage|significance/i, 'heritage'],
  [/height/i, 'height'],
  [/setback|separation/i, 'setbacks'],
  [/landscap|deep.soil|canopy|garden|tree|planting/i, 'landscaping'],
  [/stormwater|drainage|flood|overland flow/i, 'stormwater'],
  [/car.?space|parking|vehicle/i, 'parking'],
  [/privacy|overlooking|visual/i, 'privacy'],
  [/solar|shadow|overshadow|sunlight/i, 'solar_access'],
  [/site.?coverage|coverage|footprint/i, 'site_coverage'],
  [/material|finish|cladding|colour/i, 'materials'],
  [/waste|bin|collection/i, 'waste'],
  [/access|disabled|mobility|universal/i, 'accessibility'],
  [/retaining|retain.?wall|cut.?fill|earthwork/i, 'retaining_walls'],
];

const GENERIC: TemplateSet = {
  complies: 'The proposed development complies with this control.',
  varies:
    'The proposed development varies from this control. [Insert reason and justification.]',
  not_applicable: 'This control does not apply to the proposed development.',
};

// ─── Public API ──────────────────────────────────────────────────────────────

export function getTemplatesForProvision(ctx: ProvisionContext): TemplateSet {
  if (ctx.category) {
    const key = CATEGORY_MAP[ctx.category.toLowerCase()];
    if (key && TEMPLATES[key]) return TEMPLATES[key];
  }
  const combined = [ctx.topic, ctx.sectionHeader, ctx.marker].filter(Boolean).join(' ');
  for (const [re, key] of TOPIC_KEYWORDS) {
    if (re.test(combined) && TEMPLATES[key]) return TEMPLATES[key];
  }
  return GENERIC;
}

export function getTemplate(status: ComplianceStatus, ctx: ProvisionContext): string {
  return getTemplatesForProvision(ctx)[status];
}
