import { NextRequest, NextResponse } from 'next/server';
import { ReportGenerator, ReportConfig } from '@/lib/assessment/reports';
import { ReportSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';


export const dynamic = 'force-dynamic';
export async function POST(request: NextRequest) {
 try {
 const body = await request.json();

 // Validate request using ReportSchema
 const validation = validateRequest(ReportSchema, body);

 if (!validation.success) {
 return NextResponse.json(
 {
 success: false,
 error: 'Invalid request data',
 details: formatValidationErrors(validation.details),
 },
 { status: 400 }
 );
 }

 const config: ReportConfig = body;

 // Generate report
 const report = await ReportGenerator.generateReport(config);

 return NextResponse.json({
 success: true,
 report
 });

 } catch (error) {
 console.error('Report generation error:', error);
 return NextResponse.json(
 {
 error: 'Failed to generate report',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}

export async function GET(request: NextRequest) {
 const searchParams = request.nextUrl.searchParams;
 const action = searchParams.get('action');

 if (action === 'templates') {
 // Return available templates
 const { REPORT_TEMPLATES } = await import('@/lib/assessment/reports');

 return NextResponse.json({
 templates: Object.values(REPORT_TEMPLATES).map(template => ({
 id: template.id,
 name: template.name,
 description: template.description,
 category: template.category,
 sections: template.sections.length
 }))
 });
 }

 return NextResponse.json(
 { error: 'Invalid action parameter' },
 { status: 400 }
 );
}
