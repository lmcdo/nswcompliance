'use client';

/**
 * Provision Display Component
 * Shows provisions for selected section with filters
 */

import React, { useState, useEffect } from 'react';
import { Loader2, Table2, Hash, Search, ExternalLink } from 'lucide-react';
import Link from 'next/link';
import { FormattedProvisionText } from '@/components/compliance/FormattedProvisionText';

interface Provision {
  id: number;
  documentId: string;
  refNumber: string;
  sectionHeader: string | null;
  provisionText: string;
  provisionType: string | null;
  pdfPage: number | null;
  zone: string | null;
  developmentType: string | null;
}

interface SectionInfo {
  sectionNumber: string;
  sectionTitle: string;
  pageStart: number;
  pageEnd: number | null;
  depth: number;
  parentSection: string | null;
}

interface ProvisionDisplayProps {
  documentId: string;
  sectionNumber: string;
  sectionTitle: string;
}

export function ProvisionDisplay({ documentId, sectionNumber, sectionTitle }: ProvisionDisplayProps) {
  const [provisions, setProvisions] = useState<Provision[]>([]);
  const [sectionInfo, setSectionInfo] = useState<SectionInfo | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [filterTablesOnly, setFilterTablesOnly] = useState(false);
  const [filterNumericOnly, setFilterNumericOnly] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetchProvisions();
  }, [documentId, sectionNumber]);

  const fetchProvisions = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/browse/section', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documentId, sectionNumber }),
      });

      const data = await response.json();

      if (data.success) {
        setProvisions(data.data.provisions);
        setSectionInfo(data.data.sectionInfo);
      } else {
        setError(data.details || 'Failed to load provisions');
      }
    } catch (err) {
      setError('Network error: Failed to fetch provisions');
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const filteredProvisions = provisions.filter(p => {
    if (filterTablesOnly && !p.provisionText.includes('<table')) return false;
    if (filterNumericOnly && !/\d+\.?\d*\s*(m|metre|mm|%)/.test(p.provisionText)) return false;
    if (searchQuery && !p.provisionText.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  if (loading) {
    return (
      <div className="bg-white border rounded-lg shadow-sm p-12 flex flex-col items-center justify-center">
        <Loader2 size={48} className="text-blue-500 animate-spin mb-4" />
        <p className="text-gray-600">Loading provisions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white border rounded-lg shadow-sm p-12">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="font-semibold text-red-800 mb-2">Error Loading Provisions</h3>
          <p className="text-sm text-red-600">{error}</p>
          <button
            onClick={fetchProvisions}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white border rounded-lg shadow-sm">
      {/* Section Header */}
      <div className="border-b p-6 bg-gradient-to-r from-yellow-50 to-white border-l-4 border-yellow-400">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 bg-yellow-100 text-yellow-800 text-xs font-medium rounded-full">
                DCP GUIDELINE
              </span>
              <span className="text-sm text-gray-600">
                {sectionInfo && sectionInfo.pageEnd
                  ? `Pages ${sectionInfo.pageStart}-${sectionInfo.pageEnd}`
                  : sectionInfo
                  ? `Page ${sectionInfo.pageStart}+`
                  : ''}
              </span>
            </div>
            <h2 className="text-xl font-bold text-gray-900">
              {sectionNumber} {sectionTitle}
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {filteredProvisions.length} provision{filteredProvisions.length !== 1 ? 's' : ''}
              {filteredProvisions.length !== provisions.length && (
                <span> (filtered from {provisions.length})</span>
              )}
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2">
            <Link
              href={`/assessment/search?q=${encodeURIComponent(sectionTitle)}`}
              className="flex items-center gap-2 px-3 py-2 text-sm text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
              target="_blank"
            >
              <Search size={14} />
              Search Similar
              <ExternalLink size={12} />
            </Link>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="border-b p-4 bg-gray-50">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filterTablesOnly}
              onChange={(e) => setFilterTablesOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <Table2 size={16} className="text-gray-600" />
            <span className="text-sm text-gray-700">Tables only</span>
          </label>

          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={filterNumericOnly}
              onChange={(e) => setFilterNumericOnly(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <Hash size={16} className="text-gray-600" />
            <span className="text-sm text-gray-700">Numeric values only</span>
          </label>

          <div className="flex-1 ml-auto max-w-xs">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Search within section..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Provisions List */}
      <div className="divide-y max-h-[calc(100vh-400px)] overflow-y-auto">
        {filteredProvisions.length === 0 ? (
          <div className="p-12 text-center">
            <Search size={48} className="mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-medium text-gray-500 mb-2">
              No provisions found
            </h3>
            <p className="text-sm text-gray-600">
              Try adjusting your filters or search query
            </p>
          </div>
        ) : (
          filteredProvisions.map((provision, index) => (
            <div
              key={provision.id}
              className="p-5 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-start gap-4">
                {/* Provision Number */}
                <div className="flex-shrink-0 w-12 h-12 bg-yellow-100 rounded-lg flex items-center justify-center">
                  <span className="text-sm font-bold text-yellow-700">
                    {index + 1}
                  </span>
                </div>

                {/* Provision Content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-4 mb-2">
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <span className="font-mono bg-gray-100 px-2 py-1 rounded">
                        {provision.refNumber}
                      </span>
                      {provision.pdfPage && (
                        <span>Page {provision.pdfPage}</span>
                      )}
                    </div>

                    {/* Apply to Property Link */}
                    <Link
                      href={`/assessment?provisionId=${provision.id}`}
                      className="flex items-center gap-1 px-3 py-1 text-xs text-blue-600 hover:bg-blue-50 rounded-lg transition-colors whitespace-nowrap"
                    >
                      Apply to Property
                      <ExternalLink size={12} />
                    </Link>
                  </div>

                  {/* Provision Text */}
                  <div className="prose prose-sm max-w-none">
                    {provision.provisionText.includes('<table') ? (
                      <div
                        className="border rounded-lg p-3 bg-gray-50 overflow-x-auto"
                        dangerouslySetInnerHTML={{ __html: provision.provisionText }}
                      />
                    ) : (
                      <FormattedProvisionText text={provision.provisionText} />
                    )}
                  </div>

                  {/* Metadata */}
                  {(provision.zone || provision.developmentType) && (
                    <div className="flex items-center gap-3 mt-3 text-xs">
                      {provision.zone && (
                        <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded">
                          Zone: {provision.zone}
                        </span>
                      )}
                      {provision.developmentType && (
                        <span className="px-2 py-1 bg-green-50 text-green-700 rounded">
                          Type: {provision.developmentType}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
