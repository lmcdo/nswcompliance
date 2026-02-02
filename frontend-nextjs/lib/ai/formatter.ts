/**
 * Response Formatter for AI Assistant
 *
 * Formats data endpoint responses into human-readable text.
 * Attaches citations and suggests follow-up questions.
 * No AI generation - only templated formatting.
 */

import { DataResponse, Citation } from './router';
import { QuestionCategory } from './classifier';

// Formatted response structure
export interface FormattedResponse {
  message: string;
  citations: Citation[];
  suggestedQuestions: string[];
  category: QuestionCategory;
  isRefusal: boolean;
}

/**
 * Format a data response into human-readable text
 */
export function formatResponse(dataResponse: DataResponse): FormattedResponse {
  const { category, data, sources, error, refusalMessage } = dataResponse;

  // Handle errors
  if (!dataResponse.success && error) {
    return {
      message: error,
      citations: [],
      suggestedQuestions: getSuggestedQuestions(category, false),
      category,
      isRefusal: false,
    };
  }

  // Handle refusals (interpretation questions)
  if (refusalMessage) {
    const factualPart = data ? formatFactualData(data) : '';
    return {
      message: refusalMessage + (factualPart ? `\n\n${factualPart}` : ''),
      citations: sources,
      suggestedQuestions: [
        'What is the height limit?',
        'What are the setback requirements?',
        'Is dual occupancy permitted?',
      ],
      category,
      isRefusal: true,
    };
  }

  // Format based on category
  let message: string;

  switch (category) {
    case 'definition':
      message = formatDefinitionResponse(data);
      break;

    case 'procedural':
      message = formatProceduralResponse(data);
      break;

    case 'factual_lookup':
      message = formatFactualResponse(data);
      break;

    case 'permissibility':
      message = formatPermissibilityResponse(data);
      break;

    case 'housing_sepp':
      message = formatHousingSeppResponse(data);
      break;

    case 'constraint_check':
      message = formatConstraintResponse(data);
      break;

    case 'synthesis':
      message = formatSynthesisResponse(data);
      break;

    case 'guide':
      message = formatGuideResponse(data);
      break;

    default:
      message = 'I found some information, but I\'m not sure how to present it. Please try rephrasing your question.';
  }

  return {
    message,
    citations: sources,
    suggestedQuestions: getSuggestedQuestions(category, true),
    category,
    isRefusal: false,
  };
}

/**
 * Format definition lookup response
 */
function formatDefinitionResponse(data: any): string {
  if (!data?.definitions?.length) {
    return 'No definition found for that term.';
  }

  const { term, definitions } = data;
  const primary = definitions[0];

  let response = `**${cleanText(term)}** — ${cleanText(primary.text)}`;

  if (primary.summary && primary.summary !== primary.text) {
    response += `\n${cleanText(primary.summary)}`;
  }

  response += `\n*Source: ${cleanText(primary.source)}${primary.clause ? ` (${cleanText(primary.clause)})` : ''}*`;

  if (definitions.length > 1) {
    const otherSources = definitions.slice(1, 3).map((d: any) => cleanText(d.source));
    response += ` · Also in: ${otherSources.join(', ')}`;
  }

  return response;
}

/**
 * Format procedural guidance response
 */
function formatProceduralResponse(data: any): string {
  const { guidance, checklist } = data;

  if (!guidance?.length && !checklist?.length) {
    return 'No procedural guidance found.';
  }

  let response = '';

  if (guidance?.length > 0) {
    const primary = guidance[0];
    response += `${cleanText(primary.answer_summary)}`;

    if (primary.answer_detailed && primary.answer_detailed !== primary.answer_summary) {
      response += `\n\n${cleanText(primary.answer_detailed)}`;
    }

    if (primary.answer_conditions?.length > 0) {
      response += '\n\n**Key conditions:**';
      for (const condition of primary.answer_conditions) {
        response += `\n• ${cleanText(condition)}`;
      }
    }

    if (primary.follow_up_questions?.length > 0) {
      response += '\n\n*Related:* ' + primary.follow_up_questions.map((q: string) => cleanText(q)).join(' · ');
    }
  }

  if (checklist?.length > 0) {
    const grouped: Record<string, any[]> = {};
    for (const item of checklist) {
      if (!grouped[item.checklist_name]) grouped[item.checklist_name] = [];
      grouped[item.checklist_name].push(item);
    }

    for (const [name, items] of Object.entries(grouped)) {
      response += `\n\n**${cleanText(name)}**`;
      for (const item of items) {
        const tag = item.item_required ? '✓' : '○';
        response += `\n${tag} ${cleanText(item.item_name)}`;
      }
    }
  }

  return response;
}

