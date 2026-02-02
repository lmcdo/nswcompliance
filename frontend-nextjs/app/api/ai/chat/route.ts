/**
 * AI Chat Assistant API Endpoint
 *
 * POST /api/ai/chat
 *
 * Receives user questions, classifies them using Gemini,
 * routes to appropriate data endpoints, and returns formatted responses.
 *
 * No content generation - all responses come from precomputed data.
 */

import { NextRequest, NextResponse } from 'next/server';
import { classifyQuestion, PropertyContext, ClassificationResult } from '@/lib/ai/classifier';
import { routeQuestion } from '@/lib/ai/router';
import { formatResponse, FormattedResponse } from '@/lib/ai/formatter';
import { AIChatSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import {
  aiRateLimiter,
  getClientIdentifier,
  checkRateLimit,
  createRateLimitHeaders,
} from '@/lib/rate-limit';

// Request body structure
interface ChatRequest {
  message: string;
  propertyContext?: PropertyContext;
  conversationId?: string;
}

/**
 * Build a clarification response when confidence is too low to proceed.
 * Suggests what the user might be asking about based on the best-guess classification.
 */
function buildClarificationResponse(
  originalQuestion: string,
  classification: ClassificationResult,
  propertyContext?: PropertyContext
): FormattedResponse {
  const hasProperty = !!propertyContext?.address;

  // Build suggestions based on the uncertain classification
  const suggestions: string[] = [];

  switch (classification.category) {
    case 'factual_lookup':
      suggestions.push('What is the maximum building height?');
      suggestions.push('What are the setback requirements?');
      suggestions.push('What is the FSR (floor space ratio)?');
      break;
    case 'permissibility':
      suggestions.push('Is dual occupancy permitted here?');
      suggestions.push('Can I build a granny flat?');
      suggestions.push('Are townhouses allowed in this zone?');
      break;
    case 'definition':
      suggestions.push('What is a habitable room?');
      suggestions.push('What does FSR mean?');
      suggestions.push('Define building height');
      break;
    case 'procedural':
      suggestions.push('Should I use CDC or DA?');
      suggestions.push('What documents do I need for a DA?');
      suggestions.push('How long does approval take?');
      break;
    case 'housing_sepp':
      suggestions.push('Am I eligible for low-rise housing under SEPP?');
      suggestions.push('What are the lot size requirements for a manor house?');
      break;
    case 'constraint_check':
      suggestions.push('Is this property heritage listed?');
      suggestions.push('Is there flood risk on this property?');
      break;
    default:
      // Generic suggestions based on whether property is selected
      if (hasProperty) {
        suggestions.push('What are the development controls for this property?');
        suggestions.push('What can I build here?');
        suggestions.push('Is this property heritage listed?');
      } else {
        suggestions.push('What is a habitable room?');
        suggestions.push('Should I use CDC or DA?');
        suggestions.push('What does FSR mean?');
      }
  }

  const propertyNote = hasProperty
    ? ''
    : '\n\nTip: Select a property above for specific development control questions.';

  return {
    message: `**I'm not sure what you're asking**\n\nI couldn't confidently interpret your question. Could you try rephrasing it, or select one of the suggestions below?${propertyNote}`,
    suggestedQuestions: suggestions.slice(0, 4),
    citations: [],
    category: classification.category,
    isRefusal: false,
  };
}

// Response structure
interface ChatResponse {
  success: boolean;
  response?: FormattedResponse;
  classification?: {
    category: string;
    confidence: number;
  };
  error?: string;
  processingTimeMs: number;
}

export async function POST(request: NextRequest): Promise<NextResponse<ChatResponse>> {
  const startTime = Date.now();

  try {
    // AI-specific rate limit check (5 requests per minute per IP)
    // More strict than global rate limit to protect LLM API costs
    const clientIP = getClientIdentifier(request);
    const rateLimitResult = await checkRateLimit(clientIP, aiRateLimiter, 5, 60000);

    if (!rateLimitResult.success) {
      const headers = createRateLimitHeaders(rateLimitResult);

      return NextResponse.json(
        {
          success: false,
          error: 'Rate limit exceeded. Please wait a minute before trying again.',
          processingTimeMs: Date.now() - startTime,
        },
        {
          status: 429,
          headers,
        }
      );
    }

    const body: ChatRequest = await request.json();

    // Validate input with Zod schema
    const validation = validateRequest(AIChatSchema, body);

    if (!validation.success) {
      const errorDetails = formatValidationErrors(validation.details);
      console.error('[AI Chat] Validation failed:', errorDetails);
      return NextResponse.json(
        {
          success: false,
          error: `Invalid request data: ${errorDetails.join(', ')}`,
          details: errorDetails,
          processingTimeMs: Date.now() - startTime,
        },
        { status: 400 }
      );
    }

    const { message, propertyContext } = validation.data;

    console.log(`[AI Chat] Received: "${message.substring(0, 100)}..."`);
    console.log(`[AI Chat] Property context: ${propertyContext?.address || 'None'}`);

    // Step 1: Classify the question
    const classification = await classifyQuestion(message, propertyContext);

    console.log(`[AI Chat] Classification: ${classification.category} (${(classification.confidence * 100).toFixed(0)}%)`);
    console.log(`[AI Chat] Reasoning: ${classification.reasoning}`);

    // Step 1.5: Check for low confidence - ask for clarification instead of guessing
    const CONFIDENCE_THRESHOLD = 0.5;
    if (classification.confidence < CONFIDENCE_THRESHOLD) {
      console.log(`[AI Chat] Low confidence (${classification.confidence}) - requesting clarification`);

      const clarificationResponse = buildClarificationResponse(message, classification, propertyContext);

      return NextResponse.json({
        success: true,
        response: clarificationResponse,
        classification: {
          category: 'clarification_needed',
          confidence: classification.confidence,
        },
        processingTimeMs: Date.now() - startTime,
      });
    }

    // Step 2: Route to appropriate data endpoint
    const dataResponse = await routeQuestion(classification, propertyContext);

    // Step 3: Format the response
    const formattedResponse = formatResponse(dataResponse);

    const processingTime = Date.now() - startTime;
    console.log(`[AI Chat] Completed in ${processingTime}ms`);

    return NextResponse.json({
      success: true,
      response: formattedResponse,
      classification: {
        category: classification.category,
        confidence: classification.confidence,
      },
      processingTimeMs: processingTime,
    });

  } catch (error) {
    const processingTime = Date.now() - startTime;
    console.error('[AI Chat] Error:', error);

    // Check for specific error types
    if (error instanceof SyntaxError) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request format',
          processingTimeMs: processingTime,
        },
        { status: 400 }
      );
    }

    return NextResponse.json(
      {
        success: false,
        error: 'Something went wrong. Please try again.',
        processingTimeMs: processingTime,
      },
      { status: 500 }
    );
  }
}

// Health check / info endpoint
export async function GET(): Promise<NextResponse> {
  return NextResponse.json({
    service: 'AI Planning Assistant',
    version: '1.0.0',
    status: 'healthy',
    capabilities: [
      'definition - Look up planning term definitions',
      'procedural - CDC vs DA guidance, checklists',
      'factual_lookup - Height, FSR, setback requirements',
      'permissibility - Check if development type is permitted',
      'housing_sepp - SEPP Housing 2021 eligibility',
      'constraint_check - Property constraints (heritage, flood, etc.)',
      'synthesis - Combined property overview',
    ],
    limitations: [
      'Cannot provide professional advice',
      'Cannot predict application outcomes',
      'Cannot interpret regulations',
      'Requires property selection for specific questions',
    ],
  });
}
