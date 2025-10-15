'use client';

/**
 * PROVISION SEARCH PAGE - /assessment/search
 *
 * Dedicated page for searching provisions across SEPP/LEP/DCP documents
 * Features Tier 1 ranking when zone context is available
 */

import React, { useState } from 'react';
import { PropertySearch } from '@/components/property/PropertySearch';
import ProvisionSearch from '@/components/assessment/core/ProvisionSearch';
import { ComplianceProvision } from '@/lib/assessment/types';

export default function ProvisionSearchPage() {
  const [selectedAddress, setSelectedAddress] = useState('');
  const [selectedProperty, setSelectedProperty] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProvision, setSelectedProvision] = useState<ComplianceProvision | null>(null);

  const handleAddressSelect = async (address: string) => {
    setSelectedAddress(address);
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`);
      if (response.ok) {
        const apiResponse = await response.json();
        if (apiResponse.success) {
          setSelectedProperty(apiResponse.data);
        } else {
          throw new Error(apiResponse.error || 'Failed to load property');
        }
      } else {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load property');
      setSelectedProperty(null);
    } finally {
      setLoading(false);
    }
  };

  const handleProvisionSelect = (provision: ComplianceProvision) => {
    setSelectedProvision(provision);
    console.log('Selected provision:', provision);
  };

  // Extract zone from property data for Tier 1 ranking
  const userZone = selectedProperty?.constraints?.zone || selectedProperty?.zoning_zone || selectedProperty?.zone;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <h1 className="text-2xl font-bold text-gray-900">
            Provision Search
          </h1>
          <p className="text-gray-600 mt-1">
            Search across all SEPP, LEP, and DCP provisions with intelligent ranking
          </p>
        </div>
      </div>

      {/* Optional Property Context */}
      <div className="bg-white border-b px-4 py-3">
        <div className="max-w-7xl mx-auto">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700 whitespace-nowrap">
              Property Context (Optional):
            </label>
            <PropertySearch
              onAddressSelect={handleAddressSelect}
              selectedAddress={selectedAddress}
              loading={loading}
            />
          </div>
          {error && (
            <div className="text-red-600 text-sm mt-2">{error}</div>
          )}
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Panel - Search */}
          <div className="lg:col-span-2">
            <ProvisionSearch
              userZone={userZone}
              enableRanking={true}
              showRankingDetails={false}
              onProvisionSelect={handleProvisionSelect}
            />
          </div>

          {/* Right Panel - Selected Provision Details */}
          <div className="lg:col-span-1">
            {selectedProvision ? (
              <div className="bg-white border rounded-lg shadow-sm p-6 sticky top-6">
                <h3 className="text-lg font-semibold mb-4">Provision Details</h3>
                <div className="space-y-3">
                  <div>
                    <label className="text-xs text-gray-600">Authority Level</label>
                    <div className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                      selectedProvision.authority_level === 'SEPP' ? 'bg-orange-100 text-orange-800' :
                      selectedProvision.authority_level === 'LEP' ? 'bg-blue-100 text-blue-800' :
                      'bg-green-100 text-green-800'
                    }`}>
                      {selectedProvision.authority_level}
                    </div>
                  </div>

                  <div>
                    <label className="text-xs text-gray-600">Clause</label>
                    <p className="font-medium text-sm">{selectedProvision.ref_number || selectedProvision.clause}</p>
                  </div>

                  {selectedProvision.page_number > 0 && (
                    <div>
                      <label className="text-xs text-gray-600">Page Number</label>
                      <p className="font-medium text-sm">{selectedProvision.page_number}</p>
                    </div>
                  )}

                  {selectedProvision.zone && (
                    <div>
                      <label className="text-xs text-gray-600">Zone</label>
                      <p className="font-medium text-sm">{selectedProvision.zone}</p>
                    </div>
                  )}

                  {selectedProvision.section_header && (
                    <div>
                      <label className="text-xs text-gray-600">Section</label>
                      <p className="font-medium text-sm">{selectedProvision.section_header}</p>
                    </div>
                  )}

                  <div>
                    <label className="text-xs text-gray-600">Content</label>
                    <div
                      className="text-sm text-gray-700 leading-relaxed prose prose-sm max-w-none"
                      dangerouslySetInnerHTML={{
                        __html: (selectedProvision.provision_text || selectedProvision.content || '')
                          .replace(/<table/g, '<table class="min-w-full border-collapse border border-gray-300 my-2"')
                          .replace(/<td/g, '<td class="border border-gray-300 px-2 py-1 text-xs"')
                          .replace(/<th/g, '<th class="border border-gray-300 px-2 py-1 text-xs font-semibold bg-gray-100"')
                      }}
                    />
                  </div>

                  {selectedProvision.ranking && (
                    <div className="border-t pt-3 mt-3">
                      <label className="text-xs text-gray-600">Ranking Score</label>
                      <p className="text-lg font-bold text-blue-600">
                        {selectedProvision.ranking.final_rank.toFixed(2)}
                      </p>
                      <div className="text-xs text-gray-500 space-y-1 mt-2">
                        <div>Text: {selectedProvision.ranking.text_rank.toFixed(2)}</div>
                        <div>Zone: {selectedProvision.ranking.zone_boost.toFixed(2)}x</div>
                        <div>Quant: {selectedProvision.ranking.quant_boost.toFixed(2)}x</div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white border rounded-lg shadow-sm p-12 text-center sticky top-6">
                <h3 className="text-lg font-medium mb-2 text-gray-500">No Provision Selected</h3>
                <p className="text-sm text-gray-600">Click on a search result to view details</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
