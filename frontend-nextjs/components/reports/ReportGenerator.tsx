'use client';

import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { FileText, Download, Settings, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { useReports } from '@/hooks/assessment/useReports';
import { ReportConfig, ReportExportOptions } from '@/lib/assessment/reports';

interface ReportGeneratorProps {
 propertyData?: any;
 assessmentData?: any;
 complianceData?: any;
 onReportGenerated?: (report: any) => void;
}

export function ReportGenerator({
 propertyData,
 assessmentData,
 complianceData,
 onReportGenerated
}: ReportGeneratorProps) {
 const {
 isGenerating,
 isExporting,
 generateReport,
 exportReport,
 getAvailableTemplates,
 error,
 clearError
 } = useReports();

 const [templates, setTemplates] = useState<any[]>([]);
 const [selectedTemplate, setSelectedTemplate] = useState('professional_full');
 const [exportFormat, setExportFormat] = useState<'pdf' | 'html' | 'json'>('pdf');
 const [includeAttachments, setIncludeAttachments] = useState(true);
 const [customSections, setCustomSections] = useState('');
 const [reportTitle, setReportTitle] = useState('');
 const [generatedReport, setGeneratedReport] = useState<any>(null);

 useEffect(() => {
 loadTemplates();
 }, []);

 const loadTemplates = async () => {
 const availableTemplates = await getAvailableTemplates();
 setTemplates(availableTemplates);
 };

 const handleGenerateReport = async () => {
 if (!propertyData) {
 return;
 }

 clearError();

 const config: ReportConfig = {
 template_id: selectedTemplate,
 property_data: propertyData,
 assessment_data: assessmentData,
 compliance_data: complianceData,
 export_format: exportFormat,
 include_attachments: includeAttachments,
 custom_sections: customSections ? [
 {
 title: 'Additional Information',
 content: customSections,
 position: 'appendix' as const
 }
 ] : undefined
 };

 const report = await generateReport(config);
 if (report) {
 setGeneratedReport(report);
 onReportGenerated?.(report);
 }
 };

 const handleExportReport = async (format: 'pdf' | 'html' | 'json') => {
 if (!generatedReport) return;

 const options: ReportExportOptions = {
 format,
 quality: 'high',
 include_metadata: true,
 compress: format === 'pdf'
 };

 await exportReport(generatedReport, options);
 };

 const getStatusIcon = (status: string) => {
 switch (status) {
 case 'valid':
 return <CheckCircle className="w-4 h-4 text-green-600" />;
 case 'warnings':
 return <AlertCircle className="w-4 h-4 text-yellow-600" />;
 case 'errors':
 return <AlertCircle className="w-4 h-4 text-red-600" />;
 default:
 return <Clock className="w-4 h-4 text-gray-400" />;
 }
 };

 return (
 <div className="space-y-6">
 {/* Report Configuration */}
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <FileText className="w-5 h-5" />
 Report Configuration
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-4">
 {/* Template Selection */}
 <div className="space-y-2">
 <Label htmlFor="template">Report Template</Label>
 <Select value={selectedTemplate} onValueChange={setSelectedTemplate}>
 <SelectTrigger>
 <SelectValue placeholder="Select report template" />
 </SelectTrigger>
 <SelectContent>
 {templates.map((template) => (
 <SelectItem key={template.id} value={template.id}>
 <div className="flex flex-col">
 <span className="font-medium">{template.name}</span>
 <span className="text-sm text-muted-foreground">
 {template.description}
 </span>
 </div>
 </SelectItem>
 ))}
 </SelectContent>
 </Select>
 </div>

 {/* Export Format */}
 <div className="space-y-2">
 <Label htmlFor="format">Export Format</Label>
 <Select value={exportFormat} onValueChange={(value: any) => setExportFormat(value)}>
 <SelectTrigger>
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="pdf">PDF (Recommended)</SelectItem>
 <SelectItem value="html">HTML</SelectItem>
 <SelectItem value="json">JSON Data</SelectItem>
 </SelectContent>
 </Select>
 </div>

 {/* Report Title */}
 <div className="space-y-2">
 <Label htmlFor="title">Custom Report Title (Optional)</Label>
 <Input
 id="title"
 value={reportTitle}
 onChange={(e) => setReportTitle(e.target.value)}
 placeholder="Enter custom report title"
 />
 </div>

 {/* Options */}
 <div className="space-y-3">
 <div className="flex items-center space-x-2">
 <Checkbox
 id="attachments"
 checked={includeAttachments}
 onCheckedChange={(checked) => setIncludeAttachments(checked as boolean)}
 />
 <Label htmlFor="attachments">Include attachments and appendices</Label>
 </div>
 </div>

 {/* Custom Sections */}
 <div className="space-y-2">
 <Label htmlFor="custom">Additional Information (Optional)</Label>
 <Textarea
 id="custom"
 value={customSections}
 onChange={(e) => setCustomSections(e.target.value)}
 placeholder="Enter additional information to include in the report..."
 rows={3}
 />
 </div>

 {/* Error Display */}
 {error && (
 <div className="p-3 bg-red-50 border border-red-200 rounded-md">
 <div className="flex items-center gap-2 text-red-700">
 <AlertCircle className="w-4 h-4" />
 <span className="text-sm font-medium">Error</span>
 </div>
 <p className="text-sm text-red-600 mt-1">{error}</p>
 </div>
 )}

 {/* Generate Button */}
 <Button
 onClick={handleGenerateReport}
 disabled={isGenerating || !propertyData}
 className="w-full"
 >
 {isGenerating ? (
 <>
 <Clock className="w-4 h-4 mr-2 animate-spin" />
 Generating Report...
 </>
 ) : (
 <>
 <FileText className="w-4 h-4 mr-2" />
 Generate Report
 </>
 )}
 </Button>
 </CardContent>
 </Card>

 {/* Generated Report Display */}
 {generatedReport && (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <CheckCircle className="w-5 h-5 text-green-600" />
 Report Generated Successfully
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-4">
 {/* Report Details */}
 <div className="grid grid-cols-2 gap-4">
 <div>
 <Label className="text-sm font-medium text-muted-foreground">
 Report ID
 </Label>
 <p className="text-sm font-mono">{generatedReport.id}</p>
 </div>
 <div>
 <Label className="text-sm font-medium text-muted-foreground">
 Generated
 </Label>
 <p className="text-sm">
 {new Date(generatedReport.generated_date).toLocaleString()}
 </p>
 </div>
 <div>
 <Label className="text-sm font-medium text-muted-foreground">
 Pages
 </Label>
 <p className="text-sm">{generatedReport.page_count}</p>
 </div>
 <div>
 <Label className="text-sm font-medium text-muted-foreground">
 Status
 </Label>
 <div className="flex items-center gap-2">
 {getStatusIcon(generatedReport.validation_status)}
 <Badge variant={
 generatedReport.validation_status === 'valid' ? 'default' :
 generatedReport.validation_status === 'warnings' ? 'secondary' : 'destructive'
 }>
 {generatedReport.validation_status}
 </Badge>
 </div>
 </div>
 </div>

 <Separator />

 {/* Export Options */}
 <div className="space-y-3">
 <Label className="text-sm font-medium">Export Options</Label>
 <div className="flex gap-2">
 <Button
 variant="outline"
 size="sm"
 onClick={() => handleExportReport('pdf')}
 disabled={isExporting}
 >
 <Download className="w-4 h-4 mr-2" />
 Export PDF
 </Button>
 <Button
 variant="outline"
 size="sm"
 onClick={() => handleExportReport('html')}
 disabled={isExporting}
 >
 <Download className="w-4 h-4 mr-2" />
 Export HTML
 </Button>
 <Button
 variant="outline"
 size="sm"
 onClick={() => handleExportReport('json')}
 disabled={isExporting}
 >
 <Download className="w-4 h-4 mr-2" />
 Export JSON
 </Button>
 </div>
 </div>

 {/* Validation Messages */}
 {generatedReport.validation_messages.length > 0 && (
 <div className="space-y-2">
 <Label className="text-sm font-medium">Validation Messages</Label>
 <div className="space-y-1">
 {generatedReport.validation_messages.map((message: string, index: number) => (
 <div key={index} className="flex items-center gap-2 text-sm text-muted-foreground">
 <AlertCircle className="w-3 h-3" />
 {message}
 </div>
 ))}
 </div>
 </div>
 )}
 </CardContent>
 </Card>
 )}

 {/* Data Requirements */}
 {!propertyData && (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <AlertCircle className="w-5 h-5 text-yellow-600" />
 Missing Required Data
 </CardTitle>
 </CardHeader>
 <CardContent>
 <p className="text-sm text-muted-foreground">
 Property data is required to generate reports. Please complete a property assessment first.
 </p>
 </CardContent>
 </Card>
 )}
 </div>
 );
}
