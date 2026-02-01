/**
 * Security Layer - Anti-Copycat Protection
 *
 * Centralized exports for all security utilities
 */

// Route Obfuscation
export { SECURE_ROUTES, verifySecureRoute, validateRouteConfig } from './route-obfuscation';

// Response Encoding
export {
  encodeResponse,
  decodeResponse,
  isEncodedResponse,
  type StandardResponse,
  type EncodedResponse,
} from './response-encoder';

// Enhanced Rate Limiting
export {
  isBotUserAgent,
  hasFingerprint,
  getRateLimit,
  recordViolation,
  isBlocked,
  clearViolations,
} from './enhanced-rate-limit';

// Error Sanitization
export {
  sanitizeError,
  formatErrorResponse,
  logErrorInternal,
} from './error-sanitizer';
