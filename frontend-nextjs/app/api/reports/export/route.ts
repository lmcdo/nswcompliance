import { NextRequest, NextResponse } from 'next/server';
import { ReportExporter, ReportExportOptions } from '@/lib/assessment/reports';
import { ReportSchema, validateRequest, formatValidationErrors } from '@/lib/schemas';

export async function POST(request: NextRequest) {
 try {
 const body = await request.json();

 // Validate core report data using ReportSchema
 const validation = validateRequest(ReportSchema, {
 address: body.address || 'N/A',
 zone: body.zone || 'N/A',
 developmentType: body.developmentType || 'other',
 format: body.options?.format || 'json',
 });

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

 const { content, options }: { content: any; options: ReportExportOptions } = body;

 if (!content) {
 return NextResponse.json(
 { error: 'Report content is required' },
 { status: 400 }
 );
 }

 let exportResult: any;
 let contentType: string;
 let fileExtension: string;

 switch (options.format) {
 case 'pdf':
 exportResult = await ReportExporter.exportToPDF(content, options);
 contentType = 'application/pdf';
 fileExtension = 'pdf';
 break;

 case 'html':
 exportResult = await ReportExporter.exportToHTML(content, options);
 contentType = 'text/html';
 fileExtension = 'html';
 break;

 case 'json':
 exportResult = await ReportExporter.exportToJSON(content, options);
 contentType = 'application/json';
 fileExtension = 'json';
 break;

 default:
 return NextResponse.json(
 { error: 'Unsupported export format' },
 { status: 400 }
 );
 }

 const fileName = `compliance_report_${Date.now()}.${fileExtension}`;

 // For PDF/binary content
 if (options.format === 'pdf') {
 return new NextResponse(exportResult, {
 headers: {
 'Content-Type': contentType,
 'Content-Disposition': `attachment; filename="${fileName}"`,
 },
 });
 }

 // For text-based content
 return new NextResponse(exportResult, {
 headers: {
 'Content-Type': contentType,
 'Content-Disposition': `attachment; filename="${fileName}"`,
 },
 });

 } catch (error) {
 console.error('Report export error:', error);
 return NextResponse.json(
 {
 error: 'Failed to export report',
 details: error instanceof Error ? error.message : 'Unknown error'
 },
 { status: 500 }
 );
 }
}
