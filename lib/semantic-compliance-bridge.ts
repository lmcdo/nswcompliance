/**
 * Bridge between dual semantic processor and compliance engine
 * Converts semantic rule extractions to ComplianceRule format with source authority
 */

import { ComplianceRule, RuleRequirement, SourceReference, PropertySelector } from './compliance-engine';

export interface SemanticRuleExtraction {
 area: string;
 extraction_method: string;
 enhanced_rules: EnhancedRule[];
 total_enhanced_rules: number;
 high_confidence_rules: number;
}

export interface EnhancedRule {
 rule_id: string;
 rule_text: string;
 rule_type: string;
 measurements: RuleMeasurement[];
 rule_classification: RuleClassification;
 source_grounding: SourceGrounding;
 overall_confidence: number;
 rule_complexity: string;
}

export interface RuleMeasurement {
 measurement_type: string;
 value: number | string;
 unit: string;
 context: string;
 confidence: number;
}

export interface RuleClassification {
 tier: number;
 enforcement_level: string;
 linguistic_confidence: number;
 prescriptive_indicators: string[];
 compliance_message_type: string;
}

export interface SourceGrounding {
 extraction_text: string;
 source_section: string;
 source_page: number;
 confidence: number;
 highlighted_spans: [number, number][];
}

export class SemanticComplianceBridge {
 
 /**
 * Convert dual semantic processor output to ComplianceRule format
 */
 convertToComplianceRules(
 semanticExtraction: SemanticRuleExtraction,
 formerCouncilArea: string
 ): ComplianceRule[] {
 const complianceRules: ComplianceRule[] = [];
 
 for (const enhancedRule of semanticExtraction.enhanced_rules) {
 // Only convert Tier 1 (mandatory) and Tier 2 (strong guidance) rules
 if (enhancedRule.rule_classification.tier <= 2) {
 const complianceRule = this.enhancedRuleToComplianceRule(
 enhancedRule,
 formerCouncilArea,
 semanticExtraction.area
 );
 
 if (complianceRule) {
 complianceRules.push(complianceRule);
 }
 }
 }
 
 return complianceRules;
 }
 
 private enhancedRuleToComplianceRule(
 enhancedRule: EnhancedRule,
 formerCouncilArea: string,
 area: string
 ): ComplianceRule | null {
 try {
 // Determine rule type and create requirements
 const requirements = this.extractRuleRequirements(enhancedRule);
 if (requirements.length === 0) return null;
 
 // Create property selector
 const propertySelector: PropertySelector = {
 lga: ["Inner West"],
 zones: ["R2"], // Default for residential setbacks
 former_council: [formerCouncilArea]
 };
 
 // Create source reference with semantic grounding
 const sourceReference: SourceReference = {
 document: `${formerCouncilArea} DCP`,
 section: enhancedRule.source_grounding.source_section || "Setback Requirements",
 clause: enhancedRule.rule_id,
 url: "https://www.innerwest.nsw.gov.au/development/development-control-plans",
 effective_date: "Current"
 };
 
 // Determine jurisdiction and priority based on classification
 const jurisdiction = enhancedRule.rule_classification.tier === 1 ? "DCP" : "DCP";
 const priority = enhancedRule.rule_classification.tier === 1 ? 1 : 2;
 
 return {
 id: `IW_${enhancedRule.rule_type.toUpperCase()}_${formerCouncilArea.toUpperCase()}_SEMANTIC`,
 jurisdiction,
 authority: `Inner West Council (former ${formerCouncilArea})`,
 applies_to: propertySelector,
 requirements,
 source: sourceReference,
 priority
 };
 
 } catch (error) {
 console.error(`Failed to convert enhanced rule ${enhancedRule.rule_id}:`, error);
 return null;
 }
 }
 
 private extractRuleRequirements(enhancedRule: EnhancedRule): RuleRequirement[] {
 const requirements: RuleRequirement[] = [];
 
 for (const measurement of enhancedRule.measurements) {
 // Handle different measurement types
 const requirement = this.measurementToRequirement(measurement, enhancedRule);
 if (requirement) {
 requirements.push(requirement);
 }
 }
 
 return requirements;
 }
 
