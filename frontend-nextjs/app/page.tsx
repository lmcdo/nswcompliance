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
      <div className="compliance-app">
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              NSW Planning Compliance Engine
            </h1>
            <p className="text-xl text-gray-600">
              Precision planning analysis with intelligent reasoning
            </p>
          </div>

          {/* Property Search */}
          <div className="property-search-container">
            <PropertySearch 
              onAddressSelect={handleAddressSelect}
              loading={loading?.property}
              selectedAddress={selectedAddress}
            />
          </div>

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