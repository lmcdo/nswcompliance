import { streamText, convertToCoreMessages, CoreMessage } from 'ai';
import { google } from '@ai-sdk/google';
import { openai } from '@ai-sdk/openai';
import { NextRequest } from 'next/server';

// Query complexity classification
type QueryComplexity = 'simple' | 'standard' | 'complex';

interface RegulatoryContext {
  address: string;
  zone: string;
  lga: string;
  formerCouncil: string;
  precinctId?: string;
  heritage?: {
    isHeritage: boolean;
    heritageType?: string;
  };
  lotArea?: number;
  developmentType: string;
}

interface ChatRequest {
  messages: Array<{
    role: 'user' | 'assistant' | 'system';
    content: string;
  }>;
  context: RegulatoryContext;
  precomputedData?: {
    height?: { value: string; source: string; provisionId?: number };
    fsr?: { value: string; source: string; provisionId?: number };
    setbacks?: { value: string; source: string; provisionId?: number };
    parking?: { value: string; source: string; provisionId?: number };
  };
}

/**
 * Classify query complexity to determine model routing
 * - Simple: Single-topic factual (use precomputed if available)
 * - Standard: Multi-topic or context-dependent (Gemini)
 * - Complex: Cross-layer synthesis, compliance analysis (GPT-4o)
 */
