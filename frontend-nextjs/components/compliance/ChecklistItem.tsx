import React from 'react';
import type { ComplianceItem } from './types';

interface ChecklistItemProps {
 item: ComplianceItem;
 isExpanded: boolean;
 onToggleExpanded: () => void;
 onStatusChange: (status: string) => void;
}

export const ChecklistItem: React.FC<ChecklistItemProps> = ({
 item,
 isExpanded,
 onToggleExpanded,
 onStatusChange
}) => {
 const getStatusColor = (status: string) => {
 switch (status) {
 case 'compliant': return 'bg-emerald-50 text-emerald-900 border-emerald-500';
 case 'non-compliant': return 'bg-rose-50 text-rose-800 border-rose-400';
 case 'pending': return 'bg-amber-50 text-amber-900 border-amber-400';
 case 'not-applicable': return 'bg-gray-100 text-gray-800 border-gray-200';
 default: return 'bg-gray-100 text-gray-800 border-gray-200';
 }
 };

 const getTierBadge = (tier: string) => {
 const colors = {
 tier1: 'bg-red-100 text-red-800',
 tier2: 'bg-amber-100 text-amber-800',
 tier3: 'bg-blue-100 text-blue-800'
 };
 return colors[tier as keyof typeof colors] || 'bg-gray-100 text-gray-800';
 };

 const getConfidenceColor = (confidence: number) => {
 if (confidence >= 90) return 'text-green-600';
 if (confidence >= 70) return 'text-yellow-600';
 return 'text-red-600';
 };

 return (
 <div className="bg-white border rounded-lg overflow-hidden">
 {/* Header */}
 <div
 className="p-4 cursor-pointer hover:bg-gray-50 transition-colors"
 onClick={onToggleExpanded}
 >
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-2">
 <h3 className="font-medium text-gray-900">{item.title}</h3>
 <span className={`px-2 py-1 text-xs rounded-full ${getTierBadge(item.tier)}`}>
 {item.tier.toUpperCase()}
 </span>
 </div>
 <p className="text-sm text-gray-600 mb-2">{item.description}</p>

 <div className="flex items-center gap-4 text-xs text-gray-500">
 <span>Authority: {item.authority}</span>
 <span className={`font-medium ${getConfidenceColor(item.confidence)}`}>
 Confidence: {item.confidence}%
 </span>
 </div>
 </div>

 <div className="flex items-center gap-2 ml-4">
 {/* Status Selector */}
 <select
 value={item.status}
 onChange={(e) => {
 e.stopPropagation();
 onStatusChange(e.target.value);
 }}
 className={`px-3 py-1 text-xs rounded border ${getStatusColor(item.status)}`}
 onClick={(e) => e.stopPropagation()}
 >
 <option value="pending">Pending</option>
 <option value="compliant">Compliant</option>
 <option value="non-compliant">Non-Compliant</option>
 <option value="not-applicable">Not Applicable</option>
 </select>

 {/* Expand/Collapse Icon */}
 <div className="text-gray-400">
 {isExpanded ? (
 <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
 </svg>
 ) : (
 <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
 </svg>
 )}
 </div>
 </div>
 </div>
 </div>

 {/* Expanded Content */}
 {isExpanded && (
 <div className="border-t bg-gray-50 p-4">
 {/* Requirements */}
 {item.requirements && item.requirements.length > 0 && (
 <div className="mb-4">
 <h4 className="font-medium text-gray-900 mb-2">Requirements:</h4>
 <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
 {item.requirements.map((req, index) => (
 <li key={index}>{req}</li>
 ))}
 </ul>
 </div>
 )}

 {/* Evidence */}
 {item.evidence && item.evidence.length > 0 && (
 <div className="mb-4">
 <h4 className="font-medium text-gray-900 mb-2">Evidence:</h4>
 <div className="space-y-2">
 {item.evidence.map((evidence, index) => (
 <div key={index} className="bg-white p-2 rounded border text-sm">
 {evidence}
 </div>
 ))}
 </div>
 </div>
 )}

 {/* Add Evidence Button */}
 <div className="flex gap-2">
 <button className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 transition-colors">
 Add Evidence
 </button>
 <button className="px-3 py-1 bg-gray-600 text-white text-sm rounded hover:bg-gray-700 transition-colors">
 View Details
 </button>
 </div>
 </div>
 )}
 </div>
 );
};