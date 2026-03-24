/**
 * Pattern Book Eligibility Assessment
 *
 * Master function that combines exclusion checks, override checks,
 * and numeric compliance to determine Pattern Book CDC pathway eligibility.
 */

import { Pool } from 'pg';
import { checkExclusions, isZoneEligible, PropertyConstraints } from './check-exclusions';
import { checkOverrides, generateOverrideSteps } from './check-overrides';
import { checkNumericStandards, formatNumericFailure, LotDimensions } from './check-numerics';

export type EligibilityStatus = 'ELIGIBLE' | 'CONDITIONAL' | 'INELIGIBLE';
export type PathwayType = 'PATTERN_BOOK_CDC' | 'PATTERN_BOOK_WITH_ASSESSMENT' | 'DA_REQUIRED';

export interface PatternBookEligibility {
  // Overall result
  status: EligibilityStatus;
  pathway: PathwayType;
  confidence: number; // 0-1 (based on data completeness)

  // Detailed results
  zoneEligible: boolean;
  exclusionCheck: {
    hasExclusions: boolean;
    count: number;
    details: any[];
  };
  overrideCheck: {
    anyOverrideable: boolean;
    count: number;
    details: any[];
  };
  numericCheck: {
    allCompliant: boolean;
    failureCount: number;
    details: any[];
  };

  // User-facing
  summary: string;
  reasons: string[];
  nextSteps: string[];
  estimatedApprovalTime?: string;
}

/**
 * Assess Pattern Book CDC pathway eligibility for a property
 */