/**
 * Format DCP provisions response (parking/landscaping from provisions API)
 */
function formatDcpProvisions(data: any): string {
  const { dcpProvisions, topic, totalCount } = data;
  const topicTitle = capitalize(topic.replace(/_/g, ' '));

  let response = `**${topicTitle} Requirements** — ${totalCount} provision${totalCount === 1 ? '' : 's'}`;

  // Filter and show useful provisions only
  let shownCount = 0;
  for (const p of dcpProvisions) {
    const text = cleanText(p.text || '');
    const summary = extractSummary(text);

    // Skip useless provisions
    if (!summary || !isUsefulProvision(summary, p.section)) {
      continue;
    }

    response += `\n\n• ${cleanText(summary)}`;
    if (p.section) {
      response += `\n  *${cleanText(p.section)}*`;
    }
    shownCount++;

    // Limit to 5 most relevant provisions to avoid overwhelming users
    if (shownCount >= 5) break;
  }

  if (shownCount === 0) {
    response += '\n\n*No specific requirements found. Check the **DCP tab** for detailed provisions.*';
  }

  // Add data limitations note
  response += '\n\n---\n**Data Note:** DCP provisions shown are extracted from the applicable council DCP. Not all provisions may be displayed. Check the **DCP tab** for the full list or consult the DCP document.';

  return response;
}

/**
 * Check if a provision is useful to display (not just a header, definition, or fragment)
 */
function isUsefulProvision(summary: string, section: string): boolean {
  if (!summary || summary.length < 20) return false;

  const lower = summary.toLowerCase();
  const sectionLower = (section || '').toLowerCase();

  // Skip section headers and generic part names
  if (/^(part|section|chapter)\s+\d+/i.test(summary)) return false;
  if (/^(generic provisions|definitions|key terms|introduction)/i.test(summary)) return false;

  // Skip pure definitions (starts with term + "means")
  if (/^\w+\s+(means|refers to|is defined as)/i.test(summary)) return false;

  // Skip if section is "Definitions" or "unknown"
  if (sectionLower.includes('definition') || sectionLower === 'unknown') return false;

  // Skip table fragments and reference-only text
  if (/^(table|figure|diagram|refer to|see |note:|code requirement)/i.test(summary)) return false;

  // Skip if it's mostly numbers/symbols (table data)
  const alphaChars = summary.replace(/[^a-zA-Z]/g, '').length;
  if (alphaChars < summary.length * 0.5) return false;

  return true;
}

/**
 * Extract a summary from provision text (first meaningful sentence, max 250 chars)
 */
function extractSummary(text: string): string {
  if (!text) return '';

  // Remove section headers and clean up
  let cleaned = text
    .replace(/^\d+\.\d+(\.\d+)?\s+[A-Z][^\n]*/m, '') // Remove "2.10.1 Title" headers
    .replace(/^[a-z]\.\s*/gm, '') // Remove list markers like "a. ", "b. ", "c. "
    .replace(/^[ivx]+\.\s*/gm, '') // Remove roman numeral markers
    .replace(/\n+/g, ' ')
    .trim();

  // Skip any remaining short fragments at the start
  while (cleaned.length > 0 && cleaned.length < 20 && cleaned.includes(' ')) {
    const spaceIdx = cleaned.indexOf(' ');
    if (spaceIdx > 0 && spaceIdx < 15) {
      cleaned = cleaned.slice(spaceIdx + 1).trim();
    } else {
      break;
    }
  }

  // Get first meaningful sentence (must be at least 30 chars to be meaningful)
  const sentences = cleaned.split(/[.!?]+/);
  let firstSentence = '';
  for (const s of sentences) {
    const trimmed = s.trim();
    if (trimmed.length >= 30) {
      firstSentence = trimmed;
      break;
    }
  }

  // If no long sentence found, use whatever we have
  if (!firstSentence) {
    firstSentence = cleaned.slice(0, 250);
  }

  // Truncate if too long
  if (firstSentence.length > 250) {
    return firstSentence.slice(0, 247) + '...';
  }

  return firstSentence;
}

