/**
 * Enhanced Compliance Engine with Semantic Rule Integration
 * Extends the base compliance engine to work with dual semantic processor outputs
 */

import { ComplianceEngine, ComplianceRule, ComplianceResult, PropertyData } from './compliance-engine';
import { EnhancedSetbackProcessor, ProcessedSetbackData } from './enhanced-setback-processor';
import { SemanticComplianceBridge } from './semantic-compliance-bridge';
import { RegulatoryTextRetriever } from './regulatory-text-retriever';

export interface EnhancedComplianceResult extends ComplianceResult {
 source_grounding?: {
 extraction_text: string;
 source_section: string;
 highlighted_spans: [number, number][];
 semantic_confidence: number;
 };
 rule_classification?: {
 tier: number;
 enforcement_level: string;
 compliance_message_type: string;
 };
 processing_method: 'semantic' | 'manual' | 'fallback';
 has_actual_regulatory_text?: boolean;
 rule_explanation?: string;
}

export class EnhancedComplianceEngine extends ComplianceEngine {
 private setbackProcessor: EnhancedSetbackProcessor;
 private semanticBridge: SemanticComplianceBridge;
 private regulatoryTextRetriever: RegulatoryTextRetriever;

 constructor() {
 super();
 this.setbackProcessor = new EnhancedSetbackProcessor();
 this.semanticBridge = new SemanticComplianceBridge();
 this.regulatoryTextRetriever = new RegulatoryTextRetriever();
 }

 /**
 * Enhanced compliance check with semantic rule integration
 */
 async checkEnhancedCompliance(
 propertyData: PropertyData,
 proposal: {
 height?: number;
 fsr?: number;
 front_setback?: number;
 side_setback?: number;
 rear_setback?: number;
 },
 formerCouncilArea?: string,
 useSemanticRules: boolean = true
 ): Promise<EnhancedComplianceResult[]> {
 console.log(` checkEnhancedCompliance called for ${formerCouncilArea} with semantic rules: ${useSemanticRules}`);
 const results: EnhancedComplianceResult[] = [];

 // Start with base compliance checks (LEP rules from NSW API)
 const baseResults = await this.checkCompliance(propertyData, proposal, formerCouncilArea);
 
 // Convert base results to enhanced format with real regulatory text
 console.log(` Processing ${baseResults.length} base results for regulatory text enrichment`);
 for (const baseResult of baseResults) {
 const enhancedResult = {
 ...baseResult,
 processing_method: 'manual' as const, // These are manually encoded rules
 rule_classification: {
 tier: 1, // LEP rules are always Tier 1 (mandatory)
 enforcement_level: 'MANDATORY',
 compliance_message_type: 'MUST_COMPLY'
 }
 };

 // Set real regulatory text from our LightRAG storage
 const resultWithText = await this.setRegulatoryText(enhancedResult, formerCouncilArea);
 results.push(resultWithText);
 }

 // Add semantic DCP rules if enabled and former council area is available
 if (useSemanticRules && formerCouncilArea) {
 try {
 const semanticResults = await this.checkSemanticCompliance(
 propertyData,
 proposal,
 formerCouncilArea
 );
 
 // Set real regulatory text on semantic results too
 for (const semanticResult of semanticResults) {
 const semanticResultWithText = await this.setRegulatoryText(semanticResult, formerCouncilArea);
 results.push(semanticResultWithText);
 }
 } catch (error) {
 console.warn(`Semantic compliance check failed for ${formerCouncilArea}:`, error);
 // Continue with base results only
 }
 }

 // Deduplicate rules by requirement type, keeping the most restrictive/highest confidence
 const deduplicatedResults = this.deduplicateResults(results);
 
 // Sort results by priority and enforcement level
 deduplicatedResults.sort((a, b) => {
 // Prioritize non-compliant rules first
 if (a.compliant !== b.compliant) {
 return a.compliant ? 1 : -1;
 }
 
 // Then by enforcement tier (lower tier = higher priority)
 const aTier = a.rule_classification?.tier || 3;
 const bTier = b.rule_classification?.tier || 3;
 if (aTier !== bTier) {
 return aTier - bTier;
 }
 
 // Finally by confidence (higher confidence first)
 const aConfidence = a.confidence === 'HIGH' ? 3 : a.confidence === 'MEDIUM' ? 2 : 1;
 const bConfidence = b.confidence === 'HIGH' ? 3 : b.confidence === 'MEDIUM' ? 2 : 1;
 return bConfidence - aConfidence;
 });

 return deduplicatedResults;
 }

