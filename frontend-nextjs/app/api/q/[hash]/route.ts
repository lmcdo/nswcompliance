/**
 * Secure AI Chat Endpoint (Obfuscated)
 *
 * This is the REAL AI chat endpoint, accessed via hash route.
 * The hash is set via environment variable and rotated periodically.
 *
 * Route: /api/q/[hash]
 * Hash: NEXT_PUBLIC_ROUTE_HASH_1
 *
 * Security layers:
 * - Route obfuscation (hash-based URL)
 * - Response encoding (base64 obfuscation)
 * - Enhanced rate limiting (bot detection)
 * - Error sanitization (no schema leaks)
 */

import { NextRequest, NextResponse } from 'next/server';
import { classifyQuestion, PropertyContext } from '@/lib/ai/classifier';
import { routeQuestion } from '@/lib/ai/router';
import { formatResponse, FormattedResponse } from '@/lib/ai/formatter';
import { AIChatSchema, validateRequest } from '@/lib/schemas';
import { getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';
import { encodeResponse } from '@/lib/security/response-encoder';
import { getRateLimit, isBlocked, recordViolation } from '@/lib/security/enhanced-rate-limit';
import { formatErrorResponse, logErrorInternal } from '@/lib/security/error-sanitizer';

interface ChatRequest {
  message: string;
  propertyContext?: PropertyContext;
  conversationId?: string;
}

/**
 * Build clarification response for low-confidence classification
 */
function buildClarificationResponse(
  classification: any,
  propertyContext?: PropertyContext
): FormattedResponse {
  const hasProperty = !!propertyContext?.address;
  const suggestions: string[] = [];

  switch (classification.category) {
    case 'factual_lookup':
      suggestions.push('What is the maximum building height?', 'What are the setback requirements?');
      break;
    case 'permissibility':
      suggestions.push('Is dual occupancy permitted here?', 'Can I build a granny flat?');
      break;
    default:
      if (hasProperty) {
        suggestions.push('What are the development controls for this property?');
      } else {
        suggestions.push('What is a habitable room?', 'Should I use CDC or DA?');
      }
  }

  return {
    message: `I'm not sure what you're asking. Could you try rephrasing it?${hasProperty ? '' : '\n\nTip: Select a property above for specific development control questions.'}`,
    suggestedQuestions: suggestions.slice(0, 4),
    citations: [],
    category: 'synthesis' as import('@/lib/ai/classifier').QuestionCategory,
    isRefusal: false,
  };
}

/**
 * Verify request hash matches expected environment variable
 */
function verifyHash(requestHash: string): boolean {
  const expectedHash = process.env.NEXT_PUBLIC_ROUTE_HASH_1;

  // Development fallback
  if (!expectedHash && process.env.NODE_ENV === 'development') {
    return requestHash === 'dev-fallback-1';
  }

  return requestHash === expectedHash;
}

export async function POST(
  request: NextRequest,
  { params }: { params: { hash: string } }
): Promise<NextResponse> {
  const startTime = Date.now();

  try {
    // Security Layer 1: Verify route hash
    if (!verifyHash(params.hash)) {
      return NextResponse.json({ error: 'Not found' }, { status: 404 });
    }

    // Security Layer 2: Check if IP is blocked
    const clientIP = getClientIdentifier(request);
    if (isBlocked(clientIP)) {
      return NextResponse.json(
        { error: 'Access denied. Too many violations.' },
        { status: 403 }
      );
    }

    // Security Layer 3: Enhanced rate limiting (bot detection)
    const { limit, window } = getRateLimit(request);
    const rateLimitResult = await checkRateLimit(clientIP, null, limit, window);

    if (!rateLimitResult.success) {
      recordViolation(clientIP);
      const headers = createRateLimitHeaders(rateLimitResult);

      return NextResponse.json(
        { error: 'Rate limit exceeded. Please wait before trying again.' },
        { status: 429, headers }
      );
    }

    // Parse and validate request
    const body: ChatRequest = await request.json();
    const validation = validateRequest(AIChatSchema, body);

    if (!validation.success) {
      return NextResponse.json(
        formatErrorResponse(new Error('Invalid request data')),
        { status: 400 }
      );
    }

    const { message, propertyContext } = validation.data;

    // Step 1: Classify question
    const classification = await classifyQuestion(message, propertyContext);

    // Step 2: Check confidence threshold
    const CONFIDENCE_THRESHOLD = 0.5;
    if (classification.confidence < CONFIDENCE_THRESHOLD) {
      const clarificationResponse = buildClarificationResponse(classification, propertyContext);

      // Encode response for obfuscation
      const encoded = encodeResponse({
        answer: clarificationResponse.message,
        citations: clarificationResponse.citations.map(c => c.source),
        confidence: classification.confidence,
        suggestedQuestions: clarificationResponse.suggestedQuestions,
        category: 'clarification_needed',
      });

      return NextResponse.json({
        success: true,
        response: encoded,
        processingTimeMs: Date.now() - startTime,
      });
    }

    // Step 3: Route to data endpoint
    const dataResponse = await routeQuestion(classification, propertyContext);

    // Step 4: Format response
    const formattedResponse = formatResponse(dataResponse);

    // Security Layer 4: Encode response (obfuscation)
    const encoded = encodeResponse({
      answer: formattedResponse.message,
      citations: formattedResponse.citations.map(c => c.source),
      confidence: classification.confidence,
      suggestedQuestions: formattedResponse.suggestedQuestions,
      category: classification.category,
    });

    return NextResponse.json({
      success: true,
      response: encoded,
      processingTimeMs: Date.now() - startTime,
    });

  } catch (error) {
    // Security Layer 5: Sanitize errors (prevent schema leakage)
    logErrorInternal(error, { route: 'secure-ai-chat', hash: params.hash });

    return NextResponse.json(
      {
        success: false,
        ...formatErrorResponse(error),
        processingTimeMs: Date.now() - startTime,
      },
      { status: 500 }
    );
  }
}

// Health check
export async function GET(
  request: NextRequest,
  { params }: { params: { hash: string } }
): Promise<NextResponse> {
  if (!verifyHash(params.hash)) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  return NextResponse.json({
    service: 'AI Planning Assistant',
    version: '2.0.0',
    status: 'healthy',
  });
}