function classifyQueryComplexity(query: string, context: RegulatoryContext): QueryComplexity {
  const lowerQuery = query.toLowerCase();

  // Simple: Single-topic factual questions
  const simplePatterns = [
    /^what is the (height|fsr|setback|parking)/i,
    /^what('s| is) the (max|maximum) (height|fsr)/i,
    /^is .+ permitted/i,
    /^can i build .+ here/i,
    /^what zone is this/i,
  ];

  if (simplePatterns.some(p => p.test(lowerQuery))) {
    return 'simple';
  }

  // Complex: Cross-layer reasoning, compliance synthesis
  const complexIndicators = [
    /maximum .* (can|could) .* build/i,
    /comply|compliant|compliance/i,
    /what .* requirements .* (all|complete|full)/i,
    /compare|difference|override/i,
    /sepp .* (and|vs|versus) .* (lep|dcp)/i,
    /heritage .* (and|plus|with) .* (height|setback)/i,
    /(can|could) i .* (and|also|plus)/i,
    /what .* (need|require) .* (approval|da|cdc)/i,
  ];

  if (complexIndicators.some(p => p.test(lowerQuery))) {
    return 'complex';
  }

  // Heritage properties get upgraded to complex for heritage-related questions
  if (context.heritage?.isHeritage && /heritage|historic|conservation/i.test(lowerQuery)) {
    return 'complex';
  }

  // Default: standard complexity (Gemini)
  return 'standard';
}

/**
 * Build system prompt with regulatory context
 */
function buildSystemPrompt(context: RegulatoryContext): string {
  return `You are a NSW planning compliance assistant for the property at ${context.address}.

PROPERTY CONTEXT:
- Zone: ${context.zone}
- LGA: ${context.lga}
- Former Council: ${context.formerCouncil}
${context.precinctId ? `- Precinct: ${context.precinctId}` : ''}
${context.heritage?.isHeritage ? `- Heritage Status: ${context.heritage.heritageType || 'Yes'}` : '- Heritage Status: None'}
${context.lotArea ? `- Lot Area: ${context.lotArea}m²` : ''}
- Development Type: ${context.developmentType}

REGULATORY HIERARCHY (CRITICAL):
1. State Environmental Planning Policies (SEPPs) - highest priority, can override LEP/DCP
2. Local Environmental Plan (LEP) - sets land use zones, height, FSR
3. Development Control Plan (DCP) - detailed design controls, setbacks, parking

RULES FOR RESPONSES:
1. ALWAYS cite provision references (e.g., "LEP Clause 4.3", "DCP Part 4.2.3", "SEPP Housing s.30")
2. When SEPP overrides LEP/DCP, explicitly state this
3. Be specific with numbers - don't round or approximate
4. If data is unavailable, say so clearly - never guess values
5. Keep responses concise but complete
6. Use bullet points for lists of requirements
7. End with a brief note on assessment pathway (CDC vs DA) when relevant

RESPONSE FORMAT:
- Start with a direct answer to the question
- Follow with supporting details and provision references
- Use [provision_id:N] format for citations that can be linked to sources`;
}

/**
 * POST /api/ai/chat
 *
 * Streaming chat endpoint for compliance questions.
 * Routes to Gemini (fast, cheap) or GPT-4o (complex synthesis) based on query.
 */
export async function POST(request: NextRequest) {
  try {
    const body: ChatRequest = await request.json();
    const { messages, context, precomputedData } = body;

    if (!messages || messages.length === 0) {
      return new Response(JSON.stringify({ error: 'No messages provided' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    if (!context || !context.address || !context.zone) {
      return new Response(JSON.stringify({ error: 'Property context required' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Get the latest user message for complexity classification
    const latestUserMessage = messages.filter(m => m.role === 'user').pop();
    if (!latestUserMessage) {
      return new Response(JSON.stringify({ error: 'No user message found' }), {
        status: 400,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    const complexity = classifyQueryComplexity(latestUserMessage.content, context);
    console.log(`[AI Chat] Query complexity: ${complexity}`);
    console.log(`[AI Chat] Query: "${latestUserMessage.content.substring(0, 100)}..."`);

    // Check for precomputed answer for simple queries
    if (complexity === 'simple' && precomputedData) {
      const precomputedAnswer = tryPrecomputedAnswer(latestUserMessage.content, precomputedData);
      if (precomputedAnswer) {
        console.log('[AI Chat] Using precomputed answer');
        // Return non-streaming precomputed response
        return new Response(JSON.stringify({
          role: 'assistant',
          content: precomputedAnswer,
          model: 'precomputed',
          complexity,
        }), {
          headers: { 'Content-Type': 'application/json' },
        });
      }
    }

    // Build system prompt with context
    const systemPrompt = buildSystemPrompt(context);

    // Select model based on complexity
    const model = complexity === 'complex'
      ? openai('gpt-4o')
      : google('gemini-2.0-flash-exp');

    const modelName = complexity === 'complex' ? 'gpt-4o' : 'gemini-2.0-flash';
    console.log(`[AI Chat] Using model: ${modelName}`);

    // Convert messages for the AI SDK
    const coreMessages: CoreMessage[] = convertToCoreMessages(messages);

    // Stream the response
    const result = await streamText({
      model,
      system: systemPrompt,
      messages: coreMessages,
      temperature: 0.3, // Lower for more consistent regulatory responses
      maxTokens: 1024,
    });

    // Return streaming response
    return result.toDataStreamResponse({
      headers: {
        'X-Model-Used': modelName,
        'X-Query-Complexity': complexity,
      },
    });

  } catch (error) {
    console.error('[AI Chat] Error:', error);

    const message = error instanceof Error ? error.message : 'Unknown error';

    return new Response(JSON.stringify({
      error: 'AI chat failed',
      details: message,
    }), {
      status: 500,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}

/**
 * Try to answer simple questions from precomputed data
 */
function tryPrecomputedAnswer(
  query: string,
  data: NonNullable<ChatRequest['precomputedData']>
): string | null {
  const lowerQuery = query.toLowerCase();

  // Height questions
  if (/height/i.test(lowerQuery) && data.height) {
    return `The maximum building height for this property is **${data.height.value}**.

Source: ${data.height.source}${data.height.provisionId ? ` [provision_id:${data.height.provisionId}]` : ''}`;
  }

  // FSR questions
  if (/fsr|floor space ratio/i.test(lowerQuery) && data.fsr) {
    return `The maximum Floor Space Ratio (FSR) for this property is **${data.fsr.value}**.

Source: ${data.fsr.source}${data.fsr.provisionId ? ` [provision_id:${data.fsr.provisionId}]` : ''}`;
  }

  // Setback questions
  if (/setback/i.test(lowerQuery) && data.setbacks) {
    return `The setback requirements for this property are:

${data.setbacks.value}

Source: ${data.setbacks.source}${data.setbacks.provisionId ? ` [provision_id:${data.setbacks.provisionId}]` : ''}`;
  }

  // Parking questions
  if (/parking/i.test(lowerQuery) && data.parking) {
    return `The parking requirements for this property are:

${data.parking.value}

Source: ${data.parking.source}${data.parking.provisionId ? ` [provision_id:${data.parking.provisionId}]` : ''}`;
  }

  // No precomputed match
  return null;
}
