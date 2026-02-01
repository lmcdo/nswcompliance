/**
 * Database Error Sanitization
 *
 * Prevents database schema leakage through error messages
 */

/**
 * Sanitize database errors to prevent schema leakage
 */
export function sanitizeError(error: unknown): { message: string; safe: boolean } {
  const errorMessage = error instanceof Error ? error.message : String(error);

  // Database schema leakage patterns
  const schemaLeakPatterns = [
    /column .* does not exist/i,
    /relation .* does not exist/i,
    /table .* does not exist/i,
    /syntax error at or near/i,
    /invalid input syntax/i,
    /could not connect to server/i,
    /connection refused/i,
    /permission denied/i,
  ];

  const hasSchemaLeak = schemaLeakPatterns.some(pattern => pattern.test(errorMessage));

  if (hasSchemaLeak) {
    // Log internally for debugging
    if (process.env.NODE_ENV === 'development') {
      console.error('[DB Error - Internal Only]:', errorMessage);
    }

    // Return generic message to client
    return {
      message: 'Query failed. Please try again.',
      safe: false
    };
  }

  // Safe to return (no schema information)
  return {
    message: errorMessage,
    safe: true
  };
}

/**
 * Sanitize and format error for API response
 */
export function formatErrorResponse(error: unknown): { error: string; code?: string } {
  const { message, safe } = sanitizeError(error);

  // Add generic error code for tracking (doesn't leak info)
  return {
    error: message,
    code: safe ? undefined : 'QUERY_ERROR'
  };
}

/**
 * Log error internally without exposing to client
 */
export function logErrorInternal(error: unknown, context?: Record<string, any>): void {
  const timestamp = new Date().toISOString();
  const errorMessage = error instanceof Error ? error.message : String(error);
  const stack = error instanceof Error ? error.stack : undefined;

  console.error('[Internal Error Log]', {
    timestamp,
    error: errorMessage,
    stack,
    context,
  });

  // In production, send to monitoring service
  // if (process.env.NODE_ENV === 'production') {
  //   // Sentry.captureException(error, { extra: context });
  // }
}
