// components/analysis/EnhancedSetbackVerification.tsx
'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
 Loader2, 
 Calculator, 
 AlertTriangle, 
 CheckCircle2, 
 FileText, 
 Scale, 
 Info,
 ChevronDown,
 ChevronUp,
 Building,
 Ruler,
 Shield,
 CheckCircle,
 AlertCircle,
 Award
} from 'lucide-react';
import { useSetbackCalculation } from '@/hooks/useSetbackCalculation';
import type { PropertyData, LotGeometry } from '@/types/property';
import type { SetbackResult } from '@/types/setback';

interface EnhancedSetbackVerificationProps {
 property: PropertyData | null;
 lotGeometry: LotGeometry | null;
 nswPlanningData?: any; // NSW Planning API response
 loading?: boolean;
 error?: string | null;
}

export function EnhancedSetbackVerification({ 
 property, 
 lotGeometry,
 nswPlanningData,
 loading: externalLoading,
 error: externalError
}: EnhancedSetbackVerificationProps) {
 const { 
 results, 
 buildableArea, 
 calculating, 
 error: calculationError, 
 calculateSetbacks 
 } = useSetbackCalculation();

 const [attempted, setAttempted] = useState(false);
 const [expandedCards, setExpandedCards] = useState<Set<string>>(new Set());

 // Extract planning context from NSW data
 const planningContext = extractPlanningContext(nswPlanningData);

 const handleCalculate = () => {
 if (property?.prop_id && lotGeometry) {
 setAttempted(true);
 
 const lotArea = estimateLotArea(lotGeometry);
 
 calculateSetbacks({
 property_id: property.prop_id,
 lot_geometry: lotGeometry,
 property_zone: property.zone || planningContext.zone || 'R2',
 lot_area: lotArea
 });
 }
 };

 const toggleCard = (boundaryType: string) => {
 const newExpanded = new Set(expandedCards);
 if (newExpanded.has(boundaryType)) {
 newExpanded.delete(boundaryType);
 } else {
 newExpanded.add(boundaryType);
 }
 setExpandedCards(newExpanded);
 };

 // Loading state
 if (calculating || externalLoading) {
 return (
 <Card>
 <CardContent className="p-8">
 <div className="flex items-center justify-center gap-3">
 <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
 <span className="text-lg">Calculating precise setbacks with full verification...</span>
 </div>
 </CardContent>
 </Card>
 );
 }

 // Error state
 if (calculationError || externalError) {
 return (
 <Card className="border-red-200 bg-red-50">
 <CardContent className="p-8">
 <div className="text-center">
 <AlertTriangle className="h-12 w-12 mx-auto mb-4 text-red-500" />
 <h3 className="text-lg font-semibold mb-2">Calculation Error</h3>
 <p className="text-sm text-gray-700 mb-4">{calculationError || externalError}</p>
 <Button onClick={handleCalculate} variant="outline" size="sm">
 Retry Calculation
 </Button>
 </div>
 </CardContent>
 </Card>
 );
 }

 // No geometry available
 if (!lotGeometry) {
 return (
 <Card>
 <CardContent className="p-8">
 <div className="text-center text-gray-500">
 <Calculator className="h-12 w-12 mx-auto mb-4 opacity-50" />
 <h3 className="text-lg font-semibold mb-2">Lot Geometry Required</h3>
 <p className="text-sm mb-4">
 Precise setback calculations require lot boundary data from NSW Planning Portal.
 </p>
 </div>
 </CardContent>
 </Card>
 );
 }

 // Ready to calculate
 if (!attempted || !results || results.length === 0) {
 return (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <Calculator className="h-5 w-5" />
 NSW Compliant Setback Verification System
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-4">
 {/* Property Summary */}
 <div className="bg-blue-50 p-4 rounded-lg">
 <h4 className="font-semibold mb-2">Property Details</h4>
 <div className="grid grid-cols-2 gap-2 text-sm">
 <div>Address: {property?.address || 'Not specified'}</div>
 <div>Zone: {property?.zone || planningContext.zone || 'Unknown'}</div>
 <div>LEP: {planningContext.lep || 'Not available'}</div>
 <div>SEPPs: {planningContext.sepps?.length || 0} applicable</div>
 </div>
 </div>

 {/* Calculate Button */}
 <div className="text-center py-4">
 <Button 
 onClick={handleCalculate}
 disabled={!property?.prop_id}
 size="lg"
 className="w-full md:w-auto"
 >
 <Calculator className="mr-2 h-5 w-5" />
 Calculate Setbacks with Full Verification
 </Button>
 <p className="text-xs text-gray-500 mt-2">
 Includes legislation quotes, authority levels, and compliance hierarchy
 </p>
 </div>
 </div>
 </CardContent>
 </Card>
 );
 }

 // Display Results with Full Verification
 return (
 <div className="space-y-6">
 {/* Header */}
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <CheckCircle2 className="h-5 w-5 text-green-600" />
 NSW Compliant Setback Verification Results
 {/* Phase 1A Enhancement Indicator */}
 {results.some(r => r.legal_authority || r.domain_classification) && (
 <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded font-medium">
 Phase 1A Enhanced
 </span>
 )}
 </div>
 <div className="flex items-center gap-2">
 <span className="text-sm font-normal text-green-600 bg-green-50 px-2 py-1 rounded border border-green-200">
 Precision: Centimeter
 </span>
 {/* Domain Classification Count */}
 {results.filter(r => r.cross_contamination_checked).length > 0 && (
 <span className="text-xs font-normal text-emerald-600 bg-emerald-50 px-2 py-1 rounded border border-emerald-200">
 {results.filter(r => r.cross_contamination_checked).length} Cross-Contamination Checks
 </span>
 )}
 </div>
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="flex items-start gap-2 text-sm text-gray-600">
 <Info className="h-4 w-4 mt-0.5" />
 <p>
 Calculations based on NSW Planning API data with enhanced domain classification, 
 cross-contamination prevention, and complete legal authority hierarchy 
 (LEP → DCP → SEPP) for certifier verification.
 {results.some(r => r.cross_contamination_checked) && (
 <span className="text-green-600 font-medium"> Cross-domain contamination prevention active.</span>
 )}
 </p>
 </div>
 </CardContent>
 </Card>

 {/* Compliance Hierarchy */}
 <ComplianceHierarchy results={results} />

 {/* Multiple Rules Explanation */}
 {results.filter(r => r.boundary_type === 'side').length > 1 && (
 <Card className="border-blue-200 bg-blue-50">
 <CardContent className="p-4">
 <div className="flex items-start gap-2">
 <Info className="h-4 w-4 text-blue-600 mt-0.5 flex-shrink-0" />
 <div className="text-sm">
 <strong>Multiple Setback Rules Explained</strong>
 <p className="mt-1 text-blue-800">
 Different setback requirements apply based on your development type. 
 The system shows all applicable rules - choose the one matching your intended building height:
 <span className="block mt-2 font-medium">
 • Single storey = smaller setbacks • Two storey = medium setbacks • Three storey = larger setbacks
 </span>
 </p>
 </div>
 </div>
 </CardContent>
 </Card>
 )}

 {/* Setback Results with Full Verification */}
 <div className="space-y-4">
 {results.map((result, index) => (
 <EnhancedSetbackCard 
 key={`${result.boundary_type}-${index}`} 
 result={result}
 index={index + 1}
 isExpanded={expandedCards.has(result.boundary_type)}
 onToggle={() => toggleCard(result.boundary_type)}
 />
 ))}
 </div>

 {/* Buildable Area Analysis */}
 {buildableArea && (
 <BuildableAreaAnalysis buildableArea={buildableArea} />
 )}

 {/* Professional Disclaimer */}
 <Card className="border-yellow-200 bg-yellow-50">
 <CardContent className="p-4">
 <div className="flex items-start gap-2">
 <AlertTriangle className="h-4 w-4 text-yellow-600 mt-0.5 flex-shrink-0" />
 <div className="text-sm">
 <strong>Professional Verification Required</strong>
 <p className="mt-1 text-gray-700">
 These calculations provide comprehensive regulatory citations and legislation quotes 
 for professional use. Final design must be verified by a certified professional 
 against current planning instruments.
 </p>
 </div>
 </div>
 </CardContent>
 </Card>
 </div>
 );
}

