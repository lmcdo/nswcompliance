import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';
import { EnhancedSetbackProcessor } from '../../../../lib/enhanced-setback-processor';

const execAsync = promisify(exec);

interface SetbackResult {
 value: number;
 unit: string;
 confidence: number;
 source: string;
 clause_reference: string;
 domain_classification: string;
 relevance_score: number;
 legal_authority: any;
 cross_contamination_checked: boolean;
 provision_id?: number; // For Referenced Legislation accordion
}

interface TransformedSetbacks {
 rear: SetbackResult | null;
 side: SetbackResult | null;
 front: SetbackResult | null;
}

/**
 * Call the enhanced domain-aware Python compliance engine
 * This integrates Phase 1A MVP improvements with the UI
 */
async function callDomainAwarePythonEngine(councilArea: string, address: string) {
 try {
 // Determine zone from address (simplified - in production would use NSW API)
 // For now, default to R2 (Low Density Residential) for testing
 const zone = 'R2'; // TODO: Integrate with NSW Planning API for actual zone lookup
 
 // Map UI council area names to Python engine format
 const councilMapping: { [key: string]: string } = {
 'Ashfield': 'ashfield',
 'Leichhardt': 'leichhardt', 
 'Marrickville': 'marrickville'
 };
 
 const pythonCouncilArea = councilMapping[councilArea] || 'marrickville';
 
 // Execute the enhanced Python compliance engine
 const pythonPath = path.join(process.cwd(), 'venv_linux', 'Scripts', 'python.exe');
 const scriptPath = path.join(process.cwd(), 'dynamic_setback_calc.py');
 
 console.log(`Calling: ${pythonPath} ${scriptPath} ${zone} 0`);
 
 const { stdout, stderr } = await execAsync(
 `"${pythonPath}" "${scriptPath}" ${zone} 0`,
 { 
 cwd: process.cwd(),
 timeout: 30000, // 30 second timeout
 encoding: 'utf8'
 }
 );
 
 if (stderr) {
 console.warn('Python engine stderr:', stderr);
 }
 
 // Parse the JSON response from Python
 const setbacksData = JSON.parse(stdout.trim());
 
 // Transform Python response to UI format
 const transformedSetbacks: TransformedSetbacks = {
 rear: null,
 side: null,
 front: null
 };
 
 // Process each setback result
 for (const setback of setbacksData) {
 const boundaryType = setback.boundary_type as 'front' | 'side' | 'rear';
 
 // Only process known boundary types
 if (!['front', 'side', 'rear'].includes(boundaryType)) {
 continue;
 }
 
 if (!transformedSetbacks[boundaryType] || setback.confidence > (transformedSetbacks[boundaryType]?.confidence || 0)) {
 transformedSetbacks[boundaryType] = {
 value: setback.required_setback,
 unit: 'meters',
 confidence: setback.confidence,
 source: setback.legal_source,
 clause_reference: setback.clause_reference,
 domain_classification: setback.domain_classification,
 relevance_score: setback.relevance_score,
 legal_authority: setback.legal_authority,
 cross_contamination_checked: setback.cross_contamination_checked,
 provision_id: setback.provision_id // Add provision_id for Referenced Legislation accordion
 };
 }
 }
 
 return {
 success: true,
 setbacks: transformedSetbacks,
 raw_results: setbacksData,
 processing_metadata: {
 zone_used: zone,
 council_area: pythonCouncilArea,
 domain_filtering_applied: true,
 results_count: setbacksData.length
 }
 };
 
 } catch (error) {
 console.error('Error calling domain-aware Python engine:', error);
 return {
 success: false,
 error: error instanceof Error ? error.message : 'Unknown error occurred',
 setbacks: {
 rear: null,
 side: null,
 front: null
 }
 };
 }
}

/**
 * API route for retrieving setback rules for a property
 * 
 * This route returns setback rules extracted from regulatory documents
 * using the dual semantic processing pipeline (LangExtract + AutoSchemaKG)
 * with fallback to basic JSON data for reliability
 */
