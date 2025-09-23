'use client';

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import {
 FileText,
 Download,
 Search,
 Filter,
 Plus,
 Settings,
 BarChart,
 Clock,
 CheckCircle,
 AlertCircle
} from 'lucide-react';
import { ReportGenerator } from '@/components/reports/ReportGenerator';
import { ReportTemplateSelector } from '@/components/reports/ReportTemplateSelector';
import { useReports } from '@/hooks/assessment/useReports';

export default function ReportsPage() {
 const [activeTab, setActiveTab] = useState('generate');
 const [searchTerm, setSearchTerm] = useState('');
 const [filterCategory, setFilterCategory] = useState('all');
 const [templates, setTemplates] = useState<any[]>([]);
 const [selectedTemplate, setSelectedTemplate] = useState('professional_full');
 const [recentReports, setRecentReports] = useState<any[]>([]);

 const { getAvailableTemplates, error } = useReports();

 useEffect(() => {
 loadTemplates();
 loadRecentReports();
 }, []);

 const loadTemplates = async () => {
 const availableTemplates = await getAvailableTemplates();
 setTemplates(availableTemplates);
 };

 const loadRecentReports = () => {
 // Mock recent reports - in real implementation, this would fetch from API
 setRecentReports([
 {
 id: 'report_001',
 name: 'Professional Assessment Report',
 property_address: '123 George Street, Sydney NSW',
 generated_date: '2024-01-15T10:30:00Z',
 template: 'professional_full',
 status: 'completed',
 file_size: '2.4 MB',
 page_count: 24
 },
 {
 id: 'report_002',
 name: 'Summary Report',
 property_address: '456 Pitt Street, Sydney NSW',
 generated_date: '2024-01-14T14:22:00Z',
 template: 'summary',
 status: 'completed',
 file_size: '890 KB',
 page_count: 8
 }
 ]);
 };

 const handleReportGenerated = (report: any) => {
 setRecentReports(prev => [report, ...prev]);
 setActiveTab('recent');
 };

 const filteredTemplates = templates.filter(template => {
 const matchesSearch = template.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
 template.description.toLowerCase().includes(searchTerm.toLowerCase());
 const matchesCategory = filterCategory === 'all' || template.category === filterCategory;
 return matchesSearch && matchesCategory;
 });

 const getStatusIcon = (status: string) => {
 switch (status) {
 case 'completed':
 return <CheckCircle className="w-4 h-4 text-green-600" />;
 case 'processing':
 return <Clock className="w-4 h-4 text-yellow-600" />;
 case 'failed':
 return <AlertCircle className="w-4 h-4 text-red-600" />;
 default:
 return <Clock className="w-4 h-4 text-gray-400" />;
 }
 };

 return (
 <div className="container mx-auto px-6 py-8">
 <div className="flex justify-between items-center mb-8">
 <div>
 <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
 <p className="text-muted-foreground mt-2">
 Generate professional compliance assessment reports for NSW planning applications
 </p>
 </div>
 <Button onClick={() => setActiveTab('generate')}>
 <Plus className="w-4 h-4 mr-2" />
 New Report
 </Button>
 </div>

 {/* Error Display */}
 {error && (
 <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
 <div className="flex items-center gap-2 text-red-700">
 <AlertCircle className="w-5 h-5" />
 <span className="font-medium">Error</span>
 </div>
 <p className="text-red-600 mt-1">{error}</p>
 </div>
 )}

 <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
 <TabsList>
 <TabsTrigger value="generate" className="flex items-center gap-2">
 <FileText className="w-4 h-4" />
 Generate Report
 </TabsTrigger>
 <TabsTrigger value="templates" className="flex items-center gap-2">
 <Settings className="w-4 h-4" />
 Templates
 </TabsTrigger>
 <TabsTrigger value="recent" className="flex items-center gap-2">
 <BarChart className="w-4 h-4" />
 Recent Reports
 </TabsTrigger>
 </TabsList>

 {/* Generate Report Tab */}
 <TabsContent value="generate" className="space-y-6">
 <Card>
 <CardHeader>
 <CardTitle>Generate New Report</CardTitle>
 </CardHeader>
 <CardContent>
 <ReportGenerator
 onReportGenerated={handleReportGenerated}
 propertyData={{
 id: 1,
 address: '123 Example Street, Sydney NSW 2000',
 owner: 'Property Owner'
 }}
 />
 </CardContent>
 </Card>
 </TabsContent>

 {/* Templates Tab */}
 <TabsContent value="templates" className="space-y-6">
 {/* Template Filters */}
 <Card>
 <CardHeader>
 <CardTitle>Report Templates</CardTitle>
 </CardHeader>
 <CardContent className="space-y-4">
 <div className="flex gap-4">
 <div className="flex-1">
 <Label htmlFor="search">Search Templates</Label>
 <div className="relative">
 <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground w-4 h-4" />
 <Input
 id="search"
 value={searchTerm}
 onChange={(e) => setSearchTerm(e.target.value)}
 placeholder="Search by name or description..."
 className="pl-10"
 />
 </div>
 </div>
 <div>
 <Label htmlFor="category">Category</Label>
 <Select value={filterCategory} onValueChange={setFilterCategory}>
 <SelectTrigger className="w-48">
 <SelectValue />
 </SelectTrigger>
 <SelectContent>
 <SelectItem value="all">All Categories</SelectItem>
 <SelectItem value="professional">Professional</SelectItem>
 <SelectItem value="summary">Summary</SelectItem>
 <SelectItem value="detailed">Detailed</SelectItem>
 <SelectItem value="executive">Executive</SelectItem>
 </SelectContent>
 </Select>
 </div>
 </div>

 <ReportTemplateSelector
 templates={filteredTemplates}
 selectedTemplate={selectedTemplate}
 onTemplateSelect={setSelectedTemplate}
 />
 </CardContent>
 </Card>
 </TabsContent>

 {/* Recent Reports Tab */}
 <TabsContent value="recent" className="space-y-6">
 <Card>
 <CardHeader>
 <CardTitle>Recent Reports</CardTitle>
 </CardHeader>
 <CardContent>
 {recentReports.length === 0 ? (
 <div className="text-center py-8 text-muted-foreground">
 <FileText className="w-12 h-12 mx-auto mb-4 opacity-50" />
 <p>No reports generated yet</p>
 <Button
 variant="outline"
 onClick={() => setActiveTab('generate')}
 className="mt-4"
 >
 Generate Your First Report
 </Button>
 </div>
 ) : (
 <div className="space-y-4">
 {recentReports.map((report) => (
 <Card key={report.id}>
 <CardContent className="p-4">
 <div className="flex items-center justify-between">
 <div className="flex-1">
 <div className="flex items-center gap-3 mb-2">
 <div className="flex items-center gap-2">
 {getStatusIcon(report.status)}
 <h3 className="font-medium">{report.name}</h3>
 </div>
 <Badge variant="outline">{report.template}</Badge>
 </div>
 <p className="text-sm text-muted-foreground mb-1">
 {report.property_address}
 </p>
 <div className="flex items-center gap-4 text-xs text-muted-foreground">
 <span>Generated: {new Date(report.generated_date).toLocaleString()}</span>
 <span>{report.file_size}</span>
 <span>{report.page_count} pages</span>
 </div>
 </div>
 <div className="flex gap-2">
 <Button variant="outline" size="sm">
 <Download className="w-4 h-4 mr-2" />
 Download
 </Button>
 </div>
 </div>
 </CardContent>
 </Card>
 ))}
 </div>
 )}
 </CardContent>
 </Card>
 </TabsContent>
 </Tabs>
 </div>
 );
}
