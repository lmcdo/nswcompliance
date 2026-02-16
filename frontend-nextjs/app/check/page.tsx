'use client';

/**
 * /check - Pre-DA Check Tool for Owner Builders & Homeowners
 *
 * Simplified assessment interface for non-professionals:
 * - Can I build a deck/garage/extension?
 * - CDC vs DA pathway
 * - Simple capacity check (FSR, height, setbacks)
 * - Plain-English explanations
 */

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import { CDCScreener } from '@/components/compliance/CDCScreener';
import { CapacityCalculator } from '@/components/compliance/CapacityCalculator';
import { usePropertyAssessment } from '@/hooks';
import { Home, Ruler, CheckCircle2, HelpCircle } from 'lucide-react';

export default function CheckPage() {
  const {
    selectedAddress,
    selectedProperty,
    selectedCoordinates,
    loading,
    error,
    developmentType,
    handleAddressSelect,
  } = usePropertyAssessment();

  const [proposedWorks, setProposedWorks] = useState<'deck' | 'garage' | 'extension' | 'other'>('deck');

  return (
    <div className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-blue-50">
      {/* Header */}
      <header className="bg-white border-b shadow-sm">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/logo.png" alt="PlotDetect" className="h-8 w-auto" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Pre-DA Check</h1>
                <p className="text-xs text-gray-600">Can you build it without council approval?</p>
              </div>
            </div>
            <a
              href="/assessment"
              className="text-sm text-teal-600 hover:text-teal-700 font-medium"
            >
              Professional Tool →
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-4xl mx-auto px-4 py-6 space-y-6">
        {/* Hero Section */}
        <div className="bg-white rounded-xl border border-teal-200 p-6 shadow-sm">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-12 h-12 rounded-full bg-teal-100 flex items-center justify-center">
              <Home className="w-6 h-6 text-teal-600" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Check Your Property
              </h2>
              <p className="text-gray-700 leading-relaxed">
                Find out if your deck, garage, or home extension qualifies for{' '}
                <strong>Complying Development</strong> — a faster, cheaper alternative to full Development Applications.
                Enter your address to see what you can build.
              </p>
            </div>
          </div>
        </div>

        {/* Address Search */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Your Property Address
          </label>
          <PropertySearch
            onAddressSelect={handleAddressSelect}
            selectedAddress={selectedAddress}
            loading={loading}
          />
          {error && (
            <p className="mt-2 text-sm text-red-600">{error}</p>
          )}
        </div>

        {/* Property Summary */}
        {selectedProperty && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Property Details</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <p className="text-xs text-gray-500 mb-1">Address</p>
                <p className="text-sm font-medium text-gray-900">{selectedProperty.address}</p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Zone</p>
                <span className="inline-block px-2 py-1 rounded text-xs font-medium bg-sky-100 text-sky-700">
                  {selectedProperty.constraints?.zoneDescription || selectedProperty.constraints?.zone || 'Unknown'}
                </span>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Lot Area</p>
                <p className="text-sm font-medium text-gray-900">
                  {selectedProperty.lotDimensions?.area
                    ? `${Math.round(selectedProperty.lotDimensions.area)}m²`
                    : 'Unknown'}
                </p>
              </div>
              <div>
                <p className="text-xs text-gray-500 mb-1">Heritage</p>
                <p className={`text-sm font-medium ${selectedProperty.heritage?.isHeritage ? 'text-red-600' : 'text-green-600'}`}>
                  {selectedProperty.heritage?.isHeritage ? 'Yes' : 'No'}
                </p>
              </div>
            </div>

            {selectedProperty.heritage?.isHeritage && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <strong>Heritage restrictions apply.</strong> Your property is a heritage item or within a heritage conservation area.
                  CDC eligibility is limited — council approval may be required.
                </p>
              </div>
            )}
          </div>
        )}

        {/* What are you planning to build? */}
        {selectedProperty && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <Ruler className="w-5 h-5 text-teal-600" />
              What are you planning to build?
            </h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { id: 'deck', label: 'Deck', icon: '🏡' },
                { id: 'garage', label: 'Garage', icon: '🚗' },
                { id: 'extension', label: 'Extension', icon: '🏠' },
                { id: 'other', label: 'Other', icon: '🔨' },
              ].map((work) => (
                <button
                  key={work.id}
                  onClick={() => setProposedWorks(work.id as any)}
                  className={`p-4 rounded-lg border-2 transition-all text-center ${
                    proposedWorks === work.id
                      ? 'border-teal-500 bg-teal-50 text-teal-700 font-medium'
                      : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                  }`}
                >
                  <div className="text-2xl mb-1">{work.icon}</div>
                  <div className="text-sm">{work.label}</div>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* CDC Screener */}
        {selectedProperty && (
          <div className="bg-white rounded-xl border border-teal-200 p-6 shadow-sm">
            <div className="flex items-start gap-3 mb-4">
              <CheckCircle2 className="w-6 h-6 text-teal-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">CDC Eligibility Check</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Does your proposed work qualify for a Complying Development Certificate?
                </p>
              </div>
            </div>
            <CDCScreener
              propertyData={selectedProperty}
              coordinates={selectedCoordinates}
            />
          </div>
        )}

        {/* Capacity Calculator */}
        {selectedProperty && (
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <div className="flex items-start gap-3 mb-4">
              <HelpCircle className="w-6 h-6 text-blue-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-lg font-semibold text-gray-900">Development Capacity</h3>
                <p className="text-sm text-gray-600 mt-1">
                  Maximum building size allowed on your property based on planning controls.
                </p>
              </div>
            </div>
            <CapacityCalculator
              propertyAddress={selectedProperty.address}
              coordinates={selectedCoordinates}
              developmentType={proposedWorks}
              lotArea={selectedProperty.lotDimensions?.area || null}
              zone={selectedProperty.constraints?.zone || ''}
              lga={selectedProperty.constraints?.lga || ''}
              formerCouncil={selectedProperty.constraints?.formerCouncil || ''}
            />
          </div>
        )}

        {/* What's Next Section */}
        {selectedProperty && (
          <div className="bg-gradient-to-r from-blue-50 to-teal-50 rounded-xl border border-blue-200 p-6 shadow-sm">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">What's Next?</h3>
            <div className="space-y-3 text-sm text-gray-700">
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-teal-600 text-white flex items-center justify-center text-xs font-bold">1</span>
                <p>
                  <strong>If CDC-eligible:</strong> Engage a Private Certifier to lodge your CDC application. Faster approval (typically 10-20 days).
                </p>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-blue-600 text-white flex items-center justify-center text-xs font-bold">2</span>
                <p>
                  <strong>If CDC not eligible:</strong> Lodge a Development Application (DA) with council. Requires architect drawings, may take 8-12 weeks.
                </p>
              </div>
              <div className="flex gap-3">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-purple-600 text-white flex items-center justify-center text-xs font-bold">3</span>
                <p>
                  <strong>Need help?</strong> Consult a planning consultant or architect to refine your design and navigate the approval process.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!selectedProperty && !loading && (
          <div className="bg-white rounded-xl border border-gray-200 p-12 text-center shadow-sm">
            <Home className="w-12 h-12 text-gray-400 mx-auto mb-3" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No Property Selected</h3>
            <p className="text-gray-600">Enter your property address above to start the check.</p>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-white border-t mt-12 py-6">
        <div className="max-w-4xl mx-auto px-4 text-center text-sm text-gray-600">
          <p>
            This tool provides indicative guidance only. Always verify with a qualified planning consultant or private certifier before proceeding with works.
          </p>
          <p className="mt-2">
            Powered by <strong>PlotDetect</strong> · <a href="https://plotdetect.com.au" className="text-teal-600 hover:underline">Learn more</a>
          </p>
        </div>
      </footer>
    </div>
  );
}