// Enhanced Setback Card with Full Verification Display
function EnhancedSetbackCard({ 
 result, 
 index, 
 isExpanded, 
 onToggle 
}: { 
 result: SetbackResult; 
 index: number;
 isExpanded: boolean;
 onToggle: () => void;
}) {
 const boundaryTypeColors = {
 front: 'border-blue-200 bg-blue-50',
 rear: 'border-green-200 bg-green-50', 
 side_left: 'border-purple-200 bg-purple-50',
 side_right: 'border-orange-200 bg-orange-50',
 side: 'border-purple-200 bg-purple-50'
 };

 const colorClass = boundaryTypeColors[result.boundary_type] || 'border-gray-200 bg-gray-50';
 
 // Parse source provision to extract document and clause
 const [document, provisionText] = result.database_source?.split(': ') || ['', ''];
 
 // Determine authority icon
 const getAuthorityIcon = () => {
 const authority = result.authority || result.authority_level || 'DCP';
 switch(authority) {
 case 'SEPP': return <Scale className="h-4 w-4 text-red-600" />;
 case 'LEP': return <FileText className="h-4 w-4 text-blue-600" />;
 case 'DCP': return <Building className="h-4 w-4 text-green-600" />;
 default: return <Info className="h-4 w-4 text-gray-600" />;
 }
 };

 return (
 <Card className={`${colorClass} transition-all duration-200`}>
 <CardHeader 
 className="cursor-pointer"
 onClick={onToggle}
 >
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <div className="text-lg font-semibold">
 {result.boundary_type.replace('_', ' ').toUpperCase()} Setback
 {/* Show storey information from conditions field */}
 <span className="text-sm font-normal text-purple-600 ml-2">
 ({result.conditions || `Rule ${index}`})
 </span>
 </div>
 {getAuthorityIcon()}
 <span className="text-sm font-normal text-blue-600 bg-blue-50 px-2 py-1 rounded border border-blue-200">
 {result.authority || result.authority_level || 'DCP'} • Level {result.precedence || result.legal_precedence || 3}
 </span>
 
 {/* Enhanced Storey Information Display */}
 <span className="text-sm font-medium text-purple-700 bg-purple-50 px-3 py-1 rounded-full border border-purple-200">
 {result.conditions || 'Multi-Storey Rule'}
 </span>
 
 {/* Rule Type Badge */}
 <span className="text-xs font-medium text-gray-600 bg-gray-50 px-2 py-1 rounded border border-gray-200">
 #{index} {result.required_setback}m
 </span>
 
 {/* Phase 1A: Domain Classification Badge */}
 {result.domain_classification && (
 <span className={`text-xs font-normal px-2 py-1 rounded border ${getDomainBadgeColor(result.domain_classification)}`}>
 {getDomainDisplayName(result.domain_classification)}
 </span>
 )}
 
 {/* Phase 1A: Cross-Contamination Status */}
 {result.cross_contamination_checked && (
 <div className="flex items-center gap-1">
 <CheckCircle className="h-3 w-3 text-green-600" />
 <span className="text-xs text-green-600">Verified</span>
 </div>
 )}
 </div>
 {isExpanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
 </div>
 </CardHeader>
 
 <CardContent>
 {/* Main Measurement Display */}
 <div className="grid grid-cols-3 gap-4 mb-4">
 <div className="text-center">
 <div className="text-3xl font-bold text-gray-900">
 {result.required_setback}m
 </div>
 <div className="text-sm text-gray-600">Required Setback</div>
 {result.conditions && result.conditions !== 'None' && (
 <div className="text-xs text-purple-600 font-medium mt-1">
 {result.conditions}
 </div>
 )}
 </div>
 <div className="text-center">
 <div className="text-3xl font-bold text-blue-600">
 {result.buildable_depth}m
 </div>
 <div className="text-sm text-gray-600">Buildable Depth</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold">
 <span className={`text-${result.confidence >= 0.8 ? 'green' : result.confidence >= 0.6 ? 'yellow' : 'red'}-600`}>
 {Math.round(result.confidence >= 1 ? result.confidence : result.confidence * 100)}%
 </span>
 </div>
 <div className="text-sm text-gray-600">Confidence</div>
 </div>
 </div>

 {/* Expanded Verification Details */}
 {isExpanded && (
 <div className="space-y-4 pt-4 border-t">
 {/* Phase 1A Enhanced Legal Authority */}
 {result.legal_authority ? (
 <div className="bg-white p-4 rounded border border-green-200">
 <h4 className="font-semibold mb-2 flex items-center gap-2">
 <Shield className="h-4 w-4 text-green-600" />
 ENHANCED LEGAL AUTHORITY (Phase 1A):
 </h4>
 <div className="space-y-2 text-sm">
 <div className="grid grid-cols-2 gap-4">
 <div>
 <strong>Primary Authority:</strong>
 <div className="text-blue-600">{result.legal_authority.primary_authority}</div>
 </div>
 <div>
 <strong>Secondary Authority:</strong>
 <div className="text-green-600">{result.legal_authority.secondary_authority}</div>
 </div>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div>
 <strong>Clause Reference:</strong>
 <div className="font-mono text-xs">{result.legal_authority.clause_reference}</div>
 </div>
 <div>
 <strong>Amendment:</strong>
 <div className="text-purple-600">{result.legal_authority.amendment_reference}</div>
 </div>
 </div>
 {result.legal_authority.override_authority && (
 <div className="bg-yellow-50 p-2 rounded border border-yellow-200">
 <strong>SEPP Override:</strong> {result.legal_authority.override_authority}
 </div>
 )}
 <div className="text-xs text-gray-500 mt-2">
 <strong>Source Document:</strong> {result.legal_authority.document_source}
 </div>
 </div>
 </div>
 ) : (
 /* Fallback to legacy citation */
 <div className="bg-white p-4 rounded">
 <h4 className="font-semibold mb-2 flex items-center gap-2">
 <FileText className="h-4 w-4" />
 REGULATORY CITATION:
 </h4>
 <div className="space-y-1 text-sm">
 <div><strong>Document:</strong> {document || 'NSW Planning Database'}</div>
 <div><strong>Authority Level:</strong> {result.authority_level || 'DCP'}</div>
 <div><strong>Legal Precedence:</strong> {result.legal_precedence || 3}</div>
 <div><strong>Can be Varied:</strong> {result.can_be_varied ? 'Yes' : 'No'}</div>
 </div>
 </div>
 )}

 {/* Phase 1A Domain Classification & Cross-Contamination */}
 {(result.domain_classification || result.relevance_score !== undefined || result.cross_contamination_checked) && (
 <div className="bg-blue-50 p-4 rounded border border-blue-200">
 <h4 className="font-semibold mb-2 flex items-center gap-2">
 <Award className="h-4 w-4 text-blue-600" />
 DOMAIN CLASSIFICATION & QUALITY ASSURANCE:
 </h4>
 <div className="space-y-2 text-sm">
 {result.domain_classification && (
 <div className="flex items-center justify-between">
 <div>
 <strong>Domain:</strong> {getDomainDisplayName(result.domain_classification)}
 </div>
 <span className={`px-2 py-1 rounded text-xs ${getDomainBadgeColor(result.domain_classification)}`}>
 {result.domain_classification}
 </span>
 </div>
 )}
 {result.relevance_score !== undefined && (
 <div className="flex items-center justify-between">
 <div><strong>Relevance Score:</strong></div>
 <div className={`font-bold ${result.relevance_score >= 0.8 ? 'text-green-600' : result.relevance_score >= 0.6 ? 'text-yellow-600' : 'text-red-600'}`}>
 {(result.relevance_score * 100).toFixed(0)}% {result.relevance_score >= 0.8 ? '(High)' : result.relevance_score >= 0.6 ? '(Medium)' : '(Low)'}
 </div>
 </div>
 )}
 {result.cross_contamination_checked && (
 <div className="flex items-center gap-2 text-green-600">
 <CheckCircle className="h-4 w-4" />
 <span><strong>Cross-Contamination Check:</strong> Passed - No signage/residential mixing detected</span>
 </div>
 )}
 {result.zone_applicability && (
 <div>
 <strong>Zone Applicability:</strong> {result.zone_applicability}
 </div>
 )}
 </div>
 </div>
 )}

 {/* Legislation Quoted */}
 {provisionText && (
 <div className="bg-white p-4 rounded">
 <h4 className="font-semibold mb-2 flex items-center gap-2">
 <Scale className="h-4 w-4" />
 LEGISLATION QUOTED:
 </h4>
 <blockquote className="border-l-4 border-gray-300 pl-4 italic text-sm text-gray-700">
 "{provisionText}"
 </blockquote>
 </div>
 )}

 {/* Calculation Justification */}
 <div className="bg-white p-4 rounded">
 <h4 className="font-semibold mb-2 flex items-center gap-2">
 <Calculator className="h-4 w-4" />
 CALCULATION JUSTIFICATION:
 </h4>
 <div className="text-sm text-gray-700">
 <p>{result.reasoning || 'Database-sourced planning requirement'}</p>
 <div className="mt-2 text-xs text-gray-500">
 <strong>Precision:</strong> {result.precision_level || 'centimeter'}
 </div>
 </div>
 </div>

 {/* Compliance Notes */}
 {result.can_be_varied && (
 <div className="bg-yellow-50 p-3 rounded text-sm">
 <strong>Variation Possible:</strong> This requirement can be varied under 
 {result.authority_level === 'LEP' ? ' Clause 4.6' : ' DCP provisions'} 
 with proper justification demonstrating compliance is unreasonable or 
 unnecessary and there are sufficient environmental planning grounds.
 </div>
 )}
 </div>
 )}
 </CardContent>
 </Card>
 );
}

// Compliance Hierarchy Component
function ComplianceHierarchy({ results }: { results: SetbackResult[] }) {
 // Extract unique authority levels
 const authorities = new Map<string, number>();
 results.forEach(r => {
 const level = r.authority_level || 'DCP';
 const precedence = r.legal_precedence || 3;
 if (!authorities.has(level) || authorities.get(level)! > precedence) {
 authorities.set(level, precedence);
 }
 });

 const sortedAuthorities = Array.from(authorities.entries())
 .sort((a, b) => a[1] - b[1]);

 if (sortedAuthorities.length === 0) return null;

 return (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <Scale className="h-5 w-5" />
 Compliance Hierarchy Applied
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="space-y-2">
 {sortedAuthorities.map(([authority, precedence], index) => (
 <div key={authority} className="flex items-center gap-3">
 <div className={`text-lg font-bold ${precedence === 1 ? 'text-red-600' : precedence === 2 ? 'text-blue-600' : 'text-green-600'}`}>
 {precedence}
 </div>
 <div>
 <strong>{authority}</strong>
 {precedence === 1 && ' - Cannot be varied (State level)'}
 {precedence === 2 && ' - Can be varied with Clause 4.6 justification'}
 {precedence === 3 && ' - Can be varied with council approval'}
 </div>
 </div>
 ))}
 </div>
 <div className="mt-4 text-xs text-gray-600 bg-gray-50 p-3 rounded">
 Lower precedence numbers override higher numbers. SEPP (1) &gt; LEP (2) &gt; DCP (3).
 </div>
 </CardContent>
 </Card>
 );
}

// Buildable Area Analysis Component
function BuildableAreaAnalysis({ buildableArea }: { buildableArea: any }) {
 const getStatusColor = (percentage: number) => {
 if (percentage >= 60) return 'text-green-600';
 if (percentage >= 40) return 'text-yellow-600';
 return 'text-red-600';
 };

 return (
 <Card>
 <CardHeader>
 <CardTitle className="flex items-center gap-2">
 <Building className="h-5 w-5" />
 Buildable Area Analysis
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
 <div className="text-center">
 <div className="text-2xl font-bold text-gray-900">
 {buildableArea.total_lot_area}m²
 </div>
 <div className="text-sm text-gray-600">Total Lot Area</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-green-600">
 {buildableArea.buildable_area}m²
 </div>
 <div className="text-sm text-gray-600">Buildable Area</div>
 </div>
 <div className="text-center">
 <div className={`text-2xl font-bold ${getStatusColor(buildableArea.buildable_percentage)}`}>
 {buildableArea.buildable_percentage}%
 </div>
 <div className="text-sm text-gray-600">Buildable %</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-red-600">
 {buildableArea.setback_area_lost}m²
 </div>
 <div className="text-sm text-gray-600">Lost to Setbacks</div>
 </div>
 </div>
 
 {buildableArea.buildable_percentage < 50 && (
 <div className="mt-4 p-3 bg-yellow-50 rounded text-sm">
 <strong>Design Note:</strong> Low buildable percentage may affect development 
 viability. Consider design optimization or variation applications where permitted.
 </div>
 )}
 </CardContent>
 </Card>
 );
}

// Phase 1A Helper Functions for Domain Classification
function getDomainDisplayName(domain: string): string {
 const domainNames: { [key: string]: string } = {
 'RESIDENTIAL_BUILDINGS': 'Residential Buildings',
 'COMMERCIAL_BUILDINGS': 'Commercial Buildings', 
 'INDUSTRIAL_BUILDINGS': 'Industrial Buildings',
 'SIGNAGE_ADVERTISING': 'Signage & Advertising',
 'PARKING_TRANSPORT': 'Parking & Transport',
 'HERITAGE_CONSERVATION': 'Heritage Conservation',
 'ENVIRONMENTAL_PROTECTION': 'Environmental Protection',
 'INFRASTRUCTURE_UTILITIES': 'Infrastructure & Utilities',
 'GENERAL_PROVISIONS': 'General Provisions'
 };
 return domainNames[domain] || domain;
}

function getDomainBadgeColor(domain: string): string {
 const domainColors: { [key: string]: string } = {
 'RESIDENTIAL_BUILDINGS': 'text-green-700 bg-green-100 border-green-300',
 'COMMERCIAL_BUILDINGS': 'text-blue-700 bg-blue-100 border-blue-300',
 'INDUSTRIAL_BUILDINGS': 'text-purple-700 bg-purple-100 border-purple-300',
 'SIGNAGE_ADVERTISING': 'text-red-700 bg-red-100 border-red-300',
 'PARKING_TRANSPORT': 'text-orange-700 bg-orange-100 border-orange-300',
 'HERITAGE_CONSERVATION': 'text-yellow-700 bg-yellow-100 border-yellow-300',
 'ENVIRONMENTAL_PROTECTION': 'text-emerald-700 bg-emerald-100 border-emerald-300',
 'INFRASTRUCTURE_UTILITIES': 'text-gray-700 bg-gray-100 border-gray-300',
 'GENERAL_PROVISIONS': 'text-slate-700 bg-slate-100 border-slate-300'
 };
 return domainColors[domain] || 'text-gray-700 bg-gray-100 border-gray-300';
}

// Helper Functions
function estimateLotArea(geometry: LotGeometry): number {
 if (!geometry || !geometry.rings || geometry.rings.length === 0) {
 return 0;
 }
 
 const ring = geometry.rings[0];
 if (!ring || ring.length < 3) {
 return 0;
 }
 
 let area = 0;
 for (let i = 0; i < ring.length - 1; i++) {
 area += ring[i][0] * ring[i + 1][1];
 area -= ring[i + 1][0] * ring[i][1];
 }
 
 return Math.abs(area / 2);
}

function extractPlanningContext(nswData: any) {
 if (!nswData) return {};
 
 const context: any = {};
 
 // Extract zone
 const zoningLayer = nswData?.find((layer: any) => layer.layerName === 'Land Zoning Map');
 if (zoningLayer?.results?.[0]) {
 context.zone = zoningLayer.results[0].Zone;
 context.landUse = zoningLayer.results[0]['Land Use'];
 }
 
 // Extract LEP
 const lepLayer = nswData?.find((layer: any) => layer.layerName === 'Land Application Map');
 if (lepLayer?.results?.[0]) {
 context.lep = lepLayer.results[0]['EPI Name'];
 }
 
 // Extract SEPPs
 const seppLayer = nswData?.find((layer: any) => layer.layerName === 'Special Provisions');
 if (seppLayer?.results) {
 context.sepps = seppLayer.results
 .filter((r: any) => r['EPI Type'] === 'SEPP')
 .map((r: any) => r['EPI Name']);
 }
 
 // Extract key clauses
 const keySitesLayer = nswData?.find((layer: any) => layer.layerName === 'Key Sites Map');
 if (keySitesLayer?.results?.[0]) {
 context.legislativeClauses = keySitesLayer.results[0]['Legislative Clause'];
 }
 
 return context;
}

export default EnhancedSetbackVerification;