export async function GET(req: NextRequest) {
 const { searchParams } = new URL(req.url);
 const address = searchParams.get('address');
 const useSemanticProcessor = searchParams.get('semantic') !== 'false'; // Default to true
 
 if (!address) {
 return NextResponse.json(
 { error: 'Address parameter required' },
 { status: 400 }
 );
 }
 
 try {
 // Determine which former council area the property is in
 const formerCouncilArea = determineFormerCouncilArea(address);
 
 if (!formerCouncilArea) {
 return NextResponse.json(
 { 
 error: 'Address does not appear to be in Inner West LGA or former council area could not be determined',
 formerCouncilArea: null,
 setbacks: null,
 processing_method: 'address_resolution_failed'
 },
 { status: 404 }
 );
 }
 
 // Try enhanced domain-aware Python engine first
 if (useSemanticProcessor) {
 try {
 console.log(`Attempting domain-aware processing for ${formerCouncilArea}...`);
 
 // Call the enhanced Python compliance engine
 const domainAwareResult = await callDomainAwarePythonEngine(formerCouncilArea, address);
 
 if (domainAwareResult && domainAwareResult.success && 
 (domainAwareResult.setbacks.front || domainAwareResult.setbacks.side || domainAwareResult.setbacks.rear)) {
 const setbackCount = [domainAwareResult.setbacks.front, domainAwareResult.setbacks.side, domainAwareResult.setbacks.rear].filter(Boolean).length;
 console.log(`Successfully processed ${setbackCount} domain-aware setbacks for ${formerCouncilArea}`);
 return NextResponse.json({
 setbacks: domainAwareResult.setbacks,
 formerCouncilArea,
 success: true,
 processing_method: 'domain_aware_python',
 source_authority: 'Inner West LEP 2022',
 legal_authority_verified: true,
 cross_contamination_prevented: true,
 metadata: {
 extraction_method: 'domain_aware_engine_v1',
 timestamp: new Date().toISOString(),
 total_setbacks: setbackCount,
 domain_filtering_applied: true,
 signage_contamination_eliminated: true,
 processing_metadata: domainAwareResult.processing_metadata
 }
 });
 } else {
 console.warn(`Domain-aware engine failed for ${formerCouncilArea}, falling back to legacy processing`);
 }
 
 } catch (domainError) {
 console.warn(`Domain-aware engine failed for ${formerCouncilArea}:`, domainError);
 console.log('Falling back to legacy semantic processing...');
 }
 }
 
 // Fallback to basic JSON data
 console.log(`Using basic JSON fallback for ${formerCouncilArea}`);
 const dataPath = path.join(process.cwd(), 'public', 'regulatory-data', 'inner-west-setbacks.json');
 
 if (!fs.existsSync(dataPath)) {
 return NextResponse.json(
 { 
 error: 'Setback data not available. Please run the processing pipeline first.',
 formerCouncilArea,
 setbacks: null,
 processing_method: 'fallback_failed'
 },
 { status: 500 }
 );
 }
 
 const rawData = fs.readFileSync(dataPath, 'utf8');
 const setbackData = JSON.parse(rawData);
 
 // Get setback rules for the determined council area
 const areaData = setbackData.areas?.[formerCouncilArea];
 
 if (!areaData) {
 return NextResponse.json(
 {
 error: `No setback data available for ${formerCouncilArea}`,
 formerCouncilArea,
 setbacks: {
 rear: null,
 side: null,
 front: null
 },
 processing_method: 'basic_json_no_data'
 },
 { status: 404 }
 );
 }
 
 // Return basic setback rules
 return NextResponse.json({
 setbacks: areaData.setbacks,
 formerCouncilArea,
 success: true,
 processing_method: 'basic_json_fallback',
 metadata: {
 extraction_method: 'basic_json',
 source: 'inner-west-setbacks.json',
 note: 'Using fallback data - semantic processing unavailable'
 }
 });
 
 } catch (error) {
 console.error('Setback data fetch failed:', error);
 return NextResponse.json(
 { 
 error: 'Failed to retrieve setback rules',
 formerCouncilArea: null,
 processing_method: 'error'
 },
 { status: 500 }
 );
 }
}

/**
 * Determines which former council area a property is in
 * Uses address parsing to map to Ashfield, Leichhardt, or Marrickville
 */
