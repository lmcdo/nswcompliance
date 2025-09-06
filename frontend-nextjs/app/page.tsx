// app/page.tsx
'use client';

import { useState, useCallback } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { PropertyPanel } from '@/components/property/PropertyPanel';
import { AnalysisTabs } from '@/components/dashboard/AnalysisTabs';
import { ErrorBoundary } from '@/components/dashboard/ErrorBoundary';
import { usePropertyData } from '@/hooks/usePropertyData';

export default function DashboardPage() {
  const [selectedAddress, setSelectedAddress] = useState<string>('');
  const { 
    property, 
    lotGeometry, 
    loading, 
    error, 
    analyzeProperty 
  } = usePropertyData();

  const handleAddressSelect = useCallback(async (
    address: string, 
    coordinates?: google.maps.LatLngLiteral
  ) => {
    setSelectedAddress(address);
    await analyzeProperty(address, coordinates);
  }, [analyzeProperty]);

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        {/* Compact Header with integrated search */}
        <div className="bg-indigo-600 text-white px-4 py-2">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-lg font-bold">NSW Planning Compliance Engine</h1>
            </div>
          </div>
        </div>

        {/* Search Bar - Full width, minimal padding */}
        <div className="bg-white border-b px-4 py-3">
          <PropertySearch 
            onAddressSelect={handleAddressSelect}
            loading={loading?.property}
            selectedAddress={selectedAddress}
          />
        </div>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 py-6">

          {/* Main Content Grid */}
          {(property || loading.property) && (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
              {/* Property Information Panel */}
              <div className="lg:col-span-1">
                <PropertyPanel 
                  property={property}
                  loading={loading.property}
                  error={error.property}
                />
              </div>

              {/* Analysis Tabs */}
              <div className="lg:col-span-3">
                <AnalysisTabs 
                  property={property}
                  lotGeometry={lotGeometry}
                  loading={loading}
                  error={error}
                />
              </div>
            </div>
          )}

          {/* Initial State */}
          {!property && !loading.property && (
            <div className="text-center py-16">
              <div className="text-gray-500 text-lg">
                Enter a NSW property address above to begin compliance analysis
              </div>
              <div className="mt-4 text-sm text-gray-400">
                Example: "15 Norton Street, Leichhardt NSW 2040"
              </div>
            </div>
          )}
        </div>
      </div>
    </ErrorBoundary>
  );
}