 /**
 * Deduplicate compliance results by requirement type, keeping the most restrictive/highest priority rule
 */
 private deduplicateResults(results: EnhancedComplianceResult[]): EnhancedComplianceResult[] {
 const resultMap = new Map<string, EnhancedComplianceResult>();
 
 for (const result of results) {
 const key = result.requirement_type;
 
 if (!resultMap.has(key)) {
 resultMap.set(key, result);
 } else {
 const existing = resultMap.get(key)!;
 
 // Priority logic: keep the most restrictive rule (or highest priority)
 const shouldReplace = this.shouldReplaceRule(existing, result);
 
 if (shouldReplace) {
 resultMap.set(key, result);
 }
 }
 }
 
 return Array.from(resultMap.values());
 }

 /**
 * Determine if a new rule should replace an existing rule
 */
 private shouldReplaceRule(existing: EnhancedComplianceResult, candidate: EnhancedComplianceResult): boolean {
 // Priority 1: Manual (LEP) rules trump semantic (DCP) rules
 if (existing.processing_method === 'manual' && candidate.processing_method === 'semantic') {
 return false;
 }
 if (existing.processing_method === 'semantic' && candidate.processing_method === 'manual') {
 return true;
 }
 
 // Priority 2: Higher enforcement tier (lower number = higher priority)
 const existingTier = existing.rule_classification?.tier || 3;
 const candidateTier = candidate.rule_classification?.tier || 3;
 if (existingTier !== candidateTier) {
 return candidateTier < existingTier;
 }
 
 // Priority 3: Higher confidence
 const existingConfidence = existing.confidence === 'HIGH' ? 3 : existing.confidence === 'MEDIUM' ? 2 : 1;
 const candidateConfidence = candidate.confidence === 'HIGH' ? 3 : candidate.confidence === 'MEDIUM' ? 2 : 1;
 if (existingConfidence !== candidateConfidence) {
 return candidateConfidence > existingConfidence;
 }
 
 // Priority 4: For same type, keep the most restrictive (higher required value for setbacks)
 if (existing.requirement_type.includes('SETBACK') && typeof existing.required_value === 'number' && typeof candidate.required_value === 'number') {
 return candidate.required_value > existing.required_value;
 }
 
 // Default: keep existing
 return false;
 }

 /**
 * Check compliance against semantic rules
 */
 private async checkSemanticCompliance(
 propertyData: PropertyData,
 proposal: {
 height?: number;
 fsr?: number;
 front_setback?: number;
 side_setback?: number;
 rear_setback?: number;
 },
 formerCouncilArea: string
 ): Promise<EnhancedComplianceResult[]> {
 const results: EnhancedComplianceResult[] = [];

 // Get processed setback data from dual semantic pipeline
 const processedData = await this.setbackProcessor.processSetbackRules(formerCouncilArea);

 if (!processedData.processing_metadata.success || processedData.compliance_rules.length === 0) {
 console.warn(`No semantic rules available for ${formerCouncilArea}`);
 return results;
 }

 // Check each semantic compliance rule
 for (const rule of processedData.compliance_rules) {
 for (const requirement of rule.requirements) {
 const proposalValue = this.getProposalValue(proposal, requirement.type);
 if (proposalValue === undefined) continue;

 const compliant = this.evaluateRequirement(proposalValue, requirement);
 const gap = this.calculateGap(proposalValue, requirement);

 // Find corresponding enhanced rule for additional metadata
 const enhancedRule = processedData.source_authority ? 
 this.findEnhancedRuleMetadata(rule.id, processedData) : null;

 const enhancedResult: EnhancedComplianceResult = {
 rule_id: rule.id,
 requirement_type: requirement.type,
 compliant,
 proposed_value: proposalValue,
 required_value: requirement.value,
 gap,
 source: enhancedRule?.source_grounding ? {
 document: rule.source.document,
 section: enhancedRule.source_grounding.source_section,
 clause: enhancedRule.source_grounding.source_section,
 url: rule.source.url,
 effective_date: rule.source.effective_date
 } : rule.source,
 mitigation: !compliant ? this.generateMitigation(requirement, gap) : undefined,
 confidence: this.mapSemanticConfidence(enhancedRule?.overall_confidence || 0.8),
 processing_method: 'semantic',
 rule_classification: enhancedRule ? {
 tier: enhancedRule.rule_classification.tier,
 enforcement_level: enhancedRule.rule_classification.enforcement_level,
 compliance_message_type: enhancedRule.rule_classification.compliance_message_type
 } : {
 tier: 2,
 enforcement_level: 'RECOMMENDED',
 compliance_message_type: 'SHOULD_ALIGN'
 },
 source_grounding: enhancedRule?.source_grounding ? {
 extraction_text: enhancedRule.source_grounding.extraction_text,
 source_section: enhancedRule.source_grounding.source_section,
 highlighted_spans: enhancedRule.source_grounding.highlighted_spans,
 semantic_confidence: enhancedRule.source_grounding.confidence
 } : undefined
 };

 results.push(enhancedResult);
 }
 }

 console.log(`Generated ${results.length} semantic compliance results for ${formerCouncilArea}`);
 return results;
 }

