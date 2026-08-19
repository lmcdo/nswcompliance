// lib/geometry/calculator.ts
import { DatabaseClient } from '@/lib/database/client';
// import { KGZoneExtractor, type KGSetbackRequirement } from '@/lib/compliance/kg-zone-extractor';
import type { LotGeometry } from '@/types/property';
import type { 
 SetbackResult, 
 BuildableAreaAnalysis,
 BoundaryLine,
 SetbackRequirement 
} from '@/types/setback';

interface Point {
 x: number;
 y: number;
}

import { scaleFactorForRing, usableRing } from './mercator';

// Helper functions for angle conversions.
// toRadians() was removed with the fixed-latitude constant that was its only
// caller; the Mercator correction now lives in ./mercator.
function toDegrees(radians: number): number {
 return radians * (180 / Math.PI);
}

export class PreciseSetbackCalculator {
 private db: DatabaseClient;

 // Web Mercator scale correction is per-lot, taken from the ring's own
 // latitude — see ./mercator. This class used to hold a single constant built
 // from -33.87 (Sydney), which measured a Tweed Heads lot ~9.8% small and a
 // Bega lot ~4.8% large against the surveyed area on title. Setbacks are
 // derived from these distances, so the error reached a customer-facing number.

 constructor() {
 this.db = new DatabaseClient();
 }

 async calculatePreciseSetbacks(
 lotGeometry: LotGeometry,
 propertyZone: string,
 lotArea: number
 ): Promise<SetbackResult[]> {
 console.log(`[Calculator] Starting setback calculation for zone: ${propertyZone}`);

 // Step 1: Process geometry into boundary lines
 const boundaries = this.processGeometryToBoundaries(lotGeometry);
 console.log(`[Calculator] Processed ${boundaries.length} boundary lines`);

 // Step 2: Get setback requirements from database
 const requirements = await this.getSetbackRequirements(propertyZone, lotArea);
 console.log(`[Calculator] Found ${requirements.length} setback requirements`);

 // Step 3: Apply requirements to each boundary
 const results: SetbackResult[] = [];

 for (const boundary of boundaries) {
 // Find applicable requirements for this boundary type (with flexible matching)
 const applicableRequirements = requirements.filter(req => {
 // Exact match first
 if (req.boundary_type === boundary.boundary_type) {
 return true;
 }
 
 // Flexible matching for side setbacks
 if (req.boundary_type === 'side' && 
 (boundary.boundary_type === 'side_left' || boundary.boundary_type === 'side_right')) {
 return true;
 }
 
 // General setbacks apply to all boundaries
 if (req.boundary_type === 'general') {
 return true;
 }
 
 return false;
 });

 if (applicableRequirements.length > 0) {
 // Only use requirements with confidence >= 80% (high confidence only)
 const highConfidenceRequirements = applicableRequirements.filter(
 req => req.confidence >= 0.8
 );

 if (highConfidenceRequirements.length > 0) {
 // Use the highest confidence requirement
 const bestRequirement = highConfidenceRequirements.reduce((best, current) => 
 current.confidence > best.confidence ? current : best
 );

 // Calculate buildable depth
 const buildableDepth = Math.max(0, boundary.length - bestRequirement.distance);

 const result: SetbackResult = {
 boundary_type: boundary.boundary_type as any,
 required_setback: this.roundToCentimeter(bestRequirement.distance),
 buildable_depth: this.roundToCentimeter(buildableDepth),
 reasoning: bestRequirement.reasoning || "Database-sourced planning requirement",
 confidence: bestRequirement.confidence,
 database_source: bestRequirement.source_provision,
 precision_level: "centimeter",
 authority_level: bestRequirement.authority_level,
 legal_precedence: bestRequirement.legal_precedence,
 can_be_varied: bestRequirement.can_be_varied
 };

 results.push(result);
 }
 // If no high-confidence requirements, skip this boundary (no result added)
 }
 // Removed: No default fallback - only database-sourced results with high confidence
 }

 console.log(`[Calculator] Generated ${results.length} setback results`);
 return results;
 }

