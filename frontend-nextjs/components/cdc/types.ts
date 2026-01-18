/**
 * CDC Compliance Calculator Types
 *
 * Type definitions for the CDC compliance checking form and results.
 * Based on SEPP Housing 2021, Part 3, Division 1 standards.
 */

/**
 * Development type options for CDC assessment
 */
export type CdcDevelopmentType =
  | 'new_dwelling'
  | 'alteration'
  | 'addition'
  | 'secondary_dwelling';

/**
 * User input for CDC compliance calculation
 */
export interface CdcComplianceInput {
  developmentType: CdcDevelopmentType;
  setbacks: {
    front: number;      // meters
    sideLeft: number;   // meters
    sideRight: number;  // meters
    rear: number;       // meters
  };
  hasUpperFloorHabitableRooms: boolean;  // affects rear setback requirement
  siteCoveragePercent: number;           // 0-100
  landscapedAreaPercent: number;         // 0-100
  buildingHeightMeters: number;          // meters
  storeys: number;                       // 1 or 2
  parkingSpaces: number;                 // spaces provided
  bedrooms: number;                      // for parking calculation
}

/**
 * Default values for the form
 */
export const CDC_INPUT_DEFAULTS: CdcComplianceInput = {
  developmentType: 'new_dwelling',
  setbacks: {
    front: 6.0,
    sideLeft: 0.9,
    sideRight: 0.9,
    rear: 3.0,
  },
  hasUpperFloorHabitableRooms: false,
  siteCoveragePercent: 45,
  landscapedAreaPercent: 30,
  buildingHeightMeters: 8.5,
  storeys: 2,
  parkingSpaces: 2,
  bedrooms: 3,
};

/**
 * SEPP Housing 2021 CDC standards
 */
export const CDC_STANDARDS = {
  setbacks: {
    front: {
      minimum: 6.0,
      reference: 'SEPP Housing 2021, Clause 22(a)',
      description: 'Front setback to street boundary',
    },
    side: {
      minimum: 0.9,
      reference: 'SEPP Housing 2021, Clause 22(b)',
      description: 'Side setback to side boundary',
    },
    rear: {
      minimum: 3.0,
      minimumUpperFloor: 6.0,
      reference: 'SEPP Housing 2021, Clause 22(c)',
      description: 'Rear setback to rear boundary',
    },
  },
  siteCoverage: {
    maximum: 50, // percentage - zone dependent, using R2 default
    reference: 'SEPP Housing 2021, Clause 23',
    description: 'Maximum site coverage',
  },
  landscapedArea: {
    minimum: 30, // percentage
    reference: 'SEPP Housing 2021, Clause 24',
    description: 'Minimum landscaped area',
  },
  buildingHeight: {
    maximum: 8.5, // meters
    reference: 'SEPP Housing 2021, Clause 21',
    description: 'Maximum building height',
  },
  storeys: {
    maximum: 2,
    reference: 'SEPP Housing 2021, Clause 21',
    description: 'Maximum number of storeys',
  },
  parking: {
    reference: 'SEPP Housing 2021, Clause 25',
    description: 'Minimum car parking spaces',
    // Bedroom-based requirements
    thresholds: [
      { bedrooms: 1, spaces: 1 },
      { bedrooms: 2, spaces: 1 },
      { bedrooms: 3, spaces: 2 },
      { bedrooms: 4, spaces: 2 },
    ],
  },
} as const;

/**
 * Get required parking spaces based on bedroom count
 */
export function getRequiredParking(bedrooms: number): number {
  if (bedrooms <= 2) return 1;
  return 2;
}

/**
 * Field validation state
 */
export interface FieldValidation {
  valid: boolean;
  required: number;
  proposed: number;
  margin: number;
  reference: string;
  message: string;
}

/**
 * Overall form validation state
 */
export interface FormValidation {
  front: FieldValidation;
  sideLeft: FieldValidation;
  sideRight: FieldValidation;
  rear: FieldValidation;
  siteCoverage: FieldValidation;
  landscapedArea: FieldValidation;
  buildingHeight: FieldValidation;
  storeys: FieldValidation;
  parking: FieldValidation;
}

/**
 * Result of a single compliance check
 */
export interface ComplianceCheckResult {
  standard: string;
  proposed: number | string;
  required: number | string;
  compliant: boolean;
  margin: number | string;
  reference: string;
  unit: string;
}

/**
 * Overall compliance check response
 */
export interface CdcComplianceResponse {
  success: boolean;
  overallCompliant: boolean;
  passCount: number;
  totalChecks: number;
  results: ComplianceCheckResult[];
  summary: string;
  recommendations: string[];
  disclaimer: string;
  meta?: {
    timestamp: string;
    standardsApplied: string;
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
