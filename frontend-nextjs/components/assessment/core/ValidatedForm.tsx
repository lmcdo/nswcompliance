'use client';

import React from 'react';
import { DevelopmentType } from '@/lib/assessment/types';

interface ValidatedAddressInputProps {
 value: string;
 onChange: (value: string) => void;
 onSubmit: () => void;
 loading?: boolean;
 error?: string | null;
 placeholder?: string;
}

export function ValidatedAddressInput({
 value,
 onChange,
 onSubmit,
 loading = false,
 error = null,
 placeholder = "Enter NSW property address..."
}: ValidatedAddressInputProps) {
 const handleSubmit = (e: React.FormEvent) => {
 e.preventDefault();
 if (value.trim()) {
 onSubmit();
 }
 };

 return (
 <form onSubmit={handleSubmit} className="space-y-3">
 <div className="relative">
 <input
 type="text"
 value={value}
 onChange={(e) => onChange(e.target.value)}
 placeholder={placeholder}
 disabled={loading}
 className={`w-full h-12 px-4 pr-16 text-base border rounded-lg bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:bg-gray-50 disabled:cursor-not-allowed ${
 error ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300'
 }`}
 />
 <button
 type="submit"
 disabled={loading || !value.trim()}
 className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors disabled:bg-gray-400 disabled:cursor-not-allowed"
 >
 <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
 <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
 </svg>
 </button>
 </div>
 {error && (
 <p className="text-red-600 text-sm">{error}</p>
 )}
 </form>
 );
}

interface ValidatedDevelopmentSelectorProps {
 value: DevelopmentType | '';
 onChange: (value: DevelopmentType | '') => void;
 error?: string | null;
 disabled?: boolean;
}

export function ValidatedDevelopmentSelector({
 value,
 onChange,
 error = null,
 disabled = false
}: ValidatedDevelopmentSelectorProps) {
 const developmentTypes = [
 { value: 'dwelling_house', label: 'Single Dwelling House' },
 { value: 'dual_occupancy', label: 'Dual Occupancy' },
 { value: 'multi_dwelling_housing', label: 'Multi Dwelling Housing' },
 { value: 'residential_flat_building', label: 'Residential Flat Building' },
 { value: 'commercial_premises', label: 'Commercial Premises' },
 { value: 'retail_premises', label: 'Retail Premises' },
 { value: 'office_premises', label: 'Office Premises' },
 { value: 'industrial', label: 'Industrial Development' },
 { value: 'warehouse', label: 'Warehouse or Storage' },
 { value: 'mixed_use', label: 'Mixed Use Development' }
 ];

 return (
 <div className="space-y-2">
 <label className="block text-sm font-medium text-gray-700">
 Development Type *
 </label>
 <select
 value={value}
 onChange={(e) => onChange(e.target.value as DevelopmentType | '')}
 disabled={disabled}
 className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:bg-gray-50 disabled:cursor-not-allowed ${
 error ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300'
 }`}
 >
 <option value="">Select development type...</option>
 {developmentTypes.map((type) => (
 <option key={type.value} value={type.value}>
 {type.label}
 </option>
 ))}
 </select>
 {error && (
 <p className="text-red-600 text-sm">{error}</p>
 )}
 </div>
 );
}

interface ValidatedDateInputProps {
 value: string;
 onChange: (value: string) => void;
 label?: string;
 error?: string | null;
 disabled?: boolean;
 min?: string;
 max?: string;
}

export function ValidatedDateInput({
 value,
 onChange,
 label = "Assessment Date",
 error = null,
 disabled = false,
 min,
 max
}: ValidatedDateInputProps) {
 return (
 <div className="space-y-2">
 <label className="block text-sm font-medium text-gray-700">
 {label} *
 </label>
 <input
 type="date"
 value={value}
 onChange={(e) => onChange(e.target.value)}
 disabled={disabled}
 min={min}
 max={max}
 className={`w-full px-3 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-all disabled:bg-gray-50 disabled:cursor-not-allowed ${
 error ? 'border-red-300 focus:ring-red-500 focus:border-red-500' : 'border-gray-300'
 }`}
 />
 {error && (
 <p className="text-red-600 text-sm">{error}</p>
 )}
 <p className="text-xs text-gray-500">
 Select the date for compliance assessment
 </p>
 </div>
 );
}

interface AssessmentSubmitButtonProps {
 onClick: () => void;
 loading?: boolean;
 disabled?: boolean;
 formValid?: boolean;
 children: React.ReactNode;
}

export function AssessmentSubmitButton({
 onClick,
 loading = false,
 disabled = false,
 formValid = true,
 children
}: AssessmentSubmitButtonProps) {
 const isDisabled = disabled || loading || !formValid;

 return (
 <button
 onClick={onClick}
 disabled={isDisabled}
 className={`w-full px-6 py-3 rounded-lg font-medium transition-all focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
 isDisabled
 ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
 : 'bg-blue-600 hover:bg-blue-700 text-white shadow-sm hover:shadow-md'
 }`}
 >
 <div className="flex items-center justify-center gap-2">
 {loading && (
 <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
 )}
 {children}
 </div>
 </button>
 );
}