 async calculateBuildableArea(
 lotGeometry: LotGeometry,
 setbackResults: SetbackResult[]
 ): Promise<BuildableAreaAnalysis> {
 const totalArea = this.estimateLotAreaFromGeometry(lotGeometry);

 // If no valid setback results found, cannot calculate buildable area
 if (setbackResults.length === 0) {
 return {
 total_lot_area: this.roundToCentimeter(totalArea),
 buildable_area: 0,
 buildable_percentage: 0,
 setback_area_lost: 0,
 note: "No high-confidence setback data available - cannot calculate buildable area"
 };
 }

 const boundaries = this.processGeometryToBoundaries(lotGeometry);

 // Simple rectangular approximation for now
 // TODO: Implement proper polygon offset for complex shapes
 if (boundaries.length === 4 && setbackResults.length >= 2) {
 const frontSetback = setbackResults.find(r => r.boundary_type === 'front')?.required_setback;
 const rearSetback = setbackResults.find(r => r.boundary_type === 'rear')?.required_setback;
 const leftSetback = setbackResults.find(r => r.boundary_type === 'side_left')?.required_setback;
 const rightSetback = setbackResults.find(r => r.boundary_type === 'side_right')?.required_setback;

 // Only calculate if we have setbacks for at least 2 boundaries
 const setbackCount = [frontSetback, rearSetback, leftSetback, rightSetback].filter(s => s !== undefined).length;
 
 if (setbackCount >= 2) {
 // Approximate lot dimensions from boundaries
 const widthBoundaries = boundaries.filter(b => b.boundary_type.includes('side'));
 const depthBoundaries = boundaries.filter(b => ['front', 'rear'].includes(b.boundary_type));

 const width = Math.max(...widthBoundaries.map(b => b.length));
 const depth = Math.max(...depthBoundaries.map(b => b.length));

 const buildableWidth = Math.max(0, width - (leftSetback || 0) - (rightSetback || 0));
 const buildableDepth = Math.max(0, depth - (frontSetback || 0) - (rearSetback || 0));

 const buildableArea = buildableWidth * buildableDepth;

 return {
 total_lot_area: this.roundToCentimeter(totalArea),
 buildable_area: this.roundToCentimeter(buildableArea),
 buildable_percentage: totalArea > 0 ? Math.round((buildableArea / totalArea) * 100 * 10) / 10 : 0,
 setback_area_lost: this.roundToCentimeter(totalArea - buildableArea)
 };
 }
 }

 // Insufficient data for precise calculation
 return {
 total_lot_area: this.roundToCentimeter(totalArea),
 buildable_area: 0,
 buildable_percentage: 0,
 setback_area_lost: 0,
 note: "Insufficient setback data for buildable area calculation"
 };
 }

 private processGeometryToBoundaries(geometry: LotGeometry): BoundaryLine[] {
 if (!geometry || !geometry.rings || geometry.rings.length === 0) {
 throw new Error("Invalid geometry data");
 }

 const coordinates = geometry.rings[0];
 if (coordinates.length < 4) {
 throw new Error("Insufficient coordinate points for boundary analysis");
 }

 // Convert Web Mercator coordinates to real-world meters
 // A malformed ring must fail the setback calculation visibly rather than
 // producing NaN geometry that downstream setbacks silently consume.
 const safeRing = usableRing(coordinates);
 if (safeRing == null) {
 throw new Error("Lot geometry contains non-finite coordinates");
 }
 const scaleFactor = scaleFactorForRing(safeRing);
 const realPoints: Point[] = safeRing.slice(0, -1).map(coord => ({
 x: coord[0] / scaleFactor,
 y: coord[1] / scaleFactor
 }));

 // Create boundary lines
 const boundaries: BoundaryLine[] = [];
 
 for (let i = 0; i < realPoints.length; i++) {
 const start = realPoints[i];
 const end = realPoints[(i + 1) % realPoints.length];

 // Calculate line properties
 const dx = end.x - start.x;
 const dy = end.y - start.y;
 const length = Math.sqrt(dx * dx + dy * dy);
 const bearing = (toDegrees(Math.atan2(dx, dy)) + 360) % 360;

 // Determine boundary type based on position and bearing
 const boundaryType = this.classifyBoundary(i, realPoints.length, bearing, length);

 boundaries.push({
 start,
 end,
 length,
 bearing,
 boundary_type: boundaryType
 });
 }

 return boundaries;
 }

