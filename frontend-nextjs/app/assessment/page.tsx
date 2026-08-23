'use client';

export const dynamic = 'force-dynamic';

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

import React, { useMemo, useState, useRef, useEffect } from 'react';
import { MapPin, HelpCircle } from 'lucide-react';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/assessment/core/ui/tooltip';
import { PropertySearch } from '@/components/property/PropertySearch';
import { DCPInterestForm } from '@/components/compliance/DCPInterestForm';
import { VerifyRegistrationPrompt } from '@/components/compliance/VerifyRegistrationPrompt';
import { ProvisionsByTocStructure } from '@/components/compliance/ProvisionsByTocStructure';
import { StateLevelControls } from '@/components/compliance/StateLevelControls';
import { LepControls } from '@/components/compliance/LepControls';
import { ErrorBoundary } from '@/components/ErrorBoundary';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';
import { RegulatoryCurrencyBanner } from '@/components/compliance/RegulatoryCurrencyNotice';
import { InstrumentCurrency } from '@/components/compliance/InstrumentCurrency';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';
import { StatusColors } from '@/lib/design-tokens';
import { usePropertyAssessment, useAssessmentUI, useSpatialContext } from '@/hooks';
import { SpatialContextCard } from '@/components/property/SpatialContextCard';
import AerialTile from '@/components/reports/AerialTile';
import { classifyHeritageType } from '@/lib/see/heritageType';
import { SkeletonSeppContent, SkeletonDcpContent, SkeletonPropertyDetails } from '@/components/compliance/AssessmentSkeleton';

const DCP_ENABLED = process.env.NEXT_PUBLIC_DCP_ENABLED === 'true';
// When set, only show DCP for listed councils (comma-separated formerCouncil slugs).
// When unset, all councils show DCP (if DCP_ENABLED is true).
// Example: NEXT_PUBLIC_ENABLED_LGAS=marrickville,leichhardt,ashfield,waverley,ku_ring_gai
const ENABLED_LGAS = process.env.NEXT_PUBLIC_ENABLED_LGAS
  ? process.env.NEXT_PUBLIC_ENABLED_LGAS.split(',').map(s => s.trim().toLowerCase())
  : null;

// LGA display names that differ from their slug form
const LGA_NAME_TO_SLUG: Record<string, string> = {
  'city of parramatta': 'parramatta',
  'sydney': 'city_of_sydney',
  'city of sydney': 'city_of_sydney',
  'the hills shire': 'the_hills',
  'city of canada bay': 'canada_bay',
  'city of ryde': 'ryde',
  'strathfield municipal': 'strathfield',
};

function normalizeLgaSlug(name: string): string {
  const lower = name.toLowerCase().trim();
  if (LGA_NAME_TO_SLUG[lower]) return LGA_NAME_TO_SLUG[lower];
  return lower.replace(/[-\s]+/g, '_').replace(/[^a-z0-9_]/g, '');
}

