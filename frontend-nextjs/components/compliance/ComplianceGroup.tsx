import React, { useMemo } from 'react';
import { ComplianceCheck } from './types';

interface ComplianceGroupProps {
 title: string;
 checks: ComplianceCheck[];
 isExpanded: boolean;
 onToggle: () => void;
 onRunCheck: (checkId: string) => void;
}

export const ComplianceGroup: React.FC<ComplianceGroupProps> = ({
 title,
 checks,
 isExpanded,
 onToggle,
 onRunCheck
}) => {
 const statusCounts = useMemo(() => {
 return checks.reduce((acc, check) => {
 acc[check.status] = (acc[check.status] || 0) + 1;
 return acc;
 }, {} as Record<string, number>);
 }, [checks]);

 const getStatusColor = (status: string) => {
 switch (status) {
 case 'compliant': return 'bg-green-100 text-green-800 border-green-200';
 case 'non-compliant': return 'bg-red-100 text-red-800 border-red-200';
 case 'conditional': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
 case 'not-applicable': return 'bg-gray-100 text-gray-800 border-gray-200';
 case 'pending': return 'bg-blue-100 text-blue-800 border-blue-200';
 default: return 'bg-gray-100 text-gray-800 border-gray-200';
 }
 };

 return (
 <div className="bg-white border border-gray-200 rounded-lg">
 <button
 onClick={onToggle}
 className="w-full px-6 py-4 flex items-center justify-between hover:bg-gray-50"
 >
 <div className="flex items-center space-x-3">
 <span className={`transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
 ▶
 </span>
 <h3 className="font-medium text-gray-900">{title}</h3>
 <span className="text-sm text-gray-500">({checks.length} checks)</span>
 </div>
 <div className="flex items-center space-x-2">
 {Object.entries(statusCounts).map(([status, count]) => (
 <span
 key={status}
 className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(status)}`}
 >
 {count}
 </span>
 ))}
 </div>
 </button>

 {isExpanded && (
 <div className="border-t border-gray-200">
 {checks.map((check) => (
 <div key={check.id} className="px-6 py-4 border-b border-gray-100 last:border-b-0">
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <div className="flex items-center space-x-2 mb-2">
 <span className="font-mono text-sm text-gray-500">{check.provision}</span>
 <span className={`px-2 py-1 text-xs rounded-full border ${getStatusColor(check.status)}`}>
 {check.status.replace('-', ' ')}
 </span>
 {check.severity === 'critical' && (
 <span className="px-2 py-1 text-xs bg-red-100 text-red-800 rounded-full">
 Critical
 </span>
 )}
 </div>
 <p className="text-sm text-gray-900 mb-1">{check.requirement}</p>
 {check.recommendations && check.recommendations.length > 0 && (
 <div className="text-sm text-gray-600">
 <strong>Recommendations:</strong> {check.recommendations.join(', ')}
 </div>
 )}
 </div>
 <div className="ml-4">
 <button
 onClick={() => onRunCheck(check.id)}
 className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
 >
 Re-check
 </button>
 </div>
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 );
};
