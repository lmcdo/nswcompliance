/**
 * Consolidated Assessment API - Backend for Frontend (BFF) Pattern
 *
 * Single endpoint that returns ALL assessment data for a property.
 * Eliminates multiple simultaneous client requests that overwhelm the database.
 *
 * POST /api/assessment/full
 *
 * Request body:
 * - address: string (required)
 * - coordinates?: { lat: number, lng: number }
 * - developmentType?: string (default: 'dwelling_house')
 *
 * Response:
 * - property: zone, LGA, heritage, constraints
 * - capacity: height, FSR, setbacks
 * - sepp: structured requirements
 * - dcp: provisions grouped by TOC
 * - timing: how long each fetch took (for debugging)
 */

import { NextRequest, NextResponse } from 'next/server';
import { FullAssessmentSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';
import { searchRateLimiter, getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';
import { captureServerException } from '@/lib/posthog-server';

interface AssessmentRequest {
  address: string;
  coordinates?: { lat: number; lng: number };
  developmentType?: string;
}

interface TimingInfo {
  property: number;
  capacity: number;
  sepp: number;
  dcp: number;
  total: number;
}

interface FetchResult {
  data: any;
  error: string | null;
  timing: number;
}

export async function POST(request: NextRequest) {
  const totalStart = Date.now();
  const timing: Partial<TimingInfo> = {};

  try {
    const clientIP = getClientIdentifier(request);
    const rateLimitResult = await checkRateLimit(clientIP, searchRateLimiter, 20, 60000);
    if (!rateLimitResult.success) {
      return NextResponse.json(
        { error: 'Rate limit exceeded. Please try again in a minute.' },
        { status: 429, headers: createRateLimitHeaders(rateLimitResult) }
      );
    }

    const body: AssessmentRequest = await request.json();

    // Validate input with Zod schema
    const validation = validateRequest(FullAssessmentSchema, body);

    if (!validation.success) {
      return NextResponse.json(
        {
          success: false,
          error: 'Invalid request data',
          details: formatValidationErrors(validation.details),
          timing: { ...timing, total: Date.now() - totalStart }
        },
        { status: 400 }
      );
    }

    const { address, developmentType = 'dwelling_house' } = validation.data;
    const coordinates = (body as any).coordinates;

    const baseUrl = getBaseUrl(request);
    console.log(`[Assessment/Full] Starting for: ${address}`);

    // =========================================================================
    // PHASE 1: Fetch property basics (required for subsequent queries)
    // =========================================================================
    const propertyStart = Date.now();
    let property: any;

    try {
      const propertyResponse = await fetch(
        `${baseUrl}/api/property?address=${encodeURIComponent(address)}`,
        { headers: { 'Content-Type': 'application/json' } }
      );
      const propertyData = await propertyResponse.json();
      timing.property = Date.now() - propertyStart;

      if (!propertyData.success || !propertyData.data) {
        return NextResponse.json({
          success: false,
          error: propertyData.error || 'Failed to fetch property data',
          timing: { ...timing, total: Date.now() - totalStart }
        }, { status: 404 });
      }

      property = propertyData.data;
    } catch (error) {
      timing.property = Date.now() - propertyStart;
      return NextResponse.json({
        success: false,
        error: 'Failed to fetch property data',
        timing: { ...timing, total: Date.now() - totalStart }
      }, { status: 500 });
    }

    const zone = property.constraints?.zone || '';
    const lga = property.constraints?.lga || '';
    const formerCouncil = property.constraints?.formerCouncil || '';
    const heritage = property.heritage?.isHeritage || false;
    const precinctId = property.constraints?.precinctId;
    const lotArea = property.lotDimensions?.area ||
      (property.propertyArea ? parseFloat(property.propertyArea.replace(/[^\d.]/g, '')) : null);

    console.log(`[Assessment/Full] Property loaded in ${timing.property}ms`);
    console.log(`[Assessment/Full] Zone: ${zone}, LGA: ${lga}, Council: ${formerCouncil}`);

    // =========================================================================
    // PHASE 2: Parallel fetch of all detailed data
    // =========================================================================
    const parallelStart = Date.now();

    // Build request params
    const capacityBody = {
      address,
      coordinates,
      developmentType,
      lotArea,
      zone,
      lga,
      formerCouncil
    };

    const dcpParams = new URLSearchParams();
    dcpParams.set('groupBy', 'toc');
    if (formerCouncil) dcpParams.set('former_council', formerCouncil);
    if (zone) dcpParams.set('zone', zone);
    dcpParams.set('heritage', String(heritage));
    if (precinctId) dcpParams.set('precinct_id', precinctId);

    const seppBody = {
      zoneCode: zone,
      lotSize: lotArea,
      lotWidth: property.lotDimensions?.frontage,
      developmentType,
      lga
    };

    // Execute all fetches in parallel with individual error handling
    const [capacityResult, dcpResult, seppResult] = await Promise.all([
      fetchWithErrorHandling(
        `${baseUrl}/api/capacity/calculate`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(capacityBody)
        },
        'capacity'
      ),

      fetchWithErrorHandling(
        `${baseUrl}/api/provisions/for-property?${dcpParams.toString()}`,
        { headers: { 'Content-Type': 'application/json' } },
        'dcp'
      ),

      fetchWithErrorHandling(
        `${baseUrl}/api/sepp/structured-requirements`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(seppBody)
        },
        'sepp'
      )
    ]);

    timing.capacity = capacityResult.timing;
    timing.dcp = dcpResult.timing;
    timing.sepp = seppResult.timing;
    timing.total = Date.now() - totalStart;

    console.log(`[Assessment/Full] Parallel fetches completed in ${Date.now() - parallelStart}ms`);
    console.log(`[Assessment/Full] Capacity: ${timing.capacity}ms, DCP: ${timing.dcp}ms, SEPP: ${timing.sepp}ms`);
    console.log(`[Assessment/Full] Total time: ${timing.total}ms`);

    // =========================================================================
    // Return consolidated response
    // =========================================================================
    const hasErrors = capacityResult.error || dcpResult.error || seppResult.error;

    return NextResponse.json({
      success: true,
      data: {
        property,
        capacity: capacityResult.data,
        sepp: seppResult.data,
        dcp: dcpResult.data,
      },
      // Only include errors object if there are errors
      ...(hasErrors && {
        errors: {
          capacity: capacityResult.error,
          sepp: seppResult.error,
          dcp: dcpResult.error,
        }
      }),
      timing,
    });

  } catch (error) {
    console.error('[Assessment/Full] Error:', error);
    captureServerException(error, { endpoint: '/api/assessment/full' });
    return NextResponse.json({
      success: false,
      error: 'Failed to load assessment data',
      details: error instanceof Error ? error.message : 'Unknown error',
      timing: { ...timing, total: Date.now() - totalStart }
    }, { status: 500 });
  }
}

/**
 * Get the base URL for internal API calls
 */
function getBaseUrl(request: NextRequest): string {
  const host = request.headers.get('host') || 'localhost:3000';
  const protocol = process.env.NODE_ENV === 'production' ? 'https' : 'http';
  return `${protocol}://${host}`;
}

/**
 * Fetch with error handling and timing - never throws
 */
async function fetchWithErrorHandling(
  url: string,
  options: RequestInit,
  name: string
): Promise<FetchResult> {
  const start = Date.now();

  try {
    const response = await fetch(url, options);
    const data = await response.json();
    const timing = Date.now() - start;

    if (!response.ok) {
      console.warn(`[Assessment/Full] ${name} returned ${response.status}`);
      return {
        data: null,
        error: data.error || `${name} failed with status ${response.status}`,
        timing
      };
    }

    return { data, error: null, timing };

  } catch (error) {
    const timing = Date.now() - start;
    console.error(`[Assessment/Full] ${name} fetch error:`, error);
    return {
      data: null,
      error: `Failed to fetch ${name}`,
      timing
    };
  }
}
