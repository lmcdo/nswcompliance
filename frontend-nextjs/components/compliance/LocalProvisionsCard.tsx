'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ExternalLink, ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { LocalProvision } from '@/lib/nsw-planning-portal';
import { SemanticColors } from '@/lib/design-tokens';

interface LocalProvisionsCardProps {
  localProvisions: LocalProvision[];
}

interface ProvisionDetail {
  clauseNumber: string;
  clauseTitle: string;
  provisionText: string;
  pageNumber: number;
}

export function LocalProvisionsCard({ localProvisions }: LocalProvisionsCardProps) {
  const [expandedProvisions, setExpandedProvisions] = useState<Set<string>>(new Set());
  const [provisionDetails, setProvisionDetails] = useState<Record<string, ProvisionDetail>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [showNearby, setShowNearby] = useState(false);

  // Split provisions into exact matches and nearby
  const exactProvisions = localProvisions.filter(p => !p.isNearby);
  const nearbyProvisions = localProvisions.filter(p => p.isNearby);

  // Property is a Key Site only if it has an exact-match Part 6 clause (e.g. 6.24, 6.27).
  // General KSM clauses like 4.4 (floor space ratio) apply to ALL properties in KSM polygons
  // and do NOT mean this specific property is at a Key Site.
  const isKeySite = exactProvisions.some(p =>
    (p.mapType === 'KSM' || p.mapType === 'Key Sites Map') &&
    p.clauseNumber?.startsWith('6.')
  );

  const toggleProvision = async (provisionKey: string, clauseNumber: string | undefined, fallbackPageNumber: number | undefined) => {
    if (!clauseNumber) return;

    const isExpanded = expandedProvisions.has(provisionKey);

    if (isExpanded) {
      const newExpanded = new Set(expandedProvisions);
      newExpanded.delete(provisionKey);
      setExpandedProvisions(newExpanded);
    } else {
      const newExpanded = new Set(expandedProvisions);
      newExpanded.add(provisionKey);
      setExpandedProvisions(newExpanded);

      if (!provisionDetails[provisionKey]) {
        setLoading({ ...loading, [provisionKey]: true });

        try {
          const response = await fetch(`/api/lep/provisions?clause=${encodeURIComponent(clauseNumber)}`);
          console.log(`[LocalProvisionsCard] Fetching clause ${clauseNumber}, status: ${response.status}`);
          if (response.ok) {
            const data = await response.json();
            console.log(`[LocalProvisionsCard] Received data for clause ${clauseNumber}:`, data);

            // Use pageNumber from provision object if API returns null
            // (Planning Portal extraction sets pageNumber from KSM mapping, but DB may have null)
            const pageNumber = data.pageNumber || fallbackPageNumber;

            setProvisionDetails({
              ...provisionDetails,
              [provisionKey]: {
                ...data,
                pageNumber
              }
            });
          } else {
            console.error(`[LocalProvisionsCard] API returned ${response.status} for clause ${clauseNumber}`);
          }
        } catch (error) {
          console.error('Error fetching provision:', error);
        } finally {
          setLoading({ ...loading, [provisionKey]: false });
        }
      }
    }
  };

  const renderProvision = (provision: LocalProvision) => {
          const uniqueKey = `${provision.title}-${provision.epiName || ''}-${provision.class || ''}`.replace(/\s+/g, '-');
          const isExpanded = expandedProvisions.has(uniqueKey);
          const detail = provisionDetails[uniqueKey];
          const isLoading = loading[uniqueKey];

          // Deep-link to specific clause using #sec.{clauseNumber} anchor
          const clauseUrl = provision.clauseNumber && provision.legislationUrl
            ? `${provision.legislationUrl}#sec.${provision.clauseNumber}`
            : provision.legislationUrl;

          return (
            <div key={uniqueKey} className="border-l-4 border-amber-500 pl-4 py-2 bg-amber-50/50 rounded-r-md">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <h4 className="font-semibold text-sm text-amber-900">
                      {provision.title}
                    </h4>
                    {provision.clauseNumber && (
                      <button
                        onClick={() => toggleProvision(uniqueKey, provision.clauseNumber, provision.pageNumber)}
                        className="text-amber-700 hover:text-amber-900 transition-colors"
                        aria-label={isExpanded ? 'Collapse provision' : 'Expand provision'}
                      >
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </button>
                    )}
                  </div>
                  {/* For provisions without a clause number (e.g. SEPP overlays),
                      show class as the primary constraint description */}
                  {!provision.clauseNumber && provision.class && (
                    <p className="text-sm font-medium text-amber-800 mt-1">
                      {provision.class}
                    </p>
                  )}
                  {provision.description && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {provision.description}
                    </p>
                  )}
                  <div className="flex flex-wrap gap-2 mt-2">
                    {provision.clauseNumber && (
                      <Badge variant="outline" className="text-xs bg-amber-100 text-amber-900 border-amber-300">
                        Clause {provision.clauseNumber}
                      </Badge>
                    )}
                    {(detail?.pageNumber || provision.pageNumber) && (
                      <Badge variant="outline" className="text-xs bg-white">
                        Page {detail?.pageNumber || provision.pageNumber}
                      </Badge>
                    )}
                    {provision.class && (
                      <Badge variant="outline" className="text-xs">
                        {provision.class}
                      </Badge>
                    )}
                    {provision.epiName && (
                      <Badge variant="outline" className="text-xs bg-white">
                        {provision.epiName}
                      </Badge>
                    )}
                  </div>

                  {isExpanded && (
                    <div className="mt-3 p-3 bg-white rounded-md border border-amber-200">
                      {isLoading ? (
                        <p className="text-sm text-muted-foreground">Loading provision text...</p>
                      ) : (provision.mapType === 'Site-Specific' || provision.mapType === 'KSM') && provision.clauseNumber && (detail?.pageNumber || provision.pageNumber) ? (
                        <div className="space-y-2">
                          <h5 className="font-semibold text-sm text-amber-900">
                            {provision.title}
                          </h5>
                          <p className="text-sm text-gray-700 mb-2">
                            View the full provision from Inner West LEP 2022:
                          </p>
                          <img
                            src={`https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/iwlep_clause_${provision.clauseNumber.replace('.', '_')}_page_${detail?.pageNumber || provision.pageNumber}.png`}
                            alt={`Clause ${provision.clauseNumber} - Page ${detail?.pageNumber || provision.pageNumber}`}
                            className="w-full border border-amber-200 rounded"
                            onError={(e) => {
                              // If image fails to load, hide it and show fallback text
                              e.currentTarget.style.display = 'none';
                              const parent = e.currentTarget.parentElement;
                              if (parent) {
                                const fallback = document.createElement('div');
                                fallback.className = 'text-sm text-gray-600 mt-2';
                                fallback.innerHTML = `<p class="mb-2">PDF image not yet extracted. View the full clause in the LEP document:</p><a href="${clauseUrl}" target="_blank" rel="noopener noreferrer" class="text-amber-700 hover:text-amber-900 underline font-medium">View Clause ${provision.clauseNumber} in LEP →</a>`;
                                parent.appendChild(fallback);
                              }
                            }}
                          />
                        </div>
                      ) : detail && detail.provisionText && detail.provisionText.length > 100 ? (
                        <div className="space-y-2">
                          {detail.clauseTitle && (
                            <h5 className="font-semibold text-sm text-amber-900">
                              {detail.clauseTitle}
                            </h5>
                          )}
                          <div className="text-sm text-gray-700 whitespace-pre-wrap">
                            {detail.provisionText}
                          </div>
                          {detail.pageNumber && (
                            <p className="text-xs text-gray-500 mt-2">
                              Page {detail.pageNumber}
                            </p>
                          )}
                        </div>
                      ) : (
                        <div className="text-sm text-gray-600">
                          <p className="mb-2">
                            Provision text is being extracted. View the full clause in the LEP document:
                          </p>
                          <a
                            href={clauseUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-amber-700 hover:text-amber-900 underline font-medium"
                          >
                            View Clause {provision.clauseNumber} in LEP →
                          </a>
                        </div>
                      )}
                    </div>
                  )}
                </div>
                {clauseUrl && (
                  <Button
                    variant="ghost"
                    size="sm"
                    asChild
                    className="shrink-0"
                  >
                    <a
                      href={clauseUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-amber-700 hover:text-amber-900"
                    >
                      <ExternalLink className="h-3 w-3" />
                      <span className="text-xs">View legislation</span>
                    </a>
                  </Button>
                )}
              </div>
            </div>
          );
  };

  const hasSepp = exactProvisions.some(p =>
    p.epiName?.toLowerCase().includes('sepp') ||
    p.epiName?.toLowerCase().includes('state environmental planning policy')
  );
  const cardTitle = isKeySite ? 'Key Site (LEP Part 6)' : hasSepp ? 'Planning Overlays' : 'Local Provisions (LEP Part 6)';

  return (
    <Card className="border-amber-200 bg-amber-50/30">
      <CardHeader>
        <CardTitle className="text-base flex items-center justify-between">
          <span>{cardTitle}</span>
          <Badge className="bg-amber-100 text-amber-800">
            {exactProvisions.length} {exactProvisions.length === 1 ? 'overlay' : 'overlays'}
          </Badge>
        </CardTitle>
        {isKeySite ? (
          <p className="text-sm text-amber-800 font-medium mt-2">
            This property is identified as a Key Site in the LEP with site-specific controls.
          </p>
        ) : (
          <p className="text-sm text-muted-foreground mt-2">
            Additional planning overlays that apply to this property — may include LEP local provisions, SEPP overlays, or other instruments.
          </p>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Exact address provisions */}
        {exactProvisions.map(renderProvision)}

        {/* Nearby provisions (same Key Sites Map area, different addresses) */}
        {nearbyProvisions.length > 0 && (
          <div className="mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={() => setShowNearby(!showNearby)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900 mb-3"
            >
              {showNearby ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Other properties in this Key Site area ({nearbyProvisions.length})
              <span className="text-xs text-gray-500 font-normal">
                — same planning controls apply
              </span>
            </button>

            {showNearby && (
              <div className="space-y-3 opacity-75">
                {nearbyProvisions.map(renderProvision)}
              </div>
            )}
          </div>
        )}

        <div className="mt-4 p-3 bg-amber-50 rounded-md border border-amber-200">
          <p className="text-xs text-amber-800">
            <strong>Note:</strong> Planning overlays may include LEP Part 6 local provisions, SEPP spatial overlays, or other instruments. Each overlay imposes specific requirements — verify against the current legislation before issuing approvals.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
