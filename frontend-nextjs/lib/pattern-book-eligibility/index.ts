/**
 * Pattern Book Eligibility Assessment Library
 *
 * Uses 425 extracted SEPP requirements to determine Pattern Book CDC
 * pathway eligibility before users spend $1k-$25k on pattern designs.
 */

export {
  checkExclusions,
  isZoneEligible,
  type PropertyConstraints,
  type ExclusionTrigger,
  type ExclusionCheckResult
} from './check-exclusions';

export {
  checkOverrides,
  generateOverrideSteps,
  type OverrideOption,
  type OverrideCheckResult
} from './check-overrides';

export {
  checkNumericStandards,
  formatNumericFailure,
  type LotDimensions,
  type NumericFailure,
  type NumericCheckResult
} from './check-numerics';

export {
  assessPatternBookEligibility,
  type EligibilityStatus,
  type PathwayType,
  type PatternBookEligibility
} from './assess-eligibility';
