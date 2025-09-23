'use client';

import React, { useState } from 'react';

interface DevelopmentPermission {
 development_type: string;
 source: string;
 confidence: number;
}

interface DevelopmentPermissions {
 permitted_without_consent: DevelopmentPermission[];
 permitted_with_consent: DevelopmentPermission[];
 prohibited: DevelopmentPermission[];
 source_summary: Record<string, number>;
 total_combinations: number;
 coverage_note: string;
}

interface FeasibilityCheck {
 development_type: string;
 zone: string;
 permission_status: string;
 confidence: string;
 message: string;
 source_type?: string;
}

interface ComplianceResponse {
 zone: string;
 property_id?: number;
 development_type?: string;

 // Core hierarchy resolver fields (existing)
 tier_1_provisions?: any[];
 tier_2_provisions?: any[];
 tier_3_provisions?: any[];
 tier_4_provisions?: any[];
 tier_5_provisions?: any[];
 primary_authorities?: any;
 complexity_assessment?: string;
 confidence_level?: number;
 legal_disclaimer?: string;

 // Enhanced fields (new - optional)
 development_permissions?: DevelopmentPermissions;
 feasibility_check?: FeasibilityCheck;

 // Error handling
 error?: string;
 fallback?: boolean;
}

export default function EnhancedComplianceCheck() {
 const [zoneCode, setZoneCode] = useState('');
 const [developmentType, setDevelopmentType] = useState('');
 const [includeDevelopmentPermissions, setIncludeDevelopmentPermissions] = useState(false);
 const [isLoading, setIsLoading] = useState(false);
 const [response, setResponse] = useState<ComplianceResponse | null>(null);
 const [error, setError] = useState<string | null>(null);

 const handleSubmit = async (e: React.FormEvent) => {
 e.preventDefault();
 setIsLoading(true);
 setError(null);
 setResponse(null);

 try {
 const requestBody: any = {
 zone_code: zoneCode
 };

 // Add optional parameters
 if (developmentType) {
 requestBody.development_type = developmentType;
 }

 if (includeDevelopmentPermissions) {
 requestBody.include_development_permissions = true;
 }

 console.log('Making API request:', requestBody);

 const apiResponse = await fetch('/api/authoritative/compliance-check', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify(requestBody),
 });

 const data = await apiResponse.json();
 console.log('API response:', data);

 if (!apiResponse.ok) {
 throw new Error(data.error || 'API request failed');
 }

 setResponse(data);
 } catch (err) {
 console.error('API error:', err);
 setError(err instanceof Error ? err.message : 'Unknown error occurred');
 } finally {
 setIsLoading(false);
 }
 };

 return (
 <div className="max-w-4xl mx-auto p-6 bg-white rounded-lg shadow-lg">
 <h2 className="text-2xl font-bold mb-6 text-gray-900">
 Enhanced Compliance Check (PRP-P5)
 </h2>

 <form onSubmit={handleSubmit} className="space-y-4 mb-6">
 <div>
 <label htmlFor="zoneCode" className="block text-sm font-medium text-gray-700 mb-1">
 Zone Code (Required)
 </label>
 <input
 type="text"
 id="zoneCode"
 value={zoneCode}
 onChange={(e) => setZoneCode(e.target.value)}
 placeholder="e.g., R2, B1, IN1"
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 required
 />
 </div>

 <div>
 <label htmlFor="developmentType" className="block text-sm font-medium text-gray-700 mb-1">
 Development Type (Optional - enables feasibility check)
 </label>
 <input
 type="text"
 id="developmentType"
 value={developmentType}
 onChange={(e) => setDevelopmentType(e.target.value)}
 placeholder="e.g., dwelling_house, retail_premises"
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 />
 </div>

 <div className="flex items-center">
 <input
 type="checkbox"
 id="includeDevelopmentPermissions"
 checked={includeDevelopmentPermissions}
 onChange={(e) => setIncludeDevelopmentPermissions(e.target.checked)}
 className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
 />
 <label htmlFor="includeDevelopmentPermissions" className="ml-2 block text-sm text-gray-900">
 Include Development Permissions (shows all allowed/prohibited development types)
 </label>
 </div>

 <button
 type="submit"
 disabled={isLoading}
 className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
 >
 {isLoading ? 'Checking...' : 'Check Compliance'}
 </button>
 </form>

 {error && (
 <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
 <p className="text-red-600 font-medium">Error:</p>
 <p className="text-red-600">{error}</p>
 </div>
 )}

 {response && (
 <div className="space-y-6">
 {/* Basic Response Info */}
 <div className="bg-gray-50 p-4 rounded-md">
 <h3 className="text-lg font-semibold mb-2">Basic Information</h3>
 <p><strong>Zone:</strong> {response.zone}</p>
 {response.fallback && (
 <p className="text-yellow-600 mt-2"> Using fallback response - some features may be limited</p>
 )}
 </div>

 {/* Feasibility Check (new feature) */}
 {response.feasibility_check && (
 <div className="bg-blue-50 p-4 rounded-md">
 <h3 className="text-lg font-semibold mb-2">Feasibility Check</h3>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 <div>
 <p><strong>Development Type:</strong> {response.feasibility_check.development_type}</p>
 <p><strong>Zone:</strong> {response.feasibility_check.zone}</p>
 </div>
 <div>
 <p className="flex items-center">
 <strong>Status:</strong>
 <span className={`ml-2 px-2 py-1 rounded text-sm ${
 response.feasibility_check.permission_status === 'permitted' ? 'bg-green-100 text-green-800' :
 response.feasibility_check.permission_status === 'consent' ? 'bg-yellow-100 text-yellow-800' :
 response.feasibility_check.permission_status === 'prohibited' ? 'bg-red-100 text-red-800' :
 'bg-gray-100 text-gray-800'
 }`}>
 {response.feasibility_check.permission_status}
 </span>
 </p>
 <p><strong>Confidence:</strong> {response.feasibility_check.confidence}</p>
 </div>
 </div>
 <p className="mt-2 text-sm"><strong>Result:</strong> {response.feasibility_check.message}</p>
 </div>
 )}

 {/* Development Permissions (new feature) */}
 {response.development_permissions && (
 <div className="bg-green-50 p-4 rounded-md">
 <h3 className="text-lg font-semibold mb-2">Development Permissions</h3>
 <p className="text-sm text-gray-600 mb-4">{response.development_permissions.coverage_note}</p>

 <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
 {/* Permitted */}
 <div>
 <h4 className="font-medium text-green-800 mb-2">
 Permitted ({response.development_permissions.permitted_without_consent.length})
 </h4>
 <div className="space-y-1 max-h-40 overflow-y-auto">
 {response.development_permissions.permitted_without_consent.map((perm, index) => (
 <div key={index} className="text-sm bg-green-100 p-2 rounded">
 <div className="font-medium">{perm.development_type}</div>
 <div className="text-xs text-green-600">Source: {perm.source}</div>
 </div>
 ))}
 </div>
 </div>

 {/* Consent Required */}
 <div>
 <h4 className="font-medium text-yellow-800 mb-2">
 Consent Required ({response.development_permissions.permitted_with_consent.length})
 </h4>
 <div className="space-y-1 max-h-40 overflow-y-auto">
 {response.development_permissions.permitted_with_consent.map((perm, index) => (
 <div key={index} className="text-sm bg-yellow-100 p-2 rounded">
 <div className="font-medium">{perm.development_type}</div>
 <div className="text-xs text-yellow-600">Source: {perm.source}</div>
 </div>
 ))}
 </div>
 </div>

 {/* Prohibited */}
 <div>
 <h4 className="font-medium text-red-800 mb-2">
 Prohibited ({response.development_permissions.prohibited.length})
 </h4>
 <div className="space-y-1 max-h-40 overflow-y-auto">
 {response.development_permissions.prohibited.map((perm, index) => (
 <div key={index} className="text-sm bg-red-100 p-2 rounded">
 <div className="font-medium">{perm.development_type}</div>
 <div className="text-xs text-red-600">Source: {perm.source}</div>
 </div>
 ))}
 </div>
 </div>
 </div>

 <div className="mt-4 text-xs text-gray-500">
 <p><strong>Data Sources:</strong> {JSON.stringify(response.development_permissions.source_summary)}</p>
 <p><strong>Total Combinations:</strong> {response.development_permissions.total_combinations}</p>
 </div>
 </div>
 )}

 {/* Existing Hierarchy Information (maintained for backward compatibility) */}
 {(response.tier_1_provisions || response.complexity_assessment) && (
 <div className="bg-gray-50 p-4 rounded-md">
 <h3 className="text-lg font-semibold mb-2">Hierarchy Resolution (Existing)</h3>
 {response.complexity_assessment && (
 <p><strong>Complexity:</strong> {response.complexity_assessment}</p>
 )}
 {response.confidence_level && (
 <p><strong>Confidence:</strong> {(response.confidence_level * 100).toFixed(1)}%</p>
 )}
 {response.tier_1_provisions && response.tier_1_provisions.length > 0 && (
 <p><strong>Tier 1 Provisions:</strong> {response.tier_1_provisions.length} found</p>
 )}
 </div>
 )}

 {/* Raw Response (for debugging) */}
 <details className="bg-gray-100 p-4 rounded-md">
 <summary className="cursor-pointer font-medium">Raw API Response (Debug)</summary>
 <pre className="mt-2 text-xs overflow-x-auto">
 {JSON.stringify(response, null, 2)}
 </pre>
 </details>
 </div>
 )}
 </div>
 );
}