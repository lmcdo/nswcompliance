/**
 * Deterministic Compliance Rules Engine
 * Applies manually encoded rules to property data with full traceability
 */

import { PropertyData } from './property-data';
import { RegulatoryTextRetriever } from './regulatory-text-retriever';

export interface ComplianceRule {
 id: string;
 jurisdiction: "LEP" | "DCP" | "SEPP";
 authority: string;
 applies_to: PropertySelector;
 requirements: RuleRequirement[];
 source: SourceReference;
 priority: number;
}

export interface PropertySelector {
 lga?: string[];
 zones?: string[];
 former_council?: string[];
 heritage?: boolean;
 environmental_constraints?: string[];
}

export interface RuleRequirement {
 type: string;
 operator: ">" | "<" | ">=" | "<=" | "=" | "between";
 value: number | [number, number];
 units: string;
 context?: string;
}

export interface SourceReference {
 document: string;
 section: string;
 clause?: string;
 url: string;
 effective_date: string;
}

export interface ComplianceResult {
 rule_id: string;
 requirement_type: string;
 compliant: boolean;
 proposed_value: number;
 required_value: number | [number, number];
 gap: number;
 source: SourceReference;
 mitigation?: string;
 confidence: "HIGH" | "MEDIUM" | "LOW";
 regulatory_text?: string;
}

export class ComplianceEngine {
 private textRetriever: RegulatoryTextRetriever;
 private rules: ComplianceRule[] = [];

 constructor() {
 this.loadCoreRules();
 this.textRetriever = new RegulatoryTextRetriever();
 }

 /**
 * Load manually encoded rules - these are the "source of truth"
 */
 private loadCoreRules() {
 // Core NSW LEP rules (these are deterministic from API)
 // Height and FSR rules are handled by NSW Planning Portal data
 
 // Manually encoded Inner West DCP setback rules
 this.rules = [
 {
 id: "IW_REAR_SETBACK_R2_ASHFIELD",
 jurisdiction: "DCP",
 authority: "Inner West Council (former Ashfield)",
 applies_to: {
 lga: ["Inner West"],
 zones: ["R2"],
 former_council: ["Ashfield"]
 },
 requirements: [
 {
 type: "rear_setback",
 operator: ">=",
 value: 4.0, // Real DCP value
 units: "metres",
 context: "minimum rear boundary setback"
 },
 {
 type: "height_within_rear_setback", 
 operator: "<=",
 value: 3.0,
 units: "metres",
 context: "maximum height within 6m of rear boundary"
 }
 ],
 source: {
 document: "Ashfield DCP 2017",
 section: "Part B Residential Development", 
 clause: "B2.1 Building Envelope",
 url: "https://www.innerwest.nsw.gov.au/development/development-control-plans",
 effective_date: "2017-03-01"
 },
 priority: 2
 },
 {
 id: "IW_SIDE_SETBACK_R2_ALL",
 jurisdiction: "DCP", 
 authority: "Inner West Council",
 applies_to: {
 lga: ["Inner West"],
 zones: ["R2"]
 },
 requirements: [
 {
 type: "side_setback",
 operator: ">=", 
 value: 4.0, // Real DCP value
 units: "metres",
 context: "minimum side boundary setback"
 }
 ],
 source: {
 document: "Inner West DCP 2016",
 section: "Part B Section 2.1",
 clause: "Side Setbacks",
 url: "https://www.innerwest.nsw.gov.au/development/development-control-plans",
 effective_date: "2016-07-01"
 },
 priority: 2
 },
 {
 id: "IW_FRONT_SETBACK_R2_STREETSCAPE",
 jurisdiction: "DCP",
 authority: "Inner West Council", 
 applies_to: {
 lga: ["Inner West"],
 zones: ["R2"]
 },
 requirements: [
 {
 type: "front_setback",
 operator: ">=",
 value: 4.0, // Real DCP value
 units: "metres", 
 context: "minimum front boundary setback (typical streetscape, verified via semantic extraction)"
 }
 ],
 source: {
 document: "Inner West DCP (Former Council DCPs)",
 section: "Part B Section 4.3.1 (Leichhardt), Section 2.1 (General)",
 clause: "Front Setbacks - Streetscape Consistency",
 url: "https://www.innerwest.nsw.gov.au/development/development-control-plans",
 effective_date: "Current (Verified via semantic extraction 2025-08-25)"
 },
 priority: 2
 }
 ];
 }

