/**
 * ExtractedRule Schema — data contract between deterministic extractors and LLM
 *
 * Every provision gets an array of ExtractedRule objects. This is the typed
 * contract that flows between:
 *   - Python deterministic extractors (regex, heading rules, table parsing)
 *   - LLM one-shot interpretation (Claude API)
 *   - Validation gates (Zod on frontend, Python checks on backend)
 *   - Human review CLI
 *
 * Stored in DB as: regulatory_provisions.v2_extracted_rules jsonb
 */

import { z } from 'zod';

// ============================================================================
// COMPLIANCE TYPES
// ============================================================================

/**
 * How this rule should be assessed in a DA/SEE:
 * - numeric_check: Has a measurable requirement (6m setback, 9m height, 40% landscaping)
 * - merit_assessment: Requires professional judgment ("to the satisfaction of Council")
 * - binary_prohibition: Permitted or not ("is not permitted", "must not be demolished")
 * - procedural: Submission requirement ("shall submit a landscape plan")
 */
export const ComplianceTypeSchema = z.enum([
  'numeric_check',
  'merit_assessment',
  'binary_prohibition',
  'procedural',
]);
export type ComplianceType = z.infer<typeof ComplianceTypeSchema>;

// ============================================================================
// VALUE TYPES — what's being measured
// ============================================================================

export const ValueTypeSchema = z.enum([
  'setback',
  'height',
  'fsr',
  'lot_area',
  'lot_width',
  'site_coverage',
  'landscaping',
  'deep_soil',
  'parking',
  'parking_spaces',
  'dimension',
  'wall_height',
  'floor_area',
  'dwelling_density',
  'solar_access',
  'privacy_distance',
  'other',
]);
export type ValueType = z.infer<typeof ValueTypeSchema>;

// ============================================================================
// CONDITION — for conditional/tiered rules
// ============================================================================

/**
 * A conditional branch within a rule.
 *
 * Example: "3.6m maximum wall height, except on dominant corners, where 6m"
 *   → { when: "dominant corner", then_value: 6, then_unit: "m" }
 *
 * Example: "match prevailing building line"
 *   → { when: "all cases", then_text: "match prevailing building line" }
 */
export const RuleConditionSchema = z.object({
  when: z.string().min(3).max(500),
  then_value: z.number().optional(),
  then_unit: z.string().max(20).optional(),
  then_text: z.string().max(1000).optional(),
});
export type RuleCondition = z.infer<typeof RuleConditionSchema>;

// ============================================================================
// REFERENCE — cross-references to other instruments/clauses
// ============================================================================

/**
 * A reference to another planning instrument, clause, or section.
 *
 * Example: "Refer to Clause 6.20 of the Inner West LEP 2022"
 *   → { target: "Inner West LEP 2022 Clause 6.20", relationship: "defers_to" }
 *
 * Example: "In accordance with Part C1.9 Safety by Design"
 *   → { target: "Part C1.9", relationship: "supplements" }
 */
export const RuleReferenceSchema = z.object({
  target: z.string().min(3).max(200),
  relationship: z.enum(['supplements', 'overrides', 'defers_to', 'see_also']),
});
export type RuleReference = z.infer<typeof RuleReferenceSchema>;

// ============================================================================
// EXTRACTION METHOD + CONFIDENCE
// ============================================================================

export const ExtractionMethodSchema = z.enum([
  'regex',        // NumericExtractor patterns
  'heading_rule', // ActionableClassifier heading suffix rules
  'table_parse',  // HTML table PC/DS splitting
  'llm',          // Claude API one-shot extraction
]);
export type ExtractionMethod = z.infer<typeof ExtractionMethodSchema>;

export const ExtractionConfidenceSchema = z.enum(['high', 'medium', 'low']);
export type ExtractionConfidence = z.infer<typeof ExtractionConfidenceSchema>;

// ============================================================================
// EXTRACTED RULE — the core type
// ============================================================================

