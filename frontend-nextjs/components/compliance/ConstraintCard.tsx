'use client';

/**
 * Constraint Card Component with Proper Color Coding
 * LEP = Blue, DCP = Green, SEPP = Orange
 * Follows Universal Technical Implementation Specification
 */

import { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, ExternalLink, AlertCircle, FileText, MapPin } from 'lucide-react';
import { ProvisionVersionInline } from './ProvisionVersionBadge';
import type { ProvisionVersionMetadata } from '@/types/provision-search';

// Import types
export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
  version?: ProvisionVersionMetadata; // Version tracking for certifier compliance
}

// Truncated text component with "Show more..." button
function TruncatedText({ text, wordLimit = 100 }: { text: string; wordLimit?: number }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const words = text.split(/\s+/);
  const shouldTruncate = words.length > wordLimit;
  const displayText = shouldTruncate && !isExpanded
    ? words.slice(0, wordLimit).join(' ') + '...'
    : text;

  return (
    <div className="text-sm text-gray-600 leading-relaxed whitespace-pre-wrap">
      {displayText}
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-blue-600 hover:text-blue-800 ml-2 font-medium"
        >
          {isExpanded ? 'Show less' : 'Show more...'}
        </button>
      )}
    </div>
  );
}

export interface ComplianceConstraint {
  type: 'height' | 'fsr' | 'setback' | 'heritage' | 'environmental' | 'special';
  value: string | number;
  unit?: string;
  description?: string;
  source: {
    clause: string;
    document: string;
    authority_level: 'LEP' | 'DCP' | 'SEPP';
  };
  provisions?: ProvisionContent[];
  provision_id?: number;
  seppMetadata?: {
    epiName: string;
    mapType?: string;
    keywords?: string[];
  };
}

interface ConstraintCardProps {
  constraint: ComplianceConstraint;
  onViewDetails?: (constraint: ComplianceConstraint) => void;
  className?: string;
  compact?: boolean;  // Compact mode for single-column list with slide-out panel
}

