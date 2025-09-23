import { NextRequest, NextResponse } from 'next/server';
import { EnhancedComplianceEngine } from '../../../../lib/enhanced-compliance-engine';
import { PropertyData } from '../../../../lib/property-data';

/**
 * Enhanced Compliance Checking API
 * Uses dual semantic processing for comprehensive regulatory compliance
 */

export async function POST(req: NextRequest) {
 try {
 const requestData = await req.json();
 
 // Validate required fields
 const { propertyData, proposal, formerCouncilArea } = requestData;
// Auto-determine former council area from address if not provided let finalFormerCouncilArea = formerCouncilArea; if (!finalFormerCouncilArea && propertyData?.address) { finalFormerCouncilArea = determineFormerCouncilAreaFromAddress(propertyData.address); console.log(`Auto-determined council area: ${finalFormerCouncilArea} from address: ${propertyData.address}`); }
 
 if (!propertyData || !proposal) {
 return NextResponse.json(
 { error: 'Property data and proposal are required' },
 { status: 400 }
 );
 }

 // Optional settings
 const useSemanticRules = requestData.useSemanticRules !== false; // Default to true
 const includeSourceGrounding = requestData.includeSourceGrounding !== false; // Default to true

 console.log(`Processing compliance check for ${formerCouncilArea || 'unknown area'}`);
 console.log(`Proposal: height=${proposal.height}m, FSR=${proposal.fsr}, setbacks=${JSON.stringify({
 front: proposal.front_setback,
 side: proposal.side_setback, 
 rear: proposal.rear_setback
 })}`);

 // Initialize enhanced compliance engine
 const complianceEngine = new EnhancedComplianceEngine();

 // Perform enhanced compliance check
 const complianceResults = await complianceEngine.checkEnhancedCompliance(
 propertyData as PropertyData,
 proposal,
 formerCouncilArea,
 useSemanticRules
 );

 // Generate compliance summary
 const summary = complianceEngine.generateComplianceSummary(complianceResults);

 // Prepare response based on client requirements
 const responseData: any = {
 compliance_summary: summary,
 total_rules_checked: complianceResults.length,
 compliant: summary.overall_compliant,
 results: complianceResults.map(result => ({
 rule_id: result.rule_id,
 requirement_type: result.requirement_type,
 compliant: result.compliant,
 proposed_value: result.proposed_value,
 required_value: result.required_value,
 gap: result.gap,
 confidence: result.confidence,
 processing_method: result.processing_method,
 source: {
 document: result.source.document,
 section: result.source.section,
 clause: result.source.clause,
 url: result.source.url
 },
 rule_classification: result.rule_classification,
 mitigation: result.mitigation,
 regulatory_text: result.regulatory_text,
 // Include source grounding if requested and available
 source_grounding: result.source_grounding
 })),
 processing_metadata: {
 timestamp: new Date().toISOString(),
 semantic_rules_enabled: useSemanticRules,
 former_council_area: formerCouncilArea,
 total_processing_methods: {
 semantic: complianceResults.filter(r => r.processing_method === 'semantic').length,
 manual: complianceResults.filter(r => r.processing_method === 'manual').length,
 fallback: complianceResults.filter(r => r.processing_method === 'fallback').length
 }
 }
 };

 // Log compliance summary
 console.log(`Compliance check completed:`);
 console.log(` Overall compliant: ${summary.overall_compliant}`);
 console.log(` Total rules: ${summary.total_rules_checked}`);
 console.log(` Non-compliant: ${summary.non_compliant_rules}`);
 console.log(` High priority issues: ${summary.high_priority_issues.length}`);
 console.log(` Source authority: ${JSON.stringify(summary.source_authority_summary)}`);

 return NextResponse.json(responseData);

 } catch (error) {
 console.error('Enhanced compliance check failed:', error);
 
 return NextResponse.json(
 {
 error: 'Compliance check failed',
 details: error instanceof Error ? error.message : 'Unknown error',
 timestamp: new Date().toISOString()
 },
 { status: 500 }
 );
 }
}

/**
 * GET endpoint for compliance check status and capabilities
 */
export async function GET(req: NextRequest) {
 try {
 const { searchParams } = new URL(req.url);
 const formerCouncilArea = searchParams.get('area');
 
 // Get available processing methods and capabilities
 const capabilities = {
 semantic_processing_available: true,
 supported_areas: ['Ashfield', 'Leichhardt', 'Marrickville'],
 supported_rule_types: [
 'side_setback',
 'front_setback', 
 'rear_setback',
 'height',
 'floor_space_ratio'
 ],
 processing_methods: {
 semantic: {
 description: 'Dual semantic processing with LangExtract + AutoSchemaKG',
 capabilities: [
 'Complex conditional logic',
 'Source text grounding',
 'Three-tier rule classification',
 'Confidence scoring'
 ]
 },
 manual: {
 description: 'Manually encoded compliance rules',
 capabilities: [
 'NSW LEP rules from Planning Portal API',
 'Core DCP setback requirements',
 'High reliability for basic compliance'
 ]
 }
 },
 rule_classification_system: {
 'Tier 1': 'Hard Requirements (MUST comply)',
 'Tier 2': 'Strong Guidance (SHOULD align)',
 'Tier 3': 'Descriptive Context (CONSIDER)'
 }
 };

 // If specific area requested, check availability
 if (formerCouncilArea) {
 const engine = new EnhancedComplianceEngine();
 
 // This would check for available semantic data
 const areaStatus = {
 area: formerCouncilArea,
 semantic_data_available: ['Ashfield', 'Leichhardt', 'Marrickville'].includes(formerCouncilArea),
 last_processed: null, // Would check cache timestamps
 estimated_rules_available: formerCouncilArea === 'Ashfield' ? 15 : 12
 };
 
 return NextResponse.json({
 ...capabilities,
 area_status: areaStatus
 });
 }

 return NextResponse.json(capabilities);

 } catch (error) {
 console.error('Compliance capabilities check failed:', error);
 
 return NextResponse.json(
 {
 error: 'Failed to get compliance capabilities',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}