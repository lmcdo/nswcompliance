'use client';

/**
 * PRIMARY ASSESSMENT PAGE - /assessment
 *
 * Two-column layout:
 * - Left (1/4): Property search + NSW Planning API data (all layers with clickable URLs)
 * - Right (3/4): Tabbed view with:
 *   - Tab 1 "SEPP": State-level controls (StructuredSeppRequirements, LandUseZoning, ADG, TOD)
 *   - Tab 2 "Planning Controls": Zone, height, FSR, overlays from Planning Portal
 *   - Tab 2 "DCP Provisions": Council-level provisions via ProvisionsByTocStructure (TOC-based view)
 */

import React from 'react';
import { MapPin } from 'lucide-react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { DCPInterestForm } from '@/components/compliance/DCPInterestForm';
import { ProvisionsByTocStructure } from '@/components/compliance/ProvisionsByTocStructure';

const DCP_ENABLED = process.env.NEXT_PUBLIC_DCP_ENABLED === 'true';
// When set, only show DCP for listed councils (comma-separated formerCouncil slugs).
// When unset, all councils show DCP (if DCP_ENABLED is true).
// Example: NEXT_PUBLIC_ENABLED_LGAS=marrickville,leichhardt,ashfield,waverley,ku_ring_gai
const ENABLED_LGAS = process.env.NEXT_PUBLIC_ENABLED_LGAS
  ? process.env.NEXT_PUBLIC_ENABLED_LGAS.split(',').map(s => s.trim().toLowerCase())
  : null;

function isDcpEnabledForCouncil(formerCouncil: string | undefined): boolean {
  if (!DCP_ENABLED) return false;
  if (!ENABLED_LGAS) return true; // no restriction — show all
  return ENABLED_LGAS.includes((formerCouncil || '').toLowerCase());
}
import { StateLevelControls } from '@/components/compliance/StateLevelControls';
import { LepControls } from '@/components/compliance/LepControls';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';
import { RegulatoryCurrencyBanner } from '@/components/compliance/RegulatoryCurrencyNotice';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';
import { StatusColors } from '@/lib/design-tokens';
import { usePropertyAssessment, useAssessmentUI } from '@/hooks';
import { SkeletonSeppContent, SkeletonDcpContent, SkeletonPropertyDetails } from '@/components/compliance/AssessmentSkeleton';