export function ConstraintCard({
  constraint,
  onViewDetails,
  className = '',
  compact = false
}: ConstraintCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [seppProvisions, setSeppProvisions] = useState<ProvisionContent[]>([]);

  // Compact mode: just trigger callback, no inline expansion
  const handleCompactView = useCallback(() => {
    if (onViewDetails) {
      onViewDetails(constraint);
    }
  }, [constraint, onViewDetails]);

  const handleToggleExpand = useCallback(async () => {
    // If expanding and no provisions loaded yet
    if (!isExpanded && (!constraint.provisions || constraint.provisions.length === 0)) {
      setLoading(true);

      // Check if this is a SEPP provision with metadata
      if (constraint.seppMetadata) {
        try {
          console.log('[ConstraintCard] Fetching SEPP full text:', constraint.seppMetadata);

          const response = await fetch('/api/sepp/full-text', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              epiName: constraint.seppMetadata.epiName,
              keywords: constraint.seppMetadata.keywords,
              mapType: constraint.seppMetadata.mapType
            })
          });

          if (response.ok) {
            const data = await response.json();
            if (data.success && data.data.provisions) {
              // Convert API response to ProvisionContent format
              const provisions: ProvisionContent[] = data.data.provisions.map((p: any) => ({
                id: p.id,
                ref_number: p.clause,
                section_header: p.sectionHeader || '',
                provision_text: p.fullText,
                document_id: p.documentId
              }));

              setSeppProvisions(provisions);
              console.log('[ConstraintCard] Loaded', provisions.length, 'SEPP provisions');
            }
          }
        } catch (error) {
          console.error('[ConstraintCard] Failed to fetch SEPP text:', error);
        }
      }
      // Check if this is a SEPP override with provision_id
      else if (constraint.source.authority_level === 'SEPP' && constraint.provision_id) {
        try {
          console.log('[ConstraintCard] Fetching SEPP override by provision ID:', constraint.provision_id);

          const response = await fetch('/api/sepp/full-text', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              provisionId: constraint.provision_id
            })
          });

          if (response.ok) {
            const data = await response.json();
            if (data.success && data.data.provisions) {
              // Convert API response to ProvisionContent format
              const provisions: ProvisionContent[] = data.data.provisions.map((p: any) => ({
                id: p.id,
                ref_number: p.clause,
                section_header: p.sectionHeader || '',
                provision_text: p.fullText,
                document_id: p.documentId
              }));

              setSeppProvisions(provisions);
              console.log('[ConstraintCard] Loaded', provisions.length, 'SEPP override provisions');
            }
          }
        } catch (error) {
          console.error('[ConstraintCard] Failed to fetch SEPP override text:', error);
        }
      } else {
        // For non-SEPP provisions, use the callback
        onViewDetails?.(constraint);
      }

      setLoading(false);
    }
    setIsExpanded(!isExpanded);
  }, [isExpanded, constraint, onViewDetails]);

  const getConstraintIcon = (type: string) => {
    switch (type) {
      case 'height': return '📏';
      case 'fsr': return '📐';
      case 'setback': return '↔️';
      case 'heritage': return '🏛️';
      case 'environmental': return '🌳';
      case 'special': return '⚡';
      default: return '📋';
    }
  };

  // Get color scheme based on authority level
  const getColorScheme = (level: string) => {
    switch (level) {
      case 'SEPP':
        return {
          border: 'border-orange-500',
          bg: 'bg-orange-50',
          badge: 'bg-orange-100 text-orange-800 border-orange-300',
          icon: 'text-orange-600',
          header: 'bg-orange-100',
          text: 'text-orange-900'
        };
      case 'LEP':
        return {
          border: 'border-blue-500',
          bg: 'bg-blue-50',
          badge: 'bg-blue-100 text-blue-800 border-blue-300',
          icon: 'text-blue-600',
          header: 'bg-blue-100',
          text: 'text-blue-900'
        };
      case 'DCP':
        return {
          border: 'border-green-500',
          bg: 'bg-green-50',
          badge: 'bg-green-100 text-green-800 border-green-300',
          icon: 'text-green-600',
          header: 'bg-green-100',
          text: 'text-green-900'
        };
      default:
        return {
          border: 'border-gray-300',
          bg: 'bg-gray-50',
          badge: 'bg-gray-100 text-gray-800 border-gray-300',
          icon: 'text-gray-600',
          header: 'bg-gray-100',
          text: 'text-gray-900'
        };
    }
  };

  const colors = getColorScheme(constraint.source.authority_level);

  // Get authority icon
  const getAuthorityIcon = (level: string) => {
    switch (level) {
      case 'SEPP': return <AlertCircle className="h-4 w-4" />;
      case 'LEP': return <MapPin className="h-4 w-4" />;
      case 'DCP': return <FileText className="h-4 w-4" />;
      default: return null;
    }
  };

  // Compact mode: single-column card with value and button at bottom
  if (compact) {
    return (
      <Card className={`${colors.border} ${colors.bg} border-l-4 transition-all hover:shadow-md ${className}`}>
        <CardContent className="p-4">
          <div className="space-y-3">
            {/* Header with icon and badge */}
            <div className="flex items-center gap-2">
              <span className={`text-lg ${colors.icon}`}>{getConstraintIcon(constraint.type)}</span>
              <Badge variant="outline" className={`${colors.badge} text-xs`}>
                {constraint.source.authority_level}
              </Badge>
            </div>

            {/* Main value/title */}
            <div className="font-bold text-xl text-gray-900">
              {/* Format the value - show meaningful title based on content */}
              {(() => {
                const val = constraint.value;
                const clause = constraint.source.clause;

                // Helper to clean up titles
                const cleanTitle = (title: string) => {
                  // Fix "7storeys" → "7 Storeys"
                  title = title.replace(/(\d+)(storeys?|floors?|metres?|meters?)/gi, '$1 $2');
                  // Capitalize first letter of each word if all lowercase
                  if (title === title.toLowerCase()) {
                    title = title.split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
                  }
                  return title;
                };

                // If "See provision" placeholder, show the clause title/number
                if (typeof val === 'string' && val.toLowerCase().includes('provision')) {
                  // Use the first provision's section_header if available, otherwise clause
                  const title = constraint.provisions?.[0]?.section_header || clause;
                  return <span className="text-base text-gray-700">{cleanTitle(title)}</span>;
                }

                // If value looks like a clause number (e.g., "9.29.3"), use section_header instead
                if (typeof val === 'string' && /^\d+(\.\d+)+[A-Z]?$/.test(val)) {
                  const title = constraint.provisions?.[0]?.section_header || clause;
                  return <span className="text-base text-gray-700">{cleanTitle(title)}</span>;
                }

                // If value is a descriptive title but no units, it's a reference to controls
                if (typeof val === 'string' && !constraint.unit && val.length > 10) {
                  return <span className="text-base text-gray-700">{cleanTitle(val)}</span>;
                }

                // Otherwise show the value with units (e.g., "9.5 m", "0.6:1")
                // Also clean the value in case it's like "7storeys"
                const displayVal = typeof val === 'string' ? cleanTitle(val) : val;
                return (
                  <>
                    {displayVal}
                    {constraint.unit && <span className="text-base ml-1 text-gray-600">{constraint.unit}</span>}
                  </>
                );
              })()}
            </div>

            {/* Description - helpful context about what this constraint means */}
            {constraint.description && (
              <div className="text-sm text-gray-600 leading-relaxed">
                {constraint.description}
              </div>
            )}

            {/* Metadata */}
            <div>
              <div className="text-sm text-gray-600">
                {constraint.type.charAt(0).toUpperCase() + constraint.type.slice(1)} • {constraint.source.clause}
              </div>
              <div className="text-xs text-gray-500 mt-0.5 flex items-center gap-2">
                <span>{constraint.source.document}</span>
                {/* Version badge if provision has version metadata */}
                {constraint.provisions?.[0]?.version && (
                  <ProvisionVersionInline version={constraint.provisions[0].version} />
                )}
              </div>
            </div>

            {/* Full Text button at bottom - full width */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleCompactView}
              className={`w-full gap-1 ${colors.text}`}
            >
              <FileText className="h-4 w-4" />
              Full Text
            </Button>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Full mode: original expandable card (fallback)
  return (
    <Card className={`${colors.border} ${colors.bg} border-2 transition-all hover:shadow-lg ${className}`}>
      <CardHeader className={`${colors.header} pb-3`}>
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className={`text-2xl ${colors.icon}`}>{getConstraintIcon(constraint.type)}</span>
            <div>
              <div className={`font-bold text-lg ${colors.text}`}>
                {constraint.type.charAt(0).toUpperCase() + constraint.type.slice(1)}
              </div>
              <div className="text-sm text-gray-600 mt-0.5">
                {constraint.source.clause}
              </div>
            </div>
          </div>
          <Badge variant="outline" className={colors.badge}>
            <span className="flex items-center gap-1">
              {getAuthorityIcon(constraint.source.authority_level)}
              {constraint.source.authority_level}
            </span>
          </Badge>
        </CardTitle>
      </CardHeader>

      <CardContent className="pt-4">
        {/* Main Value Display */}
        <div className="mb-4">
          <div className="text-3xl font-bold text-gray-900">
            {constraint.value}
            {constraint.unit && <span className="text-xl ml-1 text-gray-600">{constraint.unit}</span>}
          </div>
          <div className="text-sm text-gray-600 mt-1 flex items-center gap-2">
            <span>{constraint.source.document}</span>
            {/* Version badge if provision has version metadata */}
            {constraint.provisions?.[0]?.version && (
              <ProvisionVersionInline version={constraint.provisions[0].version} />
            )}
          </div>
        </div>

        {/* View Details Button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleToggleExpand}
          disabled={loading}
          className={`w-full ${colors.text} hover:${colors.bg}`}
        >
          {loading ? (
            'Loading provisions...'
          ) : (
            <>
              {isExpanded ? 'Hide' : 'View'} Full Provisions
              {isExpanded ? <ChevronUp className="ml-2 h-4 w-4" /> : <ChevronDown className="ml-2 h-4 w-4" />}
            </>
          )}
        </Button>

        {/* Expanded Provisions */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t border-gray-200">
            {/* Show SEPP provisions if loaded */}
            {seppProvisions.length > 0 && (
              <>
                <h4 className="font-semibold text-sm mb-2">SEPP Legal Text:</h4>
                <div className="space-y-3">
                  {seppProvisions.map((provision) => (
                    <div key={provision.id} className="bg-white p-3 rounded-lg border border-gray-200">
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-medium text-sm">Clause {provision.ref_number}</span>
                        <span className="text-xs text-gray-500">{provision.document_id}</span>
                      </div>
                      {provision.section_header && (
                        <div className="font-semibold text-sm mb-2 text-gray-700">
                          {provision.section_header}
                        </div>
                      )}
                      <TruncatedText text={provision.provision_text} wordLimit={100} />
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* Show database provisions if available */}
            {constraint.provisions && constraint.provisions.length > 0 && (
              <>
                <h4 className="font-semibold text-sm mb-2">Detailed Provisions:</h4>
                <div className="space-y-3">
                  {constraint.provisions.map((provision) => (
                    <div key={provision.id} className="bg-white p-3 rounded-lg border border-gray-200">
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-medium text-sm">{provision.ref_number}</span>
                        <span className="text-xs text-gray-500">{provision.document_id}</span>
                      </div>
                      {provision.section_header && (
                        <div className="font-semibold text-sm mb-1 text-gray-700">
                          {provision.section_header}
                        </div>
                      )}
                      <TruncatedText text={provision.provision_text} wordLimit={100} />
                    </div>
                  ))}
                </div>
              </>
            )}

            {/* No provisions message */}
            {seppProvisions.length === 0 && (!constraint.provisions || constraint.provisions.length === 0) && !loading && (
              <p className="text-sm text-gray-500 italic">
                No detailed provisions available. Check the source document for full details.
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}