/**
 * Question Classifier using Gemini
 *
 * Classifies user questions into 8 categories:
 * 1. factual_lookup - Height, FSR, setbacks for a property
 * 2. permissibility - Whether specific developments are permitted
 * 3. housing_sepp - SEPP Housing 2021 eligibility questions
 * 4. constraint_check - Property constraints (heritage, flood, etc.)
 * 5. definition - Planning term definitions
 * 6. synthesis - Questions requiring multiple data sources
 * 7. procedural - CDC vs DA, checklists, process questions
 * 8. interpretation - Professional judgment required (REFUSED)
 */

import { google } from '@ai-sdk/google';
import { generateText } from 'ai';

// Question categories
export type QuestionCategory =
  | 'factual_lookup'
  | 'permissibility'
  | 'housing_sepp'
  | 'constraint_check'
  | 'definition'
  | 'synthesis'
  | 'procedural'
  | 'guide'
  | 'interpretation';

// Extracted parameters from the question
export interface ExtractedParams {
  term?: string;
  developmentType?: string;
  controlType?: string;  // Any DCP topic: height, fsr, setbacks, parking, landscaping, waste, stormwater, social_impact, etc.
  subQuestions?: string[];
  originalQuestion: string;
}

// Classification result
export interface ClassificationResult {
  category: QuestionCategory;
  confidence: number;
  extractedParams: ExtractedParams;
  reasoning: string;
}

// Property context for classification
export interface PropertyContext {
  address?: string;
  zone?: string;
  lga?: string;
  formerCouncil?: string;
  lotSize?: number;
  lotWidth?: number;
  precinctId?: string;
  maxHeight?: number;  // From Planning Portal spatial layers
  maxFsr?: number;     // From Planning Portal spatial layers
  constraints?: {
    heritage?: boolean;
    heritageName?: string;
    hca?: string;  // HCA code from Planning Portal (e.g., "C98" or slug like "parramatta_road")
    flood?: boolean;
    bushfire?: boolean;
  };
}

/**
 * Classify a user question using Gemini
 */
