/**
 * DCP Resolver Service
 * Integrates planning portal API with spatial mapping to determine correct DCP
 */

import { getCompletePlanningData, extractKeyPlanningInfo } from './planning-portal-api';
import { determineFormerCouncilAreaEnhanced, Polygon } from '../spatial/geometry-utils';

export interface DCPResolution {
 address: string;
 formerCouncilArea: string | null;
 determinationMethod: 'spatial' | 'address' | 'failed';
 lgaName?: string;
 zone?: string;
 planningData?: {
 zone: string;
 landUse: string;
 maxHeight?: number;
 fsr?: number;
 minLotSize?: number;
 };
 confidence: 'high' | 'medium' | 'low';
}

/**
 * Complete DCP resolution using planning portal API + spatial mapping
 */
export async function resolveDCPForAddress(address: string): Promise<DCPResolution> {
 try {
 // Step 1: Get complete planning data from portal
 console.log(`Resolving DCP for address: ${address}`);
 const planningData = await getCompletePlanningData(address);
 
 if (!planningData) {
 return {
 address,
 formerCouncilArea: null,
 determinationMethod: 'failed',
 confidence: 'low'
 };
 }
 
 // Step 2: Extract key planning info
 const planningInfo = extractKeyPlanningInfo(planningData.layers);
 console.log('Planning info extracted:', planningInfo);
 
 // Step 3: Verify this is Inner West LGA
 if (planningInfo.lgaName !== 'INNER WEST') {
 console.log(`Property is not in Inner West LGA (found: ${planningInfo.lgaName})`);
 return {
 address,
 formerCouncilArea: null,
 determinationMethod: 'failed',
 planningData: planningInfo,
 confidence: 'low'
 };
 }
 
 // Step 4: Use spatial geometry to determine former council area
 let formerCouncilArea: string | null = null;
 let determinationMethod: 'spatial' | 'address' = 'spatial';
 let confidence: 'high' | 'medium' | 'low' = 'high';
 
 if (planningData.geometry && planningData.geometry.rings) {
 // Convert geometry format for our utilities
 const polygon: Polygon = {
 rings: planningData.geometry.rings
 };
 
 formerCouncilArea = determineFormerCouncilAreaEnhanced(polygon, address);
 
 if (!formerCouncilArea) {
 // Fallback to address parsing
 formerCouncilArea = determineFormerCouncilAreaEnhanced(undefined, address);
 determinationMethod = 'address';
 confidence = 'medium';
 }
 } else {
 // No geometry available, use address parsing
 formerCouncilArea = determineFormerCouncilAreaEnhanced(undefined, address);
 determinationMethod = 'address';
 confidence = 'medium';
 }
 
 if (!formerCouncilArea) {
 confidence = 'low';
 }
 
 console.log(`Determined former council area: ${formerCouncilArea} (method: ${determinationMethod})`);
 
 return {
 address,
 formerCouncilArea,
 determinationMethod,
 lgaName: planningInfo.lgaName,
 zone: planningInfo.zone,
 planningData: planningInfo,
 confidence
 };
 
 } catch (error) {
 console.error('DCP resolution failed:', error);
 return {
 address,
 formerCouncilArea: null,
 determinationMethod: 'failed',
 confidence: 'low'
 };
 }
}

/**
 * Get DCP rules for resolved council area
 */
export async function getDCPRules(resolution: DCPResolution) {
 if (!resolution.formerCouncilArea) {
 return null;
 }
 
 try {
 // This would integrate with the processed DCP data
 const response = await fetch(`/api/compliance/setbacks?address=${encodeURIComponent(resolution.address)}`);
 
 if (!response.ok) {
 throw new Error(`API request failed: ${response.status}`);
 }
 
 return await response.json();
 } catch (error) {
 console.error('Failed to get DCP rules:', error);
 return null;
 }
}

/**
 * Complete workflow: resolve DCP and get rules
 */
export async function getCompleteComplianceData(address: string) {
 const resolution = await resolveDCPForAddress(address);
 
 if (!resolution.formerCouncilArea) {
 return {
 resolution,
 rules: null,
 error: 'Could not determine which DCP applies to this address'
 };
 }
 
 const rules = await getDCPRules(resolution);
 
 return {
 resolution,
 rules,
 error: rules ? null : 'DCP rules not available'
 };
}