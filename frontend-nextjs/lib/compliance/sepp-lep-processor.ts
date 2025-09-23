// lib/compliance/sepp-lep-processor.ts
import { DatabaseClient } from '@/lib/database/client';
// Temporary interface definition - TODO: Move to shared types
interface NSWPlanningAPILayer {
 layerName: string;
 results?: any[];
}

export interface SEPPProvision {
 sepp_name: string;
 provision_type: 'climate_zone' | 'thermal_energy' | 'water_use' | 'transport_infrastructure';
 applicable_value: string;
 authority_level: 'SEPP' | 'LEP' | 'DCP';
 legal_precedence: number; // 1=highest, 4=lowest
 provision_text: string;
 document_id: string;
 confidence_score: number;
}

export interface LEPProvision {
 lep_name: string;
 clause_reference: string;
 provision_type: 'zoning' | 'height' | 'fsr' | 'lot_size' | 'setback' | 'heritage';
 applicable_value: string;
 authority_level: 'LEP';
 legal_precedence: number;
 provision_text: string;
 document_id: string;
 confidence_score: number;
}

export interface HierarchicalComplianceResult {
 controlling_authority: 'SEPP' | 'LEP' | 'DCP';
 applicable_provision: SEPPProvision | LEPProvision;
 overridden_provisions: Array<SEPPProvision | LEPProvision>;
 conflict_resolution_method: 'sepp_override' | 'lep_default' | 'most_restrictive';
 compliance_value: string | number;
 legal_justification: string;
 audit_trail: string[];
}

export class SEPPLEPProcessor {
 private dbClient: DatabaseClient;

 constructor(dbPath?: string) {
 this.dbClient = new DatabaseClient();
 }

 /**
 * Process NSW Planning API layers to extract SEPP provisions
 */
 processSEPPProvisions(nswApiLayers: NSWPlanningAPILayer[]): SEPPProvision[] {
 console.log('[SEPP Processor] Processing NSW API SEPP provisions');
 
 const seppProvisions: SEPPProvision[] = [];
 
 // Find Special Provisions layer containing SEPPs
 const specialProvisionsLayer = nswApiLayers.find(
 layer => layer.layerName === 'Special Provisions'
 );
 
 if (!specialProvisionsLayer?.results) {
 console.log('[SEPP Processor] No Special Provisions layer found');
 return seppProvisions;
 }
 
 for (const result of specialProvisionsLayer.results) {
 if (result['EPI Type'] === 'SEPP') {
 let provisionType: SEPPProvision['provision_type'] = 'transport_infrastructure';
 
 // Determine provision type from SEPP name
 if (result['EPI Name']?.includes('Sustainable Buildings')) {
 if (result.title?.includes('Climate')) {
 provisionType = 'climate_zone';
 } else if (result.title?.includes('Water')) {
 provisionType = 'water_use';
 }
 } else if (result['EPI Name']?.includes('Transport and Infrastructure')) {
 provisionType = 'transport_infrastructure';
 }
 
 seppProvisions.push({
 sepp_name: result['EPI Name'] || 'Unknown SEPP',
 provision_type: provisionType,
 applicable_value: result.Class || result.Label || 'Not specified',
 authority_level: 'SEPP',
 legal_precedence: 1, // SEPPs have highest precedence
 provision_text: result.title || 'SEPP provision',
 document_id: result['EPI Name'] || 'SEPP',
 confidence_score: 1.0 // NSW API is authoritative
 });
 }
 }
 
 console.log(`[SEPP Processor] Found ${seppProvisions.length} SEPP provisions`);
 return seppProvisions;
 }