 private measurementToRequirement(
 measurement: RuleMeasurement,
 enhancedRule: EnhancedRule
 ): RuleRequirement | null {
 try {
 // Handle conditional measurements (e.g., "0.9m minimum OR 0.5 times building height")
 if (measurement.measurement_type === "conditional") {
 return this.handleConditionalMeasurement(measurement, enhancedRule);
 }
 
 // Handle standard measurements
 const numericValue = this.parseNumericValue(measurement.value);
 if (numericValue === null) return null;
 
 // Determine operator based on context and classification
 const operator = this.determineOperator(measurement, enhancedRule);
 
 return {
 type: this.mapMeasurementTypeToRequirementType(measurement.measurement_type),
 operator,
 value: numericValue,
 units: measurement.unit,
 context: `${measurement.context} (${enhancedRule.rule_classification.enforcement_level})`
 };
 
 } catch (error) {
 console.error(`Failed to convert measurement ${measurement.measurement_type}:`, error);
 return null;
 }
 }
 
 private handleConditionalMeasurement(
 measurement: RuleMeasurement,
 enhancedRule: EnhancedRule
 ): RuleRequirement | null {
 // For conditional rules like "0.9m minimum OR 0.5 times building height, whichever is greater"
 // We need to create a requirement that captures the primary constraint
 
 // Extract the base minimum value for now
 const valueStr = measurement.value.toString();
 const minMatch = valueStr.match(/(\d+\.?\d*)\s*m\s*minimum/);
 
 if (minMatch) {
 const minValue = parseFloat(minMatch[1]);
 return {
 type: this.mapMeasurementTypeToRequirementType(measurement.measurement_type.replace('_conditional', '')),
 operator: ">=",
 value: minValue,
 units: "metres",
 context: `${measurement.context} (conditional: ${valueStr})`
 };
 }
 
 return null;
 }
 
 private parseNumericValue(value: number | string): number | null {
 if (typeof value === 'number') return value;
 
 const numStr = value.toString();
 const numMatch = numStr.match(/(\d+\.?\d*)/);
 return numMatch ? parseFloat(numMatch[1]) : null;
 }
 
 private determineOperator(measurement: RuleMeasurement, enhancedRule: EnhancedRule): ">=" | "<=" | ">" | "<" | "=" {
 // Analyze context and classification to determine appropriate operator
 const context = measurement.context.toLowerCase();
 const enforcement = enhancedRule.rule_classification.enforcement_level;
 
 if (context.includes('minimum') || context.includes('at least')) {
 return ">=";
 } else if (context.includes('maximum') || context.includes('not exceed')) {
 return "<=";
 } else if (enforcement === "MANDATORY") {
 // For mandatory rules without clear direction, default to minimum
 return ">=";
 } else {
 // For guidance rules, use minimum as safe default
 return ">=";
 }
 }
 
 private mapMeasurementTypeToRequirementType(measurementType: string): string {
 const typeMapping: { [key: string]: string } = {
 'side_setback': 'side_setback',
 'rear_setback': 'rear_setback', 
 'front_setback': 'front_setback',
 'setback': 'setback',
 'height': 'height',
 'building_height': 'height'
 };
 
 return typeMapping[measurementType] || measurementType;
 }
 
 /**
 * Create enhanced response with source authority and confidence
 */
 createEnhancedSetbackResponse(
 complianceRules: ComplianceRule[],
 semanticExtraction: SemanticRuleExtraction,
 formerCouncilArea: string
 ) {
 return {
 setbacks: this.formatSetbacksFromRules(complianceRules),
 formerCouncilArea,
 success: true,
 source_authority: {
 extraction_method: semanticExtraction.extraction_method,
 total_rules_analyzed: semanticExtraction.total_enhanced_rules,
 high_confidence_rules: semanticExtraction.high_confidence_rules,
 semantic_confidence: this.calculateOverallConfidence(semanticExtraction)
 },
 rule_details: complianceRules.map(rule => ({
 rule_id: rule.id,
 authority: rule.authority,
 source_section: rule.source.section,
 enforcement_priority: rule.priority,
 requirements_count: rule.requirements.length
 }))
 };
 }
 
 private formatSetbacksFromRules(rules: ComplianceRule[]) {
 const setbacks = {
 rear: null as number | null,
 side: null as number | null, 
 front: null as number | null
 };
 
 for (const rule of rules) {
 for (const req of rule.requirements) {
 if (req.type === 'rear_setback' && typeof req.value === 'number') {
 setbacks.rear = req.value;
 } else if (req.type === 'side_setback' && typeof req.value === 'number') {
 setbacks.side = req.value;
 } else if (req.type === 'front_setback' && typeof req.value === 'number') {
 setbacks.front = req.value;
 }
 }
 }
 
 return setbacks;
 }
 
 private calculateOverallConfidence(extraction: SemanticRuleExtraction): number {
 if (extraction.enhanced_rules.length === 0) return 0;
 
 const totalConfidence = extraction.enhanced_rules.reduce(
 (sum, rule) => sum + rule.overall_confidence, 0
 );
 
 return totalConfidence / extraction.enhanced_rules.length;
 }
}