 private classifyBoundary(index: number, totalBoundaries: number, bearing: number, length: number): string {
 if (totalBoundaries === 4) {
 // For rectangular lots, use predictable classification
 const boundaryTypes = ['front', 'side_right', 'rear', 'side_left'];
 return boundaryTypes[index % 4];
 } else {
 // For irregular lots, use bearing and length heuristics
 if (bearing >= 315 || bearing < 45) { // North-facing
 return length < 30 ? 'front' : 'side_left';
 } else if (bearing >= 45 && bearing < 135) { // East-facing
 return 'side_right';
 } else if (bearing >= 135 && bearing < 225) { // South-facing
 return 'rear';
 } else { // West-facing
 return 'side_left';
 }
 }
 }

 private async getSetbackRequirements(propertyZone: string, lotArea: number): Promise<SetbackRequirement[]> {
 const requirements: SetbackRequirement[] = [];

 try {
 console.log(`[Calculator] Querying KG-based setback data for zone: ${propertyZone}`);
 
 // Step 1: Use KG Zone Extractor for comprehensive zone-based setback extraction
 // const kgSetbacks = this.kgExtractor.getHierarchicalZoneSetbacks(propertyZone);
 const kgSetbacks: any[] = []; // Disabled for now, using PRP-K3 instead
 console.log(`[Calculator] Found ${kgSetbacks.length} KG-based setback requirements`);
 
 // Step 2: Convert KG setbacks to calculator format
 for (const kgSetback of kgSetbacks) {
 console.log(`[Calculator] Processing KG setback: ${kgSetback.boundary_type} = ${kgSetback.setback_meters}m (confidence: ${kgSetback.confidence_score})`);
 
 requirements.push({
 boundary_type: kgSetback.boundary_type,
 distance: kgSetback.setback_meters,
 qualifier: 'minimum',
 confidence: kgSetback.confidence_score,
 source_provision: `${kgSetback.document_source}: ${kgSetback.requirement_text}`,
 reasoning: kgSetback.legal_basis,
 authority_level: kgSetback.authority_level || 'DCP',
 legal_precedence: kgSetback.legal_precedence || 3,
 can_be_varied: kgSetback.authority_level !== 'SEPP' // SEPP requirements cannot be varied
 });
 }
 
 // Step 3: Fallback to database methods if no KG setbacks found
 if (requirements.length === 0) {
 console.log(`[Calculator] No KG setbacks found for ${propertyZone}, using database fallback`);
 
 const setbackControls = await this.db.getHierarchicalSetbackControls(propertyZone);
 console.log(`[Calculator] Found ${setbackControls.length} database setback controls`);
 
 // Process development controls first (higher reliability from PRP-F)
 for (const control of setbackControls) {
 console.log(`[Calculator] Processing control: value_text="${control.value_text}", provision_text="${control.provision_text}"`);
 
 // Parse setback distances from provision_text (more reliable than value_text)
 const textToParse = control.provision_text || control.value_text || '';
 // Match millimeters first, then meters (order matters!)
 const distanceMatch = textToParse.match(/(\d+(?:\.\d+)?)\s*(millimetres?|mm|metres?|m)/i);
 if (distanceMatch) {
 const value = parseFloat(distanceMatch[1]);
 const unit = distanceMatch[2].toLowerCase();
 const setbackMeters = this.convertToMeters(value, unit);
 
 console.log(`[Calculator] Parsing: "${textToParse}" -> ${value}${unit} -> ${setbackMeters}m`);
 
 // Determine boundary type from provision text
 const boundaryTypes = this.extractBoundaryTypesFromText(control.provision_text || control.value_text || '');
 
 console.log(`[Calculator] Text: "${textToParse}" -> Boundary types: ${JSON.stringify(boundaryTypes)}`);
 
 for (const boundaryType of boundaryTypes) {
 const authorityInfo = control.authority_level ? ` [${control.authority_level}]` : '';
 requirements.push({
 boundary_type: boundaryType,
 distance: setbackMeters,
 qualifier: 'minimum', // Most setbacks are minimums
 confidence: control.confidence_score || 0.85,
 source_provision: `${control.document_id}: ${control.provision_text}`,
 reasoning: this.extractReasoningFromProvision(control.provision_text || ''),
 authority_level: control.authority_level,
 legal_precedence: control.legal_precedence,
 can_be_varied: control.can_be_varied
 });
 
 console.log(`[Calculator] ADDED: ${boundaryType} = ${setbackMeters}m (confidence: ${control.confidence_score})${authorityInfo}`);
 }
 } else {
 console.log(`[Calculator] No numeric match in: "${textToParse}"`);
 }
 }
 
 // Process quantitative standards if no controls found 
 const quantitativeStandards = await this.db.getQuantitativeStandards('setback', propertyZone);
 console.log(`[Calculator] Found ${quantitativeStandards.length} quantitative setback standards`);
 
 for (const standard of quantitativeStandards) {
 const setbackMeters = this.convertToMeters(standard.numeric_value, standard.unit);
 const boundaryTypes = this.extractBoundaryTypesFromText(standard.provision_text || '');
 
 for (const boundaryType of boundaryTypes) {
 requirements.push({
 boundary_type: boundaryType,
 distance: setbackMeters,
 qualifier: standard.qualifier,
 confidence: standard.confidence_score,
 source_provision: `${standard.document_id}: ${standard.provision_text}`,
 reasoning: this.extractReasoningFromProvision(standard.provision_text || '')
 });
 }
 }
 }

 // Get explanatory relationships from knowledge graph
 // const reasoningData = this.db.getKGRelationships('because', 'setback');
 // const protectionData = this.db.getKGRelationships('protect', 'setback');
 const reasoningData: any[] = [];
 const protectionData: any[] = [];
 
 // Enhance reasoning for requirements that don't have detailed reasoning
 for (const requirement of requirements) {
 if (!requirement.reasoning && reasoningData.length > 0) {
 requirement.reasoning = reasoningData[0].object_text;
 } else if (!requirement.reasoning && protectionData.length > 0) {
 requirement.reasoning = `To protect ${protectionData[0].object_text}`;
 }
 }

 console.log(`[Calculator] Processed ${requirements.length} setback requirements from database`);

 } catch (error) {
 console.error('[Calculator] Database query error:', error);
 }

 // Deduplicate requirements by boundary type, keeping the highest confidence
 const dedupedRequirements: SetbackRequirement[] = [];
 const boundaryTypeMap = new Map<string, SetbackRequirement>();
 
 for (const req of requirements) {
 const existing = boundaryTypeMap.get(req.boundary_type);
 if (!existing || req.confidence >= existing.confidence) { // Fix: use >= to handle equal confidence
 boundaryTypeMap.set(req.boundary_type, req);
 }
 }
 
 dedupedRequirements.push(...Array.from(boundaryTypeMap.values()));
 console.log(`[Calculator] After deduplication: ${dedupedRequirements.length} unique requirements`);

 return dedupedRequirements;
 }