export async function assessPatternBookEligibility(
  constraints: PropertyConstraints,
  lotDimensions: LotDimensions | null,
  dbPool: Pool
): Promise<PatternBookEligibility> {

  // Step 1: Check zone eligibility (Pattern Book only applies to R1/R2/R3)
  const zoneEligible = isZoneEligible(constraints.zone);

  if (!zoneEligible) {
    return {
      status: 'INELIGIBLE',
      pathway: 'DA_REQUIRED',
      confidence: 1.0,
      zoneEligible: false,
      exclusionCheck: { hasExclusions: false, count: 0, details: [] },
      overrideCheck: { anyOverrideable: false, count: 0, details: [] },
      numericCheck: { allCompliant: true, failureCount: 0, details: [] },
      summary: `Zone ${constraints.zone || 'unknown'} is not eligible for Pattern Book pathway`,
      reasons: [
        `Pattern Book CDC only applies to R1, R2, R3 zones`,
        `This property is zoned ${constraints.zone || 'unknown'}`
      ],
      nextSteps: [
        'Standard Development Application (DA) required',
        'DA assessed under Housing SEPP standards (50+ days)'
      ]
    };
  }

  // Step 2: Check exclusions
  const exclusionResult = await checkExclusions(constraints, dbPool);

  // Step 3: If exclusions triggered, check overrides
  let overrideResult: any = { anyOverrideable: false, overrides: [], summary: '' };
  if (exclusionResult.hasExclusions) {
    overrideResult = await checkOverrides(exclusionResult.triggered, dbPool);
  }

  // Step 4: Check numeric standards
  const numericResult = await checkNumericStandards(
    lotDimensions,
    constraints.zone,
    constraints.lga,
    dbPool
  );

  // Determine eligibility status
  let status: EligibilityStatus;
  let pathway: PathwayType;
  let summary: string;
  let reasons: string[] = [];
  let nextSteps: string[] = [];
  let estimatedApprovalTime: string | undefined;

  // Case 1: No exclusions, numerics compliant → ELIGIBLE
  if (!exclusionResult.hasExclusions && numericResult.allCompliant) {
    status = 'ELIGIBLE';
    pathway = 'PATTERN_BOOK_CDC';
    summary = 'Property is eligible for Pattern Book CDC pathway (10-day approval)';
    reasons = [
      'Zone is eligible (R1/R2/R3)',
      'No exclusions triggered',
      'Numeric standards met'
    ];
    nextSteps = [
      'Browse Pattern Book designs at shop-pattern-book.planning.nsw.gov.au',
      'Purchase design matching your lot size ($1,000-$25,000, discounted to $1-$2,500)',
      'Engage accredited designer to adapt design to site',
      'Lodge CDC application with private certifier or council',
      'Receive approval within 10 days'
    ];
    estimatedApprovalTime = '10 days';
  }
  // Case 2: Exclusions triggered, but all overrideable → CONDITIONAL
  else if (exclusionResult.hasExclusions && overrideResult.anyOverrideable) {
    const allOverrideable = overrideResult.overrides.every((o: any) => o.canOverride);

    if (allOverrideable) {
      status = 'CONDITIONAL';
      pathway = 'PATTERN_BOOK_WITH_ASSESSMENT';
      summary = 'Property eligible for Pattern Book CDC AFTER obtaining required assessments';
      reasons = [
        `${exclusionResult.triggered.length} exclusion(s) triggered`,
        'All exclusions can be overridden with assessments'
      ];
      nextSteps = generateOverrideSteps(overrideResult.overrides);
      estimatedApprovalTime = '10 days (after assessments obtained)';
    } else {
      status = 'INELIGIBLE';
      pathway = 'DA_REQUIRED';
      summary = 'Property has non-overrideable exclusions - DA required';
      reasons = [
        `${exclusionResult.triggered.length} exclusion(s) triggered`,
        'Some exclusions cannot be overridden'
      ];
      nextSteps = generateOverrideSteps(overrideResult.overrides);
    }
  }
  // Case 3: Exclusions triggered, none overrideable → INELIGIBLE
  else if (exclusionResult.hasExclusions && !overrideResult.anyOverrideable) {
    status = 'INELIGIBLE';
    pathway = 'DA_REQUIRED';
    summary = 'Pattern Book CDC pathway blocked by exclusions';
    reasons = exclusionResult.triggered.map(e => e.reason);
    nextSteps = [
      'Pattern Book CDC not available',
      'Standard Development Application (DA) required',
      'DA assessed under Housing SEPP non-discretionary standards (50+ days)'
    ];
  }
  // Case 4: Numeric failures → INELIGIBLE (for now)
  else if (!numericResult.allCompliant) {
    status = 'INELIGIBLE';
    pathway = 'DA_REQUIRED';
    summary = 'Property does not meet numeric standards for Pattern Book';
    reasons = numericResult.failures.map(formatNumericFailure);
    nextSteps = [
      'Lot dimensions do not meet Pattern Book minimums',
      'Standard Development Application (DA) required'
    ];
  }
  // Fallback
  else {
    status = 'INELIGIBLE';
    pathway = 'DA_REQUIRED';
    summary = 'Insufficient data to assess Pattern Book eligibility';
    reasons = ['Unable to complete eligibility assessment'];
    nextSteps = ['Contact PlotDetect support for assistance'];
  }

  // Calculate confidence based on data completeness
  let confidence = 1.0;
  if (!lotDimensions) confidence -= 0.2;
  if (!constraints.zone) confidence -= 0.3;
  if (!constraints.heritage && !constraints.environmental) confidence -= 0.2;

  return {
    status,
    pathway,
    confidence,
    zoneEligible,
    exclusionCheck: {
      hasExclusions: exclusionResult.hasExclusions,
      count: exclusionResult.triggered.length,
      details: exclusionResult.triggered
    },
    overrideCheck: {
      anyOverrideable: overrideResult.anyOverrideable,
      count: overrideResult.overrides.length,
      details: overrideResult.overrides
    },
    numericCheck: {
      allCompliant: numericResult.allCompliant,
      failureCount: numericResult.failures.length,
      details: numericResult.failures
    },
    summary,
    reasons,
    nextSteps,
    estimatedApprovalTime
  };
}
