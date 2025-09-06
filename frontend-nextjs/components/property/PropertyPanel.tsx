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
      <div className="property-panel p-6">
        <div className="flex items-center gap-2 mb-4">
          <Loader2 className="h-5 w-5 animate-spin" />
          <h3 className="text-lg font-semibold">Loading Property Data...</h3>
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
      <div className="property-panel p-6">
        <div className="error-container">
          <h3 className="font-semibold mb-2">Property Analysis Failed</h3>
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!property) {
    return (
      <div className="property-panel p-6">
        <div className="text-center text-gray-500 py-8">
          <Building className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <p>Enter an address to view property details</p>
        </div>
      </div>
    );
  }

  return (
    <div className="property-panel p-6">
      <div className="space-y-6">
        {/* Property Address */}
        <div>
          <div className="flex items-center gap-2 mb-2">
            <MapPin className="h-4 w-4 text-blue-600" />
            <h3 className="font-semibold text-gray-900">Property Address</h3>
          </div>
          <p className="text-sm text-gray-700 leading-relaxed">{property.address}</p>
          {property.prop_id && (
            <p className="text-xs text-gray-500 mt-1">Property ID: {property.prop_id}</p>
          )}
        </div>

        {/* Planning Controls */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <FileText className="h-4 w-4 text-green-600" />
            <h3 className="font-semibold text-gray-900">Planning Controls</h3>
          </div>
          
          <div className="space-y-3">
            {/* Zone */}
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Zone:</span>
              <span className="font-medium text-sm">
                {property.zone || 'Not available'}
              </span>
            </div>

            {/* Height Limit */}
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">Height Limit:</span>
              <span className="font-medium text-sm">
                {property.height_limit ? `${property.height_limit}${property.height_units || 'm'}` : 'Not available'}
              </span>
            </div>

            {/* FSR Limit */}
            <div className="flex justify-between items-center py-2 border-b border-gray-100">
              <span className="text-sm text-gray-600">FSR Limit:</span>
              <span className="font-medium text-sm">
                {property.fsr_limit ? `${property.fsr_limit}:1` : 'Not available'}
              </span>
            </div>

            {/* Heritage Status */}
            {property.heritage_status && (
              <div className="flex justify-between items-center py-2 border-b border-gray-100">
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
          <div className="flex items-center gap-2 mb-3">
            <Shield className="h-4 w-4 text-purple-600" />
            <h3 className="font-semibold text-gray-900">Council Information</h3>
          </div>
          
          <div className="space-y-2">
            {property.lga_name && (
              <div className="text-sm">
                <span className="text-gray-600">LGA:</span>
                <span className="ml-2 font-medium">{property.lga_name}</span>
              </div>
            )}
            
            {property.applicable_lep && (
              <div className="text-sm">
                <span className="text-gray-600">LEP:</span>
                <span className="ml-2 font-medium text-xs">{property.applicable_lep}</span>
              </div>
            )}
          </div>
        </div>

        {/* Heritage Overlays */}
        {property.heritage_overlays && property.heritage_overlays.length > 0 && (
          <div>
            <h4 className="font-medium text-gray-900 mb-2">Heritage Overlays:</h4>
            <div className="space-y-1">
              {property.heritage_overlays.map((overlay, index) => (
                <div key={index} className="text-xs bg-orange-50 text-orange-800 px-2 py-1 rounded">
                  {overlay}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Coordinates */}
        {property.coordinates && (
          <div className="pt-4 border-t border-gray-200">
            <p className="text-xs text-gray-500">
              Coordinates: {property.coordinates.lat.toFixed(6)}, {property.coordinates.lng.toFixed(6)}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}