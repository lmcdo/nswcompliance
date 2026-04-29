'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { useFeatureFlags } from '@/components/providers/FeatureFlagProvider';
import { useDevelopmentContext } from '@/contexts/DevelopmentContext';
import { DevelopmentCard } from './DevelopmentCard';
import { DevelopmentSelectorProps, DevelopmentType } from './types';

export const EnhancedDevelopmentSelector: React.FC<DevelopmentSelectorProps> = ({
 selectedDevelopment,
 onDevelopmentChange,
 propertyId,
 zoning,
 lotSize,
 disabled = false,
 variant = 'default',
 showDescription = true,
 filterByZoning = true,
}) => {
 const { flags } = useFeatureFlags();
 const {
 availableDevelopments,
 isLoading,
 error,
 filters,
 updateFilters,
 validateDevelopment,
 loadDevelopmentTypes
 } = useDevelopmentContext();

 const [searchTerm, setSearchTerm] = useState('');
 const [showValidationErrors, setShowValidationErrors] = useState(false);

 // Load development types on mount
 useEffect(() => {
 loadDevelopmentTypes(propertyId);
 }, [propertyId, loadDevelopmentTypes]);

 // Filter developments based on property constraints
 const filteredDevelopments = useMemo(() => {
 let filtered = availableDevelopments;

 if (filterByZoning && zoning) {
 filtered = filtered.filter(dev =>
 dev.applicableZones.includes(zoning) || dev.applicableZones.includes('*')
 );
 }

 // Lot size is validated on selection (shows warning), not used to hide options from the list.

 if (searchTerm) {
 const term = searchTerm.toLowerCase();
 filtered = filtered.filter(dev =>
 dev.name.toLowerCase().includes(term) ||
 dev.code.toLowerCase().includes(term) ||
 dev.description.toLowerCase().includes(term)
 );
 }

 if (filters.category) {
 filtered = filtered.filter(dev => dev.category === filters.category);
 }

 return filtered.filter(dev => dev.isEnabled);
 }, [availableDevelopments, filterByZoning, zoning, searchTerm, filters]);

 // Validation for selected development
 const validationResult = useMemo(() => {
 if (!selectedDevelopment) return null;
 return validateDevelopment(selectedDevelopment, { zoning, lotSize });
 }, [selectedDevelopment, zoning, lotSize, validateDevelopment]);

 const handleDevelopmentSelect = useCallback((development: DevelopmentType) => {
 const validation = validateDevelopment(development, { zoning, lotSize });

 if (validation.isValid) {
 onDevelopmentChange(development);
 setShowValidationErrors(false);
 } else {
 setShowValidationErrors(true);
 // Still allow selection but show warnings
 onDevelopmentChange(development);
 }
 }, [validateDevelopment, zoning, lotSize, onDevelopmentChange]);

 const getUniqueCategories = () => {
 const categories = availableDevelopments.map(dev => dev.category);
 return [...new Set(categories)];
 };

 if (variant === 'compact') {
 return (
 <div className="development-selector-compact">
 <select
 value={selectedDevelopment?.id || ''}
 onChange={(e) => {
 const development = availableDevelopments.find(d => d.id === e.target.value);
 onDevelopmentChange(development || null);
 }}
 disabled={disabled || isLoading}
 className="w-full px-3 py-2 border rounded-md"
 >
 <option value="">Select development type...</option>
 {filteredDevelopments.map((dev) => (
 <option key={dev.id} value={dev.id}>
 {dev.name} ({dev.code})
 </option>
 ))}
 </select>
 </div>
 );
 }

 return (
 <div className={`development-selector ${variant === 'detailed' ? 'detailed' : ''}`}>
 {/* Search and Filter Controls */}
 <div className="flex flex-col space-y-4 mb-4">
 <div className="flex items-center space-x-2">
 <input
 type="text"
 placeholder="Search development types..."
 value={searchTerm}
 onChange={(e) => setSearchTerm(e.target.value)}
 className="flex-1 px-3 py-2 border rounded-md"
 disabled={disabled || isLoading}
 />
 <select
 value={filters.category || ''}
 onChange={(e) => updateFilters({ category: e.target.value || undefined })}
 className="px-3 py-2 border rounded-md"
 disabled={disabled || isLoading}
 >
 <option value="">All Categories</option>
 {getUniqueCategories().map((category) => (
 <option key={category} value={category}>
 {category.charAt(0).toUpperCase() + category.slice(1)}
 </option>
 ))}
 </select>
 </div>
 </div>

 {/* Development Type Grid */}
 {isLoading ? (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {[...Array(6)].map((_, i) => (
 <div key={i} className="h-24 bg-gray-200 animate-pulse rounded-md" />
 ))}
 </div>
 ) : error ? (
 <div className="p-4 bg-red-50 border border-red-200 rounded-md">
 <p className="text-red-600">Error loading development types: {error}</p>
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
 {filteredDevelopments.map((development) => (
 <DevelopmentCard
 key={development.id}
 development={development}
 isSelected={selectedDevelopment?.id === development.id}
 onSelect={() => handleDevelopmentSelect(development)}
 showDescription={showDescription}
 disabled={disabled}
 validation={selectedDevelopment?.id === development.id ? validationResult : null}
 />
 ))}
 </div>
 )}

 {/* Validation Messages */}
 {showValidationErrors && validationResult && !validationResult.isValid && (
 <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-md">
 <h4 className="font-medium text-yellow-800">Development Compatibility Warnings:</h4>
 <ul className="mt-2 list-disc list-inside text-yellow-700">
 {validationResult.warnings.map((warning, i) => (
 <li key={i}>{warning}</li>
 ))}
 </ul>
 </div>
 )}

 {/* No Results Message */}
 {!isLoading && !error && filteredDevelopments.length === 0 && (
 <div className="text-center py-8">
 <p className="text-gray-500">No development types match your criteria.</p>
 <button
 onClick={() => {
 setSearchTerm('');
 updateFilters({ category: undefined });
 }}
 className="mt-2 text-blue-600 hover:text-blue-800"
 >
 Clear filters
 </button>
 </div>
 )}
 </div>
 );
};
