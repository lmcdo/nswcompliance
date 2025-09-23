'use client';

import React, { useState, useCallback } from 'react';
import { ProvisionSearchFilters, ProvisionSearchResult, ComplianceProvision } from '@/lib/assessment/types';

interface ProvisionSearchProps {
 onProvisionSelect?: (provision: ComplianceProvision) => void;
 initialFilters?: ProvisionSearchFilters;
 className?: string;
}

export default function ProvisionSearch({
 onProvisionSelect,
 initialFilters = {},
 className = ''
}: ProvisionSearchProps) {
 const [query, setQuery] = useState('');
 const [filters, setFilters] = useState<ProvisionSearchFilters>(initialFilters);
 const [results, setResults] = useState<ProvisionSearchResult | null>(null);
 const [loading, setLoading] = useState(false);
 const [showFilters, setShowFilters] = useState(false);

 const performSearch = useCallback(async () => {
 if (!query.trim() && Object.keys(filters).length === 0) return;

 setLoading(true);
 try {
 const params = new URLSearchParams();
 if (query.trim()) params.append('q', query);
 if (filters.document_types) params.append('document_types', filters.document_types.join(','));
 if (filters.categories) params.append('categories', filters.categories.join(','));
 if (filters.zones) params.append('zones', filters.zones.join(','));
 if (filters.status) params.append('status', filters.status.join(','));

 const response = await fetch(`/api/provisions?${params.toString()}`);
 const data = await response.json();

 if (data.success) {
 setResults(data.data);
 }
 } catch (error) {
 console.error('Provision search failed:', error);
 } finally {
 setLoading(false);
 }
 }, [query, filters]);

 const handleFilterChange = (key: keyof ProvisionSearchFilters, value: any) => {
 setFilters(prev => ({ ...prev, [key]: value }));
 };

 return (
 <div className={`bg-white border rounded-lg shadow-sm ${className}`}>
 <div className="p-6">
 <h3 className="text-lg font-semibold mb-4">Provision Search</h3>

 {/* Search Input */}
 <div className="space-y-4">
 <div className="flex gap-2">
 <input
 type="text"
 value={query}
 onChange={(e) => setQuery(e.target.value)}
 placeholder="Search provisions, clauses, or requirements..."
 className="flex-1 px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 onKeyPress={(e) => e.key === 'Enter' && performSearch()}
 />
 <button
 onClick={performSearch}
 disabled={loading}
 className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
 >
 {loading ? 'Searching...' : 'Search'}
 </button>
 </div>

 {/* Filter Toggle */}
 <button
 onClick={() => setShowFilters(!showFilters)}
 className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
 >
 {showFilters ? 'Hide Filters' : 'Show Filters'}
 </button>

 {/* Filters */}
 {showFilters && (
 <div className="border rounded-lg p-4 bg-gray-50 space-y-3">
 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 Document Types
 </label>
 <select
 multiple
 value={filters.document_types || []}
 onChange={(e) => handleFilterChange('document_types', Array.from(e.target.selectedOptions, option => option.value))}
 className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
 >
 <option value="LEP">Local Environmental Plan</option>
 <option value="DCP">Development Control Plan</option>
 <option value="SEPP">State Environmental Planning Policy</option>
 </select>
 </div>

 <div>
 <label className="block text-sm font-medium text-gray-700 mb-1">
 Status
 </label>
 <select
 multiple
 value={filters.status || []}
 onChange={(e) => handleFilterChange('status', Array.from(e.target.selectedOptions, option => option.value))}
 className="w-full px-3 py-1 border border-gray-300 rounded text-sm"
 >
 <option value="current">Current</option>
 <option value="superseded">Superseded</option>
 <option value="proposed">Proposed</option>
 </select>
 </div>
 </div>
 </div>
 )}
 </div>

 {/* Results */}
 {results && (
 <div className="mt-6">
 <div className="flex items-center justify-between mb-4">
 <h4 className="font-medium">
 Search Results ({results.total_count} found)
 </h4>
 <div className="text-sm text-gray-500">
 Search completed in {results.search_metadata.search_time_ms}ms
 </div>
 </div>

 <div className="space-y-3 max-h-96 overflow-y-auto">
 {results.provisions.map((provision) => (
 <div
 key={provision.id}
 className="border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors"
 onClick={() => onProvisionSelect?.(provision)}
 >
 <div className="flex items-start justify-between">
 <div className="flex-1">
 <div className="flex items-center gap-2 mb-2">
 <span className="font-medium">{provision.clause}</span>
 <span className="text-sm bg-blue-100 text-blue-800 px-2 py-1 rounded">
 {provision.document_type}
 </span>
 <span className="text-sm bg-gray-100 text-gray-800 px-2 py-1 rounded">
 {provision.category}
 </span>
 </div>
 <h5 className="font-medium text-gray-900 mb-1">{provision.title}</h5>
 <p className="text-sm text-gray-600 line-clamp-2">{provision.content}</p>
 <div className="mt-2 text-xs text-gray-500">
 {provision.document_identifier} • {new Date(provision.effective_date).toLocaleDateString()}
 </div>
 </div>
 </div>
 </div>
 ))}
 </div>

 {results.suggested_refinements && results.suggested_refinements.length > 0 && (
 <div className="mt-4 p-3 bg-blue-50 rounded-lg">
 <div className="text-sm font-medium text-blue-800 mb-1">Suggested refinements:</div>
 <div className="text-sm text-blue-700">
 {results.suggested_refinements.join(' • ')}
 </div>
 </div>
 )}
 </div>
 )}
 </div>
 </div>
 );
}
