import React from 'react';

interface ComplianceProgressBarProps {
 progress: number;
 showLabel?: boolean;
 height?: 'sm' | 'md' | 'lg';
}

export const ComplianceProgressBar: React.FC<ComplianceProgressBarProps> = ({
 progress,
 showLabel = true,
 height = 'md'
}) => {
 const heightClasses = {
 sm: 'h-2',
 md: 'h-3',
 lg: 'h-4'
 };

 const getProgressColor = (progress: number) => {
 if (progress >= 100) return 'bg-green-500';
 if (progress >= 75) return 'bg-blue-500';
 if (progress >= 50) return 'bg-yellow-500';
 return 'bg-orange-500';
 };

 return (
 <div className="mt-4">
 {showLabel && (
 <div className="flex justify-between text-sm text-gray-600 mb-2">
 <span>Progress</span>
 <span>{Math.round(progress)}%</span>
 </div>
 )}
 <div className={`w-full bg-gray-200 rounded-full ${heightClasses[height]}`}>
 <div
 className={`h-full rounded-full transition-all duration-300 ${getProgressColor(progress)}`}
 style={{ width: `${Math.min(progress, 100)}%` }}
 />
 </div>
 </div>
 );
};
