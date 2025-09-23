'use client';

import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { FileText, Clock, CheckCircle, Users, BarChart } from 'lucide-react';
import { ReportTemplate } from '@/lib/assessment/reports';

interface ReportTemplateSelectorProps {
 templates: ReportTemplate[];
 selectedTemplate?: string;
 onTemplateSelect: (templateId: string) => void;
}

export function ReportTemplateSelector({
 templates,
 selectedTemplate,
 onTemplateSelect
}: ReportTemplateSelectorProps) {

 const getCategoryIcon = (category: string) => {
 switch (category) {
 case 'professional':
 return <Users className="w-4 h-4" />;
 case 'summary':
 return <BarChart className="w-4 h-4" />;
 case 'detailed':
 return <FileText className="w-4 h-4" />;
 case 'executive':
 return <CheckCircle className="w-4 h-4" />;
 default:
 return <FileText className="w-4 h-4" />;
 }
 };

 const getCategoryColor = (category: string) => {
 switch (category) {
 case 'professional':
 return 'bg-blue-100 text-blue-800';
 case 'summary':
 return 'bg-green-100 text-green-800';
 case 'detailed':
 return 'bg-purple-100 text-purple-800';
 case 'executive':
 return 'bg-orange-100 text-orange-800';
 default:
 return 'bg-gray-100 text-gray-800';
 }
 };

 return (
 <div className="space-y-4">
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {templates.map((template) => (
 <Card
 key={template.id}
 className={`cursor-pointer transition-all hover:shadow-md ${
 selectedTemplate === template.id
 ? 'ring-2 ring-blue-500 bg-blue-50'
 : 'hover:bg-gray-50'
 }`}
 onClick={() => onTemplateSelect(template.id)}
 >
 <CardHeader className="pb-3">
 <div className="flex items-start justify-between">
 <div className="flex items-center gap-2">
 {getCategoryIcon(template.category)}
 <CardTitle className="text-lg">{template.name}</CardTitle>
 </div>
 <Badge className={getCategoryColor(template.category)}>
 {template.category}
 </Badge>
 </div>
 </CardHeader>
 <CardContent className="space-y-3">
 <p className="text-sm text-muted-foreground">
 {template.description}
 </p>

 <div className="flex items-center justify-between text-xs text-muted-foreground">
 <div className="flex items-center gap-1">
 <FileText className="w-3 h-3" />
 <span>{template.sections.length} sections</span>
 </div>
 <div className="flex items-center gap-1">
 <Clock className="w-3 h-3" />
 <span>Est. {Math.ceil(template.sections.length * 1.5)} pages</span>
 </div>
 </div>

 <div className="space-y-2">
 <div className="text-xs font-medium text-muted-foreground">
 Included Sections:
 </div>
 <div className="flex flex-wrap gap-1">
 {template.sections.slice(0, 4).map((section) => (
 <Badge key={section.id} variant="outline" className="text-xs">
 {section.title}
 </Badge>
 ))}
 {template.sections.length > 4 && (
 <Badge variant="outline" className="text-xs">
 +{template.sections.length - 4} more
 </Badge>
 )}
 </div>
 </div>

 {selectedTemplate === template.id && (
 <Button size="sm" className="w-full mt-3">
 <CheckCircle className="w-4 h-4 mr-2" />
 Selected Template
 </Button>
 )}
 </CardContent>
 </Card>
 ))}
 </div>
 </div>
 );
}
