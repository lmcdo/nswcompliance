import React from 'react';
import { DevelopmentType, ValidationResult } from './types';

interface DevelopmentCardProps {
 development: DevelopmentType;
 isSelected: boolean;
 onSelect: () => void;
 showDescription: boolean;
 disabled: boolean;
 validation: ValidationResult | null;
}

export const DevelopmentCard: React.FC<DevelopmentCardProps> = ({
 development,
 isSelected,
 onSelect,
 showDescription,
 disabled,
 validation
}) => {
 const getCategoryColor = (category: string) => {
 switch (category) {
 case 'residential': return 'bg-green-100 text-green-800';
 case 'commercial': return 'bg-blue-100 text-blue-800';
 case 'industrial': return 'bg-purple-100 text-purple-800';
 case 'mixed': return 'bg-orange-100 text-orange-800';
 default: return 'bg-gray-100 text-gray-800';
 }
 };

 const cardClasses = [
 'p-4 border rounded-md cursor-pointer transition-all',
 isSelected ? 'border-blue-500 bg-blue-50' : 'border-gray-200 hover:border-gray-300',
 disabled && 'opacity-50 cursor-not-allowed',
 validation && !validation.isValid && 'border-yellow-400 bg-yellow-50'
 ].filter(Boolean).join(' ');

 return (
 <div
 className={cardClasses}
 onClick={disabled ? undefined : onSelect}
 >
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <h3 className="font-medium text-gray-900">{development.name}</h3>
 <p className="text-sm text-gray-500 mt-1">{development.code}</p>
 {showDescription && (
 <p className="text-sm text-gray-600 mt-2">{development.description}</p>
 )}
 </div>
 <div className="ml-2">
 <span className={`px-2 py-1 text-xs rounded-full ${getCategoryColor(development.category)}`}>
 {development.category}
 </span>
 </div>
 </div>

 {/* Compliance Requirements */}
 <div className="mt-3">
 <div className="flex flex-wrap gap-1">
 {development.complianceRequirements.slice(0, 3).map((req, i) => (
 <span key={i} className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
 {req}
 </span>
 ))}
 {development.complianceRequirements.length > 3 && (
 <span className="px-2 py-1 text-xs bg-gray-100 text-gray-600 rounded">
 +{development.complianceRequirements.length - 3} more
 </span>
 )}
 </div>
 </div>

 {/* Validation Indicator */}
 {validation && (
 <div className="mt-2 flex items-center">
 {validation.isValid ? (
 <div className="flex items-center text-green-600">
 <span className="w-4 h-4 mr-1"></span>
 <span className="text-xs">Compatible</span>
 </div>
 ) : (
 <div className="flex items-center text-yellow-600">
 <span className="w-4 h-4 mr-1"></span>
 <span className="text-xs">{validation.warnings.length} warning(s)</span>
 </div>
 )}
 </div>
 )}
 </div>
 );
};
