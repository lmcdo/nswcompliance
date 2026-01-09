/**
 * Application Constants
 *
 * Centralized location for all magic numbers and configuration values.
 * Import from '@/lib/constants' instead of using inline values.
 */

// =============================================================================
// Database & Timeouts
// =============================================================================

/** Database query timeout in milliseconds (per CLAUDE.md safety requirements) */
export const DB_TIMEOUT_MS = 30000;

/** Maximum database connection pool size */
export const DB_POOL_MAX = 20;

/** Idle connection timeout in milliseconds */
export const DB_IDLE_TIMEOUT_MS = 30000;

/** Connection timeout in milliseconds */
export const DB_CONNECTION_TIMEOUT_MS = 10000;

// =============================================================================
// WebSocket
// =============================================================================

/** Initial WebSocket reconnection delay in milliseconds */
export const WS_RECONNECT_BASE_MS = 1000;

/** Maximum WebSocket reconnection delay in milliseconds */
export const WS_RECONNECT_MAX_MS = 30000;

/** Maximum number of WebSocket reconnection attempts */
export const WS_MAX_RECONNECT_ATTEMPTS = 10;

// =============================================================================
// Building & Development Defaults
// =============================================================================

/** Default buildable area percentage estimate (60%) */
export const BUILDABLE_PERCENTAGE_ESTIMATE = 0.6;

/** Default Floor Space Ratio when not specified */
export const DEFAULT_FSR = 0.9;

/** Default maximum building height in meters when not specified */
export const DEFAULT_HEIGHT_M = 6.0;

/** Minimum lot size for subdivision in square meters */
export const MIN_LOT_SIZE_SQM = 450;

/** Default front setback in meters */
export const DEFAULT_FRONT_SETBACK_M = 6.0;

/** Default side setback in meters */
export const DEFAULT_SIDE_SETBACK_M = 0.9;

/** Default rear setback in meters */
export const DEFAULT_REAR_SETBACK_M = 6.0;

// =============================================================================
// Geometry Constants
// =============================================================================

/** Meters per degree of latitude (approximate for NSW) */
export const METERS_PER_DEGREE_LAT = 111320;

/** Meters per degree of longitude at Sydney latitude (~34S) */
export const METERS_PER_DEGREE_LON = 92400;

/** Default map zoom level */
export const DEFAULT_MAP_ZOOM = 18;

/** Default map center latitude (Sydney CBD) */
export const DEFAULT_MAP_CENTER_LAT = -33.8688;

/** Default map center longitude (Sydney CBD) */
export const DEFAULT_MAP_CENTER_LON = 151.2093;

// =============================================================================
// API & Rate Limiting
// =============================================================================

/** Maximum API requests per minute per IP */
export const RATE_LIMIT_REQUESTS_PER_MIN = 100;

/** Rate limit window in milliseconds */
export const RATE_LIMIT_WINDOW_MS = 60000;

/** Maximum file upload size in bytes (10MB) */
export const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024;

/** Maximum search results to return */
export const MAX_SEARCH_RESULTS = 50;

/** Default search results limit */
export const DEFAULT_SEARCH_LIMIT = 20;

// =============================================================================
// Cache Durations
// =============================================================================

/** SEPP cache duration in milliseconds (1 hour) */
export const SEPP_CACHE_DURATION_MS = 60 * 60 * 1000;

/** Property data cache duration in milliseconds (5 minutes) */
export const PROPERTY_CACHE_DURATION_MS = 5 * 60 * 1000;

/** Section extraction cache duration in milliseconds (30 minutes) */
export const SECTION_CACHE_DURATION_MS = 30 * 60 * 1000;

// =============================================================================
// UI Constants
// =============================================================================

/** Maximum provision text length before truncation */
export const PROVISION_TEXT_TRUNCATE_LENGTH = 500;

/** Maximum excerpt length for search results */
export const EXCERPT_TRUNCATE_LENGTH = 200;

/** Number of provisions to show initially before "load more" */
export const INITIAL_PROVISIONS_DISPLAY = 10;

// =============================================================================
// Regulatory Hierarchy
// =============================================================================

/** Legal precedence values (lower = higher priority) */
export const LEGAL_PRECEDENCE = {
  SEPP: 1,
  LEP: 2,
  DCP: 3,
} as const;

/** Document type display names */
export const DOCUMENT_TYPE_NAMES = {
  SEPP: 'State Environmental Planning Policy',
  LEP: 'Local Environmental Plan',
  DCP: 'Development Control Plan',
} as const;

// =============================================================================
// NSW Planning API
// =============================================================================

/** NSW Planning Portal API base URL */
export const NSW_PLANNING_API_URL = 'https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi';

/** NSW Spatial Services CORS proxy (if needed) */
export const NSW_SPATIAL_PROXY_URL = 'https://api.apps1.nsw.gov.au/spatialservicesv2';
