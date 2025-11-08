'use client';

/**
 * PRIMARY ASSESSMENT PAGE - /assessment
 *
 * Two-column layout:
 * - Left (1/4): Property search + NSW Planning API data (all layers with clickable URLs)
 * - Right (3/4): ComplianceDashboard showing unfiltered SEPP/LEP/DCP provisions from database
 *
 * Database integration:
 * - Queries regulatory_provisions table (up to 50 provisions per zone)
 * - Displays color-coded by authority level (SEPP=red, LEP=blue, DCP=green)
 * - Expandable cards show full legal text via /api/provisions/[id]/complete
 */

import React, { useState, useEffect } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { ComplianceDashboard } from '@/components/compliance/ComplianceDashboard';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';
import { RegulatoryCurrencyBanner } from '@/components/compliance/RegulatoryCurrencyNotice';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';

export default function AssessmentPage() {
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<any>(null);
  const [selectedCoordinates, setSelectedCoordinates] = useState<google.maps.LatLngLiteral | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [developmentType, setDevelopmentType] = useState('dwelling_house');
  const [buildingHeight, setBuildingHeight] = useState<number | null>(null);
  const [showZoneInfo, setShowZoneInfo] = useState(false);
  const [lepClauseData, setLepClauseData] = useState<any>(null);

  // Fetch LEP clause data when property or dev type changes
  useEffect(() => {
    async function fetchLepClauses() {
      if (!selectedProperty) {
        setLepClauseData(null);
        return;
      }

      const lotArea = selectedProperty.propertyArea ? parseFloat(selectedProperty.propertyArea.replace(/[^\d.]/g, '')) : null;
      if (!lotArea) return;

      try {
        const response = await fetch('/api/capacity/calculate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            address: selectedProperty.address,
            coordinates: selectedCoordinates,
            developmentType: developmentType,
            lotArea: lotArea,
            zone: selectedProperty.constraints?.zone || '',
            lga: selectedProperty.constraints?.lga || '',
            formerCouncil: selectedProperty.constraints?.formerCouncil || ''
          })
        });

        if (response.ok) {
          const data = await response.json();
          setLepClauseData(data);
        }
      } catch (error) {
        console.error('Failed to fetch LEP clause data:', error);
      }
    }

    fetchLepClauses();
  }, [selectedProperty, developmentType, selectedCoordinates]);

  const handleAddressSelect = async (address: string, coordinates?: google.maps.LatLngLiteral) => {
    console.log('=== handleAddressSelect CALLED ===');
    console.log('Address:', address);
    console.log('Coordinates:', coordinates);

    setSelectedAddress(address);
    setSelectedCoordinates(coordinates || null);
    setLoading(true);
    setError(null);

    try {
      const url = `/api/property?address=${encodeURIComponent(address)}`;
      console.log('Fetching:', url);

      const response = await fetch(url);
      console.log('Response status:', response.status);
      console.log('Response ok:', response.ok);

      if (response.ok) {
        const apiResponse = await response.json();
        console.log('API Response:', apiResponse);

        if (apiResponse.success) {
          console.log('✅ Success! Property data:', apiResponse.data);
          setSelectedProperty(apiResponse.data);
        } else {
          console.error('❌ API returned error:', apiResponse.error);
          throw new Error(apiResponse.error || 'Failed to load property');
        }
      } else {
        const errorText = await response.text();
        console.error('❌ HTTP Error:', response.status, errorText);
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      console.error('❌ Fetch error:', err);
      setError(err instanceof Error ? err.message : 'Failed to load property');
      setSelectedProperty(null);
    } finally {
      setLoading(false);
      console.log('=== handleAddressSelect COMPLETE ===');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Regulatory Currency Warning Banner */}
      <RegulatoryCurrencyBanner />

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
            loading={loading}
          />
        </div>
      </div>

      {/* Main Content - 2 Column Layout */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Left Panel - Property Card (1/4 width) */}
          <div className="lg:col-span-1 space-y-6">
            <div className="bg-white border rounded-lg p-6 shadow-sm">
              <h3 className="text-lg font-semibold mb-4">Property Information</h3>

              {loading && (
                <div className="animate-pulse space-y-3">
                  <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  <div className="h-3 bg-gray-200 rounded"></div>
                  <div className="h-3 bg-gray-200 rounded w-3/4"></div>
                </div>
              )}

              {error && (
                <div className="text-red-600 text-sm">{error}</div>
              )}

              {!loading && !error && !selectedProperty && (
                <p className="text-gray-600 text-sm">Enter an address to load property data</p>
              )}

              {selectedProperty && (
                <div className="space-y-3">
                  <div>
                    <label className="text-sm text-gray-600">Address</label>
                    <p className="font-medium text-sm">{selectedProperty.address}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">
                        Zone
                      </label>
                      <span className="block px-2 py-1 rounded text-xs font-medium bg-blue-100 text-blue-800">
                        {selectedProperty.constraints?.zoneDescription || selectedProperty.constraints?.zone || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Area</label>
                      <p className="font-medium text-sm">{selectedProperty.propertyArea || 'Unknown'}</p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-sm text-gray-600">LGA</label>
                      <p className="font-medium text-sm">{selectedProperty.constraints?.lga || 'Unknown'}</p>
                    </div>
                    <div>
                      <label className="text-sm text-gray-600">Heritage</label>
                      <p className="font-medium text-sm">{selectedProperty.heritage?.isHeritage ? 'Yes' : 'No'}</p>
                    </div>
                  </div>

                  {/* TOD/HIA Indicators - Phase 6 */}
                  {selectedProperty.constraints?.todPrecinct && (
                    <div className="bg-blue-50 border-2 border-blue-300 rounded-lg p-4 mt-4">
                      <div className="flex items-center gap-2 mb-2">
                        <svg className="w-5 h-5 text-blue-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className="font-semibold text-blue-900 text-sm">
                          Transport Oriented Development Area
                        </span>
                      </div>
                      <p className="text-sm text-blue-800 mb-2">
                        {selectedProperty.constraints.todPrecinct.precinctName}
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-white rounded p-2">
                          <p className="text-gray-600 text-xs">Max FSR</p>
                          <p className="font-semibold text-blue-900">
                            {selectedProperty.constraints.todPrecinct.maxFSRBonus || 2.5}:1
                          </p>
                        </div>
                        <div className="bg-white rounded p-2">
                          <p className="text-gray-600 text-xs">Max Height</p>
                          <p className="font-semibold text-blue-900">
                            {selectedProperty.constraints.todPrecinct.maxHeightBonus || 24}m
                          </p>
                        </div>
                        {selectedProperty.constraints.todPrecinct.stationDistance && (
                          <div className="bg-white rounded p-2 col-span-2">
                            <p className="text-gray-600 text-xs">Distance to Station</p>
                            <p className="font-semibold text-blue-900">
                              {selectedProperty.constraints.todPrecinct.stationDistance}m
                            </p>
                          </div>
                        )}
                      </div>
                      <p className="text-xs text-blue-600 mt-2">
                        {selectedProperty.constraints.todPrecinct.seppReference || 'SEPP (Housing) 2021'}
                      </p>
                    </div>
                  )}

                  {selectedProperty.constraints?.acceleratedTOD && (
                    <div className="bg-purple-50 border-2 border-purple-300 rounded-lg p-4 mt-2">
                      <div className="flex items-center gap-2 mb-1">
                        <svg className="w-5 h-5 text-purple-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className="font-semibold text-purple-900 text-sm">
                          Priority Accelerated Precinct
                        </span>
                      </div>
                      <p className="text-sm text-purple-800 mt-1">
                        Fast-track rezoning: {selectedProperty.constraints.acceleratedTOD.precinctName}
                      </p>
                      {selectedProperty.constraints.acceleratedTOD.expectedRezoning && (
                        <p className="text-xs text-purple-600 mt-1">
                          Expected: {selectedProperty.constraints.acceleratedTOD.expectedRezoning}
                        </p>
                      )}
                    </div>
                  )}

                  {selectedProperty.constraints?.hiaArea && (
                    <div className="bg-green-50 border-2 border-green-300 rounded-lg p-4 mt-2">
                      <div className="flex items-center gap-2 mb-1">
                        <svg className="w-5 h-5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        <span className="font-semibold text-green-900 text-sm">
                          Housing Infrastructure Area
                        </span>
                      </div>
                      <p className="text-sm text-green-800 mt-1">
                        {selectedProperty.constraints.hiaArea.hiaName}
                      </p>
                      {selectedProperty.constraints.hiaArea.specialControls && (
                        <p className="text-xs text-green-700 mt-1">
                          {selectedProperty.constraints.hiaArea.specialControls}
                        </p>
                      )}
                    </div>
                  )}

                  {/* Development Type Selector */}
                  <div className="border-t pt-3">
                    <label className="text-sm text-gray-600 block mb-2">Development Type</label>
                    <select
                      value={developmentType}
                      onChange={(e) => setDevelopmentType(e.target.value)}
                      className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    >
                      <option value="dwelling_house">Dwelling House</option>
                      <option value="secondary_dwelling">Secondary Dwelling</option>
                      <option value="shop_top_housing">Shop Top Housing</option>
                      <option value="multi_dwelling">Multi Dwelling Housing</option>
                      <option value="residential_flat">Residential Flat Building</option>
                      <option value="boarding_house">Boarding House</option>
                      <option value="child_care">Child Care Centre</option>
                      <option value="commercial">Commercial Premises</option>
                    </select>
                    <p className="text-xs text-gray-500 mt-1">
                      Filters out clearly irrelevant DCP controls for this development type
                    </p>
                  </div>

                  {/* Building Height Input (conditional on multi-dwelling types) */}
                  {(developmentType === 'multi_dwelling' ||
                    developmentType === 'residential_flat' ||
                    developmentType === 'shop_top_housing') && (
                    <div className="border-t pt-3">
                      <label className="text-sm text-gray-600 block mb-2">
                        Building Height (meters)
                        <span className="text-red-500 ml-1">*</span>
                      </label>
                      <input
                        type="number"
                        step="0.1"
                        min="0"
                        max="100"
                        value={buildingHeight || ''}
                        onChange={(e) => setBuildingHeight(parseFloat(e.target.value) || null)}
                        className="w-full px-3 py-2 border rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                        placeholder="e.g., 10.5"
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Required for ADG building separation standards
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* Planning API Data - All Layers */}
            {selectedProperty && (
              <PropertyDetailsComprehensive
                propertyData={selectedProperty}
                lepClauseData={lepClauseData}
              />
            )}
          </div>

          {/* Right Panel - ComplianceDashboard with SEPP/LEP/DCP provisions (3/4 width) */}
          <div className="lg:col-span-3">
            {!selectedProperty && (
              <div className="bg-white border rounded-lg p-12 shadow-sm text-center">
                <h3 className="text-lg font-medium mb-2 text-gray-500">No Property Selected</h3>
                <p className="text-gray-600">Enter a property address to see compliance provisions</p>
              </div>
            )}

            {selectedProperty && (
              <>
                {/* Compliance Dashboard - Show all applicable provisions */}
                <ComplianceDashboard
                  propertyData={selectedProperty}
                  developmentType={developmentType}
                  buildingHeight={buildingHeight}
                  className="transition-all duration-300 ease-in-out"
                />
              </>
            )}
          </div>
        </div>
      </div>

      {/* Zone Information Modal */}
      {showZoneInfo && selectedProperty?.constraints?.zone && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4" onClick={() => setShowZoneInfo(false)}>
          <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b px-6 py-4 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedProperty.constraints.zoneDescription || selectedProperty.constraints.zone}
              </h3>
              <button
                onClick={() => setShowZoneInfo(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-6 py-4">
              <p className="text-sm text-gray-600 mb-4">
                Zone information is extracted from the {selectedProperty.planningLayers?.find((l: any) => l.layerName === 'Land Zoning Map')?.results[0]?.['EPI Name'] || 'Local Environmental Plan'}.
              </p>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                <p className="text-sm text-blue-900 mb-2">
                  <strong>Zone Code:</strong> {selectedProperty.constraints.zone}
                </p>
                <p className="text-sm text-blue-900">
                  <strong>Zone Name:</strong> {selectedProperty.constraints.zoneDescription?.replace(selectedProperty.constraints.zone + ':', '').trim() || 'Loading...'}
                </p>
              </div>

              <div className="text-sm text-gray-700 space-y-3">
                <p>
                  Zone objectives, permitted uses, and prohibited uses are defined in the Local Environmental Plan (LEP) for this property.
                </p>

                <p className="font-semibold text-gray-900 mt-4">
                  To view the complete zone provisions:
                </p>

                <a
                  href={(() => {
                    const baseUrl = selectedProperty.planningLayers?.find((l: any) => l.layerName === 'Land Zoning Map')?.results[0]?.['legislationUrl'];
                    const zoneCode = selectedProperty.constraints.zone;
                    // For Inner West LEP 2022, add direct zone anchor
                    if (baseUrl?.includes('epi-2022-0457') && zoneCode) {
                      return `${baseUrl}#pt-cg1.Zone_${zoneCode}`;
                    }
                    return baseUrl || '#';
                  })()}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                >
                  View {selectedProperty.constraints.zone} Zone Provisions
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>

                <p className="text-xs text-gray-500 mt-4">
                  The LEP link above provides the official zone objectives, permitted uses, and prohibited uses as gazetted by NSW legislation.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Feedback Widget - Always visible */}
      <FeedbackWidget
        propertyAddress={selectedProperty?.address}
      />
    </div>
  );
}