import { useState, useCallback } from 'react';
import { ReportConfig, GeneratedReport, ReportExportOptions, REPORT_TEMPLATES } from '@/lib/assessment/reports';

interface UseReportsReturn {
 isGenerating: boolean;
 isExporting: boolean;
 generateReport: (config: ReportConfig) => Promise<GeneratedReport | null>;
 exportReport: (content: any, options: ReportExportOptions) => Promise<void>;
 downloadReport: (reportId: string, format: string) => Promise<void>;
 getAvailableTemplates: () => Promise<any[]>;
 error: string | null;
 clearError: () => void;
}

export function useReports(): UseReportsReturn {
 const [isGenerating, setIsGenerating] = useState(false);
 const [isExporting, setIsExporting] = useState(false);
 const [error, setError] = useState<string | null>(null);

 const clearError = useCallback(() => {
 setError(null);
 }, []);

 const generateReport = useCallback(async (config: ReportConfig): Promise<GeneratedReport | null> => {
 setIsGenerating(true);
 setError(null);

 try {
 const response = await fetch('/api/reports/generate', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify(config),
 });

 const data = await response.json();

 if (!response.ok) {
 throw new Error(data.error || 'Failed to generate report');
 }

 if (!data.success) {
 throw new Error('Report generation failed');
 }

 return data.report;

 } catch (err) {
 const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
 setError(errorMessage);
 console.error('Report generation error:', err);
 return null;
 } finally {
 setIsGenerating(false);
 }
 }, []);

 const exportReport = useCallback(async (content: any, options: ReportExportOptions): Promise<void> => {
 setIsExporting(true);
 setError(null);

 try {
 const response = await fetch('/api/reports/export', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify({ content, options }),
 });

 if (!response.ok) {
 const errorData = await response.json();
 throw new Error(errorData.error || 'Failed to export report');
 }

 // Handle file download
 const blob = await response.blob();
 const url = window.URL.createObjectURL(blob);
 const link = document.createElement('a');
 link.href = url;

 const fileName = `compliance_report_${Date.now()}.${options.format}`;
 link.download = fileName;

 document.body.appendChild(link);
 link.click();
 document.body.removeChild(link);
 window.URL.revokeObjectURL(url);

 } catch (err) {
 const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
 setError(errorMessage);
 console.error('Report export error:', err);
 } finally {
 setIsExporting(false);
 }
 }, []);

 const downloadReport = useCallback(async (reportId: string, format: string): Promise<void> => {
 // This would be implemented to download previously generated reports
 setError('Download functionality not yet implemented');
 }, []);

 const getAvailableTemplates = useCallback(async (): Promise<any[]> => {
 try {
 const response = await fetch('/api/reports/generate?action=templates');
 const data = await response.json();

 if (!response.ok) {
 throw new Error(data.error || 'Failed to fetch templates');
 }

 return data.templates;

 } catch (err) {
 const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
 setError(errorMessage);
 console.error('Template fetch error:', err);
 return [];
 }
 }, []);

 return {
 isGenerating,
 isExporting,
 generateReport,
 exportReport,
 downloadReport,
 getAvailableTemplates,
 error,
 clearError,
 };
}

// Additional utility hooks for specific report types
export function useComplianceReport() {
 const reports = useReports();

 const generateComplianceReport = useCallback(async (
 propertyData: any,
 assessmentData: any,
 complianceData: any,
 templateId: string = 'professional_full'
 ) => {
 const config: ReportConfig = {
 template_id: templateId,
 property_data: propertyData,
 assessment_data: assessmentData,
 compliance_data: complianceData,
 export_format: 'pdf',
 include_attachments: true
 };

 return reports.generateReport(config);
 }, [reports]);

 return {
 ...reports,
 generateComplianceReport
 };
}

export function useSummaryReport() {
 const reports = useReports();

 const generateSummaryReport = useCallback(async (
 propertyData: any,
 complianceData: any
 ) => {
 const config: ReportConfig = {
 template_id: 'summary',
 property_data: propertyData,
 assessment_data: null,
 compliance_data: complianceData,
 export_format: 'pdf',
 include_attachments: false
 };

 return reports.generateReport(config);
 }, [reports]);

 return {
 ...reports,
 generateSummaryReport
 };
}
