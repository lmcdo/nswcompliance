/**
 * Setback Calculation Module
 *
 * Provides validation, helpers, and utilities for setback calculations.
 *
 * Usage:
 *   import { validateSetbackRequest, transformSetback } from '@/lib/setbacks';
 */

export {
  SetbackRequestSchema,
  validateSetbackRequest,
  estimateLotArea,
  type SetbackRequest
} from './validator';

export {
  getAuthorityLevel,
  getAuthorityPrecedence,
  identifyDevelopmentType,
  isRealisticSetback,
  transformSetback,
  groupSetbacksByDevType,
  determineControllingAuthority,
  type AuthorityLevel,
  type DevelopmentType,
  type RawSetbackData,
  type TransformedSetback
} from './helpers';