 /**
 * Find enhanced rule metadata for additional context
 */
 private findEnhancedRuleMetadata(ruleId: string, processedData: ProcessedSetbackData): any | null {
 console.log(` findEnhancedRuleMetadata called for rule: ${ruleId}`);
 try {
 const fs = require('fs');
 const path = require('path');
 
 // Get the area from processedData to load the correct unified file
 const area = processedData.area.toLowerCase();
 const unifiedFile = path.join(process.cwd(), 'public', 'regulatory-data', 'unified', `${area}_unified.json`);
 
 if (fs.existsSync(unifiedFile)) {
 const unifiedData = JSON.parse(fs.readFileSync(unifiedFile, 'utf8'));
 
 // Find matching source grounding based on rule type
 if (ruleId.includes('REAR_SETBACK') || ruleId.includes('rear_setback')) {
 const rearGrounding = unifiedData.source_groundings?.find((grounding: any) => 
 grounding.extraction_text.toLowerCase().includes('rear') && 
 grounding.extraction_text.toLowerCase().includes('setback')
 );
 
 if (rearGrounding) {
 return {
 overall_confidence: rearGrounding.confidence || 0.9,
 rule_classification: {
 tier: 1,
 enforcement_level: 'MANDATORY',
 compliance_message_type: 'MUST_COMPLY'
 },
 source_grounding: {
 extraction_text: rearGrounding.extraction_text,
 source_section: rearGrounding.source_location,
 highlighted_spans: [[0, rearGrounding.extraction_text.length]],
 confidence: rearGrounding.confidence || 0.9
 }
 };
 }
 }
 
 if (ruleId.includes('FRONT_SETBACK') || ruleId.includes('front_setback')) {
 const frontGrounding = unifiedData.source_groundings?.find((grounding: any) => 
 grounding.extraction_text.toLowerCase().includes('front') && 
 grounding.extraction_text.toLowerCase().includes('setback')
 );
 
 if (frontGrounding) {
 return {
 overall_confidence: frontGrounding.confidence || 0.9,
 rule_classification: {
 tier: 1,
 enforcement_level: 'MANDATORY',
 compliance_message_type: 'MUST_COMPLY'
 },
 source_grounding: {
 extraction_text: frontGrounding.extraction_text,
 source_section: frontGrounding.source_location,
 highlighted_spans: [[0, frontGrounding.extraction_text.length]],
 confidence: frontGrounding.confidence || 0.9
 }
 };
 }
 }
 
 if (ruleId.includes('SIDE_SETBACK') || ruleId.includes('side_setback')) {
 const sideGrounding = unifiedData.source_groundings?.find((grounding: any) => 
 grounding.extraction_text.toLowerCase().includes('side') && 
 grounding.extraction_text.toLowerCase().includes('setback')
 );
 
 if (sideGrounding) {
 return {
 overall_confidence: sideGrounding.confidence || 0.9,
 rule_classification: {
 tier: 1,
 enforcement_level: 'MANDATORY',
 compliance_message_type: 'MUST_COMPLY'
 },
 source_grounding: {
 extraction_text: sideGrounding.extraction_text,
 source_section: sideGrounding.source_location,
 highlighted_spans: [[0, sideGrounding.extraction_text.length]],
 confidence: sideGrounding.confidence || 0.9
 }
 };
 }
 }
 }
 } catch (error) {
 console.log(`Could not load enhanced rule metadata for ${ruleId}: ${error.message}`);
 }

 return null;
 }

 /**
 * Map semantic confidence scores to our standard levels
 */
 private mapSemanticConfidence(semanticConfidence: number): 'HIGH' | 'MEDIUM' | 'LOW' {
 if (semanticConfidence >= 0.9) return 'HIGH';
 if (semanticConfidence >= 0.7) return 'MEDIUM';
 return 'LOW';
 }

