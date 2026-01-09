/**
 * Setback Calculation Input Validation
 *
 * Zod schema and validation helpers for setback calculation requests.
 */

import { z } from 'zod';

/**
 * Request validation schema - PRP-K3 Zone-Specific (geometry optional)
 */
export const SetbackRequestSchema = z.object({
  property_id: z.number().int().positive(),
  lot_geometry: z.object({
    hasM: z.boolean().optional().default(false),
    hasZ: z.boolean().optional().default(false),
    rings: z.array(z.array(z.array(z.number()))), // NSW format: rings[0][0] = [x,y] coordinate pair
    spatialReference: z.object({
      wkid: z.number(),
      latestWkid: z.number().optional().nullable(),
      vcsWkid: z.number().optional().nullable(),
      latestVcsWkid: z.number().optional().nullable(),
      wkt: z.string().optional().nullable()
    }).optional()
  }).optional(), // Geometry is optional for PRP-K3 zone-specific calculations
  property_zone: z.string().min(1).max(10),
  lot_area: z.number().positive().optional() // Optional - can estimate from zone defaults
});

export type SetbackRequest = z.infer<typeof SetbackRequestSchema>;

/**
 * Validate setback calculation request
 */
export function validateSetbackRequest(body: unknown): {
  success: boolean;
  data?: SetbackRequest;
  error?: string;
} {
  const result = SetbackRequestSchema.safeParse(body);

  if (!result.success) {
    return {
      success: false,
      error: 'Invalid request data: ' + result.error.issues.map(i => i.message).join(', ')
    };
  }

  return {
    success: true,
    data: result.data
  };
}

/**
 * Estimate lot area based on zone defaults when not provided
 */
export function estimateLotArea(zone: string, providedArea?: number): number {
  if (providedArea) return providedArea;

  // Default lot sizes by zone type
  const zoneDefaults: Record<string, number> = {
    'R1': 600,  // General Residential
    'R2': 500,  // Low Density Residential
    'R3': 400,  // Medium Density Residential
    'R4': 350,  // High Density Residential
    'B1': 300,  // Neighbourhood Centre
    'B2': 400,  // Local Centre
    'B4': 500,  // Mixed Use
    'E1': 1000, // Local Centre (new)
    'E2': 800,  // Commercial Core (new)
  };

  // Try to match zone prefix
  const zonePrefix = zone.substring(0, 2).toUpperCase();
  return zoneDefaults[zonePrefix] || zoneDefaults[zone] || 450;
}
