// app/api/clause/[id]/route.ts - Clause Text Lookup Endpoint
import { NextRequest, NextResponse } from 'next/server';
import { DatabaseClient } from '@/lib/database/client';

export async function GET(
 request: NextRequest,
 { params }: { params: { id: string } }
) {
 const startTime = Date.now();
 
 try {
 const clauseId = parseInt(params.id);
 
 if (isNaN(clauseId)) {
 return NextResponse.json({
 success: false,
 error: 'Invalid clause ID - must be a number'
 }, { status: 400 });
 }

 const dbClient = new DatabaseClient();
 
 // Get full clause details including provision text
 const query = `
 SELECT
 rp.id,
 rp.ref_number as clause_reference,
 rp.provision_text as full_text,
 rp.section_header,
 rp.page_number,
 rp.domain_classification,
 rp.document_id,
 rp.created_at
 FROM regulatory_provisions_canonical rp
 WHERE rp.id = $1
 LIMIT 1
 `;
 
 const result = await dbClient.execute(query, [clauseId]);
 
 if (result.length === 0) {
 return NextResponse.json({
 success: false,
 error: 'Clause not found'
 }, { status: 404 });
 }
 
 const clause = result[0];
 
 // Determine document hierarchy level from document_id
 const getAuthorityLevel = (docId: string): string => {
 const docIdUpper = docId?.toUpperCase() || '';
 if (docIdUpper.includes('SEPP')) return 'SEPP';
 if (docIdUpper.includes('LEP') || docIdUpper.includes('LOCAL_ENVIRONMENTAL_PLAN')) return 'LEP'; 
 if (docIdUpper.includes('DCP')) return 'DCP';
 return 'DCP'; // Default assumption for most provisions
 };
 
 const authorityLevel = getAuthorityLevel(clause.document_id);
 
 return NextResponse.json({
 success: true,
 clause: {
 id: clause.id,
 clause_reference: clause.clause_reference || `Provision ${clause.id}`,
 full_text: clause.full_text,
 section_header: clause.section_header,
 document_name: clause.document_id,
 document_type: authorityLevel,
 page_number: clause.page_number,
 authority_level: authorityLevel,
 authority_explanation: getAuthorityExplanation(authorityLevel),
 legal_context: getLegalContext(authorityLevel),
 domain_classification: clause.domain_classification,
 created_at: clause.created_at
 },
 processing_time_ms: Date.now() - startTime
 });

 } catch (error) {
 console.error('[API] Clause lookup error:', error);
 
 return NextResponse.json({
 success: false,
 error: error instanceof Error ? error.message : 'Clause lookup failed',
 processing_time_ms: Date.now() - startTime
 }, { status: 500 });
 }
}

function getAuthorityExplanation(authorityLevel: string): string {
 switch (authorityLevel) {
 case 'SEPP':
 return 'State Environmental Planning Policy - Highest legal authority. Cannot be varied by councils. Overrides all other planning instruments.';
 case 'LEP':
 return 'Local Environmental Plan - Local law with statutory force. Can only be varied through formal Clause 4.6 variation process with consent authority approval.';
 case 'DCP':
 return 'Development Control Plan - Planning guidance document. Provides detailed design standards but cannot override SEPP or LEP requirements.';
 default:
 return 'Planning document with regulatory authority.';
 }
}

function getLegalContext(authorityLevel: string): string {
 switch (authorityLevel) {
 case 'SEPP':
 return 'This is a state-mandated requirement that applies uniformly across NSW. It forms part of the Environmental Planning and Assessment Act 1979 framework.';
 case 'LEP':
 return 'This is a local statutory requirement specific to this council area. LEP provisions have the force of law and must be complied with unless formally varied.';
 case 'DCP':
 return 'This provides detailed design guidance for development in this zone. DCP provisions are normally applied but cannot override higher-level planning instruments.';
 default:
 return 'This forms part of the NSW planning framework and should be considered in development applications.';
 }
}