function isDcpEnabledForCouncil(formerCouncil: string | undefined, lga?: string | undefined): boolean {
  if (!DCP_ENABLED) return false;
  if (!ENABLED_LGAS) return true; // no restriction — show all
  const council = (formerCouncil || '').toLowerCase();
  if (ENABLED_LGAS.includes(council)) return true;
  // Also check LGA slug — handles ENABLED_LGAS=['inner_west'] enabling all former councils
  // of that LGA (leichhardt, marrickville, ashfield) without listing each explicitly.
  if (lga) {
    const lgaSlug = normalizeLgaSlug(lga);
    return ENABLED_LGAS.some(key => lgaSlug === key || lgaSlug.startsWith(key + '_') || lgaSlug.startsWith(key));
  }
  return false;
}

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

  const heritageClass = useMemo(
    () => classifyHeritageType(selectedProperty?.heritage?.heritageType),
    [selectedProperty?.heritage?.heritageType]
  );

  // Lot boundary + centroid (WGS84) for the aerial tile — same source the brief
  // and /property pages use. The centroid is kept as well because
  // selectedCoordinates is ONLY set on the Google-autocomplete path; the
  // "Analyze Property" button calls onAddressSelect without coordinates
  // (PropertySearch.tsx), which previously left the tile unable to mount.
  const [profileMap, setProfileMap] = useState<{
    lat: number;
    lng: number;
    lotPolygon: { type: 'Polygon'; coordinates: number[][][] } | null;
  } | null>(null);
  useEffect(() => {
    setProfileMap(null);
    if (!selectedAddress) return;
    let cancelled = false;
    fetch(`/api/property/profile?address=${encodeURIComponent(selectedAddress)}`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (cancelled || typeof d?.lat !== 'number' || typeof d?.lng !== 'number') return;
        setProfileMap({ lat: d.lat, lng: d.lng, lotPolygon: d.lotPolygon ?? null });
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [selectedAddress]);
  const mapLat = selectedCoordinates?.lat ?? profileMap?.lat ?? null;
  const mapLng = selectedCoordinates?.lng ?? profileMap?.lng ?? null;

  // Spatial context (amenity + street) — user-initiated fetch. Uses the same
  // coordinate fallback as the aerial tile so the button path gets the card too.
  const spatialContext = useSpatialContext(
    mapLat,
    mapLng,
    selectedProperty?.constraints?.precinctId ?? null,
  );

  // Lazy mount: ProvisionsByTocStructure only mounts after the user first activates the DCP tab.
  // Prevents the SWR fetch and DA session initialisation from firing on every property search
  // when the planner is working on SEPP/LEP tabs.
  const [dcpEverActivated, setDcpEverActivated] = useState(false);
  // Ref to read viewMode inside the address-change effect without adding it as a dependency.
  const viewModeRef = useRef(viewMode);
  viewModeRef.current = viewMode;
  // Reset when address changes, but only if not currently on the DCP tab (if they're on DCP,
  // we want the new address's provisions to load immediately without requiring another tab click).
  useEffect(() => {
    if (viewModeRef.current !== 'dcp') setDcpEverActivated(false);
    spatialContext.reset();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAddress]);

  // Navigation handler for Pattern Book -> DCP cross-references
  const handleNavigateToDcp = (topic: string, hcaSlug?: string) => {
    setDcpEverActivated(true);
    setViewMode('dcp');
    console.log('[Pattern Book Navigation] Switching to DCP tab:', { topic, hcaSlug });
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Regulatory Currency Warning Banner */}
      <RegulatoryCurrencyBanner />

      {/* Header */}
      <header className="bg-slate-950 border-b border-slate-800/50 flex items-center gap-4 px-4 py-3 md:py-4">
        {/* Logo + name */}
        <a
          href="/"
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
        >
          <span className="text-base font-bold tracking-tight text-white">
            Plot<span className="text-teal-400">Detect</span>
          </span>
        </a>
        {/* Page title */}
        <div className="flex-1">
          <h1 className="text-lg md:text-xl font-semibold tracking-tight text-white">
            Site Controls
          </h1>
          <p className="text-slate-400 text-xs hidden sm:block">
            Every control cited to its clause — live NSW planning data
          </p>
        </div>
        {/* Quick Guide */}
        <div className="hidden sm:flex items-center">
          <a
            href="/quick-guide"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-teal-500/50 text-teal-400 hover:bg-teal-500/10 transition-colors"
          >
            <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            Quick Guide
          </a>
        </div>
        <div className="hidden sm:flex items-center">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-slate-700 bg-slate-800 text-slate-300">
            <MapPin className="h-3.5 w-3.5" />
            {selectedProperty?.constraints?.lga || 'NSW Planning'}
          </span>
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

                  {(selectedProperty as any).strataInfo?.isStrata && (
                    <div className="mt-1 bg-orange-50 border border-orange-200 rounded-lg px-3 py-2 flex items-start gap-2">
                      <svg className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-2 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                      <div>
                        <p className="text-xs font-semibold text-orange-800">Strata unit detected</p>
                        <p className="text-xs text-orange-700 mt-0.5">
                          Controls below apply to the building/scheme. Unit alterations are governed by strata by-laws and owners corporation consent.
                        </p>
                      </div>
                    </div>
                  )}

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

            {/* Aerial — NSW SIX Maps imagery with the lot boundary (shared AerialTile) */}
            {selectedProperty && mapLat != null && mapLng != null && (
              <div className="bg-white rounded-lg border overflow-hidden">
                <AerialTile
                  lat={mapLat}
                  lng={mapLng}
                  lotPolygon={profileMap?.lotPolygon ?? null}
                />
                <p className="px-3 py-1.5 text-xs text-slate-400">
                  NSW SIX Maps aerial imagery &middot; &copy; NSW Government CC BY 4.0
                </p>
              </div>
            )}

            {/* Planning API Data - All Layers */}
            {selectedProperty && (
              <PropertyDetailsComprehensive
                propertyData={selectedProperty}
                lepClauseData={lepClauseData}
              />
            )}

            {/* Spatial context — amenity walkability + street type */}
            {mapLat != null && mapLng != null && (
              <SpatialContextCard
                state={spatialContext.state}
                onFetch={spatialContext.fetch}
                lat={mapLat}
                lng={mapLng}
              />
            )}

            {/* Data currency indicator */}
            {selectedProperty?.constraints?.formerCouncil && (
              <InstrumentCurrency council={selectedProperty.constraints.formerCouncil} />
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
                      <span className="flex items-center justify-center gap-1 text-base font-bold">
                        SEPP
                        <Tooltip>
                          <TooltipTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <HelpCircle className={`w-3.5 h-3.5 ${viewMode === 'sepp' ? 'text-purple-200' : 'text-purple-400'}`} />
                          </TooltipTrigger>
                          <TooltipContent side="bottom" sideOffset={8} className="max-w-[260px]">
                            State Environmental Planning Policies — NSW-wide rules that override local controls. Covers housing codes, exempt development, infrastructure, and environmental protections.
                          </TooltipContent>
                        </Tooltip>
                      </span>
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
                      <span className="flex items-center justify-center gap-1 text-base font-bold">
                        Planning Controls
                        <Tooltip>
                          <TooltipTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <HelpCircle className={`w-3.5 h-3.5 ${viewMode === 'lep' ? 'text-blue-200' : 'text-blue-400'}`} />
                          </TooltipTrigger>
                          <TooltipContent side="bottom" sideOffset={8} className="max-w-[260px]">
                            Local Environmental Plan (LEP) — your council&apos;s zoning, height limits, floor space ratio, heritage listings, and minimum lot sizes. These are the legally enforceable development standards.
                          </TooltipContent>
                        </Tooltip>
                      </span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'lep' ? 'text-blue-100' : 'text-blue-400'}`}>Zone & Development Standards</span>
                    </button>
                    <button
                      role="tab"
                      id="tab-dcp"
                      aria-selected={viewMode === 'dcp'}
                      aria-controls="panel-dcp"
                      onClick={() => { setDcpEverActivated(true); setViewMode('dcp'); }}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] ${
                        viewMode === 'dcp'
                          ? 'bg-teal-600 text-white'
                          : 'bg-teal-100 text-teal-700 hover:bg-teal-200'
                      }`}
                    >
                      <span className="flex items-center justify-center gap-1 text-base font-bold">
                        DCP
                        <Tooltip>
                          <TooltipTrigger asChild onClick={(e) => e.stopPropagation()}>
                            <HelpCircle className={`w-3.5 h-3.5 ${viewMode === 'dcp' ? 'text-teal-200' : 'text-teal-500'}`} />
                          </TooltipTrigger>
                          <TooltipContent side="bottom" sideOffset={8} className="max-w-[260px]">
                            Development Control Plan — detailed council guidelines for setbacks, parking, landscaping, building design, and precinct-specific rules. Advisory but expected in DA submissions.
                          </TooltipContent>
                        </Tooltip>
                      </span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'dcp' ? 'text-teal-100' : 'text-teal-600'}`}>Council Controls</span>
                    </button>
                  </div>
                </div>

                {/* Professional registration prompt */}
                <VerifyRegistrationPrompt
                  councilName={selectedProperty.constraints?.lga}
                  address={selectedProperty.address}
                />

                {/* SEPP Tab Content */}
                {viewMode === 'sepp' && (
                  <div role="tabpanel" id="panel-sepp" aria-labelledby="tab-sepp">
                    <StateLevelControls
                      propertyData={selectedProperty}
                      developmentType={developmentType}
                      buildingHeight={buildingHeight || undefined}
                      onNavigateToDcp={handleNavigateToDcp}
                      strataInfo={(selectedProperty as any).strataInfo}
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
                        constraints={selectedProperty.constraints as any}
                        formerCouncil={selectedProperty.constraints?.formerCouncil || ''}
                        lotArea={selectedProperty.lotDimensions?.area}
                        strataInfo={(selectedProperty as any).strataInfo}
                        developmentType={developmentType}
                        lat={mapLat}
                        lng={mapLng}
                      />
                    </ErrorBoundary>
                  </div>
                )}

                {/* DCP Tab Content — provisions when enabled for this council, register interest otherwise */}
                <div role="tabpanel" id="panel-dcp" aria-labelledby="tab-dcp" className={viewMode !== 'dcp' ? 'hidden' : ''}>
                  {(selectedProperty as any).strataInfo?.isStrata && (
                    <div className="mb-4 bg-orange-50 border border-orange-200 rounded-lg px-4 py-3 flex items-start gap-2 text-sm">
                      <svg className="h-4 w-4 text-orange-500 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      <span className="text-orange-800">
                        <span className="font-semibold">Strata unit — </span>
                        DCP controls below apply to the building and lot as a whole. Setback controls govern new development on the scheme&apos;s parent lot. Works to individual units are governed by the strata by-laws and owners corporation consent, not DCP setbacks directly.
                      </span>
                    </div>
                  )}
                  {isDcpEnabledForCouncil(selectedProperty.constraints?.formerCouncil, selectedProperty.constraints?.lga) ? (
                    <ErrorBoundary fallbackTitle="Error loading DCP provisions">
                      <ProvisionsByTocStructure
                        key={`toc-${selectedProperty.address}`}
                        lga={selectedProperty.constraints?.lga}
                        formerCouncil={selectedProperty.constraints?.formerCouncil || normalizeLgaSlug(selectedProperty.constraints?.lga || '')}
                        zone={selectedProperty.constraints?.zone}
                        heritage={selectedProperty.heritage?.isHeritage || false}
                        hcaName={heritageClass.isConservationArea
                          ? selectedProperty.heritage?.heritageItemName
                          : undefined}
                        precinctId={selectedProperty.constraints?.precinctId}
                        precinctName={selectedProperty.constraints?.precinctName}
                        address={selectedProperty.address}
                        hcaCode={selectedProperty.heritage?.heritageItemNumber}
                        heritageItem={heritageClass.isItem}
                        heritageItemName={selectedProperty.heritage?.heritageItemName}
                        heritageItemNumber={selectedProperty.heritage?.heritageItemNumber}
                        propertyData={selectedProperty}
                        lepClauseData={lepClauseData}
                        isDaMode={isDaMode}
                        onToggleDaMode={setIsDaMode}
                      />
                    </ErrorBoundary>
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
              <p className="text-xs text-gray-500">Guides with worked examples and workflows</p>
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