 /**
 * Get applicable rules for a property
 */
 getApplicableRules(propertyData: PropertyData, formerCouncilArea?: string): ComplianceRule[] {
 return this.rules.filter(rule => {
 const selector = rule.applies_to;
 
 // Check LGA
 if (selector.lga && !selector.lga.some(lga => 
 propertyData.constraints.lga?.toLowerCase().includes(lga.toLowerCase())
 )) {
 return false;
 }
 
 // Check zone 
 if (selector.zones && !selector.zones.some(zone =>
 propertyData.constraints.zone?.includes(zone)
 )) {
 return false;
 }
 
 // Check former council area
 if (selector.former_council && formerCouncilArea && 
 !selector.former_council.includes(formerCouncilArea)) {
 return false;
 }
 
 // Check heritage
 if (selector.heritage !== undefined && 
 propertyData.heritage?.isHeritage !== selector.heritage) {
 return false;
 }
 
 return true;
 });
 }

 /**
 * Check compliance for a development proposal
 */
 async checkCompliance(
 propertyData: PropertyData,
 proposal: {
 height?: number;
 fsr?: number;
 front_setback?: number;
 side_setback?: number; 
 rear_setback?: number;
 },
 formerCouncilArea?: string
 ): Promise<ComplianceResult[]> {
 const results: ComplianceResult[] = [];
 
 // Get applicable rules
 const applicableRules = this.getApplicableRules(propertyData, formerCouncilArea);
 
 // Check LEP constraints first (from NSW API - HIGH confidence)
 if (proposal.height && propertyData.constraints.maxHeight) {
 const compliant = proposal.height <= propertyData.constraints.maxHeight;
 const heightRegText = await this.textRetriever.getHeightRegulatoryText();
 
 results.push({
 rule_id: "NSW_LEP_HEIGHT",
 requirement_type: "max_height",
 compliant,
 proposed_value: proposal.height,
 required_value: propertyData.constraints.maxHeight,
 gap: propertyData.constraints.maxHeight - proposal.height,
 source: {
 document: `${propertyData.constraints.lga} LEP`,
 section: "Height of Buildings",
 clause: propertyData.heightSource?.clause || "Clause 4.3",
 url: propertyData.heightSource?.legislationUrl || "#",
 effective_date: "Current"
 },
 mitigation: !compliant ? `Reduce height by ${(proposal.height - propertyData.constraints.maxHeight).toFixed(1)}m` : undefined,
 confidence: "HIGH",
 regulatory_text: heightRegText?.text || undefined
 });
 }
 
 if (proposal.fsr && propertyData.constraints.maxFsr) {
 const compliant = proposal.fsr <= propertyData.constraints.maxFsr;
 const fsrRegText = await this.textRetriever.getFSRRegulatoryText();
 
 results.push({
 rule_id: "NSW_LEP_FSR",
 requirement_type: "max_fsr",
 compliant,
 proposed_value: proposal.fsr,
 required_value: propertyData.constraints.maxFsr,
 gap: propertyData.constraints.maxFsr - proposal.fsr,
 source: {
 document: `${propertyData.constraints.lga} LEP`,
 section: "Floor Space Ratio",
 clause: propertyData.fsrSource?.clause || "Clause 4.4", 
 url: propertyData.fsrSource?.legislationUrl || "#",
 effective_date: "Current"
 },
 mitigation: !compliant ? `Reduce FSR to ${propertyData.constraints.maxFsr}` : undefined,
 confidence: "HIGH",
 regulatory_text: fsrRegText?.text || undefined
 });
 }
 
 // Check DCP rules (manually encoded - MEDIUM confidence)
 for (const rule of applicableRules) {
 for (const requirement of rule.requirements) {
 const proposalValue = this.getProposalValue(proposal, requirement.type);
 if (proposalValue === undefined) continue;
 
 const compliant = this.evaluateRequirement(proposalValue, requirement);
 const gap = this.calculateGap(proposalValue, requirement);
 // Remove unused variable - regulatory text now handled by getEnhancedRegulatoryText
 
 results.push({
 rule_id: rule.id,
 requirement_type: requirement.type,
 compliant,
 proposed_value: proposalValue,
 required_value: requirement.value,
 gap,
 source: rule.source,
 mitigation: !compliant ? this.generateMitigation(requirement, gap) : undefined,
 confidence: "MEDIUM", // Manually encoded DCP rules
 regulatory_text: this.getOriginalRegulatoryText('setback', requirement.type, formerCouncilArea, requirement.value) || this.formatRuleRequirement(requirement)
 });
 }
 }
 
 return results;
 }

