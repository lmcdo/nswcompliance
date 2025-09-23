import { NextRequest, NextResponse } from 'next/server';
import { ReportGenerator, ReportConfig } from '@/lib/assessment/reports';

export async function POST(request: NextRequest) {
 try {
 const config: ReportConfig = await request.json();

 // Validate required fields
 if (!config.template_id) {
 return NextResponse.json(
 { error: 'Template ID is required' },
 { status: 400 }
 );
 }

 if (!config.property_data) {
 return NextResponse.json(
 { error: 'Property data is required' },
 { status: 400 }
 );
 }

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
 const { searchParams } = new URL(request.url);
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
