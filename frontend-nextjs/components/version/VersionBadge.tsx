import React from 'react';

interface VersionBadgeProps {
 version?: string;
 documentType?: string;
 effectiveDate?: string;
 className?: string;
}

export const VersionBadge: React.FC<VersionBadgeProps> = ({
 version = 'current',
 documentType = 'Document',
 effectiveDate,
 className = ''
}) => {
 const formatDate = (dateString?: string) => {
 if (!dateString) return null;
 try {
 return new Date(dateString).toLocaleDateString('en-AU', {
 year: 'numeric',
 month: 'short',
 day: 'numeric'
 });
 } catch {
 return dateString;
 }
 };

 const getVersionColor = (ver: string) => {
 if (ver === 'current') return 'bg-green-100 text-green-800 border-green-200';
 if (ver === 'superseded') return 'bg-orange-100 text-orange-800 border-orange-200';
 return 'bg-blue-100 text-blue-800 border-blue-200';
 };

 return (
 <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg border text-sm font-medium ${getVersionColor(version)} ${className}`}>
 <div className="flex items-center gap-1">
 <span className="w-2 h-2 rounded-full bg-current opacity-60"></span>
 <span>{documentType}</span>
 </div>
 {effectiveDate && (
 <span className="text-xs opacity-75">
 {formatDate(effectiveDate)}
 </span>
 )}
 </div>
 );
};

export default VersionBadge;