export async function classifyQuestion(
  question: string,
  propertyContext?: PropertyContext
): Promise<ClassificationResult> {
  const q = question.toLowerCase();

  // Pre-check: Certain patterns should immediately classify as procedural
  // (bypass AI which sometimes misclassifies these as definition)
  const proceduralPatterns = [
    /(?:common|most common)\s+(?:reasons?|mistakes?|errors?)/i,
    /(?:das?|development applications?)\s+(?:get|are|being)\s+(?:rejected|refused|knocked back)/i,
    /(?:what|why)\s+(?:causes?|leads? to)\s+(?:delays?|rejection)/i,
    /do i need (?:a |an )?(?:certifier|architect|planner|surveyor)/i,
  ];

  for (const pattern of proceduralPatterns) {
    if (pattern.test(q)) {
      return {
        category: 'procedural',
        confidence: 0.9,
        extractedParams: { originalQuestion: question },
        reasoning: 'Question is about development process outcomes or requirements',
      };
    }
  }

  const contextString = propertyContext
    ? `
Property Context:
- Address: ${propertyContext.address || 'Not provided'}
- Zone: ${propertyContext.zone || 'Unknown'}
- LGA: ${propertyContext.lga || 'Unknown'}
- Former Council: ${propertyContext.formerCouncil || 'Unknown'}
- Lot Size: ${propertyContext.lotSize ? `${propertyContext.lotSize}m²` : 'Unknown'}
- Heritage: ${propertyContext.constraints?.heritage ? `Yes (${propertyContext.constraints.heritageName || 'Heritage listed'})` : 'No'}
`
    : 'No property selected';

  const systemPrompt = `You are a question classifier for an NSW planning compliance tool. Your job is to categorize questions to route them to the correct data endpoint.

CATEGORIES:

1. factual_lookup - Questions about specific development controls for a property
   Examples: "What's the height limit?", "What are the setbacks?", "What's the FSR?"
   Requires: Property context
   Extract: controlType (height, fsr, setbacks, parking, landscaping, or all)

2. permissibility - Questions about whether a development type is allowed
   Examples: "Can I build a duplex?", "Is dual occupancy permitted?", "Are granny flats allowed?"
   Requires: Property context + development type
   Extract: developmentType

3. housing_sepp - Questions specifically about SEPP Housing 2021 / Low-Mid Rise reforms
   Examples: "Am I eligible for low-rise housing?", "What are the LMR lot requirements?", "Can I build a manor house?"
   Requires: Property context + lot dimensions

4. constraint_check - Questions about property constraints
   Examples: "Is this property heritage listed?", "Is there flood risk?", "What are the environmental constraints?"
   Requires: Property context

5. definition - Questions asking what a planning term means
   Examples: "What is a habitable room?", "Define setback", "What does FSR mean?"
   Extract: term

6. synthesis - Complex questions requiring multiple data sources
   Examples: "What can I build on this lot?", "Give me an overview of the development controls", "What are all the requirements?"
   May extract: subQuestions (broken down parts)

7. procedural - Questions about the development application process, timelines, requirements, and outcomes
   Examples: "Should I use CDC or DA?", "What documents do I need?", "How long does approval take?", "What are common reasons DAs get rejected?", "What causes delays?", "Do I need a certifier?"

8. guide - Questions asking how to start or complete a development project
   Examples: "How do I build a granny flat?", "I want to add a second storey", "What's involved in building a duplex?", "How do I subdivide my property?", "I want to knock down and rebuild"
   Signs: Asks about the overall process/steps for a project type, mentions "getting started", "how do I", "what's involved"

9. interpretation - Questions requiring professional judgment (REFUSE THESE)
   Examples: "Will my application be approved?", "Is this a good investment?", "Should I proceed?", "What are my chances?"
   Signs: Asks for prediction, recommendation, advice, opinion, or assessment of likelihood

IMPORTANT RULES:
- If no property is selected and the question needs property context, classify as the appropriate category but note it in reasoning
- If the question asks for prediction, assessment, or professional opinion → interpretation
- If the question mentions CDC/DA process, documents, timeline → procedural
- If the question is about SEPP Housing, LMR, manor house, dual occupancy eligibility → housing_sepp
- "Can I build X" is permissibility, not interpretation
- Extract the specific term for definition questions
- Extract the development type for permissibility questions

${contextString}`;

  try {
    const result = await generateText({
      model: google('gemini-2.0-flash'),
      prompt: `${systemPrompt}

User Question: "${question}"

Respond with a JSON object containing:
- category: one of [factual_lookup, permissibility, housing_sepp, constraint_check, definition, synthesis, procedural, guide, interpretation]
- confidence: number between 0 and 1
- term: (optional) extracted term for definition questions
- developmentType: (optional) extracted development type for permissibility
- controlType: (optional) one of [height, fsr, setbacks, parking, landscaping, all]
- reasoning: brief explanation

Return ONLY the JSON object, no other text.`,
    });

    // Parse the JSON response
    const jsonMatch = result.text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) {
      console.error('[Classifier] No JSON found in response:', result.text);
      return fallbackClassify(question);
    }

    const parsed = JSON.parse(jsonMatch[0]);

    // Validate category
    const validCategories: QuestionCategory[] = [
      'factual_lookup', 'permissibility', 'housing_sepp', 'constraint_check',
      'definition', 'synthesis', 'procedural', 'guide', 'interpretation'
    ];

    const category = validCategories.includes(parsed.category)
      ? parsed.category as QuestionCategory
      : 'synthesis';

    return {
      category,
      confidence: typeof parsed.confidence === 'number' ? parsed.confidence : 0.7,
      extractedParams: {
        term: parsed.term,
        developmentType: parsed.developmentType,
        controlType: parsed.controlType,
        originalQuestion: question,
      },
      reasoning: parsed.reasoning || 'Classified by AI',
    };
  } catch (error) {
    console.error('[Classifier] Error classifying question:', error);

    // Fallback classification based on keyword matching
    return fallbackClassify(question);
  }
}

