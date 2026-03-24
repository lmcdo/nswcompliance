'use client';

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import PropertyCard from '@/components/assessment/core/PropertyCard';
import ComplianceChecklist from '@/components/assessment/core/ComplianceChecklist';
import VersionSelector from '@/components/assessment/core/VersionSelector';
import { DevelopmentType, VersionInfo } from '@/lib/assessment/types';

export default function VersionAwareAssessmentPage() {
 const [selectedAddress, setSelectedAddress] = useState('');
 const [selectedProperty, setSelectedProperty] = useState<any>(null);
 const [developmentType, setDevelopmentType] = useState<DevelopmentType | ''>('');
 const [assessmentDate, setAssessmentDate] = useState(new Date().toISOString().split('T')[0]);
 const [selectedVersion, setSelectedVersion] = useState<VersionInfo | null>(null);
 const [complianceData, setComplianceData] = useState<any>(null);
 const [loading, setLoading] = useState(false);

 const handleAddressSelect = (address: string) => {
 setSelectedAddress(address);
 setSelectedProperty(null);
 setComplianceData(null);
 };

 const handlePropertyLoaded = (property: any) => {
 setSelectedProperty(property);
 };

 const handleVersionChange = (version: VersionInfo | null) => {
 setSelectedVersion(version);
 };

 const runVersionAwareAssessment = async () => {
 if (!selectedProperty || !developmentType) return;

 setLoading(true);
 try {
 const response = await fetch('/api/assessment/version-compliance', {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 propertyId: selectedProperty.propId,
 zone: selectedProperty.zone,
 developmentType,
 assessmentDate,
 documentType: 'LEP',
 documentIdentifier: `${selectedProperty.lga}-LEP`,
 useCurrentVersion: !selectedVersion || selectedVersion.version_status === 'CURRENT'
 })
 });

 if (response.ok) {
 const data = await response.json();
 setComplianceData(data.data);
 }
 } catch (error) {
 console.error('Failed to run version-aware assessment:', error);
 } finally {
 setLoading(false);
 }
 };

 return (
 <div className="min-h-screen bg-gray-50">
 {/* Header */}
 <div className="bg-white shadow-sm border-b">
 <div className="max-w-7xl mx-auto px-4 py-4">
 <h1 className="text-2xl font-bold text-gray-900">
 Version-Aware Planning Assessment
 </h1>
 <p className="text-gray-600 mt-1">
 Professional compliance assessment with historical version support
 </p>
 </div>
 </div>

 {/* Search Bar */}
 <div className="bg-white border-b px-4 py-3">
 <div className="max-w-7xl mx-auto">
 <PropertySearch
 onAddressSelect={handleAddressSelect}
 selectedAddress={selectedAddress}
 loading={false}
 />
 </div>
 </div>

 {/* Main Content */}
 <div className="max-w-7xl mx-auto px-4 py-6">
 <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
 {/* Left Panel - Property Context & Version Control */}
 <div className="lg:col-span-1 space-y-6">
 <PropertyCard
 address={selectedAddress}
 onPropertyLoaded={handlePropertyLoaded}
 />

 {/* Assessment Date Selector */}
 {selectedProperty && (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Assessment Date</h3>
 <input
 type="date"
 value={assessmentDate}
 onChange={(e) => setAssessmentDate(e.target.value)}
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 />
 <p className="text-sm text-gray-600 mt-2">
 Select the date for historical compliance assessment
 </p>
 </div>
 )}

 {/* Version Selector */}
 {selectedProperty && (
 <VersionSelector
 documentType="LEP"
 documentIdentifier={`${selectedProperty.lga}-LEP`}
 selectedDate={assessmentDate}
 onVersionChange={handleVersionChange as any}
 />
 )}

 {/* Development Type Selector */}
 {selectedProperty && (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Development Type</h3>
 <select
 value={developmentType}
 onChange={(e) => setDevelopmentType(e.target.value as DevelopmentType)}
 className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
 >
 <option value="">Select development type...</option>
 <option value="dwelling_house">Single Dwelling House</option>
 <option value="dual_occupancy">Dual Occupancy</option>
 <option value="multi_dwelling_housing">Multi Dwelling Housing</option>
 <option value="residential_flat_building">Residential Flat Building</option>
 <option value="commercial_premises">Commercial Premises</option>
 <option value="retail_premises">Retail Premises</option>
 <option value="office_premises">Office Premises</option>
 <option value="industrial">Industrial Development</option>
 <option value="warehouse">Warehouse or Storage</option>
 <option value="mixed_use">Mixed Use Development</option>
 </select>

 {developmentType && (
 <button
 onClick={runVersionAwareAssessment}
 disabled={loading}
 className="w-full mt-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
 >
 {loading ? 'Running Assessment...' : 'Run Version-Aware Assessment'}
 </button>
 )}
 </div>
 )}
 </div>

 {/* Right Panel - Assessment Results */}
 <div className="lg:col-span-3 space-y-6">
 {complianceData && (
 <>
 {/* Assessment Context */}
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Assessment Context</h3>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <div className="text-blue-800 font-medium">Assessment Date</div>
 <div className="text-sm text-blue-600 mt-1">
 {new Date(assessmentDate).toLocaleDateString()}
 </div>
 </div>
 <div className="bg-green-50 border border-green-200 rounded-lg p-4">
 <div className="text-green-800 font-medium">Document Version</div>
 <div className="text-sm text-green-600 mt-1">
 {selectedVersion?.version_number || 'Current'}
 </div>
 </div>
 <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
 <div className="text-purple-800 font-medium">Version Status</div>
 <div className="text-sm text-purple-600 mt-1">
 {complianceData.assessment_context?.version_aware ? 'Historical' : 'Current'}
 </div>
 </div>
 <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
 <div className="text-gray-800 font-medium">Compliance Items</div>
 <div className="text-sm text-gray-600 mt-1">
 {complianceData.summary?.total_items || 0} checks
 </div>
 </div>
 </div>
 </div>

 {/* Compliance Results */}
 <ComplianceChecklist
 items={complianceData.compliance_items?.map((item: any, index: number) => ({
 id: index.toString(),
 provision: item.provision,
 clause: item.clause,
 status: item.status,
 details: `${item.details}${item.version_context ? ` (${item.version_context})` : ''}`
 })) || []}
 />
 </>
 )}

 {!selectedProperty && (
 <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
 <div className="text-gray-500">
 <h3 className="text-lg font-medium mb-2">No Property Selected</h3>
 <p>Enter a property address above to begin version-aware assessment</p>
 </div>
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 );
}