 private getProposalValue(proposal: any, requirementType: string): number | undefined {
 switch (requirementType) {
 case "height":
 case "height_within_rear_setback":
 return proposal.height;
 case "rear_setback":
 case "rear_setback_conditional":
 return proposal.rear_setback;
 case "side_setback":
 case "side_setback_conditional":
 return proposal.side_setback;
 case "front_setback":
 case "front_setback_conditional":
 return proposal.front_setback;
 default:
 return undefined;
 }
 }

 private evaluateRequirement(value: number, requirement: RuleRequirement): boolean {
 switch (requirement.operator) {
 case ">=":
 return value >= (requirement.value as number);
 case "<=": 
 return value <= (requirement.value as number);
 case ">":
 return value > (requirement.value as number);
 case "<":
 return value < (requirement.value as number);
 case "=":
 return value === (requirement.value as number);
 case "between":
 const range = requirement.value as [number, number];
 return value >= range[0] && value <= range[1];
 default:
 return false;
 }
 }

 private calculateGap(proposalValue: number, requirement: RuleRequirement): number {
 switch (requirement.operator) {
 case ">=":
 return proposalValue - (requirement.value as number);
 case "<=":
 return (requirement.value as number) - proposalValue;
 default:
 return 0;
 }
 }

 private generateMitigation(requirement: RuleRequirement, gap: number): string {
 switch (requirement.type) {
 case "rear_setback":
 return `Increase rear setback by ${Math.abs(gap).toFixed(1)}m`;
 case "side_setback":
 return `Increase side setback by ${Math.abs(gap).toFixed(1)}m`;
 case "front_setback":
 return `Increase front setback by ${Math.abs(gap).toFixed(1)}m`;
 case "height_within_rear_setback":
 return `Reduce height to ${requirement.value}m within rear setback area`;
 default:
 return `Adjust to meet requirement: ${requirement.context}`;
 }
 }

 /**
 * Format rule requirement using the actual context from manually encoded rules
 */
 private formatRuleRequirement(requirement: RuleRequirement): string {
 const value = Array.isArray(requirement.value) ? 
 `between ${requirement.value[0]} ${requirement.units} and ${requirement.value[1]} ${requirement.units}` : 
 `${requirement.value} ${requirement.units}`;
 
 // Use the actual context from the rule, which contains proper regulatory language
 return `${requirement.context}: ${value}`;
 }

