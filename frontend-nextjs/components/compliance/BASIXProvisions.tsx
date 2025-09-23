import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Droplets, Zap, Thermometer, Info, CheckCircle } from 'lucide-react';

interface BASIXProvision {
 id: string;
 provision_type: string;
 numeric_value: number;
 unit: string;
 provision_text: string;
 clause_reference: string;
 confidence_level: number;
}

interface BASIXProvisionsProps {
 climateZone?: string;
 waterZone?: string;
 provisions: BASIXProvision[];
 className?: string;
}

export default function BASIXProvisions({
 climateZone,
 waterZone,
 provisions,
 className = ""
}: BASIXProvisionsProps) {

 const getProvisionIcon = (type: string) => {
 switch(type) {
 case 'energy_efficiency':
 return <Zap className="w-5 h-5 text-yellow-600" />;
 case 'water_efficiency':
 return <Droplets className="w-5 h-5 text-blue-600" />;
 case 'thermal_comfort':
 return <Thermometer className="w-5 h-5 text-orange-600" />;
 default:
 return <Info className="w-5 h-5 text-gray-500" />;
 }
 };

 const getProvisionColor = (type: string) => {
 switch(type) {
 case 'energy_efficiency':
 return 'border-yellow-200 bg-yellow-50';
 case 'water_efficiency':
 return 'border-blue-200 bg-blue-50';
 case 'thermal_comfort':
 return 'border-orange-200 bg-orange-50';
 default:
 return 'border-gray-200 bg-gray-50';
 }
 };

 const formatValue = (value: number, unit: string) => {
 if (unit === 'percent') {
 return `${value}%`;
 } else if (unit === 'stars') {
 return `${value} `;
 }
 return `${value}${unit}`;
 };

 if (!provisions || provisions.length === 0) {
 return null;
 }

 return (
 <Card className={`border-green-200 bg-green-50 ${className}`}>
 <CardHeader className="pb-3">
 <div className="flex items-center justify-between">
 <CardTitle className="flex items-center gap-2 text-lg">
 <Badge className="bg-green-600 text-white px-3 py-1">
 <CheckCircle className="w-4 h-4 mr-1" />
 BASIX
 </Badge>
 Building Sustainability Requirements
 </CardTitle>
 <Badge variant="outline" className="text-xs">
 Tier 1 - Fully Authoritative
 </Badge>
 </div>

 {(climateZone || waterZone) && (
 <div className="flex flex-wrap gap-3 text-sm text-gray-700">
 {climateZone && (
 <div className="flex items-center gap-1">
 <span className="font-medium">Climate Zone:</span>
 <Badge variant="secondary" className="bg-green-100 text-green-800">
 {climateZone}
 </Badge>
 </div>
 )}
 {waterZone && (
 <div className="flex items-center gap-1">
 <span className="font-medium">Water Zone:</span>
 <Badge variant="secondary" className="bg-blue-100 text-blue-800">
 {waterZone}
 </Badge>
 </div>
 )}
 </div>
 )}
 </CardHeader>

 <CardContent className="space-y-4">
 {/* Provision Requirements */}
 <div className="grid gap-3">
 {provisions.map((provision, idx) => (
 <div
 key={provision.id || idx}
 className={`flex items-start gap-3 p-4 rounded-lg border ${getProvisionColor(provision.provision_type)}`}
 >
 <div className="flex-shrink-0 mt-0.5">
 {getProvisionIcon(provision.provision_type)}
 </div>

 <div className="flex-1 min-w-0">
 <div className="flex items-start justify-between gap-2">
 <div className="flex-1">
 <div className="font-medium text-gray-900 text-sm mb-1">
 {provision.clause_reference}
 </div>
 <div className="text-gray-700 text-sm leading-relaxed">
 {provision.provision_text}
 </div>
 </div>

 {provision.numeric_value && (
 <div className="flex-shrink-0 text-right">
 <div className="text-2xl font-bold text-green-700">
 {formatValue(provision.numeric_value, provision.unit)}
 </div>
 {provision.unit === 'percent' && (
 <div className="text-xs text-gray-600">
 reduction target
 </div>
 )}
 </div>
 )}
 </div>

 {/* Confidence indicator */}
 {provision.confidence_level && provision.confidence_level < 1.0 && (
 <div className="mt-2">
 <Badge variant="outline" className="text-xs">
 Confidence: {Math.round(provision.confidence_level * 100)}%
 </Badge>
 </div>
 )}
 </div>
 </div>
 ))}
 </div>

 {/* Information Notice */}
 <Alert className="border-blue-200 bg-blue-50">
 <Info className="w-4 h-4 text-blue-600" />
 <AlertDescription className="text-blue-900">
 <div className="space-y-1">
 <div className="font-medium">BASIX Certificate Required</div>
 <div className="text-sm">
 These targets must be achieved and verified through the BASIX assessment process.
 A BASIX certificate is mandatory for all new residential developments and must be
 submitted with your development application.
 </div>
 <div className="text-xs mt-2 space-y-1">
 <div>• Energy targets are compared to a reference building</div>
 <div>• Water targets include fixtures, fittings, and landscaping</div>
 <div>• Thermal comfort applies to living areas</div>
 </div>
 </div>
 </AlertDescription>
 </Alert>

 {/* Quick Actions */}
 <div className="flex flex-wrap gap-2 pt-2">
 <Badge
 variant="outline"
 className="cursor-pointer hover:bg-green-100 text-xs px-2 py-1"
 onClick={() => window.open('https://www.basix.nsw.gov.au/', '_blank')}
 >
 → BASIX Portal
 </Badge>
 <Badge
 variant="outline"
 className="cursor-pointer hover:bg-blue-100 text-xs px-2 py-1"
 onClick={() => window.open('https://www.basix.nsw.gov.au/iframe/find-assessor.html', '_blank')}
 >
 → Find BASIX Assessor
 </Badge>
 <Badge
 variant="outline"
 className="cursor-pointer hover:bg-gray-100 text-xs px-2 py-1"
 onClick={() => window.open('https://www.basix.nsw.gov.au/iframe/training.html', '_blank')}
 >
 → BASIX Guide
 </Badge>
 </div>
 </CardContent>
 </Card>
 );
}