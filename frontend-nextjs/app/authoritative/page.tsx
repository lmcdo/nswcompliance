'use client';

import React, { useState, useCallback } from 'react';
import AuthoritativeComplianceDisplay from '@/components/compliance/AuthoritativeComplianceDisplay';
import { PropertySearch } from '@/components/property/PropertySearch';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export default function AuthoritativePage() {
  const [address, setAddress] = useState('');
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [propertyData, setPropertyData] = useState<any>(null);
  const [basixProvisions, setBasixProvisions] = useState<any>(null);
  const [specialProvisions, setSpecialProvisions] = useState<any[]>([]);
  const [showResults, setShowResults] = useState(false);
  const [isLookingUp, setIsLookingUp] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

          // Automatically show compliance results when property is found
          setShowResults(true);
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
    <div className="container mx-auto p-6 space-y-6">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">
          PRP-8B Authoritative Compliance System
        </h1>
        <p className="text-xl text-gray-600">
          5-Tier Hierarchy Resolution with SEPP → LEP → DCP Authority Precedence
        </p>
      </div>

      {/* Property Address Input */}
      <Card>
        <CardHeader>
          <CardTitle>Property Address</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            <PropertySearch 
              onAddressSelect={handleAddressSelect}
              loading={isLookingUp}
              selectedAddress={address}
            />

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
                <h3 className="font-semibold text-green-800 mb-2">✅ Property Found - Analyzing Compliance...</h3>
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

      {/* Feature Documentation */}
      <Card>
        <CardHeader>
          <CardTitle>PRP-8B Implementation Features</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h3 className="text-lg font-semibold mb-3">Authority Hierarchy</h3>
              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span>Tier 1: SEPP/LEP Fully Authoritative</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                  <span>Tier 2: DCP High Authority</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-orange-500 rounded"></div>
                  <span>Tier 3: Moderate Authority</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-yellow-500 rounded"></div>
                  <span>Tier 4: Framework Guidance</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-4 h-4 bg-red-500 rounded"></div>
                  <span>Tier 5: Specialist Required</span>
                </div>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold mb-3">System Capabilities</h3>
              <ul className="space-y-1 text-sm text-gray-600">
                <li>• SEPP > LEP > DCP precedence resolution</li>
                <li>• Primary authority identification by context</li>
                <li>• Confidence scoring and complexity assessment</li>
                <li>• Legal disclaimer generation by tier</li>
                <li>• Response caching for performance</li>
                <li>• Full text provision display</li>
                <li>• Authority override tracking</li>
                <li>• Professional guidance referrals</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}