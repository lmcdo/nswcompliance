'use client';

import React, { useState } from 'react';
import { ComplianceCheck, Citation } from '@/lib/assessment/types';

interface EnhancedComplianceChecklistProps {
 checks: ComplianceCheck[];
 citations?: Citation[];
 recommendations?: string[];
 nextSteps?: string[];
 analysisMetadata?: any;
 className?: string;
}

export default function EnhancedComplianceChecklist({
 checks,
 citations = [],
 recommendations = [],
 nextSteps = [],
 analysisMetadata,
 className = ''
}: EnhancedComplianceChecklistProps) {
 const [activeTab, setActiveTab] = useState<'checks' | 'recommendations' | 'citations'>('checks');
 const [expandedCheck, setExpandedCheck] = useState<string | null>(null);

 const getStatusIcon = (status: ComplianceCheck['compliance_status']) => {
 switch (status) {
 case 'compliant':
 return <span className="text-green-600"></span>;
 case 'non_compliant':
 return <span className="text-red-600"></span>;
 case 'requires_assessment':
 return <span className="text-yellow-600">?</span>;
 case 'not_applicable':
 return <span className="text-gray-500">—</span>;
 default:
 return <span className="text-gray-400">•</span>;
 }
 };

 const getStatusColor = (status: ComplianceCheck['compliance_status']) => {
 switch (status) {
 case 'compliant':
 return 'bg-green-50 border-green-200 text-green-800';
 case 'non_compliant':
 return 'bg-red-50 border-red-200 text-red-800';
 case 'requires_assessment':
 return 'bg-yellow-50 border-yellow-200 text-yellow-800';
 case 'not_applicable':
 return 'bg-gray-50 border-gray-200 text-gray-800';
 default:
 return 'bg-gray-50 border-gray-200 text-gray-800';
 }
 };

 const getConfidenceColor = (confidence: number) => {
 if (confidence >= 80) return 'text-green-600';
 if (confidence >= 60) return 'text-yellow-600';
 return 'text-red-600';
 };

 return (
 <div className={`bg-white border rounded-lg shadow-sm ${className}`}>
 {/* Header with metadata */}
 {analysisMetadata && (
 <div className="p-4 border-b bg-gray-50">
 <div className="grid grid-cols-4 gap-4 text-sm">
 <div>
 <div className="font-medium text-gray-700">Provisions Assessed</div>
 <div className="text-xl font-bold text-blue-600">
 {analysisMetadata.total_provisions_assessed}
 </div>
 </div>
 <div>
 <div className="font-medium text-gray-700">Completeness</div>
 <div className="text-xl font-bold text-green-600">
 {analysisMetadata.assessment_completeness}%
 </div>
 </div>
 <div>
 <div className="font-medium text-gray-700">High Confidence</div>
 <div className="text-xl font-bold text-purple-600">
 {analysisMetadata.confidence_distribution?.high || 0}
 </div>
 </div>
 <div>
 <div className="font-medium text-gray-700">Processing Time</div>
 <div className="text-sm text-gray-600">
 {new Date(analysisMetadata.processing_time).toLocaleTimeString()}
 </div>
 </div>
 </div>
 </div>
 )}

 {/* Tabs */}
 <div className="border-b">
 <nav className="flex space-x-8 px-6">
 {[
 { key: 'checks', label: 'Compliance Checks', count: checks.length },
 { key: 'recommendations', label: 'Recommendations', count: recommendations.length },
 { key: 'citations', label: 'Citations', count: citations.length }
 ].map((tab) => (
 <button
 key={tab.key}
 onClick={() => setActiveTab(tab.key as any)}
 className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
 activeTab === tab.key
 ? 'border-blue-500 text-blue-600'
 : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
 }`}
 >
 {tab.label} ({tab.count})
 </button>
 ))}
 </nav>
 </div>

 {/* Tab Content */}
 <div className="p-6">
 {activeTab === 'checks' && (
 <div className="space-y-4">
 {checks.map((check) => (
 <div
 key={check.provision_id}
 className={`border rounded-lg p-4 ${getStatusColor(check.compliance_status)}`}
 >
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <div className="flex items-center gap-3 mb-2">
 {getStatusIcon(check.compliance_status)}
 <span className="font-medium">Provision {check.provision_id}</span>
 <span className="text-sm bg-white bg-opacity-50 px-2 py-1 rounded">
 {check.assessment_method}
 </span>
 <span className={`text-sm font-medium ${getConfidenceColor(check.confidence_level)}`}>
 {check.confidence_level}% confidence
 </span>
 </div>

 <p className="text-sm mb-2">{check.requirement}</p>

 {check.evidence && (
 <div className="text-sm bg-white bg-opacity-50 p-2 rounded mb-2">
 <strong>Evidence:</strong> {check.evidence}
 </div>
 )}

 {check.notes && (
 <div className="text-sm bg-white bg-opacity-50 p-2 rounded mb-2">
 <strong>Notes:</strong> {check.notes}
 </div>
 )}

 <div className="text-xs text-gray-600 mt-2">
 References: {check.references.join(', ')}
 </div>
 </div>

 <button
 onClick={() => setExpandedCheck(
 expandedCheck === check.provision_id ? null : check.provision_id
 )}
 className="ml-4 text-gray-400 hover:text-gray-600"
 >
 {expandedCheck === check.provision_id ? '−' : '+'}
 </button>
 </div>

 {expandedCheck === check.provision_id && check.calculations && (
 <div className="mt-4 pt-4 border-t border-white border-opacity-50">
 <h4 className="font-medium text-sm mb-2">Detailed Calculations:</h4>
 <pre className="text-xs bg-white bg-opacity-50 p-2 rounded overflow-x-auto">
 {JSON.stringify(check.calculations, null, 2)}
 </pre>
 </div>
 )}
 </div>
 ))}
 </div>
 )}

 {activeTab === 'recommendations' && (
 <div className="space-y-4">
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <h4 className="font-medium text-blue-800 mb-3">Recommendations</h4>
 <ul className="space-y-2">
 {recommendations.map((recommendation, index) => (
 <li key={index} className="flex items-start gap-2 text-blue-700">
 <span className="text-blue-500 mt-1">•</span>
 <span className="text-sm">{recommendation}</span>
 </li>
 ))}
 </ul>
 </div>

 {nextSteps.length > 0 && (
 <div className="bg-green-50 border border-green-200 rounded-lg p-4">
 <h4 className="font-medium text-green-800 mb-3">Next Steps</h4>
 <ol className="space-y-2">
 {nextSteps.map((step, index) => (
 <li key={index} className="flex items-start gap-2 text-green-700">
 <span className="text-green-500 mt-1 font-medium">{index + 1}.</span>
 <span className="text-sm">{step}</span>
 </li>
 ))}
 </ol>
 </div>
 )}
 </div>
 )}

 {activeTab === 'citations' && (
 <div className="space-y-3">
 {citations.map((citation) => (
 <div key={citation.id} className="border rounded-lg p-4 bg-gray-50">
 <div className="flex items-start justify-between mb-2">
 <div>
 <span className="font-medium">{citation.document_type}</span>
 <span className="text-gray-500 mx-2">•</span>
 <span>{citation.clause}</span>
 </div>
 <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
 {citation.citation_style}
 </span>
 </div>

 <div className="text-sm bg-white p-3 rounded border font-mono">
 {citation.formatted_citation}
 </div>

 <div className="text-xs text-gray-500 mt-2">
 Accessed: {new Date(citation.access_date).toLocaleDateString()}
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 </div>
 );
}
