'use client';

import React, { useState, useCallback } from 'react';
import { ProvisionSearchFilters, ProvisionSearchResult, ComplianceProvision } from '@/lib/assessment/types';

interface ProvisionSearchProps {
 onProvisionSelect?: (provision: ComplianceProvision) => void;
 initialFilters?: ProvisionSearchFilters;
 className?: string;
 userZone?: string; // User's zone from property context for ranking boost
 enableRanking?: boolean; // Enable Tier 1 ranking (default: true)
 showRankingDetails?: boolean; // Show rank scores and explanations (default: false)
}

export default function ProvisionSearch({
 onProvisionSelect,
 initialFilters = {},
 className = '',
 userZone,
 enableRanking = true,
 showRankingDetails = false
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

 // Enable Tier 1 ranking
 if (enableRanking) {
 params.append('ranked', 'true');
 }

 // Pass user's zone for ranking boost
 if (userZone && enableRanking) {
 params.append('zone', userZone);
 }

 // Existing filters
 if (filters.document_types) params.append('document_types', filters.document_types.join(','));
 if (filters.categories) params.append('categories', filters.categories.join(','));
 if (filters.zones) params.append('zones', filters.zones.join(','));
 if (filters.status) params.append('status', filters.status.join(','));

 console.log('[ProvisionSearch] Search params:', {
 query,
 ranked: enableRanking,
 zone: userZone,
 url: `/api/provisions?${params.toString()}`
 });

 const response = await fetch(`/api/provisions?${params.toString()}`);
 const data = await response.json();

 if (data.success) {
 setResults(data.data);

 console.log('[ProvisionSearch] Results:', {
 total: data.data.total_count,
 ranked: data.meta.ranking_enabled,
 implementation: data.meta.implementation,
 response_time: data.meta.response_time_ms
 });
 }
 } catch (error) {
 console.error('Provision search failed:', error);
 } finally {
 setLoading(false);
 }
 }, [query, filters, userZone, enableRanking]);

 const handleFilterChange = (key: keyof ProvisionSearchFilters, value: any) => {
 setFilters((prev: ProvisionSearchFilters) => ({ ...prev, [key]: value }));
 };

 return (
 <div className={`bg-white border rounded-lg shadow-sm ${className}`}>
 <div className="p-6">
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-semibold">Provision Search</h3>

 {/* Zone context indicator */}
 {userZone && (
 <div className="flex items-center gap-2 text-sm">
 <span className="text-gray-600">Searching for zone:</span>
 <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded font-medium">
 {userZone}
 </span>
 </div>
 )}
 </div>

 {/* Search Input */}
 <div className="space-y-4">
 <input
 type="text"
 value={query}
 onChange={(e) => setQuery(e.target.value)}
 placeholder={
 userZone
 ? `Search requirements for ${userZone} zone...`
 : "Search provisions, clauses, or requirements..."
 }
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 onKeyPress={(e) => e.key === 'Enter' && performSearch()}
 />

 {/* Filter Toggle */}
 <button
 onClick={() => setShowFilters(!showFilters)}
 className="text-sm text-blue-600 hover:text-blue-700 transition-colors"
 >
 {showFilters ? 'Hide Filters' : 'Show Filters'}
 </button>

 {/* Search Button - full width on new row */}
 <button
 onClick={performSearch}
 disabled={loading}
 className="w-full px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 transition-colors"
 >
 {loading ? 'Searching...' : 'Search'}
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
 <div className="flex items-center gap-4 text-sm text-gray-500">
 <span>{results.search_metadata?.search_time_ms}ms</span>
 {results.search_metadata?.ranking_enabled && (
 <span className="text-green-600 flex items-center gap-1">
 <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
 </svg>
 Ranked
 </span>
 )}
 </div>
 </div>

 <div className="space-y-3 max-h-96 overflow-y-auto">
 {results.provisions.map((provision: any, index: number) => {
 // Authority level styling
 const authorityStyles: Record<string, any> = {
 SEPP: { bg: 'bg-red-50', border: 'border-l-4 border-red-500', badge: 'bg-red-100 text-red-800', label: 'State Override' },
 LEP: { bg: 'bg-blue-50', border: 'border-l-4 border-blue-500', badge: 'bg-blue-100 text-blue-800', label: 'Local Law' },
 DCP: { bg: 'bg-green-50', border: 'border-l-4 border-green-500', badge: 'bg-green-100 text-green-800', label: 'Design Guidance' }
 };
 const style = authorityStyles[provision.authority_level] || authorityStyles.DCP;
 const isTopResult = index < 3;
 const zoneMatches = userZone && provision.zone === userZone;
 const hasRanking = provision.ranking !== undefined;

 return (
 <div
 key={provision.id}
 className={`border rounded-lg p-4 hover:bg-gray-50 cursor-pointer transition-colors ${style.border} ${isTopResult ? 'bg-yellow-50' : style.bg}`}
 onClick={() => onProvisionSelect?.(provision)}
 >
 {/* Header with ranking */}
 <div className="flex items-start justify-between mb-3">
 <div className="flex items-center gap-2 flex-wrap">
 {hasRanking && (
 <div className="flex items-center gap-1">
 {index === 0 && <span>🥇</span>}
 {index === 1 && <span>🥈</span>}
 {index === 2 && <span>🥉</span>}
 <span className="text-xs font-medium text-gray-600">#{index + 1}</span>
 </div>
 )}
 <span className={`text-sm px-2 py-1 rounded font-medium ${style.badge}`}>
 {provision.authority_level}
 </span>
 <span className="text-xs text-gray-600">{style.label}</span>
 </div>

 <div className="flex items-center gap-2">
 {zoneMatches && (
 <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded flex items-center gap-1">
 <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"/>
 </svg>
 Your zone
 </span>
 )}
 {provision.zone && !zoneMatches && (
 <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
 Zone: {provision.zone}
 </span>
 )}
 </div>
 </div>

 {/* Content */}
 <div className="space-y-2">
 <div className="flex items-center gap-2">
 <span className="font-medium text-gray-900">{provision.ref_number || provision.clause}</span>
 {hasRanking && provision.ranking!.quant_boost > 1 && (
 <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded">
 📋 Has measurements
 </span>
 )}
 {provision.page_number > 0 && (
 <span className="text-xs text-gray-500">
 Page {provision.page_number}
 </span>
 )}
 </div>
 <p className="text-sm text-gray-700 line-clamp-3">
 {provision.provision_text || provision.content}
 </p>
 </div>
 </div>
 );
 })}
 </div>

 {results.provisions.length === 0 && (
 <div className="text-center py-8 text-gray-500">
 <p>No provisions found matching "{query}"</p>
 <p className="text-sm mt-2">Try different keywords or check filters</p>
 </div>
 )}
 </div>
 )}
 </div>
 </div>
 );
}
