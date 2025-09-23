'use client';

import React from 'react';
import { useProperty } from '@/hooks/assessment/useProperty';

interface PropertyCardProps {
 address: string;
 onPropertyLoaded?: (property: any) => void;
}

export default function PropertyCard({ address, onPropertyLoaded }: PropertyCardProps) {
 const { property, loading, error } = useProperty(address);

 React.useEffect(() => {
 if (property && onPropertyLoaded) {
 onPropertyLoaded(property);
 }
 }, [property, onPropertyLoaded]);

 if (loading) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <div className="animate-pulse">
 <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
 <div className="space-y-3">
 <div className="h-3 bg-gray-200 rounded"></div>
 <div className="h-3 bg-gray-200 rounded w-3/4"></div>
 </div>
 </div>
 </div>
 );
 }

 if (error) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <div className="text-red-600">
 <h3 className="text-lg font-semibold mb-2">Error</h3>
 <p>{error}</p>
 </div>
 </div>
 );
 }

 if (!property) {
 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Property Information</h3>
 <p className="text-gray-600">Enter an address to load property data</p>
 </div>
 );
 }

 return (
 <div className="bg-white border rounded-lg p-6 shadow-sm">
 <h3 className="text-lg font-semibold mb-4">Property Information</h3>

 <div className="space-y-3">
 <div>
 <label className="text-sm text-gray-600">Address</label>
 <p className="font-medium">{property.address}</p>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className="text-sm text-gray-600">Zone</label>
 <div className="flex items-center gap-2">
 <span className={`px-2 py-1 rounded text-xs font-medium ${
 property.zone !== 'Unknown' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
 }`}>
 {property.zone}
 </span>
 </div>
 </div>
 <div>
 <label className="text-sm text-gray-600">Area</label>
 <p className="font-medium">{property.area}</p>
 </div>
 </div>

 <div className="grid grid-cols-2 gap-4">
 <div>
 <label className="text-sm text-gray-600">LGA</label>
 <p className="font-medium">{property.lga}</p>
 </div>
 <div>
 <label className="text-sm text-gray-600">Heritage</label>
 <p className="font-medium">{property.heritage ? 'Yes' : 'No'}</p>
 </div>
 </div>

 {property.landValue && (
 <div>
 <label className="text-sm text-gray-600">Land Value</label>
 <p className="font-medium">{property.landValue}</p>
 </div>
 )}
 </div>

 <div className="mt-4 flex gap-2">
 <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
 View Map
 </button>
 <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
 History
 </button>
 <button className="px-3 py-1 text-sm border rounded hover:bg-gray-50">
 Documents
 </button>
 </div>
 </div>
 );
}
