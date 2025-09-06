import { NextRequest, NextResponse } from 'next/server';
import fs from 'fs';
import path from 'path';
import { EnhancedSetbackProcessor } from '../../../../lib/enhanced-setback-processor';

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
    
    // Try enhanced semantic processing first
    if (useSemanticProcessor) {
      try {
        console.log(`Attempting semantic processing for ${formerCouncilArea}...`);
        const processor = new EnhancedSetbackProcessor();
        
        // Check for cached data first
        const cachedData = await processor.getCachedProcessedData(formerCouncilArea);
        if (cachedData && cachedData.processing_metadata.success) {
          console.log(`Using cached semantic data for ${formerCouncilArea}`);
          return NextResponse.json({
            setbacks: cachedData.setbacks,
            formerCouncilArea,
            success: true,
            processing_method: 'semantic_cached',
            source_authority: cachedData.source_authority,
            compliance_rules: cachedData.compliance_rules.map(rule => ({
              rule_id: rule.id,
              authority: rule.authority,
              requirements_count: rule.requirements.length,
              priority: rule.priority
            })),
            metadata: {
              extraction_method: cachedData.extraction_method,
              timestamp: cachedData.processing_metadata.timestamp,
              total_rules: cachedData.compliance_rules.length
            }
          });
        }
        
        // Process with dual semantic pipeline
        const processedData = await processor.processSetbackRules(formerCouncilArea);
        
        if (processedData.processing_metadata.success && processedData.compliance_rules.length > 0) {
          console.log(`Successfully processed ${processedData.compliance_rules.length} semantic rules for ${formerCouncilArea}`);
          return NextResponse.json({
            setbacks: processedData.setbacks,
            formerCouncilArea,
            success: true,
            processing_method: 'semantic_live',
            source_authority: processedData.source_authority,
            compliance_rules: processedData.compliance_rules.map(rule => ({
              rule_id: rule.id,
              authority: rule.authority,
              requirements_count: rule.requirements.length,
              priority: rule.priority,
              source_section: rule.source.section
            })),
            metadata: {
              extraction_method: processedData.extraction_method,
              timestamp: processedData.processing_metadata.timestamp,
              total_rules: processedData.compliance_rules.length,
              processing_time_ms: processedData.processing_metadata.processing_time_ms
            }
          });
        } else {
          console.warn(`Semantic processing failed for ${formerCouncilArea}, falling back to basic data`);
        }
        
      } catch (semanticError) {
        console.warn(`Semantic processor failed for ${formerCouncilArea}:`, semanticError);
        console.log('Falling back to basic JSON data...');
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
    '2131': 'Ashfield',  // Ashfield
    '2044': 'Ashfield',  // St Peters (part)
    '2039': 'Ashfield',  // Rozelle (part)
    '2140': 'Ashfield',  // Croydon
    '2137': 'Ashfield',  // Burwood Heights
    '2133': 'Ashfield',  // Croydon Park
    '2132': 'Ashfield',  // Enfield
    '2045': 'Ashfield',  // Haberfield
    
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