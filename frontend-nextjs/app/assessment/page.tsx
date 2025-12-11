'use client';

/**
 * PRIMARY ASSESSMENT PAGE - /assessment
 *
 * Two-column layout:
 * - Left (1/4): Property search + NSW Planning API data (all layers with clickable URLs)
 * - Right (3/4): Tabbed view with:
 *   - Tab 1 "SEPP & LEP": State-level controls (StructuredSeppRequirements, LandUseZoning, ADG, TOD)
 *   - Tab 2 "DCP Provisions": Council-level provisions via ProvisionsByTopic (4-layer model)
 */

import React, { useState } from 'react';
import { MapPin, LayoutList, FolderTree } from 'lucide-react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { ProvisionsByTopic } from '@/components/compliance/ProvisionsByTopic';
import { ProvisionsByTocStructure } from '@/components/compliance/ProvisionsByTocStructure';
import { StateLevelControls } from '@/components/compliance/StateLevelControls';
import { PropertyDetailsComprehensive } from '@/components/property-details-comprehensive';
import { RegulatoryCurrencyBanner } from '@/components/compliance/RegulatoryCurrencyNotice';
import FeedbackWidget from '@/components/feedback/FeedbackWidget';
import { StatusColors } from '@/lib/design-tokens';
import { usePropertyAssessment, useAssessmentUI } from '@/hooks';

