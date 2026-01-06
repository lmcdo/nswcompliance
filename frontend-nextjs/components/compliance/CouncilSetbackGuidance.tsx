'use client';

import React, { useState, useEffect } from 'react';
import { ChevronDown, ChevronRight, Info, ExternalLink, FileText } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface CouncilSetbackGuidanceProps {
  formerCouncil: 'Ashfield' | 'Marrickville' | 'Leichhardt';
  zone?: string;
  developmentType?: string;
}

interface SetbackProvision {
  id: number;
  section_header: string | null;
  provision_text: string;
  pdf_page: number;
  pdf_page_image_url: string | null;
  document_id: string;
}

// Approach metadata (not values - values come from database)
const COUNCIL_APPROACH = {
  Ashfield: {
    approach: 'Prescriptive',
    badgeColor: 'bg-blue-100 text-blue-800 border-blue-300',
    description: 'Ashfield DCP uses mostly prescriptive numeric minimums'
  },
  Marrickville: {
    approach: 'Character-Based',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    description: 'Marrickville DCP uses contextual character-based guidance'
  },
  Leichhardt: {
    approach: 'Character-Based',
    badgeColor: 'bg-purple-100 text-purple-800 border-purple-300',
    description: 'Leichhardt DCP uses contextual character-based guidance'
  }
};

export function CouncilSetbackGuidance({ formerCouncil, zone, developmentType }: CouncilSetbackGuidanceProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [provisions, setProvisions] = useState<SetbackProvision[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedProvision, setSelectedProvision] = useState<SetbackProvision | null>(null);
  const approach = COUNCIL_APPROACH[formerCouncil];

  // Fetch setback provisions when expanded
  useEffect(() => {
    if (!isExpanded || provisions.length > 0) return;

    const fetchSetbackProvisions = async () => {
      setLoading(true);
      try {
        const response = await fetch('/api/dcp/provisions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            lga: formerCouncil,
            zone: zone || 'R2',
            developmentType: developmentType || 'dwelling_house',
            categories: ['setback'],
            limit: 5
          })
        });

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data?.provisions) {
            setProvisions(data.data.provisions);
          }
        }
      } catch (err) {
        console.error('[CouncilSetbackGuidance] Failed to fetch provisions:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchSetbackProvisions();
  }, [isExpanded, formerCouncil, zone, developmentType, provisions.length]);

  // Truncate provision text for display
  const truncateText = (text: string, maxLength: number = 200) => {
    if (text.length <= maxLength) return text;
    return text.substring(0, maxLength) + '...';
  };

  return (
    <div className="border border-gray-200 rounded-lg bg-gray-50 mb-4">
      {/* Collapsed header - single line */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full px-3 py-2 flex items-center justify-between hover:bg-gray-100 transition-colors rounded-lg"
      >
        <div className="flex items-center gap-2">
          {isExpanded ? (
            <ChevronDown className="h-4 w-4 text-gray-500" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-500" />
          )}
          <Info className="h-4 w-4 text-gray-500" />
          <span className="text-sm font-medium text-gray-700">
            {formerCouncil} Setback Provisions
          </span>
          <Badge variant="outline" className={`text-xs ${approach.badgeColor}`}>
            {approach.approach}
          </Badge>
        </div>
        <span className="text-xs text-gray-500">
          {isExpanded ? 'Hide' : 'Show'} provisions
        </span>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 pb-3 pt-1 space-y-2">
          <p className="text-xs text-gray-600 italic">
            {approach.description}
          </p>

          {/* Loading state */}
          {loading && (
            <div className="animate-pulse space-y-2 py-2">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            </div>
          )}

          {/* Provisions from database */}
          {!loading && provisions.length > 0 && (
            <div className="space-y-2 py-2 border-t border-gray-200">
              {provisions.map((provision) => (
                <div
                  key={provision.id}
                  className={`text-xs p-2 rounded border cursor-pointer transition-colors ${
                    selectedProvision?.id === provision.id
                      ? 'bg-blue-50 border-blue-300'
                      : 'bg-white border-gray-200 hover:border-gray-300'
                  }`}
                  onClick={() => setSelectedProvision(
                    selectedProvision?.id === provision.id ? null : provision
                  )}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      {provision.section_header && (
                        <div className="font-medium text-gray-700 mb-1">
                          {provision.section_header}
                        </div>
                      )}
                      <div className="text-gray-600">
                        {selectedProvision?.id === provision.id
                          ? provision.provision_text.substring(0, 500) + (provision.provision_text.length > 500 ? '...' : '')
                          : truncateText(provision.provision_text)}
                      </div>
                    </div>
                    {provision.pdf_page_image_url && (
                      <a
                        href={provision.pdf_page_image_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 text-blue-600 hover:text-blue-800 shrink-0"
                        title="View PDF page"
                      >
                        <FileText className="h-3 w-3" />
                        <span>p.{provision.pdf_page}</span>
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* No provisions found */}
          {!loading && provisions.length === 0 && (
            <div className="text-xs text-gray-500 py-2 border-t border-gray-200">
              No setback provisions found. Check the full DCP for requirements.
            </div>
          )}

          {/* Source info */}
          {provisions.length > 0 && (
            <div className="text-xs text-gray-500 pt-1 flex items-center gap-1">
              <span>Source: {provisions[0].document_id.replace(/_/g, ' ')}</span>
              <ExternalLink className="h-3 w-3" />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
