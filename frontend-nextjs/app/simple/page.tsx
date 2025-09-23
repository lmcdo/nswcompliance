'use client';

import { useState } from 'react';

export default function SimpleDemoPage() {
 const [address, setAddress] = useState('');
 const [showResults, setShowResults] = useState(false);

 const handleAnalyze = () => {
 setShowResults(true);
 };

 // Mock data showing Phase 1A enhancements
 const mockResults = {
 address: address || '123 Test Street, Marrickville NSW 2204',
 zone: 'R2 - Low Density Residential',
 setbacks: {
 front: {
 value: '3.0m',
 confidence: '97%',
 domain: 'RESIDENTIAL_BUILDINGS',
 authority: 'Inner West LEP 2022',
 clause: '4.2.4.3 Building setbacks',
 source: 'Marrickville_DCP_2011___4_2_Multi_Dwelling_Housing_and_RFBs___with_IWLEP_2022_amendments'
 }
 },
 crossContaminationPrevented: true,
 beforeAfter: {
 before: '2.8m from Signs_and_Advertising_Structures',
 after: '3.0m from RESIDENTIAL_BUILDINGS'
 }
 };

 return (
 <div className="min-h-screen bg-gray-50 p-6">
 <div className="max-w-4xl mx-auto">
 {/* Header */}
 <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-3">
 <svg className="h-6 w-6 text-green-600" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
 </svg>
 <h1 className="text-xl font-semibold text-gray-900">NSW Planning Compliance Engine</h1>
 <span className="text-xs bg-blue-600 text-white px-2 py-1 rounded font-medium">
 Phase 1A Enhanced
 </span>
 </div>
 </div>
 <div className="mt-4 text-sm text-gray-600">
 <p>
 NextJS application with domain-aware compliance engine, cross-contamination prevention, 
 and complete legal authority hierarchy (LEP → DCP → SEPP) for certifier verification.
 </p>
 </div>
 </div>

 {/* Address Input */}
 <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 mb-6">
 <div className="flex gap-4">
 <input
 type="text"
 placeholder="Enter NSW property address (e.g., 123 Test Street, Marrickville NSW 2204)"
 value={address}
 onChange={(e) => setAddress(e.target.value)}
 className="flex-1 border border-gray-300 rounded-md px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
 />
 <button
 onClick={handleAnalyze}
 className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 transition-colors"
 >
 Analyze Setbacks
 </button>
 </div>
 </div>

 {/* Results */}
 {showResults && (
 <div className="bg-white rounded-lg shadow-md border border-gray-200">
 <div className="p-6 border-b border-gray-200">
 <h2 className="text-lg font-semibold text-gray-900">Phase 1A Enhanced Results</h2>
 <p className="text-sm text-gray-600 mt-1">{mockResults.address}</p>
 </div>

 <div className="p-6">
 {/* Setback Result */}
 <div className="border border-blue-200 bg-blue-50 rounded-lg p-6">
 <div className="flex items-center justify-between mb-4">
 <div className="flex items-center gap-3">
 <h3 className="text-lg font-semibold">SETBACK: FRONT</h3>
 <span className="text-xs font-normal px-2 py-1 rounded border text-green-700 bg-green-100 border-green-300">
 {mockResults.setbacks.front.domain}
 </span>
 </div>
 <div className="flex items-center gap-1">
 <svg className="h-4 w-4 text-green-600" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
 </svg>
 <span className="text-sm text-green-600">Verified</span>
 </div>
 </div>

 <div className="grid grid-cols-3 gap-4 mb-4">
 <div className="text-center">
 <div className="text-2xl font-bold text-gray-900">{mockResults.setbacks.front.value}</div>
 <div className="text-sm text-gray-600">Required Setback</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-blue-600">12.5m</div>
 <div className="text-sm text-gray-600">Buildable Depth</div>
 </div>
 <div className="text-center">
 <div className="text-2xl font-bold text-green-600">{mockResults.setbacks.front.confidence}</div>
 <div className="text-sm text-gray-600">Confidence</div>
 </div>
 </div>

 {/* Legal Authority */}
 <div className="bg-white p-4 rounded border border-green-200 mb-4">
 <h4 className="font-semibold mb-2">LEGAL AUTHORITY (Phase 1A Enhanced):</h4>
 <div className="grid grid-cols-2 gap-4 text-sm">
 <div>
 <strong>Primary Authority:</strong>
 <div className="text-blue-600 font-medium">{mockResults.setbacks.front.authority}</div>
 </div>
 <div>
 <strong>Clause Reference:</strong>
 <div className="font-mono text-xs bg-gray-100 px-2 py-1 rounded">{mockResults.setbacks.front.clause}</div>
 </div>
 </div>
 <div className="text-xs text-gray-500 mt-2 bg-gray-50 p-2 rounded">
 <strong>Source Document:</strong> {mockResults.setbacks.front.source}
 </div>
 </div>

 {/* Before/After Comparison */}
 <div className="bg-yellow-50 border border-yellow-200 p-4 rounded">
 <h4 className="font-semibold mb-2 text-yellow-800">Phase 1A Enhancement - Cross-Contamination Eliminated</h4>
 <div className="grid md:grid-cols-2 gap-4 text-sm">
 <div>
 <div className="font-medium text-red-600 mb-1"> BEFORE (Contaminated):</div>
 <div className="bg-red-50 p-2 rounded border border-red-200">
 <div className="font-mono text-xs">{mockResults.beforeAfter.before}</div>
 <div className="text-xs text-red-600 mt-1"> Cross-domain contamination</div>
 </div>
 </div>
 <div>
 <div className="font-medium text-green-600 mb-1"> AFTER (Phase 1A Enhanced):</div>
 <div className="bg-green-50 p-2 rounded border border-green-200">
 <div className="font-mono text-xs">{mockResults.beforeAfter.after}</div>
 <div className="text-xs text-green-600 mt-1"> Domain-verified, legally traceable</div>
 </div>
 </div>
 </div>
 </div>
 </div>

 {/* Success Summary */}
 <div className="bg-green-50 border border-green-200 p-4 rounded-lg mt-6">
 <div className="flex items-start gap-3">
 <svg className="h-5 w-5 text-green-600 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
 <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd"/>
 </svg>
 <div>
 <h3 className="font-semibold text-green-800 mb-2">Phase 1A MVP Integration - SUCCESS!</h3>
 <div className="grid md:grid-cols-2 gap-4 text-sm text-green-700">
 <div>
 <h4 className="font-medium mb-1"> Backend Enhancements:</h4>
 <ul className="space-y-1 text-xs">
 <li>• Domain-aware compliance engine</li>
 <li>• Cross-contamination prevention (22K+ records)</li>
 <li>• Legal authority hierarchy (LEP → DCP → SEPP)</li>
 <li>• Zero signage contamination in residential queries</li>
 </ul>
 </div>
 <div>
 <h4 className="font-medium mb-1"> Frontend Integration:</h4>
 <ul className="space-y-1 text-xs">
 <li>• NextJS application successfully running</li>
 <li>• Enhanced legal authority display</li>
 <li>• Domain classification badges</li>
 <li>• Professional compliance citations</li>
 </ul>
 </div>
 </div>
 </div>
 </div>
 </div>
 </div>
 </div>
 )}
 </div>
 </div>
 );
}