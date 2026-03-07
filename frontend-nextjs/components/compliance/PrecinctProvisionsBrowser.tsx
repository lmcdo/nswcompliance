'use client';

/**
 * Precinct Provisions Browser
 * Displays location-specific DCP provisions for addresses within precincts
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MapPin, FileText, FileImage, ChevronDown, ChevronRight } from 'lucide-react';
import { PdfImageModal } from '@/components/ui/pdf-image-modal';

interface PrecinctInfo {
  precinctNumber: string;
  precinctName: string;
  documentId: string;
  lga: string;
}

interface PrecinctProvision {
  id: number;
  precinct_id: string;
  precinct_name: string;
  provision_text: string;
  provision_type: string | null;
  ref_number: string;
  section_header: string;
  pdf_page: number;
  document_id: string;
  pdf_page_image_url?: string;
}

interface PrecinctProvisionsBrowserProps {
  lga: string;
  address: string;
  onViewProvision?: (provision: any) => void;
}

export function PrecinctProvisionsBrowser({
  lga,
  address,
  onViewProvision
}: PrecinctProvisionsBrowserProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [precinct, setPrecinct] = useState<PrecinctInfo | null>(null);
  const [provisions, setProvisions] = useState<PrecinctProvision[]>([]);
  const [expanded, setExpanded] = useState(true);
  const [expandedProvisionId, setExpandedProvisionId] = useState<number | null>(null);
  const [viewingPdfImage, setViewingPdfImage] = useState<string | null>(null);

  useEffect(() => {
    if (!address || !lga) {
      setLoading(false);
      return;
    }

    async function fetchPrecinctData() {
      try {
        setLoading(true);
        setError(null);

        // Step 1: Match address to precinct
        const matchResponse = await fetch('/api/precinct/match', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ address, lga })
        });

        if (!matchResponse.ok) {
          throw new Error('Failed to match precinct');
        }

        const matchData = await matchResponse.json();

        if (!matchData.success || !matchData.precinct) {
          // No precinct for this address
          setPrecinct(null);
          setProvisions([]);
          setLoading(false);
          return;
        }

        setPrecinct(matchData.precinct);

        // Step 2: Fetch precinct provisions
        // Convert precinct number format: "9_29" → "29_"
        const precinctId = matchData.precinct.precinctNumber.includes('_')
          ? matchData.precinct.precinctNumber.split('_')[1] + '_'
          : matchData.precinct.precinctNumber;

        const provisionsResponse = await fetch('/api/precinct/provisions', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            precinctId,
            lga: matchData.precinct.lga
          })
        });

        if (!provisionsResponse.ok) {
          throw new Error('Failed to fetch provisions');
        }

        const provisionsData = await provisionsResponse.json();

        if (provisionsData.success) {
          console.log('[PrecinctProvisionsBrowser] Provisions data:', {
            count: provisionsData.data.provisions.length,
            firstProvision: provisionsData.data.provisions[0] ? {
              id: provisionsData.data.provisions[0].id,
              hasPdfUrl: !!provisionsData.data.provisions[0].pdf_page_image_url,
              pdfUrl: provisionsData.data.provisions[0].pdf_page_image_url
            } : null
          });
          setProvisions(provisionsData.data.provisions);
        } else {
          throw new Error(provisionsData.error || 'Unknown error');
        }

      } catch (err) {
        console.error('[PrecinctProvisionsBrowser] Error:', err);
        setError(err instanceof Error ? err.message : 'Failed to load precinct data');
      } finally {
        setLoading(false);
      }
    }

    fetchPrecinctData();
  }, [address, lga]);

  // Loading state
  if (loading) {
    return (
      <Card className="mt-4">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-gray-500">
            <MapPin className="w-4 h-4 animate-pulse" />
            <span>Checking for precinct controls...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Error state
  if (error) {
    return (
      <Card className="mt-4 border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 text-red-600">
            <FileText className="w-4 h-4" />
            <span>Error loading precinct data: {error}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  // No precinct state
  if (!precinct) {
    return (
      <Card className="mt-4">
        <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MapPin className="w-5 h-5 text-gray-400" />
              <CardTitle className="text-base">Precinct Controls</CardTitle>
            </div>
            {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
          </div>
        </CardHeader>
        {expanded && (
          <CardContent>
            <p className="text-sm text-gray-600">
              No precinct-specific controls apply to this address.
            </p>
          </CardContent>
        )}
      </Card>
    );
  }

  // Has precinct + provisions
  return (
    <>
      <Card className="mt-4 border-blue-200 bg-blue-50/30">
      <CardHeader className="cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MapPin className="w-5 h-5 text-blue-600" />
            <div>
              <CardTitle className="text-base">
                Precinct {precinct.precinctNumber}: {precinct.precinctName}
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                {provisions.length} location-specific {provisions.length === 1 ? 'control' : 'controls'}
              </p>
            </div>
          </div>
          {expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </div>
      </CardHeader>

      {expanded && (
        <CardContent className="space-y-3">
          {provisions.length === 0 ? (
            <p className="text-sm text-gray-600">
              No provisions found for this precinct.
            </p>
          ) : (
            provisions.map((provision) => {
              const isExpanded = expandedProvisionId === provision.id;
              const textPreview = provision.provision_text
                .substring(0, 150)
                .trim();

              return (
                <div key={provision.id}>
                  <div
                    className={`border border-gray-200 bg-white rounded-lg p-4 hover:border-blue-300 transition-colors cursor-pointer ${
                      isExpanded ? 'ring-2 ring-blue-500' : ''
                    }`}
                    onClick={() => {
                      if (isExpanded) {
                        setExpandedProvisionId(null);
                      } else {
                        setExpandedProvisionId(provision.id);
                      }
                    }}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        {/* Ref number and type */}
                        <div className="flex items-center gap-2 mb-2">
                          {provision.ref_number && (
                            <Badge variant="outline" className="text-xs">
                              {provision.ref_number}
                            </Badge>
                          )}
                          {provision.provision_type && (
                            <Badge variant="secondary" className="text-xs">
                              {provision.provision_type}
                            </Badge>
                          )}
                          {provision.pdf_page && (
                            <span className="text-xs text-gray-500">
                              Page {provision.pdf_page}
                            </span>
                          )}
                        </div>

                        {/* Section header */}
                        {provision.section_header && (
                          <h4 className="font-semibold text-sm mb-2">
                            {provision.section_header}
                          </h4>
                        )}

                        {/* Provision text preview */}
                        <div className="text-sm text-gray-700 line-clamp-2">
                          {textPreview}...
                        </div>

                        {/* Toggle indicator */}
                        <div className="flex items-center gap-2 mt-2">
                          <span className="text-xs text-blue-600 hover:text-blue-700 font-medium">
                            {isExpanded ? 'Hide Full Text ▲' : 'View Full Text ▼'}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Expanded Full Text - OUTSIDE the card */}
                  {isExpanded && (
                    <div className="mt-2 mb-4 border rounded-lg bg-gray-50 p-4 relative">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setExpandedProvisionId(null);
                        }}
                        className="absolute top-2 right-2 text-gray-500 hover:text-gray-700 bg-white rounded-full p-1 shadow-sm"
                        aria-label="Close"
                      >
                        <span className="text-lg leading-none">×</span>
                      </button>
                      <div className="pr-8">
                        <div className="mb-2 pb-2 border-b">
                          <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                              {provision.ref_number && (
                                <Badge variant="outline" className="text-xs">
                                  {provision.ref_number}
                                </Badge>
                              )}
                              <span className="text-xs font-semibold text-gray-700">
                                {provision.section_header}
                              </span>
                            </div>
                            {provision.pdf_page_image_url && (
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setViewingPdfImage(provision.pdf_page_image_url || null);
                                }}
                                className="p-1.5 rounded hover:bg-blue-100 transition-colors"
                                title="View PDF Page"
                              >
                                <FileImage className="w-5 h-5 text-blue-500 hover:text-blue-700" />
                              </button>
                            )}
                          </div>
                        </div>
                        <div
                          className="text-sm text-gray-700 prose prose-sm max-w-none"
                          dangerouslySetInnerHTML={{
                            __html: (() => {
                              // Helper to escape HTML special chars
                              const escapeHtml = (str: string) => {
                                return str
                                  .replace(/&/g, '&amp;')
                                  .replace(/</g, '&lt;')
                                  .replace(/>/g, '&gt;')
                                  .replace(/"/g, '&quot;')
                                  .replace(/'/g, '&#039;');
                              };

                              let text = provision.provision_text;

                              // Format tables with proper styling first (preserve existing table tags)
                              text = text.replace(/<table/g, '<table class="min-w-full border-collapse border border-gray-300 my-4"');
                              text = text.replace(/<td/g, '<td class="border border-gray-300 px-2 py-1 text-xs"');
                              text = text.replace(/<th/g, '<th class="border border-gray-300 px-2 py-1 text-xs font-semibold bg-gray-100"');

                              // Process line by line to group continuation lines
                              const lines = text.split('\n');
                              const grouped: string[] = [];

                              for (let i = 0; i < lines.length; i++) {
                                const line = lines[i].trim();

                                // Skip empty lines and header junk
                                if (!line || /^#/.test(line) || /^\d+$/.test(line)) continue;

                                // Check if this is a section header (e.g., "9.29.1 Heritage")
                                if (/^\d+\.\d+(?:\.\d+)?\s+[A-Z]/.test(line)) {
                                  const escaped = escapeHtml(line);
                                  grouped.push('<h3 class="font-semibold text-base mt-4 mb-2">' + escaped + '</h3>');
                                }
                                // Check if this is a numbered list item (e.g., "5. To protect...")
                                else if (/^\d+\.\s+/.test(line)) {
                                  // Collect this line and any continuation lines
                                  let fullText = line;
                                  while (i + 1 < lines.length && lines[i + 1].trim() && !/^\d+\./.test(lines[i + 1].trim()) && !/^\d+\.\d+/.test(lines[i + 1].trim())) {
                                    i++;
                                    fullText += ' ' + lines[i].trim();
                                  }
                                  const escaped = escapeHtml(fullText);
                                  grouped.push('<li class="mb-2">' + escaped + '</li>');
                                }
                                // Regular paragraph text
                                else {
                                  // Collect continuation lines into a paragraph
                                  let fullText = line;
                                  while (i + 1 < lines.length && lines[i + 1].trim() && !/^\d+\./.test(lines[i + 1].trim()) && !/^\d+\.\d+/.test(lines[i + 1].trim())) {
                                    i++;
                                    fullText += ' ' + lines[i].trim();
                                  }
                                  const escaped = escapeHtml(fullText);
                                  grouped.push('<p class="mb-3">' + escaped + '</p>');
                                }
                              }

                              // Wrap consecutive <li> in <ol>
                              let html = grouped.join('\n');
                              html = html.replace(/(<li[^>]*>.*?<\/li>\n?)+/g, (match) => {
                                return '<ol class="list-decimal list-outside my-3 ml-4">' + match + '</ol>';
                              });

                              // Convert markdown bold
                              html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

                              return html;
                            })()
                          }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}

          {/* Footer note */}
          <div className="text-xs text-gray-500 mt-4 pt-4 border-t">
            These controls are specific to {precinct.precinctName} and supplement the general DCP requirements.
          </div>
        </CardContent>
      )}
      </Card>

      {/* PDF Page Image Modal */}
      <PdfImageModal
        isOpen={!!viewingPdfImage}
        onClose={() => setViewingPdfImage(null)}
        imageUrl={viewingPdfImage}
        title="Precinct DCP Document"
      />
    </>
  );
}