export default function AssessmentPage() {
  // Property data and fetching
  const {
    selectedAddress,
    selectedProperty,
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
  } = useAssessmentUI();

  // DCP view mode: 'topic' (existing) or 'toc' (new DCP structure view)
  const [dcpViewMode, setDcpViewMode] = useState<'topic' | 'toc'>('toc');

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Regulatory Currency Warning Banner */}
      <RegulatoryCurrencyBanner />

      {/* GLYPH PICKER - Choose one then tell me the number */}
      <div className="bg-gray-100 p-4 border-b">
        <p className="text-xs font-bold mb-3 text-gray-600">Pick an elegant curved glyph:</p>
        <div className="flex gap-3 flex-wrap">
          {/* 1. Swoosh */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q40 28 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">1. Swoosh</span>
          </div>

          {/* 2. Crescent */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L24 0 Q48 28 24 56 L0 56 Q20 28 0 0 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">2. Crescent</span>
          </div>

          {/* 3. Ribbon */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 C20 0 20 28 40 28 C20 28 20 56 0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">3. Ribbon</span>
          </div>

          {/* 4. Flourish */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L16 0 Q32 14 24 28 Q16 42 32 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">4. Flourish</span>
          </div>

          {/* 5. Sail */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 Q40 0 32 28 Q24 56 0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">5. Sail</span>
          </div>

          {/* 6. Teardrop */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L28 0 Q36 28 28 56 L0 56 Q8 28 0 0 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">6. Teardrop</span>
          </div>

          {/* 7. Leaf */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L8 0 Q40 28 8 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">7. Leaf</span>
          </div>

          {/* 8. Wave */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L16 0 C32 0 32 18 48 28 C32 38 32 56 16 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">8. Wave</span>
          </div>

          {/* 9. Spiral */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L12 0 Q36 8 32 28 Q28 48 8 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">9. Spiral</span>
          </div>

          {/* 10. Flame */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L12 0 Q24 14 16 28 Q8 42 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">10. Flame</span>
          </div>

          {/* 11. Fin */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L6 0 Q40 20 40 28 Q40 36 6 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">11. Fin</span>
          </div>

          {/* 12. Nouveau */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q8 14 24 28 Q40 42 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">12. Nouveau</span>
          </div>

          {/* 13. Brush */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L4 0 Q20 8 28 28 Q20 48 4 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">13. Brush</span>
          </div>

          {/* 14. Petal */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L8 0 Q32 0 32 28 Q32 56 8 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">14. Petal</span>
          </div>

          {/* 15. Hourglass */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L32 0 Q12 14 12 28 Q12 42 32 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">15. Hourglass</span>
          </div>

          {/* 16. Aurora */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-14" viewBox="0 0 56 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q40 10 30 20 Q20 30 40 40 Q30 50 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">16. Aurora</span>
          </div>

          {/* 17. Feather */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L4 0 Q16 10 20 28 Q16 46 4 56 L0 56 Q8 28 0 0 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">17. Feather</span>
          </div>

          {/* 18. Cloud */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q32 8 28 18 Q36 24 32 34 Q40 42 28 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">18. Cloud</span>
          </div>

          {/* 19. Ink */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L16 0 Q28 8 24 20 Q32 28 24 36 Q28 48 16 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">19. Ink</span>
          </div>

          {/* 20. Bow */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q4 14 4 28 Q4 42 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">20. Bow</span>
          </div>

          {/* 21. Paisley */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L16 0 Q40 4 36 28 Q32 52 8 56 L0 56 Q16 28 0 0 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">21. Paisley</span>
          </div>

          {/* 22. Fern */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L8 0 Q24 0 28 14 Q32 28 28 42 Q24 56 8 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">22. Fern</span>
          </div>

          {/* 23. Shell */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L12 0 Q48 12 40 28 Q32 44 12 56 L0 56 Q24 28 0 0 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">23. Shell</span>
          </div>

          {/* 24. Crest */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L24 0 Q36 14 28 28 Q20 42 28 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">24. Crest</span>
          </div>

          {/* 25. Billow */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q44 14 36 28 Q28 42 44 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">25. Billow</span>
          </div>

          {/* 26. Ripple */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L16 0 Q24 9 20 18 Q28 28 20 38 Q24 47 16 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">26. Ripple</span>
          </div>

          {/* 27. Torch */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L8 0 Q32 8 24 28 Q16 48 8 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">27. Torch</span>
          </div>

          {/* 28. Plume */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-12" viewBox="0 0 48 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L12 0 Q36 4 32 18 Q28 32 36 46 Q24 56 12 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">28. Plume</span>
          </div>

          {/* 29. Scallop */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L20 0 Q32 14 24 28 Q32 42 20 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">29. Scallop</span>
          </div>

          {/* 30. Tulip */}
          <div className="relative h-14 w-40 bg-teal-50 rounded border overflow-hidden">
            <svg className="absolute left-0 top-0 h-full w-10" viewBox="0 0 40 56" fill="none" preserveAspectRatio="none">
              <path d="M0 0 L12 0 Q28 14 20 28 Q12 42 28 56 L0 56 Z" fill="#0d9488" />
            </svg>
            <span className="absolute bottom-0.5 right-1 text-[10px] text-gray-400">30. Tulip</span>
          </div>
        </div>
      </div>

      {/* Header */}
      <header className="relative border-b bg-teal-50 shadow-sm overflow-hidden">
        {/* Current: Chevron - will be replaced with your choice */}
        <svg
          className="absolute left-0 top-0 h-full w-8 text-teal-600"
          viewBox="0 0 32 64"
          fill="none"
          preserveAspectRatio="none"
        >
          <path
            d="M0 0 L24 0 L32 32 L24 64 L0 64 Z"
            fill="currentColor"
            className="opacity-90"
          />
          <path
            d="M0 0 L16 0 L24 32 L16 64 L0 64 Z"
            fill="currentColor"
            className="opacity-100"
          />
        </svg>
        <div className="max-w-7xl mx-auto flex items-center gap-4 px-4 py-3 md:py-4 pl-6">
          {/* PlotDetect logo + name */}
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
            <span className="text-base font-semibold text-teal-800">PlotDetect</span>
          </div>
          <div className="h-8 w-px bg-teal-200" />
          {/* Page title */}
          <div className="flex-1">
            <h1 className="text-lg md:text-xl font-semibold tracking-tight text-teal-800">
              NSW Planning Assessment
            </h1>
            <p className="text-teal-600 text-xs hidden sm:block">
              Professional compliance assessment using real-time planning data
            </p>
          </div>
          <div className="hidden sm:flex items-center">
            <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium border border-emerald-200 bg-emerald-50 text-emerald-700">
              <MapPin className="h-3.5 w-3.5" />
              Inner West Council
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

      {/* Main Content - 2 Column Layout (stacked on mobile) */}
      <div className="max-w-7xl mx-auto px-3 sm:px-4 py-4 md:py-6">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 md:gap-6">
          {/* Left Panel - Property Card (1/4 width on desktop, full width on mobile) */}
          <div className="lg:col-span-1 space-y-4 md:space-y-6">
            <div className="bg-teal-50 border border-teal-200 rounded-lg p-4 md:p-6">
              <h3 className="text-base md:text-lg font-semibold mb-3 md:mb-4 text-teal-900">Property Summary</h3>

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
                      <label className="text-sm text-gray-500">
                        Zone
                      </label>
                      <span className="inline-block mt-1 px-2.5 py-1 rounded text-xs font-medium bg-sky-100 text-sky-700">
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

                  {/* Development Type - Auto-detected from zone (hidden from UI) */}

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
                {/* Regulatory Tabs - teal theme */}
                <div className="bg-white border rounded-lg shadow-sm mb-4 overflow-hidden">
                  <div className="flex" role="tablist" aria-label="Regulatory controls">
                    <button
                      role="tab"
                      id="tab-sepp-lep"
                      aria-selected={viewMode === 'sepp-lep'}
                      aria-controls="panel-sepp-lep"
                      onClick={() => setViewMode('sepp-lep')}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] ${
                        viewMode === 'sepp-lep'
                          ? 'bg-teal-700 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      <span className="block text-base font-bold">SEPP Provisions</span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'sepp-lep' ? 'text-teal-100' : 'text-gray-400'}`}>State Controls</span>
                    </button>
                    <button
                      role="tab"
                      id="tab-dcp"
                      aria-selected={viewMode === 'dcp'}
                      aria-controls="panel-dcp"
                      onClick={() => setViewMode('dcp')}
                      className={`flex-1 px-3 md:px-6 py-3 text-sm font-medium transition-colors min-h-[48px] ${
                        viewMode === 'dcp'
                          ? 'bg-teal-700 text-white'
                          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                      }`}
                    >
                      <span className="block text-base font-bold">DCP Provisions</span>
                      <span className={`text-xs hidden sm:block ${viewMode === 'dcp' ? 'text-teal-100' : 'text-gray-400'}`}>Council Controls</span>
                    </button>
                  </div>
                </div>

                {/* SEPP & LEP Tab Content */}
                {viewMode === 'sepp-lep' && (
                  <div role="tabpanel" id="panel-sepp-lep" aria-labelledby="tab-sepp-lep">
                    <StateLevelControls
                      propertyData={selectedProperty}
                      developmentType={developmentType}
                      buildingHeight={buildingHeight || undefined}
                    />
                  </div>
                )}

                {/* DCP Tab Content */}
                {viewMode === 'dcp' && (
                  <div role="tabpanel" id="panel-dcp" aria-labelledby="tab-dcp">
                    {/* DCP View Mode Toggle */}
                    <div className="flex items-center justify-end gap-2 mb-4">
                      <span className="text-sm text-gray-500 mr-2">View:</span>
                      <button
                        onClick={() => setDcpViewMode('toc')}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                          dcpViewMode === 'toc'
                            ? 'bg-teal-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                        title="View by DCP structure (Parts & Sections)"
                      >
                        <FolderTree className="h-4 w-4" />
                        <span className="hidden sm:inline">Structure</span>
                      </button>
                      <button
                        onClick={() => setDcpViewMode('topic')}
                        className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                          dcpViewMode === 'topic'
                            ? 'bg-teal-600 text-white'
                            : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                        }`}
                        title="View by topic (Parking, Setbacks, etc.)"
                      >
                        <LayoutList className="h-4 w-4" />
                        <span className="hidden sm:inline">Topic</span>
                      </button>
                    </div>

                    {/* TOC Structure View (new) */}
                    {dcpViewMode === 'toc' && (
                      <ProvisionsByTocStructure
                        key={`toc-${selectedProperty.address}`}
                        formerCouncil={selectedProperty.constraints?.formerCouncil || ''}
                        zone={selectedProperty.constraints?.zone}
                        heritage={selectedProperty.heritage?.isHeritage || false}
                        hcaName={selectedProperty.heritage?.heritageType?.toLowerCase().includes('conservation area')
                          ? selectedProperty.heritage?.heritageItemName
                          : undefined}
                        precinctId={selectedProperty.constraints?.precinctId}
                      />
                    )}

                    {/* Topic View (existing) */}
                    {dcpViewMode === 'topic' && (
                      <ProvisionsByTopic
                        key={`topic-${selectedProperty.address}`}
                        zone={selectedProperty.constraints?.zone}
                        heritage={selectedProperty.heritage?.isHeritage || false}
                        flood={selectedProperty.planningLayers?.some((l: any) =>
                          l.layerName?.toLowerCase().includes('flood') &&
                          l.results?.length > 0
                        ) || false}
                        precinctId={selectedProperty.constraints?.precinctId}
                        devType={developmentType}
                        council={selectedProperty.constraints?.formerCouncil?.toLowerCase()}
                        hcaName={selectedProperty.heritage?.heritageType?.toLowerCase().includes('conservation area')
                          ? selectedProperty.heritage?.heritageItemName
                          : undefined}
                        heritageItemNumber={selectedProperty.heritage?.heritageItemNumber}
                      />
                    )}
                  </div>
                )}
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

      {/* Feedback Widget */}
      <FeedbackWidget
        propertyAddress={selectedProperty?.address}
      />
    </div>
  );
}