 /**
 * Generate enhanced compliance summary with source authority
 */
 generateComplianceSummary(results: EnhancedComplianceResult[]): {
 overall_compliant: boolean;
 total_rules_checked: number;
 non_compliant_rules: number;
 high_priority_issues: EnhancedComplianceResult[];
 source_authority_summary: {
 semantic_rules: number;
 manual_rules: number;
 high_confidence_rules: number;
 };
 next_steps: string[];
 } {
 const nonCompliantResults = results.filter(r => !r.compliant);
 const highPriorityIssues = nonCompliantResults.filter(r => 
 r.rule_classification?.tier === 1 || r.confidence === 'HIGH'
 );

 const sourceAuthority = {
 semantic_rules: results.filter(r => r.processing_method === 'semantic').length,
 manual_rules: results.filter(r => r.processing_method === 'manual').length,
 high_confidence_rules: results.filter(r => r.confidence === 'HIGH').length
 };

 const nextSteps: string[] = [];
 if (highPriorityIssues.length > 0) {
 nextSteps.push(`Address ${highPriorityIssues.length} high-priority compliance issues`);
 }
 if (nonCompliantResults.some(r => r.processing_method === 'semantic')) {
 nextSteps.push('Review semantic rule interpretations with planning consultant');
 }
 if (sourceAuthority.semantic_rules > 0) {
 nextSteps.push('Reference source documents for regulatory authority citations');
 }

 return {
 overall_compliant: nonCompliantResults.length === 0,
 total_rules_checked: results.length,
 non_compliant_rules: nonCompliantResults.length,
 high_priority_issues: highPriorityIssues,
 source_authority_summary: sourceAuthority,
 next_steps: nextSteps
 };
 }

 /**
 * Set real regulatory text from LightRAG storage
 */
 private async setRegulatoryText(
 result: EnhancedComplianceResult, 
 formerCouncilArea?: string
 ): Promise<EnhancedComplianceResult> {
 console.log(` setRegulatoryText called for ${result.requirement_type} in ${formerCouncilArea}`);
 try {
 let regulatoryText: string | null = null;
 let hasActualRegulatoryText = false;

 // Determine the type of requirement and get appropriate regulatory text
 switch (result.requirement_type) {
 case 'height':
 case 'max_height':
 console.log(` Retrieving height regulatory text...`);
 const heightMatch = await this.regulatoryTextRetriever.getHeightRegulatoryText();
 console.log(` Height result:`, heightMatch);
 if (heightMatch) {
 regulatoryText = heightMatch.text;
 hasActualRegulatoryText = true;
 }
 break;

 case 'fsr':
 case 'max_fsr':
 case 'floor_space_ratio':
 console.log(` Retrieving FSR regulatory text...`);
 const fsrMatch = await this.regulatoryTextRetriever.getFSRRegulatoryText();
 console.log(` FSR result:`, fsrMatch);
 if (fsrMatch) {
 regulatoryText = fsrMatch.text;
 hasActualRegulatoryText = true;
 }
 break;

 case 'front_setback':
 if (formerCouncilArea) {
 const frontSetbackMatch = await this.regulatoryTextRetriever.getSetbackRegulatoryText('front', formerCouncilArea);
 if (frontSetbackMatch) {
 regulatoryText = frontSetbackMatch.text;
 hasActualRegulatoryText = true;
 }
 }
 break;

 case 'side_setback':
 if (formerCouncilArea) {
 const sideSetbackMatch = await this.regulatoryTextRetriever.getSetbackRegulatoryText('side', formerCouncilArea);
 if (sideSetbackMatch) {
 regulatoryText = sideSetbackMatch.text;
 hasActualRegulatoryText = true;
 }
 }
 break;

 case 'rear_setback':
 if (formerCouncilArea) {
 const rearSetbackMatch = await this.regulatoryTextRetriever.getSetbackRegulatoryText('rear', formerCouncilArea);
 if (rearSetbackMatch) {
 regulatoryText = rearSetbackMatch.text;
 hasActualRegulatoryText = true;
 }
 }
 break;
 }

 // Return result with ONLY real regulatory text or null
 console.log(` Final regulatory text for ${result.requirement_type}: "${regulatoryText}" (has_actual: ${hasActualRegulatoryText})`);
 return {
 ...result,
 regulatory_text: regulatoryText, // Only real text, no fallbacks
 has_actual_regulatory_text: hasActualRegulatoryText
 };

 } catch (error) {
 console.warn(`Failed to get regulatory text for ${result.requirement_type}:`, error);
 return {
 ...result,
 regulatory_text: null, // No fake text
 has_actual_regulatory_text: false
 };
 }
 }
}