export const ExtractedRuleSchema = z.object({
  compliance_type: ComplianceTypeSchema,

  // Numeric values (for numeric_check rules)
  value_type: ValueTypeSchema.optional(),
  value_min: z.number().optional(),
  value_max: z.number().optional(),
  value_exact: z.number().optional(),
  unit: z.string().max(20).optional(),
  context: z.string().max(50).optional(), // front, side, rear, secondary

  // Conditional/tiered rules
  conditions: z.array(RuleConditionSchema).optional(),

  // Cross-references
  references: z.array(RuleReferenceSchema).optional(),

  // Spatial dependency (maps, diagrams, figures)
  has_spatial_component: z.boolean().optional(),

  // Extraction provenance
  extraction_method: ExtractionMethodSchema,
  extraction_confidence: ExtractionConfidenceSchema,
  raw_match: z.string().max(500).optional(),
});
export type ExtractedRule = z.infer<typeof ExtractedRuleSchema>;

// Per-provision: array of extracted rules
export const ProvisionExtractedRulesSchema = z.array(ExtractedRuleSchema);
export type ProvisionExtractedRules = z.infer<typeof ProvisionExtractedRulesSchema>;

// ============================================================================
// EXTRACTION STATUS — tracks pipeline progress per provision
// ============================================================================

export const ExtractionStatusSchema = z.enum([
  'complete',       // Deterministic extraction sufficient
  'llm_complete',   // LLM filled gaps, validation passed
  'review_needed',  // Failed validation after retry — human must check
  'skipped',        // Not actionable, no extraction needed
]);
export type ExtractionStatus = z.infer<typeof ExtractionStatusSchema>;

// ============================================================================
// VALIDATION HELPERS
// ============================================================================

/** Validate a single rule and return error messages. Empty array = valid. */
export function validateRulePlausibility(rule: ExtractedRule): string[] {
  const errors: string[] = [];

  // Numeric plausibility checks
  const numFields = [rule.value_min, rule.value_max, rule.value_exact].filter(
    (v) => v !== undefined && v !== null
  ) as number[];

  if (rule.value_type === 'setback') {
    for (const v of numFields) {
      if (v < 0 || v > 100) errors.push(`Implausible setback value: ${v}m`);
    }
  }
  if (rule.value_type === 'height' || rule.value_type === 'wall_height') {
    for (const v of numFields) {
      if (v < 0 || v > 200) errors.push(`Implausible height value: ${v}m`);
    }
  }
  if (rule.value_type === 'fsr') {
    for (const v of numFields) {
      if (v < 0 || v > 20) errors.push(`Implausible FSR value: ${v}`);
    }
  }
  if (rule.unit === '%') {
    for (const v of numFields) {
      if (v < 0 || v > 100) errors.push(`Implausible percentage: ${v}%`);
    }
  }

  // Compliance type consistency
  if (rule.compliance_type === 'numeric_check') {
    const hasValue = numFields.length > 0;
    const hasConditions = rule.conditions && rule.conditions.length > 0;
    if (!hasValue && !hasConditions) {
      errors.push('numeric_check rule must have a value or conditions');
    }
  }

  // Condition completeness
  if (rule.conditions) {
    for (const cond of rule.conditions) {
      if (cond.then_value === undefined && !cond.then_text) {
        errors.push(`Condition "${cond.when}" has no outcome (then_value or then_text)`);
      }
    }
  }

  // Min/max consistency
  if (
    rule.value_min !== undefined &&
    rule.value_max !== undefined &&
    rule.value_min > rule.value_max
  ) {
    errors.push(`value_min (${rule.value_min}) > value_max (${rule.value_max})`);
  }

  return errors;
}

/** Validate an array of rules for a provision. */
export function validateProvisionRules(rules: ExtractedRule[]): string[] {
  const errors: string[] = [];

  // Schema validation
  const parseResult = ProvisionExtractedRulesSchema.safeParse(rules);
  if (!parseResult.success) {
    errors.push(
      ...parseResult.error.issues.map(
        (e) => `Schema: ${e.path.join('.')}: ${e.message}`
      )
    );
    return errors; // Don't run plausibility if schema fails
  }

  // Plausibility per rule
  for (let i = 0; i < rules.length; i++) {
    const ruleErrors = validateRulePlausibility(rules[i]);
    errors.push(...ruleErrors.map((e) => `Rule[${i}]: ${e}`));
  }

  return errors;
}
