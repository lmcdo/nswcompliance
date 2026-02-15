// components/compliance/ReferencedLegislationAccordion.tsx
'use client';

import { useState, useCallback } from 'react';
import { ChevronDown, ChevronRight, FileText, Scale, Book, AlertCircle } from 'lucide-react';
import { AuthorityColors } from '@/lib/design-tokens';

interface LegislationClause {
 id: number;
 clause_reference: string;
 full_text: string;
 section_header?: string;
 document_name: string;
 document_type: 'SEPP' | 'LEP' | 'DCP';
 authority_explanation: string;
 legal_context: string;
 page_number?: number;
}

interface SetbackReference {
 boundary_type: string;
 clause_reference: string;
 legal_source: string;
 provision_id?: number;
 legal_authority?: {
 primary_authority: string;
 secondary_authority: string;
 document_source: string;
 };
}

interface ReferencedLegislationAccordionProps {
 setbacks: SetbackReference[];
 className?: string;
}

export function ReferencedLegislationAccordion({ 
 setbacks, 
 className = '' 
}: ReferencedLegislationAccordionProps) {
 const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());
 const [loadedClauses, setLoadedClauses] = useState<Map<number, LegislationClause>>(new Map());
 const [loading, setLoading] = useState<Set<number>>(new Set());

 // Group setbacks by authority type for hierarchical display
 const groupedReferences = useCallback(() => {
 const groups: { [key: string]: SetbackReference[] } = {
 'SEPP': [],
 'LEP': [],
 'DCP': []
 };

 setbacks.forEach(setback => {
 // Determine authority level from source document
 const source = setback.legal_source || setback.legal_authority?.document_source || '';
 if (source.toUpperCase().includes('SEPP')) {
 groups.SEPP.push(setback);
 } else if (source.toUpperCase().includes('LEP')) {
 groups.LEP.push(setback);
 } else {
 groups.DCP.push(setback);
 }
 });

 // Remove empty groups
 return Object.fromEntries(
 Object.entries(groups).filter(([_, refs]) => refs.length > 0)
 );
 }, [setbacks]);

 const toggleSection = (sectionId: string) => {
 const newExpanded = new Set(expandedSections);
 if (newExpanded.has(sectionId)) {
 newExpanded.delete(sectionId);
 } else {
 newExpanded.add(sectionId);
 }
 setExpandedSections(newExpanded);
 };

 const loadClauseText = async (provisionId: number) => {
 if (loadedClauses.has(provisionId) || loading.has(provisionId)) {
 return;
 }

 setLoading(prev => new Set([...prev, provisionId]));

 try {
 const response = await fetch(`/api/clause/${provisionId}`);
 const data = await response.json();

 if (data.success && data.clause) {
 setLoadedClauses(prev => new Map([...prev, [provisionId, data.clause]]));
 } else {
 console.warn(`Failed to load clause ${provisionId}:`, data.error);
 }
 } catch (error) {
 console.error(`Error loading clause ${provisionId}:`, error);
 } finally {
 setLoading(prev => {
 const newLoading = new Set(prev);
 newLoading.delete(provisionId);
 return newLoading;
 });
 }
 };

 const getAuthorityIcon = (authority: string) => {
 switch (authority) {
 case 'SEPP': return <Scale className="h-4 w-4 text-purple-600" />;
 case 'LEP': return <FileText className="h-4 w-4 text-blue-600" />;
 case 'DCP': return <Book className="h-4 w-4 text-teal-600" />;
 default: return <AlertCircle className="h-4 w-4 text-gray-500" />;
 }
 };

 const getAuthorityColor = (authority: string) => {
 switch (authority) {
 case 'SEPP': return 'border-purple-200 bg-purple-50';
 case 'LEP': return 'border-blue-200 bg-blue-50';
 case 'DCP': return 'border-teal-200 bg-teal-50';
 default: return 'border-gray-200 bg-gray-50';
 }
 };

 const references = groupedReferences();
 
 if (Object.keys(references).length === 0) {
 return null;
 }

 return (
 <div className={`mt-4 ${className}`}>
 <div className="border border-gray-200 rounded-lg bg-white">
 <div className="px-4 py-3 border-b border-gray-200 bg-gray-50">
 <h3 className="text-sm font-semibold text-gray-800 flex items-center">
 <Scale className="h-4 w-4 mr-2 text-gray-600" />
 Referenced Legislation
 </h3>
 <p className="text-xs text-gray-600 mt-1">
 Legal provisions that determine these setback requirements
 </p>
 </div>

 <div className="divide-y divide-gray-200">
 {Object.entries(references).map(([authority, refs]) => {
 const sectionId = authority;
 const isExpanded = expandedSections.has(sectionId);
 
 return (
 <div key={authority} className={`${getAuthorityColor(authority)}`}>
 <button
 onClick={() => toggleSection(sectionId)}
 className="w-full px-4 py-3 flex items-center justify-between hover:bg-black hover:bg-opacity-5 transition-colors"
 >
 <div className="flex items-center">
 {getAuthorityIcon(authority)}
 <span className="ml-2 text-sm font-medium text-gray-800">
 {authority === 'SEPP' && 'State Environmental Planning Policy'}
 {authority === 'LEP' && 'Local Environmental Plan'}
 {authority === 'DCP' && 'Development Control Plan'}
 </span>
 <span className="ml-2 text-xs text-gray-500">
 ({refs.length} reference{refs.length !== 1 ? 's' : ''})
 </span>
 </div>
 {isExpanded ? (
 <ChevronDown className="h-4 w-4 text-gray-500" />
 ) : (
 <ChevronRight className="h-4 w-4 text-gray-500" />
 )}
 </button>

 {isExpanded && (
 <div className="px-4 pb-3 space-y-3">
 {refs.map((ref, index) => (
 <div key={`${authority}-${index}`} className="bg-white rounded border border-gray-200 p-3">
 <div className="flex justify-between items-start mb-2">
 <div>
 <div className="text-sm font-medium text-gray-800">
 {ref.clause_reference || 'Clause Reference Not Available'}
 </div>
 <div className="text-xs text-gray-600">
 Applies to: {ref.boundary_type.replace('_', ' ')} setback
 </div>
 </div>
 {ref.provision_id && (
 <button
 onClick={() => loadClauseText(ref.provision_id!)}
 disabled={loading.has(ref.provision_id)}
 className="text-xs px-2 py-1 bg-indigo-100 text-indigo-700 rounded hover:bg-indigo-200 transition-colors disabled:opacity-50"
 >
 {loading.has(ref.provision_id) ? 'Loading...' : 'View Full Text'}
 </button>
 )}
 </div>

 <div className="text-xs text-gray-700 mb-2">
 <strong>Source:</strong> {ref.legal_source || ref.legal_authority?.document_source || 'Not specified'}
 </div>

 {ref.provision_id && loadedClauses.has(ref.provision_id) && (
 <div className="mt-3 p-3 bg-gray-50 rounded text-xs">
 <div className="font-medium text-gray-800 mb-2">
 Full Legislative Text:
 </div>
 <div className="text-gray-700 italic whitespace-pre-wrap">
 {loadedClauses.get(ref.provision_id)?.full_text || 'Text not available'}
 </div>
 {loadedClauses.get(ref.provision_id)?.page_number && (
 <div className="text-gray-500 mt-2">
 Page {loadedClauses.get(ref.provision_id)?.page_number}
 </div>
 )}
 </div>
 )}
 </div>
 ))}

 <div className="text-xs text-gray-600 p-2 bg-white rounded border-l-4 border-gray-300">
 <strong>Authority Level:</strong> {authority} provisions {
 authority === 'SEPP' ? 'cannot be varied by councils and override all other planning instruments.' :
 authority === 'LEP' ? 'have statutory force and can only be varied through formal Clause 4.6 variation process.' :
 'provide detailed design guidance but cannot override SEPP or LEP requirements.'
 }
 </div>
 </div>
 )}
 </div>
 );
 })}
 </div>
 </div>
 </div>
 );
}