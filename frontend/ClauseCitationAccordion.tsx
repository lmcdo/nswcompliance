// ClauseCitationAccordion.tsx
// React component for displaying clause citations with expandable accordions

import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronUp, FileText, Info } from 'lucide-react';

interface ClauseCitation {
 citation_text: string;
 accordion_title: string;
 accordion_content: string;
 metadata: {
 document: string;
 section: string;
 type: string;
 };
 related_clauses?: Array<{
 number: string;
 type: string;
 preview: string;
 }>;
}

interface ClauseCitationAccordionProps {
 clauseRef: string;
 inline?: boolean;
}

export const ClauseCitationAccordion: React.FC<ClauseCitationAccordionProps> = ({ 
 clauseRef, 
 inline = false 
}) => {
 const [isExpanded, setIsExpanded] = useState(false);
 const [citation, setCitation] = useState<ClauseCitation | null>(null);
 const [loading, setLoading] = useState(false);

 useEffect(() => {
 fetchCitation();
 }, [clauseRef]);

 const fetchCitation = async () => {
 setLoading(true);
 try {
 const response = await fetch(`/api/clause-citation/${encodeURIComponent(clauseRef)}`);
 if (response.ok) {
 const data = await response.json();
 setCitation(data);
 }
 } catch (error) {
 console.error('Failed to fetch clause citation:', error);
 } finally {
 setLoading(false);
 }
 };

 if (loading) {
 return <span className="text-blue-600 underline">{clauseRef}</span>;
 }

 if (!citation) {
 return <span>{clauseRef}</span>;
 }

 if (inline) {
 // Inline citation with popover
 return (
 <span className="relative inline-block">
 <button
 className="text-blue-600 underline hover:text-blue-800 focus:outline-none"
 onClick={() => setIsExpanded(!isExpanded)}
 >
 {citation.citation_text}
 <sup className="ml-0.5 text-xs">
 <Info className="inline w-3 h-3" />
 </sup>
 </button>
 
 {isExpanded && (
 <div className="absolute z-50 mt-2 p-4 bg-white border border-gray-200 rounded-lg shadow-lg w-96 max-h-96 overflow-y-auto">
 <div className="flex justify-between items-start mb-2">
 <h4 className="font-semibold text-sm">{citation.accordion_title}</h4>
 <button
 onClick={() => setIsExpanded(false)}
 className="text-gray-500 hover:text-gray-700"
 >
 ×
 </button>
 </div>
 
 <div className="text-sm text-gray-700 mb-2">
 {citation.accordion_content}
 </div>
 
 <div className="text-xs text-gray-500 border-t pt-2">
 <div>Document: {citation.metadata.document}</div>
 <div>Section: {citation.metadata.section}</div>
 </div>
 </div>
 )}
 </span>
 );
 }

 // Full accordion display
 return (
 <div className="border border-gray-200 rounded-lg mb-2">
 <button
 className="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
 onClick={() => setIsExpanded(!isExpanded)}
 >
 <div className="flex items-center space-x-2">
 <FileText className="w-4 h-4 text-gray-500" />
 <span className="font-medium">{citation.accordion_title}</span>
 </div>
 {isExpanded ? (
 <ChevronUp className="w-5 h-5 text-gray-500" />
 ) : (
 <ChevronDown className="w-5 h-5 text-gray-500" />
 )}
 </button>
 
 {isExpanded && (
 <div className="px-4 py-3 border-t border-gray-200 bg-gray-50">
 <div className="prose prose-sm max-w-none">
 <p className="text-gray-700">{citation.accordion_content}</p>
 </div>
 
 <div className="mt-4 pt-3 border-t border-gray-200">
 <div className="flex flex-wrap gap-2 text-xs text-gray-500">
 <span className="bg-blue-100 text-blue-700 px-2 py-1 rounded">
 {citation.metadata.type}
 </span>
 <span className="bg-gray-100 text-gray-700 px-2 py-1 rounded">
 {citation.metadata.document}
 </span>
 <span className="bg-green-100 text-green-700 px-2 py-1 rounded">
 {citation.metadata.section}
 </span>
 </div>
 </div>
 
 {citation.related_clauses && citation.related_clauses.length > 0 && (
 <div className="mt-4 pt-3 border-t border-gray-200">
 <h5 className="text-xs font-semibold text-gray-600 mb-2">Related Clauses:</h5>
 <div className="space-y-1">
 {citation.related_clauses.map((related, idx) => (
 <div key={idx} className="text-xs text-gray-600">
 <span className="font-medium">{related.number}</span> - {related.preview}
 </div>
 ))}
 </div>
 </div>
 )}
 </div>
 )}
 </div>
 );
};

// Example usage in a component showing connected requirements
export const ConnectedRequirements: React.FC = () => {
 const requirements = [
 { clause: "Clause 4.2.4(b)", relationship: "is about", target: "Building heights" },
 { clause: "Clause 4.2.4(c)", relationship: "is after", target: "Clause 4.2.4(b)" },
 ];

 return (
 <div className="space-y-4">
 <h3 className="text-lg font-semibold">Connected Requirements</h3>
 
 {requirements.map((req, idx) => (
 <div key={idx} className="bg-white p-4 rounded-lg shadow">
 <div className="mb-2">
 <ClauseCitationAccordion clauseRef={req.clause} />
 </div>
 <div className="text-sm text-gray-600">
 {req.relationship} → {req.target}
 </div>
 </div>
 ))}
 </div>
 );
};

// Example of inline citations in text
export const RequirementText: React.FC = () => {
 return (
 <div className="prose">
 <p>
 According to <ClauseCitationAccordion clauseRef="Clause 4.2.4(b)" inline={true} />, 
 the building height must not exceed 9.5 metres. Additionally, 
 <ClauseCitationAccordion clauseRef="Clause 4.2.4(c)" inline={true} /> specifies 
 that setbacks must be consistent with the streetscape.
 </p>
 </div>
 );
};