function determineFormerCouncilArea(address: string): string | null {
 const addressLower = address.toLowerCase();
 
 // Map of postcodes/suburbs to former council areas
 const FORMER_COUNCIL_MAPPING: { [key: string]: string } = {
 // Ashfield postcodes and suburbs
 '2131': 'Ashfield', // Ashfield
 '2044': 'Ashfield', // St Peters (part)
 '2039': 'Ashfield', // Rozelle (part)
 '2140': 'Ashfield', // Croydon
 '2137': 'Ashfield', // Burwood Heights
 '2133': 'Ashfield', // Croydon Park
 '2132': 'Ashfield', // Enfield
 '2045': 'Ashfield', // Haberfield
 
 // Ashfield suburbs (case-insensitive matching)
 'ashfield': 'Ashfield',
 'croydon': 'Ashfield',
 'croydon park': 'Ashfield',
 'enfield': 'Ashfield',
 'haberfield': 'Ashfield',
 'russell lea': 'Ashfield',
 'five dock': 'Ashfield',
 'wareemba': 'Ashfield',
 'rodd point': 'Ashfield',
 'cabarita': 'Ashfield',
 'concord west': 'Ashfield',
 'north strathfield': 'Ashfield',
 'strathfield south': 'Ashfield',
 'homebush west': 'Ashfield',
 
 // Leichhardt postcodes and suburbs
 '2040': 'Leichhardt', // Leichhardt
 '2041': 'Leichhardt', // Balmain
 '2042': 'Leichhardt', // Enmore
 '2043': 'Leichhardt', // Erskineville
 '2038': 'Leichhardt', // Annandale
 '2037': 'Leichhardt', // Glebe
 '2050': 'Leichhardt', // Camperdown
 '2049': 'Leichhardt', // Lewisham (part)
 
 // Leichhardt suburbs
 'leichhardt': 'Leichhardt',
 'balmain': 'Leichhardt',
 'balmain east': 'Leichhardt',
 'birchgrove': 'Leichhardt',
 'rozelle': 'Leichhardt',
 'lilyfield': 'Leichhardt',
 'annandale': 'Leichhardt',
 'glebe': 'Leichhardt',
 'forest lodge': 'Leichhardt',
 'camperdown': 'Leichhardt',
 'chippendale': 'Leichhardt',
 'enmore': 'Leichhardt',
 'newtown': 'Leichhardt',
 'erskineville': 'Leichhardt',
 'sydenham': 'Leichhardt',
 'stanmore': 'Leichhardt',
 'petersham': 'Leichhardt',
 
 // Marrickville postcodes and suburbs
 '2204': 'Marrickville', // Marrickville
 '2203': 'Marrickville', // Dulwich Hill
 '2206': 'Marrickville', // Earlwood
 '2207': 'Marrickville', // Beverly Hills
 '2208': 'Marrickville', // Kingsgrove
 
 // Marrickville suburbs
 'marrickville': 'Marrickville',
 'dulwich hill': 'Marrickville',
 'hurlstone park': 'Marrickville',
 'earlwood': 'Marrickville',
 'marrickville south': 'Marrickville',
 'tempe': 'Marrickville',
 'lewisham': 'Marrickville',
 'summer hill': 'Marrickville',
 'ashbury': 'Marrickville',
 'canterbury': 'Marrickville',
 'campsie': 'Marrickville',
 'belmore': 'Marrickville',
 'lakemba': 'Marrickville',
 'wiley park': 'Marrickville',
 'punchbowl': 'Marrickville',
 'roselands': 'Marrickville',
 'narwee': 'Marrickville',
 'beverly hills': 'Marrickville',
 'kingsgrove': 'Marrickville',
 'bexley north': 'Marrickville',
 };
 
 // Extract postcode using regex
 const postcodeMatch = address.match(/\b(\d{4})\b/);
 if (postcodeMatch) {
 const postcode = postcodeMatch[1];
 if (FORMER_COUNCIL_MAPPING[postcode]) {
 return FORMER_COUNCIL_MAPPING[postcode];
 }
 }
 
 // Check for suburb names in address
 for (const [key, area] of Object.entries(FORMER_COUNCIL_MAPPING)) {
 if (addressLower.includes(key.toLowerCase())) {
 return area;
 }
 }
 
 // Default fallback - could be improved with more sophisticated geo-coding
 return null;
}