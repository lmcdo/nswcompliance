'use client';

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import PropertyCard from '@/components/assessment/core/PropertyCard';
import ComplianceChecklist from '@/components/assessment/core/ComplianceChecklist';
import { DevelopmentType } from '@/lib/assessment/types';

export default function AssessmentPage() {
 const [selectedAddress, setSelectedAddress] = useState('');
 const [selectedProperty, setSelectedProperty] = useState<any>(null);
 const [developmentType, setDevelopmentType] = useState<DevelopmentType | ''>('');

 const handleAddressSelect = (address: string) => {
 setSelectedAddress(address);
 setSelectedProperty(null); // Will be set by PropertyCard
 };

 const handlePropertyLoaded = (property: any) => {
 setSelectedProperty(property);
 };

 return (
 <div className="min-h-screen bg-gray-50">
 {/* Header */}
 <div className="bg-white shadow-sm border-b">
 <div className="max-w-7xl mx-auto px-4 py-4">
 <h1 className="text-2xl font-bold text-gray-900">
 NSW Planning Assessment
 </h1>
 <p className="text-gray-600 mt-1">
 Professional compliance assessment using real-time planning data
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
 {/* Left Panel - Property Context */}
 <div className="lg:col-span-1 space-y-6">
 <PropertyCard
 address={selectedAddress}
 onPropertyLoaded={handlePropertyLoaded}
 />

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
 </div>
 )}
 </div>

 {/* Right Panel - Assessment */}
 <div className="lg:col-span-3 space-y-6">
 {selectedProperty && developmentType && (
 <>
 {/* Quick Status */}
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Quick Compliance Status</h3>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <div className="bg-green-50 border border-green-200 rounded-lg p-4">
 <div className="text-green-800 font-medium"> Permissible Use</div>
 <div className="text-sm text-green-600 mt-1">
 {developmentType.replace('_', ' ')} permitted
 </div>
 </div>
 <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
 <div className="text-yellow-800 font-medium"> Height Limit</div>
 <div className="text-sm text-yellow-600 mt-1">Check required</div>
 </div>
 <div className="bg-red-50 border border-red-200 rounded-lg p-4">
 <div className="text-red-800 font-medium"> Setbacks</div>
 <div className="text-sm text-red-600 mt-1">May not comply</div>
 </div>
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
 <div className="text-blue-800 font-medium">ℹ FSR</div>
 <div className="text-sm text-blue-600 mt-1">Within limits</div>
 </div>
 </div>
 </div>

 {/* Compliance Checklist */}
 <ComplianceChecklist
 items={[
 {
 id: '1',
 provision: 'Permissibility',
 clause: 'LEP Clause 2.3',
 status: 'compliant',
 details: `${developmentType.replace('_', ' ')} is permitted with consent in Zone ${selectedProperty.zone}`
 },
 {
 id: '2',
 provision: 'Minimum Lot Size',
 clause: 'LEP Clause 4.1',
 status: 'pending',
 details: 'Requires verification against DCP standards'
 }
 ]}
 />
 </>
 )}

 {!selectedProperty && (
 <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
 <div className="text-gray-500">
 <h3 className="text-lg font-medium mb-2">No Property Selected</h3>
 <p>Enter a property address above to begin assessment</p>
 </div>
 </div>
 )}
 </div>
 </div>
 </div>
 </div>
 );
}