/**
 * Format factual lookup response (height, FSR, setbacks)
 */
function formatFactualResponse(data: any): string {
  // Handle DCP provisions format (parking/landscaping from provisions API)
  if (data?.dcpProvisions) {
    return formatDcpProvisions(data);
  }

  // Check if we have any relevant data (capacity, setbacks, parking, or landscaping)
  const hasData = data?.capacity || data?.setbacks || data?.parking !== undefined || data?.landscaping !== undefined;
  if (!hasData) {
    return 'Unable to find development controls for this property.';
  }

  const { capacity, setbacks, parking, landscaping } = data;
  let response = '';

  // Height and FSR on same line if both exist
  if (capacity) {
    const parts: string[] = [];
    if (capacity.maxHeight) {
      let h = `**Height:** ${capacity.maxHeight}m`;
      if (capacity.approxStoreys) h += ` (~${capacity.approxStoreys} storey)`;
      parts.push(h);
    }
    if (capacity.maxFSR) {
      let f = `**FSR:** ${capacity.maxFSR}:1`;
      if (capacity.maxGFA && capacity.lotArea) {
        f += ` (${Math.round(capacity.maxGFA)}m² on ${capacity.lotArea}m² lot)`;
      }
      parts.push(f);
    }
    if (parts.length) {
      response += parts.join(' · ');
    } else if (!setbacks && !parking && !landscaping) {
      // No height/FSR and no other data - explain why
      return 'Height and FSR data is retrieved from the NSW Planning Portal when a property is looked up. Please ensure the address is valid and recognized by the Planning Portal.';
    }
  }

  if (setbacks) {
    response += '\n\n**Setbacks**';
    if (setbacks.type === 'prevailing') {
      response += ` — ${setbacks.message}`;
      if (setbacks.guidance) {
        for (const g of setbacks.guidance) {
          response += `\n• ${capitalize(g.boundary)}: ${g.text}`;
        }
      }
    } else if (setbacks.values?.length > 0) {
      const valid = setbacks.values.filter((v: any) => v.value !== undefined && v.value !== null);
      if (valid.length > 0) {
        const inline = valid.map((v: any) => {
          let s = `${capitalize(v.boundary)}: ${v.value}${v.unit || 'm'}`;
          if (v.conditional) s += '*';
          return s;
        });
        response += ` — ${inline.join(' · ')}`;
      } else {
        response += ' — *Check DCP for specific requirements*';
      }
    } else if (setbacks.type === 'not_available') {
      response += ` — ${setbacks.message}`;
    }
  }

  // Parking section: show data, or "not available" message if specifically requested
  // (parking is [] when requested, undefined when not requested)
  if (parking !== undefined) {
    if (parking.length > 0) {
      response += '\n\n**Parking**';
      for (const p of parking) {
        response += `\n• ${p.text}`;
      }
    } else {
      response += '\n\n**Parking** — *Check DCP for parking requirements. Typically 1-2 spaces required for dwelling houses.*';
    }
  }

  // Landscaping section: show data, or "not available" message if specifically requested
  if (landscaping !== undefined) {
    if (landscaping.length > 0) {
      response += '\n\n**Landscaping**';
      for (const l of landscaping) {
        response += `\n• ${l.text}`;
      }
    } else {
      response += '\n\n**Landscaping** — *Check DCP for landscaping requirements. Typically 30-50% of site required as landscaped area.*';
    }
  }

  // Add LEP limitations note if height/FSR are shown
  if (capacity?.maxHeight || capacity?.maxFSR) {
    response += '\n\n---\n**Data Note:** Height and FSR values are sourced from NSW Planning Portal spatial layers based on the LEP. Check the **LEP tab** for clause details. Site-specific exceptions may apply.';
  }

  return response.trim();
}