 private convertToMeters(value: number, unit: string): number {
 const unitLower = (unit || 'm').toLowerCase();
 const conversions: Record<string, number> = {
 'm': 1.0,
 'meter': 1.0,
 'metre': 1.0,
 'mm': 0.001,
 'millimeter': 0.001,
 'millimetre': 0.001,
 'cm': 0.01,
 'centimeter': 0.01,
 'centimetre': 0.01,
 'ft': 0.3048,
 'foot': 0.3048,
 'feet': 0.3048
 };
 
 return value * (conversions[unitLower] || 1.0);
 }

 private extractBoundaryTypes(provisionText: string): string[] {
 const text = provisionText.toLowerCase();
 const boundaryTypes: string[] = [];
 
 if (text.includes('front')) {
 boundaryTypes.push('front');
 }
 if (text.includes('rear')) {
 boundaryTypes.push('rear');
 }
 if (text.includes('side')) {
 boundaryTypes.push('side_left', 'side_right');
 }
 
 // Default to all boundaries if none specified
 if (boundaryTypes.length === 0) {
 boundaryTypes.push('front', 'rear', 'side_left', 'side_right');
 }
 
 return boundaryTypes;
 }

 private extractBoundaryTypesFromText(text: string): string[] {
 if (!text) return ['side_left', 'side_right']; // Default for generic setbacks
 
 const textLower = text.toLowerCase();
 const boundaryTypes: string[] = [];
 
 // More specific parsing for database text
 if (textLower.includes('front') || textLower.includes('street')) {
 boundaryTypes.push('front');
 }
 if (textLower.includes('rear') || textLower.includes('back')) {
 boundaryTypes.push('rear');
 }
 if (textLower.includes('side')) {
 boundaryTypes.push('side_left', 'side_right');
 }
 
 // Check for specific boundary mentions
 if (textLower.includes('all boundaries') || textLower.includes('minimum setback')) {
 boundaryTypes.push('front', 'rear', 'side_left', 'side_right');
 }
 
 // If no specific boundary found, default based on common setback patterns
 if (boundaryTypes.length === 0) {
 if (textLower.includes('detached') || textLower.includes('dwelling')) {
 boundaryTypes.push('side_left', 'side_right'); // Most common for residential
 } else {
 boundaryTypes.push('front', 'rear', 'side_left', 'side_right');
 }
 }
 
 return boundaryTypes;
 }