 /**
 * Process NSW Planning API layers to extract LEP provisions
 */
 processLEPProvisions(nswApiLayers: NSWPlanningAPILayer[]): LEPProvision[] {
 console.log('[SEPP Processor] Processing NSW API LEP provisions');
 
 const lepProvisions: LEPProvision[] = [];
 
 // Process each relevant layer
 const lepLayers = [
 { name: 'Land Zoning Map', type: 'zoning' as const },
 { name: 'Height of Buildings Map', type: 'height' as const },
 { name: 'Floor Space Ratio Map', type: 'fsr' as const },
 { name: 'Lot Size Map', type: 'lot_size' as const },
 { name: 'Heritage Map', type: 'heritage' as const }
 ];
 
 for (const layerConfig of lepLayers) {
 const layer = nswApiLayers.find(l => l.layerName === layerConfig.name);
 if (!layer?.results) continue;
 
 for (const result of layer.results) {
 if (result['EPI Type'] === 'LEP') {
 let applicableValue = '';
 
 // Extract the relevant value based on layer type
 switch (layerConfig.type) {
 case 'zoning':
 applicableValue = result.Zone || result['Land Use'] || '';
 break;
 case 'height':
 applicableValue = result['Maximum Building Height'] || result['Height Limit'] || '';
 break;
 case 'fsr':
 applicableValue = result['Floor Space Ratio'] || '';
 break;
 case 'lot_size':
 applicableValue = result['Lot Size'] || '';
 break;
 case 'heritage':
 applicableValue = result['Heritage Item'] || result.title || '';
 break;
 }
 
 lepProvisions.push({
 lep_name: result['EPI Name'] || 'Unknown LEP',
 clause_reference: result['Legislative Clause'] || 'Not specified',
 provision_type: layerConfig.type,
 applicable_value: applicableValue,
 authority_level: 'LEP',
 legal_precedence: 2, // LEPs have second precedence after SEPPs
 provision_text: result.title || 'LEP provision',
 document_id: result['EPI Name'] || 'LEP',
 confidence_score: 1.0 // NSW API is authoritative
 });
 }
 }
 }
 
 console.log(`[SEPP Processor] Found ${lepProvisions.length} LEP provisions`);
 return lepProvisions;
 }

 /**
 * Query database for SEPP-LEP override relationships
 */
 async getDatabaseSEPPOverrides(zone: string): Promise<Array<SEPPProvision | LEPProvision>> {
 console.log(`[SEPP Processor] Querying database SEPP overrides for zone: ${zone}`);
 
 const overrides: Array<SEPPProvision | LEPProvision> = [];
 
 try {
 // Query the sepp_lep_overrides table
 const seppOverrides = await this.dbClient.getHierarchicalSetbackControls(zone);
 
 for (const override of seppOverrides) {
 if (override.authority_level === 'SEPP') {
 overrides.push({
 sepp_name: override.document_id || 'Database SEPP',
 provision_type: 'transport_infrastructure', // Default, could be refined
 applicable_value: override.value_text || 'Not specified',
 authority_level: 'SEPP',
 legal_precedence: override.legal_precedence || 1,
 provision_text: override.provision_text || 'SEPP override provision',
 document_id: override.document_id || 'SEPP',
 confidence_score: override.confidence_score || 0.8
 });
 } else if (override.authority_level === 'LEP') {
 overrides.push({
 lep_name: override.document_id || 'Database LEP',
 clause_reference: 'Database derived',
 provision_type: 'setback', // Most database overrides are setback related
 applicable_value: override.value_text || 'Not specified',
 authority_level: 'LEP',
 legal_precedence: override.legal_precedence || 2,
 provision_text: override.provision_text || 'LEP provision',
 document_id: override.document_id || 'LEP',
 confidence_score: override.confidence_score || 0.8
 });
 }
 }
 
 } catch (error) {
 console.error('[SEPP Processor] Database query error:', error);
 }
 
 console.log(`[SEPP Processor] Found ${overrides.length} database overrides`);
 return overrides;
 }

