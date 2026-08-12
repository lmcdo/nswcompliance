/**
 * Centralized Zod Validation Schemas
 *
 * Phase 1 Security: Input validation for all API routes
 *
 * Usage:
 *   import { AddressSchema, validateRequest } from '@/lib/schemas';
 *   const validation = validateRequest(AddressSchema, body);
 *   if (!validation.success) return badRequest(validation.error);
 */

import { z } from 'zod';

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Validates request data against a Zod schema
 * Returns typed data on success, error details on failure
 */
export function validateRequest<T>(
  schema: z.ZodSchema<T>,
  data: unknown
): { success: true; data: T } | { success: false; error: string; details: z.ZodError } {
  const result = schema.safeParse(data);

  if (!result.success) {
    return {
      success: false,
      error: 'Invalid request data',
      details: result.error,
    };
  }

  return { success: true, data: result.data };
}

// ============================================================================
// SHARED PRIMITIVES
// ============================================================================

// Australian address validation
export const AddressStringSchema = z
  .string()
  .min(5, 'Address must be at least 5 characters')
  .max(200, 'Address must be less than 200 characters')
  .regex(/^[a-zA-Z0-9\s,.\-'/]+$/, 'Address contains invalid characters');

// NSW zone code (e.g., R1, B4, RE1)
export const ZoneCodeSchema = z
  .string()
  .min(1, 'Zone code required')
  .max(10, 'Zone code too long')
  .regex(/^[A-Z0-9]+$/, 'Zone must be uppercase alphanumeric (e.g., R1, B4, RE1)');

// Development type enum (from your database)
export const DevelopmentTypeSchema = z.enum([
  'dwelling_house',
  'dual_occupancy',
  'multi_dwelling_housing',
  'residential_flat_building',
  'manor_house',
  'terrace_house',
  'semi_detached_dwelling',
  'attached_dwelling',
  'secondary_dwelling',
  'shop_top_housing',
  'boarding_house',
  'group_home',
  'hostels',
  'seniors_housing',
  'shop',
  'commercial_premises',
  'office_premises',
  'retail_premises',
  'warehouse',
  'light_industry',
  'general_industry',
  'other',
]);

// Coordinates (latitude/longitude)
export const CoordinatesSchema = z.object({
  lat: z.number().min(-90).max(90),
  lng: z.number().min(-180).max(180),
});

// LGA (Local Government Area)
export const LGASchema = z
  .string()
  .min(2)
  .max(100)
  .regex(/^[a-zA-Z\s\-']+$/, 'LGA contains invalid characters');

// ============================================================================
// API ROUTE SCHEMAS
// ============================================================================

/**
 * AI Chat Schema - /api/ai/chat
 * High-risk: Calls external LLM API (cost impact)
 * PERMISSIVE: Accepts any reasonable property context structure
 */
export const AIChatSchema = z.object({
  message: z
    .string()
    .min(3, 'Message must be at least 3 characters')
    .max(500, 'Message must be less than 500 characters'),
  propertyContext: z
    .object({
      address: z.string().optional(),
      zone: z.string().optional(),
      lga: z.string().optional(),
      formerCouncil: z.string().optional(),
      lotSize: z.number().positive().optional(),
      lotWidth: z.number().positive().optional(),
      precinctId: z.string().optional(),
      coordinates: CoordinatesSchema.optional(),
      constraints: z.record(z.string(), z.any()).optional(), // Accept any constraints structure
    })
    .passthrough() // Allow additional fields
    .optional(),
  conversationId: z.string().optional(), // Allow any string, not just UUID
});

/**
 * Property Search Schema - /api/property
 */
export const PropertySearchSchema = z.object({
  address: AddressStringSchema,
  lga: LGASchema.optional(),
  includeConstraints: z.boolean().optional(),
});

/**
 * Compliance Check Schema - /api/compliance/*, /api/permissibility/*
 */
export const ComplianceCheckSchema = z.object({
  address: AddressStringSchema,
  zone: ZoneCodeSchema,
  developmentType: DevelopmentTypeSchema,
  lga: LGASchema.optional(),
  coordinates: CoordinatesSchema.optional(),
  lotSize: z.number().positive().optional(),
  frontage: z.number().positive().optional(),
});

/**
 * Enhanced Compliance Schema - /api/compliance/enhanced
 */
export const ComplianceEnhancedSchema = z.object({
  address: AddressStringSchema,
  zone: ZoneCodeSchema,
  developmentType: DevelopmentTypeSchema,
  lga: LGASchema,
  coordinates: CoordinatesSchema.optional(),
  includeHeritage: z.boolean().optional(),
  includeFlood: z.boolean().optional(),
  includePrecinct: z.boolean().optional(),
});

/**
 * Full Assessment Schema - /api/assessment/full
 */
export const FullAssessmentSchema = z.object({
  address: AddressStringSchema,
  propertyId: z.string().optional(),
  developmentType: DevelopmentTypeSchema.optional(),
  includeAll: z.boolean().optional(),
});

/**
 * Capacity Calculation Schema - /api/capacity/calculate
 */
export const CapacityCalculationSchema = z.object({
  lotSize: z.number().positive('Lot size must be positive'),
  frontage: z.number().positive('Frontage must be positive'),
  zone: ZoneCodeSchema,
  fsr: z.number().min(0).max(10).optional(),
  heightLimit: z.number().positive().optional(),
  developmentType: DevelopmentTypeSchema.optional(),
});

/**
 * Provision Search Schema - /api/provisions
 */
export const ProvisionSearchSchema = z.object({
  query: z
    .string()
    .min(2, 'Search query must be at least 2 characters')
    .max(200, 'Search query too long'),
  documentType: z.enum(['LEP', 'DCP', 'SEPP', 'all']).optional(),
  lga: LGASchema.optional(),
  zone: ZoneCodeSchema.optional(),
  limit: z.number().int().min(1).max(100).optional().default(20),
  offset: z.number().int().min(0).optional().default(0),
});

/**
 * Provision Lookup Schema - /api/precinct/provisions, /api/provisions/by-id
 */
export const ProvisionLookupSchema = z.object({
  provisionId: z.string().uuid().optional(),
  precinctId: z.string().optional(),
  zone: ZoneCodeSchema.optional(),
  documentId: z.string().optional(),
  limit: z.number().int().min(1).max(100).optional().default(50),
});

/**
 * Housing SEPP Eligibility Schema - /api/housing-sepp/eligibility
 * Checks all development types for a property, returns eligibility for each
 */
export const HousingSEPPSchema = z.object({
  zoneCode: ZoneCodeSchema,
  lotSize: z.number().positive('Lot size must be positive'),
  lotWidth: z.number().positive('Lot width must be positive'),
  stationDistance: z.number().positive('Station distance must be positive').optional(),
  isLMRArea: z.boolean().optional(),
  address: AddressStringSchema.optional(),
  lga: LGASchema.optional(),
  coordinates: CoordinatesSchema.optional(),
});

/**
 * Live Compliance Check Schema - /api/compliance/live-check
 */
export const LiveCheckSchema = z.object({
  address: AddressStringSchema,
  developmentType: DevelopmentTypeSchema,
  includeReasons: z.boolean().optional(),
});

/**
 * Setback Request Schema - /api/setbacks/*
 */
export const SetbackRequestSchema = z.object({
  zone: ZoneCodeSchema,
  developmentType: DevelopmentTypeSchema,
  propertyLocation: z
    .object({
      lga: LGASchema.optional(),
      suburb: z.string().max(100).optional(),
    })
    .optional(),
});

/**
 * Document Lookup Schema - /api/documents/*, /api/versions/*
 */
export const DocumentLookupSchema = z.object({
  documentId: z.string().min(1).max(100),
  version: z.string().max(50).optional(),
  includeProvisions: z.boolean().optional(),
});

/**
 * TOD (Transport-Oriented Development) Schema - /api/transport/*
 */
export const TODSchema = z.object({
  address: AddressStringSchema,
  coordinates: CoordinatesSchema.optional(),
  includeRates: z.boolean().optional(),
  radius: z.number().int().min(100).max(5000).optional().default(800),
});

/**
 * Report Generation Schema - /api/reports/*
 */
export const ReportSchema = z.object({
  address: AddressStringSchema,
  zone: ZoneCodeSchema,
  developmentType: DevelopmentTypeSchema,
  format: z.enum(['pdf', 'json', 'html']).optional().default('json'),
  includeImages: z.boolean().optional(),
});

/**
 * Feedback Submit Schema - /api/feedback/submit
 */
export const FeedbackSubmitSchema = z.object({
  text: z
    .string()
    .min(10, 'Feedback must be at least 10 characters')
    .max(2000, 'Feedback must be less than 2000 characters'),
  email: z.string().email('Invalid email address').optional(),
  rating: z.number().int().min(1).max(5).optional(),
  category: z.enum(['bug', 'feature', 'usability', 'other']).optional(),
});

/**
 * Requirement Feedback Schema - /api/feedback/requirement
 */
export const RequirementFeedbackSchema = z.object({
  provisionId: z.string().uuid('Invalid provision ID'),
  feedback: z
    .string()
    .min(10, 'Feedback must be at least 10 characters')
    .max(1000, 'Feedback must be less than 1000 characters'),
  isCorrect: z.boolean(),
  suggestedCorrection: z.string().max(500).optional(),
});

/**
 * Autocomplete Schema - /api/tod/transport-autocomplete, etc.
 */
export const AutocompleteSchema = z.object({
  query: z
    .string()
    .min(2, 'Query must be at least 2 characters')
    .max(100, 'Query must be less than 100 characters'),
  limit: z.number().int().min(1).max(50).optional().default(10),
});

/**
 * ADG Separation Schema - /api/adg/separation-table
 */
export const ADGSeparationSchema = z.object({
  developmentType: DevelopmentTypeSchema,
  dwellingCount: z.number().int().positive('Dwelling count must be positive'),
  buildingHeight: z.number().positive().optional(),
});

/**
 * Pagination Schema (for list endpoints)
 */
export const PaginationSchema = z.object({
  page: z.number().int().min(1).optional().default(1),
  limit: z.number().int().min(1).max(100).optional().default(20),
  sortBy: z.string().max(50).optional(),
  sortOrder: z.enum(['asc', 'desc']).optional().default('asc'),
});

// ============================================================================
// QUERY PARAMETER SCHEMAS
// ============================================================================

/**
 * Validates URL search params (GET requests)
 */
export function validateQueryParams<T>(
  schema: z.ZodSchema<T>,
  searchParams: URLSearchParams
): { success: true; data: T } | { success: false; error: string; details: z.ZodError } {
  // Convert URLSearchParams to object
  const params: Record<string, string | string[]> = {};

  searchParams.forEach((value, key) => {
    if (params[key]) {
      // Multiple values for same key -> array
      params[key] = Array.isArray(params[key])
        ? [...(params[key] as string[]), value]
        : [params[key] as string, value];
    } else {
      params[key] = value;
    }
  });

  return validateRequest(schema, params);
}

// ============================================================================
// ERROR RESPONSE HELPERS
// ============================================================================

/**
 * Formats Zod validation errors into user-friendly messages
 */
export function formatValidationErrors(zodError: z.ZodError): string[] {
  return zodError.issues.map((err) => {
    const path = err.path.join('.');
    return path ? `${path}: ${err.message}` : err.message;
  });
}

/**
 * Creates a standardized 400 Bad Request response
 */
export function createValidationErrorResponse(zodError: z.ZodError) {
  return {
    success: false,
    error: 'Invalid request data',
    details: formatValidationErrors(zodError),
  };
}
