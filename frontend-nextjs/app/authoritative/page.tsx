'use client';

import React, { useState, useCallback } from 'react';
import AuthoritativeComplianceDisplay from '@/components/compliance/AuthoritativeComplianceDisplay';
import { PropertySearch } from '@/components/property/PropertySearch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function AuthoritativePage() {
  const [address, setAddress] = useState('');
  const [developmentType, setDevelopmentType] = useState('');
  const [propertyData, setPropertyData] = useState<any>(null);
  const [basixProvisions, setBasixProvisions] = useState<any>(null);
  const [specialProvisions, setSpecialProvisions] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Show results only when both property and development type are available
  React.useEffect(() => {
    setShowResults(Boolean(propertyData && developmentType));
  }, [propertyData, developmentType]);

  const lookupPropertyData = async (addressToLookup: string) => {
    if (!addressToLookup.trim()) return;
    
    setIsLookingUp(true);
    setError(null);
    setShowResults(false);
    
    try {
      const response = await fetch(`/api/property?address=${encodeURIComponent(addressToLookup)}`);
      if (response.ok) {
        const data = await response.json();
        if (data.data) {
          setPropertyData(data.data);

          // Extract BASIX provisions from constraints
          const constraints = data.data.constraints || {};
          if (constraints.basixClimate || constraints.basixWater) {
            setBasixProvisions({
              climate_zone: constraints.basixClimate,
              water_zone: constraints.basixWater
            });
          }

          // Extract special provisions if available
          if (data.data.layers) {
            const specialProvisionsLayer = data.data.layers.find((layer: any) =>
              layer.layerName === 'Special Provisions'
            );
            if (specialProvisionsLayer) {
              setSpecialProvisions(specialProvisionsLayer.results || []);
            }
          }

          // Only show compliance results when both property and development type are selected
          // setShowResults will be handled by useEffect when developmentType changes
        } else {
          setError('Property not found in NSW Planning Portal. Please check the address.');
          setPropertyData(null);
        }
      } else {
        const errorData = await response.text();
        setError(`Failed to lookup property: ${response.status} - Please try a different address`);
        setPropertyData(null);
      }
    } catch (error) {
      console.error('Property lookup failed:', error);
      setError('Network error: Unable to connect to property database. Please check your connection.');
      setPropertyData(null);
    } finally {
      setIsLookingUp(false);
    }
  };

  const handleAddressSelect = useCallback(async (
    newAddress: string, 
    coordinates?: google.maps.LatLngLiteral
  ) => {
    setAddress(newAddress);
    setShowResults(false);
    setPropertyData(null);
    setBasixProvisions(null);
    setSpecialProvisions([]);
    setError(null);
    await lookupPropertyData(newAddress);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              NSW Planning Compliance Analysis
            </h1>
            <p className="text-lg text-gray-600">
              Professional regulatory compliance assessment for NSW development applications
            </p>
          </div>

          <div className="space-y-8">
            {/* Property Analysis Input */}
            <Card>
        <CardHeader>
          <CardTitle>Property & Development Details</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <PropertySearch
              onAddressSelect={handleAddressSelect}
              loading={isLookingUp}
              selectedAddress={address}
            />

            {/* Development Type Selector */}
            <div>
              <label htmlFor="development-type" className="block text-sm font-medium text-gray-700 mb-2">
                Proposed Development Type <span className="text-red-500">*</span>
              </label>
              <select
                id="development-type"
                value={developmentType}
                onChange={(e) => setDevelopmentType(e.target.value)}
                className="w-full px-3 py-3 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 bg-white"
                required
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
              <p className="mt-1 text-sm text-gray-500">Select the type of development you want to assess for compliance</p>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-lg p-4">
                <h3 className="font-semibold text-red-800 mb-1">❌ Error</h3>
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            {/* Property Information Display */}
            {propertyData && (
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <h3 className="font-semibold text-green-800 mb-2">
                  ✅ Property Found
                  {developmentType ? ' - Analyzing Compliance...' : ' - Select development type to continue'}
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="font-medium">Zone:</span> {propertyData.constraints?.zone || 'Unknown'}
                  </div>
                  <div>
                    <span className="font-medium">LGA:</span> {propertyData.constraints?.lga || 'Unknown'}
                  </div>
                  <div>
                    <span className="font-medium">Property Area:</span> {propertyData.propertyArea || 'Unknown'}
                  </div>
                  <div>
                    <span className="font-medium">Heritage:</span> {propertyData.constraints?.heritage ? 'Yes' : 'No'}
                  </div>
                  <div>
                    <span className="font-medium">Max FSR:</span> {propertyData.constraints?.maxFsr ? `${propertyData.constraints.maxFsr}:1 square metres` : 'Not specified'}
                  </div>
                  <div>
                    <span className="font-medium">Land Value:</span> {propertyData.landValue || 'Unknown'}
                  </div>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Results */}
      {showResults && propertyData && (
        <AuthoritativeComplianceDisplay
          zoneCode={propertyData.constraints?.zone || 'Unknown'}
          developmentType={developmentType}
          address={address}
          propertyId={propertyData.propId}
          basixProvisions={basixProvisions}
          specialProvisions={specialProvisions}
          onDataLoaded={(data) => {
            console.log('Authoritative compliance data loaded:', data);
          }}
        />
      )}
          </div>
        </div>
      </div>
    </div>
  );
}