 private extractReasoningFromProvision(provisionText: string): string | undefined {
 if (!provisionText) return undefined;
 
 const reasoningPatterns = [
 'to maintain', 'to protect', 'to ensure', 'to preserve',
 'for privacy', 'for amenity', 'for character', 'for access',
 'to provide', 'to allow', 'to prevent'
 ];
 
 const textLower = provisionText.toLowerCase();
 for (const pattern of reasoningPatterns) {
 if (textLower.includes(pattern)) {
 const sentences = provisionText.split(/[.;]/);
 for (const sentence of sentences) {
 if (sentence.toLowerCase().includes(pattern)) {
 return sentence.trim();
 }
 }
 }
 }
 
 // If no explicit reasoning, infer from content
 if (textLower.includes('heritage')) {
 return 'To protect heritage character and values';
 }
 if (textLower.includes('amenity')) {
 return 'To maintain residential amenity and privacy';
 }
 if (textLower.includes('access')) {
 return 'To ensure adequate access and circulation';
 }
 
 return undefined;
 }

 private extractReasoning(provisionText: string): string | undefined {
 const reasoningPatterns = [
 'to maintain', 'to protect', 'to ensure', 'to preserve',
 'for privacy', 'for amenity', 'for character'
 ];
 
 const textLower = provisionText.toLowerCase();
 for (const pattern of reasoningPatterns) {
 if (textLower.includes(pattern)) {
 const sentences = provisionText.split('.');
 for (const sentence of sentences) {
 if (sentence.toLowerCase().includes(pattern)) {
 return sentence.trim();
 }
 }
 }
 }
 
 return undefined;
 }


 private roundToCentimeter(value: number): number {
 return Math.round(value * 100) / 100;
 }

 private estimateLotAreaFromGeometry(geometry: LotGeometry): number {
 if (!geometry.rings || geometry.rings.length === 0) {
 return 0;
 }

 const coordinates = geometry.rings[0];
 const safeRing = usableRing(coordinates);
 if (safeRing == null) {
 return 0;
 }
 const scaleFactor = scaleFactorForRing(safeRing);
 const points = safeRing.slice(0, -1).map(coord => ({
 x: coord[0] / scaleFactor,
 y: coord[1] / scaleFactor
 }));

 // Use shoelace formula for polygon area
 let area = 0;
 for (let i = 0; i < points.length; i++) {
 const j = (i + 1) % points.length;
 area += points[i].x * points[j].y;
 area -= points[j].x * points[i].y;
 }
 
 return Math.abs(area) / 2;
 }

 // Helper method for angle conversion
 private static toDegrees(radians: number): number {
 return radians * (180 / Math.PI);
 }

 dispose() {
 this.db.close();
 // this.kgExtractor.close();
 }
}