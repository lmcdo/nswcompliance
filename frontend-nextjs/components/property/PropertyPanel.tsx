// components/property/PropertyPanel.tsx
'use client';

import { Building, MapPin, FileText, Shield, Loader2 } from 'lucide-react';
import type { PropertyData } from '@/types/property';

interface PropertyPanelProps {
 property: PropertyData | null;
 loading?: boolean;
 error?: string | null;
}

export function PropertyPanel({ property, loading, error }: PropertyPanelProps) {
 if (loading) {
 return (
 <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
 <div className="flex items-center gap-2 mb-4">
 <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
 <h3 className="text-lg font-semibold text-gray-900">Loading Property Data...</h3>
 </div>
 <div className="space-y-3">
 <div className="h-4 bg-gray-200 rounded animate-pulse"></div>
 <div className="h-4 bg-gray-200 rounded animate-pulse w-3/4"></div>
 <div className="h-4 bg-gray-200 rounded animate-pulse w-1/2"></div>
 </div>
 </div>
 );
 }

 if (error) {
 return (
 <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
 <div className="text-red-600">
 <h3 className="font-semibold mb-2">Property Analysis Failed</h3>
 <p className="text-sm">{error}</p>
 </div>
 </div>
 );
 }

 if (!property) {
 return (
 <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
 <div className="text-center text-gray-500 py-8">
 <Building className="h-12 w-12 mx-auto mb-4 opacity-50" />
 <p>Enter an address to view property details</p>
 </div>
 </div>
 );
 }

 return (
 <div className="bg-white border border-gray-200 rounded-lg shadow-sm p-6">
 <div className="space-y-6">
 {/* Property Address */}
 <div>
 <h3 className="font-semibold text-gray-900 mb-3">Property Address</h3>
 <p className="text-sm text-gray-700 mb-2">{property.address}</p>
 {property.prop_id && (
 <p className="text-xs text-gray-500">Property ID: {property.prop_id}</p>
 )}
 </div>

 {/* Planning Controls */}
 <div>
 <h3 className="font-semibold text-gray-900 mb-3">Planning Controls</h3>
 <div className="space-y-3">
 <div className="flex justify-between items-center">
 <span className="text-sm text-gray-600">Zone:</span>
 <span className="font-medium text-sm text-blue-600">
 {property.zone || 'R2'}
 </span>
 </div>
 <div className="flex justify-between items-center">
 <span className="text-sm text-gray-600">Height Limit:</span>
 <span className="font-medium text-sm">
 {property.height_limit ? `${property.height_limit}${property.height_units || 'm'}` : '9.5m'}
 </span>
 </div>
 <div className="flex justify-between items-center">
 <span className="text-sm text-gray-600">FSR Limit:</span>
 <span className="font-medium text-sm">
 {property.fsr_limit ? `${property.fsr_limit}:1 sq m` : '0.6:1 sq m'}
 </span>
 </div>
 {property.heritage_status && (
 <div className="flex justify-between items-center">
 <span className="text-sm text-gray-600">Heritage:</span>
 <span className="font-medium text-sm text-orange-600">
 {property.heritage_status}
 </span>
 </div>
 )}
 </div>
 </div>

 {/* Council Information */}
 <div>
 <h3 className="font-semibold text-gray-900 mb-3">Council Information</h3>
 <div className="space-y-2">
 {property.lga_name && (
 <div className="flex justify-between items-center">
 <span className="text-sm text-gray-600">LGA:</span>
 <span className="font-medium text-sm">{property.lga_name}</span>
 </div>
 )}
 {property.coordinates && (
 <div className="text-xs text-gray-500 mt-2">
 Coordinates: {property.coordinates.lat.toFixed(6)}, {property.coordinates.lng.toFixed(6)}
 </div>
 )}
 </div>
 </div>

 {/* Heritage Overlays */}
 {property.heritage_overlays && property.heritage_overlays.length > 0 && (
 <div>
 <h4 className="font-semibold text-gray-900 mb-2">Heritage Overlays</h4>
 <div className="space-y-1">
 {property.heritage_overlays.map((overlay, index) => (
 <div key={index} className="text-xs bg-orange-50 text-orange-800 px-2 py-1 rounded">
 {overlay}
 </div>
 ))}
 </div>
 </div>
 )}
 </div>
 </div>
 );
}