/**
 * Format permissibility response
 */
function formatPermissibilityResponse(data: any): string {
  if (!data) {
    return 'Unable to check permissibility for this development type.';
  }

  const { developmentType, permitted, permissibility, zoneName, zone, reason, summary, alternatives } = data;
  const displayZone = zoneName || zone || 'this zone';
  const displayDevType = developmentType ? capitalize(developmentType.replace(/_/g, ' ')) : '';

  let response = '';

  if (permitted) {
    const status = permissibility === 'permitted' ? 'Permitted' : 'Permissible with consent';
    response += `✓ **${displayDevType}${displayDevType ? ' ' : ''}${status}** in ${displayZone}`;
    if (summary) response += `\n${summary}`;
  } else {
    response += `✗ **${displayDevType}${displayDevType ? ' ' : ''}Prohibited** in ${displayZone}`;
    if (reason) response += `\n${reason}`;
  }

  if (!permitted && alternatives?.length > 0) {
    response += '\n\n**Alternatives permitted:** ';
    response += alternatives.map((a: string) => a.replace(/_/g, ' ')).join(' · ');
  }

  // Add LEP limitations note
  response += '\n\n---\n**Data Note:** Permissibility is based on the LEP land use table. Check the **LEP tab** for zone details. Development must also comply with DCP and SEPP requirements.';

  return response;
}

/**
 * Format Housing SEPP response
 */
function formatHousingSeppResponse(data: any): string {
  if (!data?.eligibleTypes) {
    return 'Unable to check Housing SEPP eligibility.';
  }

  const { eligibleTypes, propertyInfo, eligibleCount, totalChecked } = data;

  let response = `**Housing SEPP** — ${eligibleCount}/${totalChecked} eligible`;
  response += `\n*${propertyInfo.zoneCode} · ${propertyInfo.lotSize}m² · ${propertyInfo.lotWidth}m wide*`;

  const eligible = eligibleTypes.filter((t: any) => t.isEligible);
  if (eligible.length > 0) {
    response += '\n\n**Eligible:**';
    for (const type of eligible) {
      response += `\n✓ **${type.displayName}** — ${type.description}`;
      if (type.eligibilityReason) response += `\n  *${type.eligibilityReason}*`;
    }
  }

  const notEligible = eligibleTypes.filter((t: any) => !t.isEligible);
  if (notEligible.length > 0) {
    response += '\n\n**Not eligible:**';
    for (const type of notEligible) {
      response += `\n✗ ${type.displayName} — ${type.eligibilityReason}`;
    }
  }

  // Add SEPP limitations note
  response += '\n\n---\n**Data Note:** SEPP eligibility is calculated based on zone, lot size, and lot width. Check the **SEPP tab** for full requirements. Site-specific constraints may apply.';

  return response;
}

/**
 * Format constraint check response
 */
function formatConstraintResponse(data: any): string {
  if (!data) {
    return 'Unable to fetch property constraints.';
  }

  // First line: zone and LGA
  let response = `**${data.zone || 'Unknown'}** · ${data.lga || 'Unknown LGA'}`;

  // Second line: controls
  const controls: string[] = [];
  if (data.maxHeight) controls.push(`Height: ${data.maxHeight}m`);
  if (data.maxFsr) controls.push(`FSR: ${data.maxFsr}:1`);
  if (controls.length) response += `\n${controls.join(' · ')}`;

  // Third line: overlays (only if any exist)
  const overlays: string[] = [];
  if (data.heritage) overlays.push(`Heritage${data.heritageName ? ` (${data.heritageName})` : ''}`);
  if (data.hca) overlays.push('HCA');
  if (data.flood) overlays.push('Flood');
  if (data.bushfire) overlays.push('Bushfire');

  if (overlays.length > 0) {
    response += `\n⚠️ ${overlays.join(' · ')}`;
  }

  return response;
}