/**
 * Fallback classifier using keyword matching when Gemini is unavailable
 */
function fallbackClassify(question: string): ClassificationResult {
  const q = question.toLowerCase();

  // Explicit definition requests (highest priority) - "Define X", "What does X mean?"
  const explicitDefinitionPatterns = [
    /^define\s+(.+?)(?:\?|\.)?$/i,
    /^what\s+does\s+(.+?)\s+mean(?:\?|\.)?$/i,
    /^meaning\s+of\s+(.+?)(?:\?|\.)?$/i,
    /^definition\s+of\s+(.+?)(?:\?|\.)?$/i,
  ];

  for (const pattern of explicitDefinitionPatterns) {
    const match = q.match(pattern);
    if (match) {
      return {
        category: 'definition',
        confidence: 0.85,
        extractedParams: {
          term: match[1].trim(),
          originalQuestion: question,
        },
        reasoning: 'Explicit definition request pattern matched',
      };
    }
  }

  // Interpretation patterns (refuse these) - CHECK EARLY to prevent false matches
  const interpretationKeywords = [
    'will my application',
    'chances of',
    'my chances',
    'likely to',
    'should i proceed',
    'good investment',
    'recommend',
    'advise',
    'opinion',
    'be approved',
    'get approved',
    'will i get',
    'will it be',
    'how likely',
  ];

  if (interpretationKeywords.some(kw => q.includes(kw))) {
    return {
      category: 'interpretation',
      confidence: 0.8,
      extractedParams: { originalQuestion: question },
      reasoning: 'Question requires professional judgment',
    };
  }

  // "What is X?" pattern - but NOT when asking about property-specific values or requirements
  // "What is FSR?" in context = asking for value, "What is a habitable room?" = definition
  const whatIsPattern = /what (?:is|are) (?:a |an |the )?(.+?)(?:\?|$)/i;
  const whatIsMatch = q.match(whatIsPattern);
  if (whatIsMatch) {
    const term = whatIsMatch[1].trim().toLowerCase();
    // Questions about "standards", "requirements", "controls" are factual lookups, not definitions
    // Extract specific controlType based on what's mentioned - includes ALL DCP topics
    const controlTypeKeywords: Record<string, string> = {
      // Core controls
      'parking requirements': 'parking',
      'parking': 'parking',
      'car spaces': 'parking',
      'landscaping requirements': 'landscaping',
      'landscaping': 'landscaping',
      'landscaped area': 'landscaping',
      'setback requirements': 'setbacks',
      'setbacks': 'setbacks',
      'setback': 'setbacks',
      'height limit': 'height',
      'height': 'height',
      'fsr': 'fsr',
      'floor space ratio': 'fsr',
      // All other DCP topics
      'access': 'access',
      'accessibility': 'access',
      'bicycle': 'bicycle_parking',
      'bike parking': 'bicycle_parking',
      'biodiversity': 'biodiversity',
      'building design': 'building_design',
      'building form': 'building_form',
      'contamination': 'contamination',
      'contaminated': 'contamination',
      'energy': 'energy',
      'fencing': 'fencing',
      'fence': 'fencing',
      'open space': 'open_space',
      'privacy': 'privacy',
      'overlooking': 'privacy',
      'safety': 'safety',
      'crime prevention': 'safety',
      'signage': 'signage',
      'signs': 'signage',
      'site analysis': 'site_analysis',
      'social impact': 'social_impact',
      'stormwater': 'stormwater',
      'drainage': 'stormwater',
      'streetscape': 'streetscape',
      'subdivision': 'subdivision',
      'sustainability': 'sustainability',
      'tree': 'tree_management',
      'trees': 'tree_management',
      'tree management': 'tree_management',
      'waste': 'waste',
      'garbage': 'waste',
      'water': 'water',
    };

    let detectedControlType: string = 'all';
    for (const [keyword, controlType] of Object.entries(controlTypeKeywords)) {
      if (term.includes(keyword)) {
        detectedControlType = controlType;
        break;
      }
    }

    // All DCP topics that should trigger factual_lookup
    const dcpTopicKeywords = [
      'height', 'fsr', 'setback', 'setbacks', 'parking', 'height limit', 'floor space ratio',
      'development standards', 'standards', 'requirements', 'controls', 'development controls',
      'landscaping', 'access', 'bicycle', 'biodiversity', 'building design', 'building form',
      'contamination', 'energy', 'fencing', 'open space', 'privacy', 'safety', 'signage',
      'site analysis', 'social impact', 'stormwater', 'streetscape', 'subdivision',
      'sustainability', 'tree', 'waste', 'water', 'drainage', 'garbage',
    ];

    const isFactualQuestion = dcpTopicKeywords.some(kw => term.includes(kw));

    if (isFactualQuestion) {
      return {
        category: 'factual_lookup',
        confidence: 0.8,
        extractedParams: {
          controlType: detectedControlType,
          originalQuestion: question,
        },
        reasoning: `Question asks about ${detectedControlType === 'all' ? 'development standards/requirements' : detectedControlType}`,
      };
    }

    // Known planning terms that are always definitions (even without article)
    const knownPlanningTerms = [
      'basix', 'cdc', 'da', 'lep', 'dcp', 'sepp', 'fsr', 'setback',
      'dual occupancy', 'secondary dwelling', 'complying development',
      'development application', 'construction certificate', 'occupation certificate',
      'principal certifier', 'section 10.7', 'clause 4.6', 'section 4.55',
      'heritage conservation area', 'floor space ratio', 'gross floor area',
      'site coverage', 'landscaped area', 'deep soil', 'private open space',
      'articulation zone', 'building envelope', 'habitable room',
    ];

    const isKnownTerm = knownPlanningTerms.some(t => term === t || term.includes(t));
    const hasArticle = /what (?:is|are) (?:a |an )(.+?)(?:\?|$)/i.test(q);

    if (hasArticle || isKnownTerm) {
      return {
        category: 'definition',
        confidence: isKnownTerm ? 0.9 : 0.7,
        extractedParams: {
          term: whatIsMatch[1].trim(),
          originalQuestion: question,
        },
        reasoning: isKnownTerm ? 'Known planning term matched' : 'What is a/an X pattern matched as definition',
      };
    }
  }

  // Guide patterns - questions about how to do specific development projects
  const guidePatterns = [
    /how (?:do i|can i|to) (?:build|construct|add|do) (?:a |an )?(.+)/i,
    /i want to (?:build|construct|add|do) (?:a |an )?(.+)/i,
    /what(?:'s| is) involved in (?:building|constructing|adding|doing) (?:a |an )?(.+)/i,
    /getting started (?:with |on )?(.+)/i,
    /steps to (?:build|construct|add) (?:a |an )?(.+)/i,
    /guide (?:to|for) (?:building|constructing|adding) (?:a |an )?(.+)/i,
  ];

  // Check for guide patterns with specific project types
  const guideProjectTypes = [
    'granny flat', 'secondary dwelling',
    'second storey', 'second story', 'two storey', 'two story', 'upstairs',
    'duplex', 'dual occupancy', 'dual occ',
    'knock down', 'knockdown', 'rebuild', 'knock down and rebuild',
    'subdivide', 'subdivision',
  ];

  for (const pattern of guidePatterns) {
    if (pattern.test(q)) {
      // Check if it mentions a guide-relevant project type
      if (guideProjectTypes.some(pt => q.includes(pt))) {
        return {
          category: 'guide',
          confidence: 0.85,
          extractedParams: { originalQuestion: question },
          reasoning: 'Question asks about how to complete a development project',
        };
      }
    }
  }

  // Direct mentions of guide project types with "i want to" or "how do i"
  if ((q.includes('i want to') || q.includes('how do i') || q.includes('how can i')) &&
      guideProjectTypes.some(pt => q.includes(pt))) {
    return {
      category: 'guide',
      confidence: 0.8,
      extractedParams: { originalQuestion: question },
      reasoning: 'Question asks about starting a development project',
    };
  }

  // "[project type] guide" or "guide for [project type]" patterns
  if (q.includes('guide') && guideProjectTypes.some(pt => q.includes(pt))) {
    return {
      category: 'guide',
      confidence: 0.9,
      extractedParams: { originalQuestion: question },
      reasoning: 'Direct request for project guide',
    };
  }

  // Procedural patterns
  const proceduralKeywords = [
    'cdc', 'da ', 'das ', 'development application', 'complying development',
    'document', 'checklist', 'how long', 'timeline', 'process',
    'rejected', 'rejection', 'refused', 'delays', 'common reasons',
    'common mistakes', 'approval', 'approved', 'lodge', 'lodgement',
    'certifier', 'council', 'assessment', 'pre-lodgement',
  ];
  if (proceduralKeywords.some(kw => q.includes(kw))) {
    return {
      category: 'procedural',
      confidence: 0.7,
      extractedParams: { originalQuestion: question },
      reasoning: 'Question is about development process',
    };
  }

  // DCP topic requirements patterns - "give me X requirements", "X requirements", "show me X"
  // Must come BEFORE synthesis patterns to prevent false matches
  const dcpTopicMap: Record<string, string> = {
    'access': 'access',
    'accessibility': 'access',
    'bicycle': 'bicycle_parking',
    'bike parking': 'bicycle_parking',
    'bike': 'bicycle_parking',
    'biodiversity': 'biodiversity',
    'building design': 'building_design',
    'building form': 'building_form',
    'site coverage': 'site_coverage',
    'contamination': 'contamination',
    'contaminated': 'contamination',
    'energy': 'energy',
    'fencing': 'fencing',
    'fence': 'fencing',
    'height': 'height',
    'fsr': 'fsr',
    'floor space ratio': 'fsr',
    'landscaping': 'landscaping',
    'landscaped': 'landscaping',
    'open space': 'open_space',
    'parking': 'parking',
    'car space': 'parking',
    'privacy': 'privacy',
    'overlooking': 'privacy',
    'safety': 'safety',
    'crime prevention': 'safety',
    'setback': 'setbacks',
    'setbacks': 'setbacks',
    'signage': 'signage',
    'signs': 'signage',
    'site analysis': 'site_analysis',
    'social impact': 'social_impact',
    'social': 'social_impact',
    'stormwater': 'stormwater',
    'drainage': 'stormwater',
    'streetscape': 'streetscape',
    'subdivision': 'subdivision',
    'sustainability': 'sustainability',
    'tree': 'tree_management',
    'trees': 'tree_management',
    'tree management': 'tree_management',
    'waste': 'waste',
    'garbage': 'waste',
    'rubbish': 'waste',
    'water': 'water',
  };

  // Check for "give me X requirements", "X requirements", "show me X requirements" patterns
  const requirementsPatterns = [
    /(?:give me|show me|get|tell me|what are) (?:the )?(.+?) requirements/i,
    /(.+?) requirements(?:\?)?$/i,
  ];

  for (const pattern of requirementsPatterns) {
    const match = q.match(pattern);
    if (match) {
      const topic = match[1].trim().toLowerCase();
      // Check if it matches a known DCP topic - prefer exact matches first
      // First pass: exact match
      if (dcpTopicMap[topic]) {
        return {
          category: 'factual_lookup',
          confidence: 0.9,
          extractedParams: {
            controlType: dcpTopicMap[topic],
            originalQuestion: question,
          },
          reasoning: `Question asks about ${dcpTopicMap[topic]} requirements`,
        };
      }
      // Second pass: partial match (topic contains keyword or keyword contains topic)
      for (const [keyword, controlType] of Object.entries(dcpTopicMap)) {
        if (topic.includes(keyword) || keyword.includes(topic)) {
          return {
            category: 'factual_lookup',
            confidence: 0.85,
            extractedParams: {
              controlType: controlType,
              originalQuestion: question,
            },
            reasoning: `Question asks about ${controlType} requirements`,
          };
        }
      }
    }
  }

  // Synthesis patterns (must come before permissibility to catch "what can I build" without specific type)
  const synthesisPatterns = [
    /what can i (?:build|develop|construct)(?:\s+(?:on|here|on this|at this))?/i,
    /what (?:are|is) (?:the |all )?(?:requirements|controls|rules)/i,
    /give me (?:an? )?(?:overview|summary)/i,
    /tell me (?:about|everything)/i,
    /what (?:are|is) (?:the )?development (?:options|possibilities)/i,
  ];

  for (const pattern of synthesisPatterns) {
    if (pattern.test(q)) {
      return {
        category: 'synthesis',
        confidence: 0.75,
        extractedParams: { originalQuestion: question },
        reasoning: 'Question requires comprehensive overview from multiple sources',
      };
    }
  }

  // Permissibility patterns (specific development types)
  const permissibilityPatterns = [
    /can i (?:build|construct|develop) (?:a |an )(.+?)(?:\?|$)/i,  // Must have "a/an" to indicate specific type
    /is (?:a |an )?(.+?) (?:permitted|allowed|permissible)/i,
    /are (.+?) (?:permitted|allowed|permissible)/i,
  ];

  for (const pattern of permissibilityPatterns) {
    const match = q.match(pattern);
    if (match) {
      return {
        category: 'permissibility',
        confidence: 0.7,
        extractedParams: {
          developmentType: match[1].trim(),
          originalQuestion: question,
        },
        reasoning: 'Question asks about development permissibility',
      };
    }
  }

  // Factual lookup patterns
  if (q.includes('height') || q.includes('how tall')) {
    return {
      category: 'factual_lookup',
      confidence: 0.8,
      extractedParams: { controlType: 'height', originalQuestion: question },
      reasoning: 'Question asks about height controls',
    };
  }

  if (q.includes('fsr') || q.includes('floor space ratio')) {
    return {
      category: 'factual_lookup',
      confidence: 0.8,
      extractedParams: { controlType: 'fsr', originalQuestion: question },
      reasoning: 'Question asks about FSR',
    };
  }

  if (q.includes('setback')) {
    return {
      category: 'factual_lookup',
      confidence: 0.8,
      extractedParams: { controlType: 'setbacks', originalQuestion: question },
      reasoning: 'Question asks about setbacks',
    };
  }

  if (q.includes('parking') || q.includes('car space')) {
    return {
      category: 'factual_lookup',
      confidence: 0.8,
      extractedParams: { controlType: 'parking', originalQuestion: question },
      reasoning: 'Question asks about parking requirements',
    };
  }

  if (q.includes('landscaping') || q.includes('landscaped')) {
    return {
      category: 'factual_lookup',
      confidence: 0.8,
      extractedParams: { controlType: 'landscaping', originalQuestion: question },
      reasoning: 'Question asks about landscaping requirements',
    };
  }

  // SEPP Housing patterns
  if (q.includes('sepp') || q.includes('lmr') || q.includes('low-rise') || q.includes('mid-rise') || q.includes('manor house')) {
    return {
      category: 'housing_sepp',
      confidence: 0.7,
      extractedParams: { originalQuestion: question },
      reasoning: 'Question relates to SEPP Housing reforms',
    };
  }

  // Constraint check patterns
  if (q.includes('heritage') || q.includes('flood') || q.includes('bushfire') || q.includes('constraint')) {
    return {
      category: 'constraint_check',
      confidence: 0.7,
      extractedParams: { originalQuestion: question },
      reasoning: 'Question asks about property constraints',
    };
  }

  // Default to synthesis for complex/unclear questions
  return {
    category: 'synthesis',
    confidence: 0.5,
    extractedParams: { originalQuestion: question },
    reasoning: 'Question appears to require multiple data sources',
  };
}
