/**
 * CDC Compliance Calculator Types
 *
 * Type definitions for the CDC compliance checking form and results.
 * Standards are read from the stored Housing Code rows (SEPP Exempt and Complying
 * Development Codes 2008, Part 3), never typed here.
 */

import type { CdcCheck, CheckKey, CdcDevelopmentType } from '@/lib/cdc/housing-code-checks';

export type { CdcDevelopmentType, CdcCheck, CheckKey };

/**
 * User input for CDC compliance calculation.
 * Every number starts blank (null): a blank is "not entered", never a default.
 */
export interface CdcComplianceInput {
  developmentType: CdcDevelopmentType;
  /** Lot area, selects the stored band for front and rear setbacks. */
  lotAreaM2: number | null;
  /** Lot width AT THE BUILDING LINE, selects the stored band for side setbacks. */
  lotWidthM: number | null;
  /** At least 2 dwelling houses on the same side of the primary road? null = not answered. */
  neighbourDwellings: 'yes' | 'no' | 'unknown' | null;
  /** Average front setback of the 2 nearest dwelling houses, when yes. */
  neighbourAverageFrontM: number | null;
  setbacks: {
    front: number | null;      // meters
    sideLeft: number | null;   // meters
    sideRight: number | null;  // meters
    rear: number | null;       // meters
  };
  hasUpperFloorHabitableRooms: boolean;
  siteCoveragePercent: number | null;
  landscapedAreaPercent: number | null;
  buildingHeightMeters: number | null;
  storeys: number | null;
  parkingSpaces: number | null;
}

/** Blank form: no typed standards and no pre-filled proposal figures. */
export const CDC_INPUT_DEFAULTS: CdcComplianceInput = {
  developmentType: 'new_dwelling',
  lotAreaM2: null,
  lotWidthM: null,
  neighbourDwellings: null,
  neighbourAverageFrontM: null,
  setbacks: { front: null, sideLeft: null, sideRight: null, rear: null },
  hasUpperFloorHabitableRooms: false,
  siteCoveragePercent: null,
  landscapedAreaPercent: null,
  buildingHeightMeters: null,
  storeys: null,
  parkingSpaces: null,
};

/**
 * One check result. Required figures and clauses come from the stored
 * Housing Code standards (lib/cdc); a check with no applicable stored
 * standard is status 'not_checked' with no number.
 */
export type FieldValidation = CdcCheck;

/** Overall form validation state, keyed by check. */
export type FormValidation = Record<CheckKey, CdcCheck>;

/**
 * Overall compliance check response (POST /api/cdc/compliance-check)
 */
export interface CdcComplianceResponse {
  success: boolean;
  overallCompliant: boolean | null;
  passCount: number;
  failCount: number;
  notCheckedCount: number;
  totalChecks: number;
  results: CdcCheck[];
  summary: string;
  recommendations: string[];
  disclaimer: string;
  meta?: {
    timestamp: string;
    standardsApplied: string;
    standardsError?: string | null;
  };
}

/**
 * Development type options for dropdown
 */
export const DEVELOPMENT_TYPE_OPTIONS: {
  value: CdcDevelopmentType;
  label: string;
  description: string;
}[] = [
  {
    value: 'new_dwelling',
    label: 'New dwelling house',
    description: 'A new single dwelling on the lot',
  },
  {
    value: 'addition',
    label: 'Addition to existing dwelling',
    description: 'Extending an existing dwelling',
  },
  {
    value: 'alteration',
    label: 'Alteration to existing dwelling',
    description: 'Internal or external modifications',
  },
  {
    value: 'secondary_dwelling',
    label: 'Secondary dwelling (granny flat)',
    description: 'Self-contained dwelling up to 60m\u00B2',
  },
];