/**
 * Format synthesis response (multiple data sources)
 */
function formatSynthesisResponse(data: any): string {
  if (!data) {
    return 'Unable to gather property information.';
  }

  let response = '';

  if (data.constraints) {
    response += formatConstraintResponse(data.constraints);
  }

  if (data.capacity) {
    const capacityData = formatFactualData(data.capacity);
    if (capacityData.trim()) {
      response += (response ? '\n\n' : '') + capacityData;
    }
  }

  return response || 'No property data available.';
}

/**
 * Format guide response
 */
function formatGuideResponse(data: any): string {
  if (!data?.guides?.length) {
    return 'No guides found for this topic.';
  }

  const { guides, isListing } = data;

  // Listing multiple guides
  if (isListing && guides.length > 1) {
    let response = '**Available Guides**';
    for (const guide of guides) {
      response += `\n• **${guide.title}** — ${guide.target_user}`;
      if (guide.typical_timeline) response += ` (${guide.typical_timeline})`;
    }
    response += '\n\n*Ask about a specific project to see the full guide.*';
    return response;
  }

  // Detailed single guide
  const guide = guides[0];
  let response = `**${guide.title}**`;
  response += `\n*${guide.target_user}*`;

  // Timeline and cost on same line
  const meta: string[] = [];
  if (guide.typical_timeline) meta.push(`⏱ ${guide.typical_timeline}`);
  if (guide.typical_cost_range) meta.push(`💰 ${guide.typical_cost_range}`);
  if (meta.length) response += `\n${meta.join(' · ')}`;

  // Eligibility inline
  if (guide.eligibility && Object.keys(guide.eligibility).length > 0) {
    const eligItems = Object.entries(guide.eligibility).map(([k, v]) => {
      const label = k.replace(/_/g, ' ');
      return `${label}: ${v}`;
    });
    response += `\n\n**Eligibility:** ${eligItems.join(' · ')}`;
  }

  // Steps - compact format
  if (guide.steps?.length > 0) {
    response += '\n';
    for (const step of guide.steps) {
      response += `\n**${step.step_number}. ${step.title}**`;
      if (step.duration) response += ` *(${step.duration})*`;
      response += `\n${step.description}`;
      if (step.tasks?.length > 0) {
        for (const task of step.tasks) {
          response += `\n  → ${task}`;
        }
      }
    }
  }

  // Pitfalls
  if (guide.common_pitfalls?.length > 0) {
    response += '\n\n**⚠️ Common Pitfalls**';
    for (const pitfall of guide.common_pitfalls) {
      response += `\n• ${pitfall}`;
    }
  }

  return response;
}

/**
 * Format factual data (for refusal responses and synthesis)
 */
function formatFactualData(data: any): string {
  const parts: string[] = [];

  if (data.capacity?.maxHeight) {
    parts.push(`Height: ${data.capacity.maxHeight}m`);
  }
  if (data.capacity?.maxFSR) {
    parts.push(`FSR: ${data.capacity.maxFSR}:1`);
  }

  if (data.setbacks?.values?.length > 0) {
    const valid = data.setbacks.values.filter((v: any) => v.value !== undefined && v.value !== null);
    if (valid.length > 0) {
      const setbackStr = valid.map((v: any) => `${v.boundary}: ${v.value}${v.unit || 'm'}`).join(', ');
      parts.push(`Setbacks: ${setbackStr}`);
    }
  }

  return parts.join(' · ');
}

/**
 * Get suggested follow-up questions based on category
 */
