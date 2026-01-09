/**
 * Standardized API Response Helpers
 *
 * Provides consistent response format across all API routes:
 * - Success responses: { success: true, data: T, timestamp: string, meta?: object }
 * - Error responses: { success: false, error: string, code?: string, timestamp: string }
 *
 * Usage:
 *   import { successResponse, errorResponse, notFound, badRequest } from '@/lib/api-response';
 *
 *   // Success
 *   return successResponse(data);
 *   return successResponse(data, { processingTimeMs: 150 });
 *
 *   // Errors
 *   return badRequest('Missing required parameter');
 *   return notFound('Provision not found');
 *   return errorResponse('Database error', 500, 'DB_ERROR');
 */

import { NextResponse } from 'next/server';

// Response type definitions
export interface ApiError {
  success: false;
  error: string;
  code?: string;
  timestamp: string;
  details?: string;
}

export interface ApiSuccess<T> {
  success: true;
  data: T;
  timestamp: string;
  meta?: Record<string, unknown>;
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

/**
 * Create a success response with consistent format
 */
export function successResponse<T>(
  data: T,
  meta?: Record<string, unknown>,
  status: number = 200
): NextResponse<ApiSuccess<T>> {
  return NextResponse.json(
    {
      success: true as const,
      data,
      timestamp: new Date().toISOString(),
      ...(meta && { meta }),
    },
    { status }
  );
}

/**
 * Create an error response with consistent format
 */
export function errorResponse(
  message: string,
  status: number = 500,
  code?: string,
  details?: string
): NextResponse<ApiError> {
  return NextResponse.json(
    {
      success: false as const,
      error: message,
      ...(code && { code }),
      ...(details && { details }),
      timestamp: new Date().toISOString(),
    },
    { status }
  );
}

/**
 * 400 Bad Request - Invalid input or missing required parameters
 */
export function badRequest(message: string, details?: string): NextResponse<ApiError> {
  return errorResponse(message, 400, 'BAD_REQUEST', details);
}

/**
 * 401 Unauthorized - Authentication required
 */
export function unauthorized(message: string = 'Authentication required'): NextResponse<ApiError> {
  return errorResponse(message, 401, 'UNAUTHORIZED');
}

/**
 * 403 Forbidden - Insufficient permissions
 */
export function forbidden(message: string = 'Insufficient permissions'): NextResponse<ApiError> {
  return errorResponse(message, 403, 'FORBIDDEN');
}

/**
 * 404 Not Found - Resource not found
 */
export function notFound(message: string, details?: string): NextResponse<ApiError> {
  return errorResponse(message, 404, 'NOT_FOUND', details);
}

/**
 * 409 Conflict - Resource conflict
 */
export function conflict(message: string): NextResponse<ApiError> {
  return errorResponse(message, 409, 'CONFLICT');
}

/**
 * 422 Unprocessable Entity - Validation error
 */
export function validationError(message: string, details?: string): NextResponse<ApiError> {
  return errorResponse(message, 422, 'VALIDATION_ERROR', details);
}

/**
 * 429 Too Many Requests - Rate limit exceeded
 */
export function rateLimitExceeded(message: string = 'Rate limit exceeded'): NextResponse<ApiError> {
  return errorResponse(message, 429, 'RATE_LIMIT_EXCEEDED');
}

/**
 * 500 Internal Server Error - Generic server error
 */
export function serverError(
  message: string = 'Internal server error',
  details?: string
): NextResponse<ApiError> {
  return errorResponse(message, 500, 'INTERNAL_ERROR', details);
}

/**
 * 503 Service Unavailable - Service temporarily unavailable
 */
export function serviceUnavailable(message: string = 'Service temporarily unavailable'): NextResponse<ApiError> {
  return errorResponse(message, 503, 'SERVICE_UNAVAILABLE');
}

/**
 * Wrap an async handler with error catching
 * Automatically converts thrown errors to proper API error responses
 */
export function withErrorHandling<T>(
  handler: () => Promise<NextResponse<ApiSuccess<T>>>
): Promise<NextResponse<ApiSuccess<T> | ApiError>> {
  return handler().catch((error: unknown) => {
    console.error('[API Error]', error);

    if (error instanceof Error) {
      // Check for specific error types
      if (error.message.includes('timeout')) {
        return errorResponse('Database operation timed out', 504, 'TIMEOUT');
      }
      return serverError('An unexpected error occurred', error.message);
    }

    return serverError('An unexpected error occurred');
  });
}