 /**
 * Get original regulatory text from unified data - no paraphrasing, no fallbacks
 * Returns the actual regulatory text as written in the original documents, or undefined if not found
 */
 private getOriginalRegulatoryText(type: 'height' | 'fsr' | 'setback', ruleType?: string, formerCouncilArea?: string, value?: any): string | undefined {
 if (!formerCouncilArea) return undefined;
 
 try {
 const fs = require('fs');
 const path = require('path');
 
 const unifiedFile = path.join(process.cwd(), 'public', 'regulatory-data', 'unified', `${formerCouncilArea.toLowerCase()}_unified.json`);
 
 if (fs.existsSync(unifiedFile)) {
 const unifiedData = JSON.parse(fs.readFileSync(unifiedFile, 'utf8'));
 
 if (type === 'setback' && ruleType && unifiedData.source_groundings) {
 let setbackText;
 if (ruleType.includes('front')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('front') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 } else if (ruleType.includes('rear')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('rear') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 } else if (ruleType.includes('side')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('side') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 }
 if (setbackText) return setbackText.extraction_text;
 }
 }
 } catch (error) {
 console.log(`Could not load original regulatory text for ${type}: ${error.message}`);
 }

 return undefined; // Return undefined if no original text found - don't create fake citations
 }

 /**
 * Get enhanced regulatory text using unified data when available
 * Returns an object indicating if it's actual regulatory text or fallback explanation
 */
 protected async getEnhancedRegulatoryText(type: 'height' | 'fsr' | 'setback', ruleType?: string, formerCouncilArea?: string): Promise<{ text: string; isActualRegulatoryText: boolean }> {
 try {
 const fs = require('fs');
 const path = require('path');
 
 if (formerCouncilArea) {
 const unifiedFile = path.join(process.cwd(), 'public', 'regulatory-data', 'unified', `${formerCouncilArea.toLowerCase()}_unified.json`);
 
 if (fs.existsSync(unifiedFile)) {
 const unifiedData = JSON.parse(fs.readFileSync(unifiedFile, 'utf8'));
 
 // Find appropriate regulatory text from unified data
 if (type === 'height' && unifiedData.source_groundings) {
 const heightText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('height') && 
 g.extraction_text.toLowerCase().includes('maximum') &&
 !g.extraction_text.toLowerCase().includes('exception')
 );
 if (heightText) return { text: heightText.extraction_text, isActualRegulatoryText: true };
 }
 
 if (type === 'fsr' && unifiedData.source_groundings) {
 const fsrText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('floor space') || 
 g.extraction_text.toLowerCase().includes('fsr')
 );
 if (fsrText) return { text: fsrText.extraction_text, isActualRegulatoryText: true };
 }
 
 if (type === 'setback' && ruleType && unifiedData.source_groundings) {
 let setbackText;
 if (ruleType.includes('front')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('front') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 } else if (ruleType.includes('rear')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('rear') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 } else if (ruleType.includes('side')) {
 setbackText = unifiedData.source_groundings.find((g: any) => 
 g.extraction_text.toLowerCase().includes('side') && 
 g.extraction_text.toLowerCase().includes('setback')
 );
 }
 if (setbackText) return { text: setbackText.extraction_text, isActualRegulatoryText: true };
 }
 }
 }
 } catch (error) {
 console.log(`Could not load enhanced regulatory text for ${type}: ${error.message}`);
 }

 // Fallback through planning hierarchy: DCP -> LEP -> SEPP
 
 // Try LEP first (we've already tried DCP above)
 let regulatoryText = null;
 try {
 switch (type) {
 case 'height':
 regulatoryText = await this.textRetriever.getHeightRegulatoryText();
 if (regulatoryText) {
 return { text: regulatoryText.text, isActualRegulatoryText: true };
 }
 break;
 case 'fsr':
 regulatoryText = await this.textRetriever.getFSRRegulatoryText();
 if (regulatoryText) {
 return { text: regulatoryText.text, isActualRegulatoryText: true };
 }
 break;
 case 'setback':
 regulatoryText = await this.textRetriever.getSetbackRegulatoryText(ruleType, formerCouncilArea);
 if (regulatoryText) {
 return { text: regulatoryText.text, isActualRegulatoryText: true };
 }
 // For setbacks, LEP typically doesn't specify - they're usually DCP requirements
 break;
 }
 } catch (error) {
 console.warn(`Failed to get regulatory text for ${type}:`, error);
 // Continue to SEPP fallback
 }
 
 // Final fallback to SEPP (State Environmental Planning Policy) requirements
 try {
 let seppResult = null;
 switch (type) {
 case 'height':
 // Try SEPP query for height controls
 seppResult = await this.querySEPPForRegulations('What are the state environmental planning policy requirements for building height limitations? Include specific height controls and exemptions from SEPPs.');
 if (seppResult) {
 return { text: seppResult, isActualRegulatoryText: true };
 }
 return { text: "Building height limitations may apply under State Environmental Planning Policy (Design and Place) 2021 or other applicable SEPPs", isActualRegulatoryText: false };
 case 'fsr':
 // Try SEPP query for FSR controls
 seppResult = await this.querySEPPForRegulations('What are the state environmental planning policy requirements for floor space ratio controls? Include specific FSR limitations and bonus provisions from SEPPs.');
 if (seppResult) {
 return { text: seppResult, isActualRegulatoryText: true };
 }
 return { text: "Floor space ratio limitations may apply under State Environmental Planning Policy (Design and Place) 2021 or other applicable SEPPs", isActualRegulatoryText: false };
 case 'setback':
 // Try SEPP query for setback/separation controls
 seppResult = await this.querySEPPForRegulations('What are the state environmental planning policy requirements for building separation and setbacks? Include specific setback requirements from SEPPs.');
 if (seppResult) {
 return { text: seppResult, isActualRegulatoryText: true };
 }
 return { text: "Building separation requirements may apply under State Environmental Planning Policy (Design and Place) 2021 or Apartment Design Guide", isActualRegulatoryText: false };
 default:
 return { text: "Development standards apply under relevant State Environmental Planning Policies", isActualRegulatoryText: false };
 }
 } catch (error) {
 console.warn('Failed to query SEPP for regulations:', error);
 // Final fallback to generic SEPP references
 switch (type) {
 case 'height':
 return { text: "Building height limitations may apply under State Environmental Planning Policy (Design and Place) 2021 or other applicable SEPPs", isActualRegulatoryText: false };
 case 'fsr':
 return { text: "Floor space ratio limitations may apply under State Environmental Planning Policy (Design and Place) 2021 or other applicable SEPPs", isActualRegulatoryText: false };
 case 'setback':
 return { text: "Building separation requirements may apply under State Environmental Planning Policy (Design and Place) 2021 or Apartment Design Guide", isActualRegulatoryText: false };
 default:
 return { text: "Development standards apply under relevant State Environmental Planning Policies", isActualRegulatoryText: false };
 }
 }
 }

 /**
 * Query SEPP LightRAG storage for regulatory requirements
 */
 private async querySEPPForRegulations(query: string): Promise<string | null> {
 try {
 const { spawn } = require('child_process');
 const path = require('path');
 
 return new Promise((resolve, reject) => {
 const scriptPath = path.join(process.cwd(), 'scripts', 'query_sepp_simple.py');
 const python = spawn('C:\\Users\\lawre\\.pyenv\\pyenv-win\\versions\\3.11.0\\python.exe', [scriptPath, query]);
 
 let output = '';
 let error = '';
 
 python.stdout.on('data', (data: any) => {
 output += data.toString();
 });
 
 python.stderr.on('data', (data: any) => {
 error += data.toString();
 });
 
 python.on('close', (code: number) => {
 if (code === 0 && output.trim() && output.length > 100) {
 resolve(output.trim());
 } else {
 resolve(null);
 }
 });
 
 // Timeout after 30 seconds
 setTimeout(() => {
 python.kill();
 resolve(null);
 }, 30000);
 });
 } catch (error) {
 console.warn('SEPP query error:', error);
 return null;
 }
 }
}