 /**
 * Resolve hierarchical conflicts between SEPP and LEP provisions
 */
 resolveHierarchicalCompliance(
 seppProvisions: SEPPProvision[],
 lepProvisions: LEPProvision[],
 databaseOverrides: Array<SEPPProvision | LEPProvision>,
 requestedProvisionType: string
 ): HierarchicalComplianceResult {
 console.log(`[SEPP Processor] Resolving hierarchical compliance for: ${requestedProvisionType}`);
 
 const auditTrail: string[] = [];
 auditTrail.push(`Hierarchical compliance assessment initiated: ${new Date().toISOString()}`);
 auditTrail.push(`Provision type: ${requestedProvisionType}`);
 auditTrail.push(`SEPP provisions: ${seppProvisions.length}`);
 auditTrail.push(`LEP provisions: ${lepProvisions.length}`);
 auditTrail.push(`Database overrides: ${databaseOverrides.length}`);
 
 // Step 1: Check if any SEPP provisions apply to this provision type
 const applicableSEPPs = seppProvisions.filter(sepp => 
 sepp.provision_type.includes(requestedProvisionType) ||
 sepp.provision_text.toLowerCase().includes(requestedProvisionType.toLowerCase())
 );
 
 // Step 2: Check if any LEP provisions apply
 const applicableLEPs = lepProvisions.filter(lep => 
 lep.provision_type.includes(requestedProvisionType) ||
 lep.provision_text.toLowerCase().includes(requestedProvisionType.toLowerCase())
 );
 
 // Step 3: Check database overrides
 const applicableOverrides = databaseOverrides.filter(override =>
 override.provision_text.toLowerCase().includes(requestedProvisionType.toLowerCase())
 );
 
 auditTrail.push(`Applicable SEPPs: ${applicableSEPPs.length}`);
 auditTrail.push(`Applicable LEPs: ${applicableLEPs.length}`);
 auditTrail.push(`Applicable overrides: ${applicableOverrides.length}`);
 
 // Step 4: Apply NSW planning hierarchy (SEPP > LEP > DCP)
 if (applicableSEPPs.length > 0) {
 // SEPP takes precedence
 const controllingSEPP = applicableSEPPs.reduce((highest, current) =>
 current.legal_precedence < highest.legal_precedence ? current : highest
 );
 
 auditTrail.push(`SEPP control applies: ${controllingSEPP.sepp_name}`);
 auditTrail.push(`Overrides ${applicableLEPs.length} LEP provisions`);
 
 return {
 controlling_authority: 'SEPP',
 applicable_provision: controllingSEPP,
 overridden_provisions: [...applicableLEPs, ...applicableOverrides.filter(o => o.authority_level !== 'SEPP')],
 conflict_resolution_method: 'sepp_override',
 compliance_value: controllingSEPP.applicable_value,
 legal_justification: `SEPP ${controllingSEPP.sepp_name} takes precedence over LEP provisions under NSW Environmental Planning and Assessment Act 1979`,
 audit_trail: auditTrail
 };
 }
 
 if (applicableLEPs.length > 0) {
 // LEP applies in absence of SEPP
 const controllingLEP = applicableLEPs.reduce((highest, current) =>
 current.legal_precedence < highest.legal_precedence ? current : highest
 );
 
 auditTrail.push(`LEP control applies: ${controllingLEP.lep_name}`);
 auditTrail.push(`No overriding SEPP provisions found`);
 
 return {
 controlling_authority: 'LEP',
 applicable_provision: controllingLEP,
 overridden_provisions: applicableOverrides.filter(o => o.authority_level === 'DCP'),
 conflict_resolution_method: 'lep_default',
 compliance_value: controllingLEP.applicable_value,
 legal_justification: `LEP ${controllingLEP.lep_name} applies as principal environmental planning instrument for the area`,
 audit_trail: auditTrail
 };
 }
 
 // Step 5: Fall back to most restrictive database override
 if (applicableOverrides.length > 0) {
 const controllingOverride = applicableOverrides.reduce((highest, current) =>
 current.confidence_score > highest.confidence_score ? current : highest
 );
 
 auditTrail.push(`Database override applies: ${controllingOverride.document_id}`);
 auditTrail.push(`No SEPP or LEP provisions found - using database intelligence`);
 
 return {
 controlling_authority: controllingOverride.authority_level as 'SEPP' | 'LEP' | 'DCP',
 applicable_provision: controllingOverride,
 overridden_provisions: [],
 conflict_resolution_method: 'most_restrictive',
 compliance_value: controllingOverride.applicable_value,
 legal_justification: `Database-derived provision applied in absence of direct SEPP/LEP requirements`,
 audit_trail: auditTrail
 };
 }
 
 // Step 6: No applicable provisions found
 auditTrail.push(`No applicable provisions found for ${requestedProvisionType}`);
 
 throw new Error(`No hierarchical compliance provisions found for ${requestedProvisionType}. Audit trail: ${auditTrail.join('; ')}`);
 }

 /**
 * Main method to process full hierarchical compliance
 */
 async processHierarchicalCompliance(
 nswApiLayers: NSWPlanningAPILayer[],
 zone: string,
 requestedProvisionType: string
 ): Promise<HierarchicalComplianceResult> {
 console.log(`[SEPP Processor] Processing hierarchical compliance for ${zone}:${requestedProvisionType}`);
 
 // Step 1: Extract SEPP provisions from NSW API
 const seppProvisions = this.processSEPPProvisions(nswApiLayers);
 
 // Step 2: Extract LEP provisions from NSW API 
 const lepProvisions = this.processLEPProvisions(nswApiLayers);
 
 // Step 3: Get database SEPP/LEP overrides
 const databaseOverrides = await this.getDatabaseSEPPOverrides(zone);
 
 // Step 4: Resolve hierarchical conflicts
 const result = this.resolveHierarchicalCompliance(
 seppProvisions,
 lepProvisions, 
 databaseOverrides,
 requestedProvisionType
 );
 
 console.log(`[SEPP Processor] Hierarchical compliance resolved: ${result.controlling_authority} authority`);
 
 return result;
 }

 close() {
 this.dbClient.close();
 }
}