function getSuggestedQuestions(category: QuestionCategory, success: boolean): string[] {
  if (!success) {
    return [
      'What is BASIX?',
      'What is a CDC?',
      'CDC vs DA difference',
      'Granny flat guide',
      'CDC documents checklist',
    ];
  }

  switch (category) {
    case 'definition':
      return [
        'What is a CDC?',
        'What is a DA?',
        'What is FSR?',
        'What is a setback?',
        'CDC vs DA difference',
        'Granny flat guide',
      ];

    case 'procedural':
      return [
        'CDC documents checklist',
        'DA documents checklist',
        'CDC vs DA difference',
        'How long does CDC take?',
        'How long does DA take?',
        'Granny flat guide',
      ];

    case 'factual_lookup':
      return [
        'Is dual occupancy permitted?',
        'What constraints apply?',
        'CDC vs DA difference',
        'Granny flat guide',
        'Duplex guide',
        'CDC documents checklist',
      ];

    case 'permissibility':
      return [
        'CDC vs DA difference',
        'CDC documents checklist',
        'DA documents checklist',
        'What is dual occupancy?',
        'Granny flat guide',
        'Duplex guide',
      ];

    case 'housing_sepp':
      return [
        'CDC vs DA difference',
        'What is dual occupancy?',
        'Granny flat guide',
        'Duplex guide',
        'CDC documents checklist',
        'DA documents checklist',
      ];

    case 'constraint_check':
      return [
        'Is dual occupancy permitted?',
        'CDC vs DA difference',
        'Granny flat guide',
        'Duplex guide',
        'CDC documents checklist',
        'DA documents checklist',
      ];

    case 'synthesis':
      return [
        'Is dual occupancy permitted?',
        'CDC vs DA difference',
        'CDC documents checklist',
        'Granny flat guide',
        'Duplex guide',
        'What is BASIX?',
      ];

    case 'guide':
      return [
        'CDC vs DA - which pathway?',
        'CDC documents checklist',
        'DA documents checklist',
        'Granny flat guide',
        'Duplex guide',
        'Second storey guide',
      ];

    default:
      return [
        'What is BASIX?',
        'What is a CDC?',
        'CDC vs DA difference',
        'Granny flat guide',
        'CDC documents checklist',
        'DA documents checklist',
      ];
  }
}

/**
 * Capitalize first letter
 */
function capitalize(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

/**
 * Clean text encoding artifacts from database content
 */
function cleanText(text: string): string {
  if (!text) return '';
  return text
    // Fix double-encoded UTF-8 (common mojibake patterns)
    .replace(/â€™/g, "'")      // Right single quote
    .replace(/â€˜/g, "'")      // Left single quote
    .replace(/â€œ/g, '"')      // Left double quote
    .replace(/â€/g, '"')       // Right double quote (partial)
    .replace(/â€"/g, '—')      // Em dash
    .replace(/â€"/g, '–')      // En dash
    .replace(/Â·/g, '·')       // Middle dot
    .replace(/Â /g, ' ')       // Non-breaking space
    .replace(/Ã©/g, 'é')       // e-acute
    .replace(/Ã¨/g, 'è')       // e-grave
    // Fix corrupted quote patterns seen in database
    .replace(/""/g, '"')       // Double corrupted quotes -> single quote
    .replace(/'''/g, "'")      // Triple single quotes -> single quote
    .replace(/"™/g, "'")       // Corrupted apostrophe
    .replace(/"'/g, "'")       // Quote + apostrophe
    .replace(/'\s*"/g, "'")    // Apostrophe + quote
    // Remove annotation artifacts that got embedded in text
    .replace(/,\s*#\s*left single quote\s*/gi, "'")  // Annotation artifact
    .replace(/#\s*left single quote\s*/gi, "'")      // Annotation artifact
    .replace(/#\s*right single quote\s*/gi, "'")     // Annotation artifact
    .replace(/#\s*left double quote\s*/gi, '"')      // Annotation artifact
    .replace(/#\s*right double quote\s*/gi, '"')     // Annotation artifact
    // Clean up Unicode escapes
    .replace(/\u00c2\u00b7/g, '·')  // Double-encoded middle dot
    .replace(/\u00e2\u0080\u0099/g, "'")  // Triple-encoded apostrophe
    .replace(/\u00e2\u0080\u0098/g, "'")  // Triple-encoded left single quote
    .replace(/\u00e2\u0080\u009c/g, '"')  // Triple-encoded left quote
    .replace(/\u00e2\u0080\u009d/g, '"')  // Triple-encoded right quote
    // Final cleanup - normalize multiple spaces
    .replace(/\s{2,}/g, ' ')
    .trim();
}