export default function AssessmentPage() {
  // Property data and fetching
  const {
    selectedAddress,
    selectedProperty,
    selectedCoordinates,
    loading,
    error,
    lepClauseData,
    developmentType,
    handleAddressSelect,
  } = usePropertyAssessment();

  // UI state (view mode, modals, inputs)
  const {
    viewMode,
    setViewMode,
    showZoneInfo,
    setShowZoneInfo,
    buildingHeight,
    setBuildingHeight,
    isDaMode,
    setIsDaMode,
  } = useAssessmentUI(selectedAddress);

  // Navigation handler for Pattern Book -> DCP cross-references
  const handleNavigateToDcp = (topic: string, hcaSlug?: string) => {
    setViewMode('dcp');
    // TODO: Apply topic and HCA filters to ProvisionsByTocStructure
    // This will require adding filter state and props to ProvisionsByTocStructure
    console.log('[Pattern Book Navigation] Switching to DCP tab:', { topic, hcaSlug });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Regulatory Currency Warning Banner */}
      <RegulatoryCurrencyBanner />

      {/* Header */}
      <header className="relative border-b shadow-sm overflow-hidden flex">
        {/* Tulip glyph - dark gray shape on white, curves into white logo area */}
        <div className="relative flex-shrink-0 bg-white">
          <svg className="h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
            <path d="M0 0 L16 0 Q36 14 28 28 Q20 42 36 56 L0 56 Z" fill="#374151" />
          </svg>
        </div>
        {/* Logo + name on white */}
        <a
          href="https://plotdetect.com.au/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 pr-4 py-3 md:py-4 bg-white hover:opacity-80 transition-opacity"
        >
          <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
          <span className="text-base font-semibold text-gray-900">PlotDetect</span>
        </a>
        {/* Rest of header - neutral white */}
        <div className="flex-1 bg-white flex items-center gap-4 px-4 py-3 md:py-4">
          {/* Page title */}
          <div className="flex-1">
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-gray-800">
              NSW Planning Assessment
            </h1>
            <p className="text-gray-600 text-xs hidden sm:block">
              Professional compliance assessment using real-time planning data
            </p>
          </div>
          {/* Quick Guide */}
          <div className="hidden sm:flex items-center">
            <a
              href="/quick-guide"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-teal-600 bg-white text-teal-700 hover:bg-teal-50 transition-colors"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Quick Guide
            </a>
          </div>
          <div className="hidden sm:flex items-center">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-gray-300 bg-gray-100 text-gray-700">
              <MapPin className="h-3.5 w-3.5" />
              {selectedProperty?.constraints?.lga || 'NSW Planning'}
            </span>
          </div>
        </div>
      </header>

      {/* Search Bar - sticky on mobile for easy access */}
      <div className="bg-white border-b px-4 py-3 sticky top-0 z-40 md:relative">
        <div className="max-w-7xl mx-auto">
          <PropertySearch
            onAddressSelect={handleAddressSelect}
            selectedAddress={selectedAddress}
            loading={loading}
          />
        </div>
      </div>

      {/* Legal Disclaimer Banner */}
      <div className="bg-amber-50 border-b border-amber-200 px-4 py-2">
        <div className="max-w-7xl mx-auto">
          <p className="text-xs text-amber-900 leading-relaxed">
            <strong>Disclaimer:</strong> PlotDetect presents DCP provisions and state/local planning data (from NSW Planning Portal and SEPP sources) as published by relevant authorities. It does not constitute planning advice. Users should verify provisions against current council instruments and seek professional advice for development applications.
          </p>
        </div>
      </div>

      {/* Main Content - 2 Column Layout (stacked on mobile) */}
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 md:py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 md:gap-6">
          {/* Left Panel - Static Property Context (1/4 width on desktop) */}
          {/* Muted styling signals "reference context" vs dynamic right panel */}
          <div className="lg:col-span-1 space-y-4 md:space-y-6">
            <div className="bg-stone-200 border-l-4 border-l-stone-500 rounded-r-lg p-4 md:p-6">
              <p className="text-xs font-medium text-stone-500 uppercase tracking-wide mb-1">The Property</p>
              <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-stone-800">Property Summary</h3>

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
                <p className="text-stone-600 text-sm">Enter an address to load property data</p>
              )}

              {selectedProperty && (
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-stone-500">Address</label>
                    <p className="font-medium text-sm text-stone-800">{selectedProperty.address}</p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-stone-500">
                        Zone
                      </label>
                      <span className="inline-block mt-1 px-2.5 py-1 rounded text-xs font-medium bg-sky-100 text-sky-700">
                        {selectedProperty.constraints?.zoneDescription || selectedProperty.constraints?.zone || 'Unknown'}
                      </span>
                    </div>
                    <div>
                      <label className="text-xs text-stone-500">Area</label>
                      <p className="font-medium text-sm text-stone-800">
                        {selectedProperty.lotDimensions?.area
                          ? `${Math.round(selectedProperty.lotDimensions.area)}m²`
                          : selectedProperty.propertyArea || 'Unknown'}
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs text-stone-500">LGA</label>
                      <p className="font-medium text-sm text-stone-800">{selectedProperty.constraints?.lga || 'Unknown'}</p>
                    </div>
                    <div>
                      <label className="text-xs text-stone-500">Heritage</label>
                      <p className="font-medium text-sm text-stone-800">{selectedProperty.heritage?.isHeritage ? 'Yes' : 'No'}</p>
                    </div>
                  </div>

                  {/* TOD/HIA Indicators - Phase 6 */}
                  {selectedProperty.constraints?.todPrecinct && (
                    <div className={`${StatusColors.TOD.bg} border-2 ${StatusColors.TOD.border} rounded-lg p-4 mt-4`}>
                      <div className="flex items-center gap-2 mb-2">
                        <svg className={`w-5 h-5 ${StatusColors.TOD.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className={`font-semibold ${StatusColors.TOD.text} text-sm`}>
                          Transport Oriented Development Area
                        </span>
                      </div>
                      <p className="text-sm text-blue-800 mb-2">
                        {selectedProperty.constraints.todPrecinct.precinctName}
                      </p>
                      <div className="grid grid-cols-2 gap-2 text-sm">
                        <div className="bg-white rounded p-2">
                          <p className="text-gray-600 text-xs">Max FSR</p>
                          <p className={`font-semibold ${StatusColors.TOD.text}`}>
                            {selectedProperty.constraints.todPrecinct.maxFSRBonus || 2.5}:1
                          </p>
                        </div>
                        <div className="bg-white rounded p-2">
                          <p className="text-gray-600 text-xs">Max Height</p>
                          <p className={`font-semibold ${StatusColors.TOD.text}`}>
                            {selectedProperty.constraints.todPrecinct.maxHeightBonus || 24}m
                          </p>
                        </div>
                        {selectedProperty.constraints.todPrecinct.stationDistance && (
                          <div className="bg-white rounded p-2 col-span-2">
                            <p className="text-gray-600 text-xs">Distance to Station</p>
                            <p className={`font-semibold ${StatusColors.TOD.text}`}>
                              {selectedProperty.constraints.todPrecinct.stationDistance}m
                            </p>
                          </div>
                        )}
                      </div>
                      <p className={`text-xs ${StatusColors.TOD.icon} mt-2`}>
                        {selectedProperty.constraints.todPrecinct.seppReference || 'SEPP (Housing) 2021'}
                      </p>
                    </div>
                  )}

                  {selectedProperty.constraints?.acceleratedTOD && (
                    <div className={`${StatusColors.Accelerated.bg} border-2 ${StatusColors.Accelerated.border} rounded-lg p-4 mt-2`}>
                      <div className="flex items-center gap-2 mb-1">
                        <svg className={`w-5 h-5 ${StatusColors.Accelerated.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                        <span className={`font-semibold ${StatusColors.Accelerated.text} text-sm`}>
                          Priority Accelerated Precinct
                        </span>
                      </div>
                      <p className="text-sm text-purple-800 mt-1">
                        Fast-track rezoning: {selectedProperty.constraints.acceleratedTOD.precinctName}
                      </p>
                      {selectedProperty.constraints.acceleratedTOD.expectedRezoning && (
                        <p className={`text-xs ${StatusColors.Accelerated.icon} mt-1`}>
                          Expected: {selectedProperty.constraints.acceleratedTOD.expectedRezoning}
                        </p>
                      )}
                    </div>
                  )}

                  {selectedProperty.constraints?.hiaArea && (
                    <div className={`${StatusColors.HIA.bg} border-2 ${StatusColors.HIA.border} rounded-lg p-4 mt-2`}>
                      <div className="flex items-center gap-2 mb-1">
                        <svg className={`w-5 h-5 ${StatusColors.HIA.icon}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                        </svg>
                        <span className={`font-semibold ${StatusColors.HIA.text} text-sm`}>
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

                  {/* Development Type - Auto-detected from zone */}
                  {/* Building Height Input is now in ADG card (SEPP tab) for better UX */}
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

          {/* Right Panel - Dynamic Regulatory Requirements (3/4 width) */}
          {/* Elevated styling signals "active working area" vs static left context */}
          <div className="lg:col-span-3 lg:border-l-2 lg:border-l-slate-200 lg:pl-6">
            {/* Loading state - show skeleton */}
            {loading && (
              <div className="animate-in fade-in duration-300">
                {/* Skeleton tab bar */}
                <div className="bg-white border rounded-lg shadow-md mb-4 overflow-hidden">
                  <div className="flex">
                    <div className="flex-1 px-6 py-3 bg-purple-100 animate-pulse">
                      <div className="h-5 w-16 bg-purple-200 rounded mx-auto mb-1" />
                      <div className="h-3 w-24 bg-purple-200 rounded mx-auto" />
                    </div>
                    <div className="flex-1 px-6 py-3 bg-amber-50">
                      <div className="h-5 w-12 bg-amber-200 rounded mx-auto mb-1 animate-pulse" />
                      <div className="h-3 w-20 bg-amber-200 rounded mx-auto animate-pulse" />
                    </div>
                    <div className="flex-1 px-6 py-3 bg-green-50">
                      <div className="h-5 w-12 bg-green-200 rounded mx-auto mb-1 animate-pulse" />
                      <div className="h-3 w-24 bg-green-200 rounded mx-auto animate-pulse" />
                    </div>
                  </div>
                </div>
                {/* Skeleton content */}
                <SkeletonSeppContent />
              </div>
            )}

            {/* No property selected */}
            {!loading && !selectedProperty && (
              <div className="bg-white border rounded-lg p-12 shadow-md text-center">
                <h3 className="text-lg font-medium mb-2 text-slate-500">No Property Selected</h3>
                <p className="text-slate-600">Enter a property address to see compliance provisions</p>
              </div>
            )}

            {!loading && selectedProperty && (
              <>
                {/* Regulatory Tabs - SEPP purple, LEP amber, DCP green */}
                <div className="bg-white border rounded-lg shadow-md mb-4 overflow-hidden">
                  <div className="flex" role="tablist" aria-label="Regulatory controls">
                    <button
                      role="tab"
                      id="tab-sepp"
                      aria-selected={viewMode === 'sepp'}
                      aria-controls="panel-sepp"
                      onClick={() => setViewMode('sepp')}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] relative ${
                        viewMode === 'sepp'
                          ? 'bg-purple-600 text-white'
                          : 'bg-purple-50 text-purple-700 hover:bg-purple-100'
                      }`}
                    >
                      <span className="block text-base font-bold">SEPP</span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'sepp' ? 'text-purple-100' : 'text-purple-400'}`}>State Planning Policies</span>
                    </button>
                    <button
                      role="tab"
                      id="tab-lep"
                      aria-selected={viewMode === 'lep'}
                      aria-controls="panel-lep"
                      onClick={() => setViewMode('lep')}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] ${
                        viewMode === 'lep'
                          ? 'bg-blue-600 text-white'
                          : 'bg-blue-50 text-blue-700 hover:bg-blue-100'
                      }`}
                    >
                      <span className="block text-base font-bold">Planning Controls</span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'lep' ? 'text-blue-100' : 'text-blue-400'}`}>Zone & Development Standards</span>
                    </button>
                    <button
                      role="tab"
                      id="tab-dcp"
                      aria-selected={viewMode === 'dcp'}
                      aria-controls="panel-dcp"
                      onClick={() => setViewMode('dcp')}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] ${
                        viewMode === 'dcp'
                          ? 'bg-teal-600 text-white'
                          : 'bg-teal-100 text-teal-700 hover:bg-teal-200'
                      }`}
                    >
                      <span className="block text-base font-bold">DCP</span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'dcp' ? 'text-teal-100' : 'text-teal-600'}`}>Council Controls</span>
                    </button>
                  </div>
                </div>

                {/* SEPP Tab Content */}
                {viewMode === 'sepp' && (
                  <div role="tabpanel" id="panel-sepp" aria-labelledby="tab-sepp">
                    <StateLevelControls
                      propertyData={selectedProperty}
                      developmentType={developmentType}
                      buildingHeight={buildingHeight || undefined}
                      onNavigateToDcp={handleNavigateToDcp}
                    />
                  </div>
                )}

                {/* LEP Tab Content */}
                {viewMode === 'lep' && (
                  <div role="tabpanel" id="panel-lep" aria-labelledby="tab-lep">
                    <ErrorBoundary fallbackTitle="Error loading LEP provisions">
                      <LepControls
                        propertyData={selectedProperty}
                        planningLayers={selectedProperty.planningLayers || []}
                        constraints={selectedProperty.constraints}
                        formerCouncil={selectedProperty.constraints?.formerCouncil || ''}
                        lotArea={selectedProperty.lotDimensions?.area}
                      />
                    </ErrorBoundary>
                  </div>
                )}

                {/* DCP Tab Content — provisions when enabled for this council, register interest otherwise */}
                <div role="tabpanel" id="panel-dcp" aria-labelledby="tab-dcp" className={viewMode !== 'dcp' ? 'hidden' : ''}>
                  {isDcpEnabledForCouncil(selectedProperty.constraints?.formerCouncil) ? (
                    <ProvisionsByTocStructure
                      key={`toc-${selectedProperty.address}`}
                      lga={selectedProperty.constraints?.lga}
                      formerCouncil={selectedProperty.constraints?.formerCouncil || ''}
                      zone={selectedProperty.constraints?.zone}
                      heritage={selectedProperty.heritage?.isHeritage || false}
                      hcaName={selectedProperty.heritage?.heritageType?.toLowerCase().includes('conservation area')
                        ? selectedProperty.heritage?.heritageItemName
                        : undefined}
                      precinctId={selectedProperty.constraints?.precinctId}
                      precinctName={selectedProperty.constraints?.precinctName}
                      address={selectedProperty.address}
                      hcaCode={selectedProperty.heritage?.heritageItemNumber}
                      heritageItem={selectedProperty.heritage?.heritageType?.toLowerCase().includes('item')}
                      heritageItemName={selectedProperty.heritage?.heritageItemName}
                      heritageItemNumber={selectedProperty.heritage?.heritageItemNumber}
                      propertyData={selectedProperty}
                      lepClauseData={lepClauseData}
                      isDaMode={isDaMode}
                      onToggleDaMode={setIsDaMode}
                    />
                  ) : (
                    <DCPInterestForm
                      councilName={selectedProperty.constraints?.lga || 'Your council'}
                      address={selectedProperty.address}
                    />
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </div>

      {/* Zone Information Modal - fullscreen on mobile */}
      {showZoneInfo && selectedProperty?.constraints?.zone && (
        <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-end md:items-center justify-center md:p-4" onClick={() => setShowZoneInfo(false)}>
          <div className="bg-white rounded-t-xl md:rounded-lg shadow-xl w-full md:max-w-2xl max-h-[90vh] md:max-h-[80vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
            <div className="sticky top-0 bg-white border-b px-4 md:px-6 py-3 md:py-4 flex items-center justify-between">
              <h3 className="text-base md:text-lg font-semibold text-gray-900 pr-4">
                {selectedProperty.constraints.zoneDescription || selectedProperty.constraints.zone}
              </h3>
              <button
                onClick={() => setShowZoneInfo(false)}
                className="text-gray-400 hover:text-gray-600 transition-colors p-2 -mr-2 min-w-[44px] min-h-[44px] flex items-center justify-center"
              >
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="px-4 md:px-6 py-4">
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
                  Zone information, permitted uses, and development standards are sourced from NSW Planning Portal (derived from the Local Environmental Plan for this property).
                </p>

                <p className="font-semibold text-gray-900 mt-4">
                  To view the complete zone provisions in the official LEP:
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


      {/* Feedback Widget */}
      <FeedbackWidget
        propertyAddress={selectedProperty?.address}
      />

      {/* Footer Help Links */}
      <footer className="bg-gray-100 border-t mt-12">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-medium text-gray-700 mb-1">Need help using PlotDetect?</p>
              <p className="text-xs text-gray-500">Comprehensive guides with examples and workflows</p>
            </div>
            <div className="flex gap-3">
              <a
                href="/quick-guide"
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm text-gray-700 hover:text-teal-700 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Quick Reference
              </a>
              <a
                href="/user-guide"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 px-4 py-1.5 bg-teal-600 text-white rounded-md text-sm font-medium hover:bg-teal-700 transition-colors"
              >
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                Complete User Guide
              </a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}