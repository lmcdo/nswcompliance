import React from 'react';

interface ComplianceMetricCardProps {
 title: string;
 value: string | number;
 subtitle?: string;
 color?: string;
 icon?: React.ReactNode;
}

export const ComplianceMetricCard: React.FC<ComplianceMetricCardProps> = ({
 title,
 value,
 subtitle,
 color = 'text-gray-900',
 icon
}) => {
 return (
 <div className="bg-gray-50 rounded-lg p-4">
 <div className="flex items-center justify-between">
 <div>
 <p className="text-sm font-medium text-gray-500">{title}</p>
 <p className={`text-2xl font-bold ${color}`}>{value}</p>
 {subtitle && (
 <p className="text-xs text-gray-500 mt-1">{subtitle}</p>
 )}
 </div>
 {icon && <div className="text-gray-400">{icon}</div>}
 </div>
 </div>
 );
};
