'use client';

import React from 'react';

interface LoadingSpinnerProps {
 size?: 'sm' | 'md' | 'lg';
 className?: string;
}

export function LoadingSpinner({ size = 'md', className = '' }: LoadingSpinnerProps) {
 const sizeClasses = {
 sm: 'w-4 h-4',
 md: 'w-6 h-6',
 lg: 'w-8 h-8'
 };

 return (
 <div className={`animate-spin rounded-full border-2 border-gray-300 border-t-blue-600 ${sizeClasses[size]} ${className}`} />
 );
}

interface PropertyLoadingProps {
 address: string;
}

export function PropertyLoading({ address }: PropertyLoadingProps) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <div className="flex items-center gap-3 mb-4">
 <LoadingSpinner size="sm" />
 <h3 className="text-lg font-semibold">Loading Property Information</h3>
 </div>
 <div className="space-y-3">
 <div>
 <label className="text-sm text-gray-600">Address</label>
 <p className="font-medium text-blue-600">{address}</p>
 </div>
 <div className="animate-pulse space-y-3">
 <div className="grid grid-cols-2 gap-4">
 <div>
 <div className="h-4 bg-gray-200 rounded w-1/3 mb-1"></div>
 <div className="h-5 bg-gray-200 rounded w-2/3"></div>
 </div>
 <div>
 <div className="h-4 bg-gray-200 rounded w-1/3 mb-1"></div>
 <div className="h-5 bg-gray-200 rounded w-1/2"></div>
 </div>
 </div>
 <div className="grid grid-cols-2 gap-4">
 <div>
 <div className="h-4 bg-gray-200 rounded w-1/3 mb-1"></div>
 <div className="h-5 bg-gray-200 rounded w-3/4"></div>
 </div>
 <div>
 <div className="h-4 bg-gray-200 rounded w-1/3 mb-1"></div>
 <div className="h-5 bg-gray-200 rounded w-1/3"></div>
 </div>
 </div>
 </div>
 </div>
 </div>
 );
}

interface ComplianceLoadingProps {
 developmentType: string;
 zone: string;
}

export function ComplianceLoading({ developmentType, zone }: ComplianceLoadingProps) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <div className="flex items-center gap-3 mb-4">
 <LoadingSpinner size="sm" />
 <h3 className="text-lg font-semibold">Running Compliance Assessment</h3>
 </div>
 <div className="space-y-4">
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <div className="text-blue-800 font-medium">Assessment Context</div>
 <div className="text-sm text-blue-600 mt-1">
 {developmentType.replace('_', ' ')} in Zone {zone}
 </div>
 </div>
 <div className="animate-pulse space-y-3">
 {[1, 2, 3, 4].map((i) => (
 <div key={i} className="border rounded p-3">
 <div className="flex items-center justify-between mb-2">
 <div className="h-4 bg-gray-200 rounded w-1/3"></div>
 <div className="h-6 bg-gray-200 rounded w-16"></div>
 </div>
 <div className="h-3 bg-gray-200 rounded w-1/4 mb-2"></div>
 <div className="h-3 bg-gray-200 rounded w-3/4"></div>
 </div>
 ))}
 </div>
 </div>
 </div>
 );
}

interface ErrorDisplayProps {
 error: string;
 onRetry?: () => void;
 className?: string;
}

export function ErrorDisplay({ error, onRetry, className = '' }: ErrorDisplayProps) {
 return (
 <div className={`bg-red-50 border border-red-200 rounded-lg p-4 ${className}`}>
 <div className="flex items-start gap-3">
 <div className="text-red-500 mt-0.5">
 <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
 </svg>
 </div>
 <div className="flex-1">
 <h4 className="text-red-800 font-medium">Error</h4>
 <p className="text-red-700 text-sm mt-1">{error}</p>
 {onRetry && (
 <button
 onClick={onRetry}
 className="mt-3 px-3 py-1 bg-red-100 hover:bg-red-200 text-red-800 text-sm rounded transition-colors"
 >
 Try Again
 </button>
 )}
 </div>
 </div>
 </div>
 );
}

interface ValidationErrorsProps {
 errors: string[];
 className?: string;
}

export function ValidationErrors({ errors, className = '' }: ValidationErrorsProps) {
 if (errors.length === 0) return null;

 return (
 <div className={`bg-yellow-50 border border-yellow-200 rounded-lg p-4 ${className}`}>
 <div className="flex items-start gap-3">
 <div className="text-yellow-500 mt-0.5">
 <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
 </svg>
 </div>
 <div className="flex-1">
 <h4 className="text-yellow-800 font-medium">Please complete the following:</h4>
 <ul className="text-yellow-700 text-sm mt-1 space-y-1">
 {errors.map((error, index) => (
 <li key={index} className="flex items-center gap-2">
 <span className="w-1 h-1 bg-yellow-600 rounded-full"></span>
 {error}
 </li>
 ))}
 </ul>
 </div>
 </div>
 </div>
 );
}
