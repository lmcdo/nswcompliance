'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, ExternalLink, Loader2 } from 'lucide-react';

const INITIAL_DISPLAY_COUNT = 8;

/** Convert slug like "dwelling_houses" to "Dwelling houses" */
function slugToDisplay(slug: string): string {
  return slug.replace(/_/g, ' ').replace(/^./, c => c.toUpperCase());
}

interface PermissibilityEntry {
  development_type: string;
  permissibility: 'exempt' | 'permitted' | 'prohibited';
}

interface LandUseZoningCardProps {
  zone: string;
  zoneDescription?: string;
  lga?: string;
  legislationUrl?: string;
  epiName?: string;
  amendment?: string;
  legislativeClause?: string;
}

export function LandUseZoningCard({
  zone,
  zoneDescription,
  lga,
  legislationUrl,
  epiName,
  amendment,
  legislativeClause = 'Clause 2.3'
}: LandUseZoningCardProps) {
  const zoneName = zoneDescription?.replace(`${zone}:`, '').trim() || zone;

  const [loading, setLoading] = useState(false);
  const [exempt, setExempt] = useState<string[]>([]);
  const [permitted, setPermitted] = useState<string[]>([]);
  const [prohibited, setProhibited] = useState<string[]>([]);
  const [covered, setCovered] = useState(false);
  const [scrapedAt, setScrapedAt] = useState<string | null>(null);
  const [sourceUrl, setSourceUrl] = useState<string | null>(null);

  const [permittedExpanded, setPermittedExpanded] = useState(false);
  const [prohibitedExpanded, setProhibitedExpanded] = useState(false);

  // Fetch permissibility data from DB
  useEffect(() => {
    if (!zone || !lga) return;
    setLoading(true);
    fetch(`/api/lep/permissibility?zone=${encodeURIComponent(zone)}&lga=${encodeURIComponent(lga)}`)
      .then(r => r.json())
      .then((data: { covered: boolean; scraped_at?: string; source_url?: string; entries: PermissibilityEntry[] }) => {
        if (data.covered && data.entries.length > 0) {
          setCovered(true);
          setScrapedAt(data.scraped_at ?? null);
          setSourceUrl(data.source_url ?? null);
          const ex: string[] = [];
          const perm: string[] = [];
          const proh: string[] = [];
          for (const e of data.entries) {
            const name = slugToDisplay(e.development_type);
            if (e.permissibility === 'exempt') ex.push(name);
            else if (e.permissibility === 'permitted') perm.push(name);
            else if (e.permissibility === 'prohibited') proh.push(name);
          }
          setExempt(ex);
          setPermitted(perm);
          setProhibited(proh);
        }
      })
      .catch(() => { /* silent — falls back to "not available" */ })
      .finally(() => setLoading(false));
  }, [zone, lga]);

  const allPermitted = [...exempt, ...permitted];
  const displayedPermitted = permittedExpanded
    ? allPermitted
    : allPermitted.slice(0, INITIAL_DISPLAY_COUNT);
  const displayedProhibited = prohibitedExpanded
    ? prohibited
    : prohibited.slice(0, INITIAL_DISPLAY_COUNT);

  return (
    <Card className="border-amber-200 bg-amber-50/50">
      <CardContent className="pt-4">
        {/* Main content - Zone name/code on left, pills on right */}
        <div className="flex justify-between items-start mb-3">
          {/* Left: Zone info stacked */}
          <div>
            {legislationUrl ? (
              <a
                href={`${legislationUrl}#pt-cg1.Zone_${zone}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-amber-600 hover:text-amber-700 underline"
              >
                Land Use Zoning:
              </a>
            ) : (
              <p className="text-sm text-gray-700">Land Use Zoning:</p>
            )}
            {legislationUrl ? (
              <a
                href={`${legislationUrl}#pt-cg1.Zone_${zone}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-lg font-bold text-amber-600 hover:text-amber-700 underline"
              >
                {zone} {zoneName !== zone && `- ${zoneName}`}
              </a>
            ) : (
              <p className="text-lg font-bold text-gray-900">
                {zone} {zoneName !== zone && `- ${zoneName}`}
              </p>
            )}
          </div>

          {/* Right: Blue and Green pills stacked */}
          <div className="flex flex-col gap-1 items-end">
            <Badge className="text-xs px-2 py-0.5 bg-amber-100 text-amber-800">
              {epiName || 'Local Environmental Plan'} — {legislativeClause}
            </Badge>
            {amendment && (
              <Badge className="text-xs px-2 py-0.5 bg-amber-50 text-amber-700">
                {amendment}
              </Badge>
            )}
          </div>
        </div>

        {/* Permitted & Prohibited Uses Table */}
        <div className="bg-white rounded-lg p-3 border border-amber-200">
          {loading && (
            <div className="flex items-center gap-2 text-xs text-amber-700 mb-2">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading land use data...
            </div>
          )}
          {!loading && !covered && (
            <p className="text-xs text-amber-700 mb-2">
              Land use data not available for this zone — see full land use table via the link below.
            </p>
          )}
          {!loading && covered && (
            <div className="grid grid-cols-2 gap-4">
              {/* Left: Permitted Uses */}
              <div>
                <div className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1">
                  Permitted Uses ({allPermitted.length})
                </div>
                {exempt.length > 0 && (
                  <div className="mb-2">
                    <span className="text-xs text-green-600 font-medium">Without consent</span>
                    <ul className="text-sm text-gray-700 space-y-0.5 mt-0.5">
                      {exempt.map((use, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <span className="text-green-500 flex-shrink-0">•</span>
                          <span>{use}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                <div>
                  {exempt.length > 0 && permitted.length > 0 && (
                    <span className="text-xs text-green-600 font-medium">With consent</span>
                  )}
                  <ul className="text-sm text-gray-700 space-y-0.5 mt-0.5">
                    {(permittedExpanded ? permitted : permitted.slice(0, Math.max(0, INITIAL_DISPLAY_COUNT - exempt.length))).map((use, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600 flex-shrink-0">•</span>
                        <span>{use}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                {allPermitted.length > INITIAL_DISPLAY_COUNT && (
                  <button
                    onClick={() => setPermittedExpanded(!permittedExpanded)}
                    className="text-xs text-green-700 hover:text-green-800 hover:underline mt-2 flex items-center gap-1"
                  >
                    {permittedExpanded ? (
                      <>
                        <ChevronUp className="h-3 w-3" />
                        Show less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-3 w-3" />
                        Show all {allPermitted.length} permitted
                      </>
                    )}
                  </button>
                )}
              </div>

              {/* Right: Prohibited Uses */}
              <div>
                <div className="text-xs font-semibold text-red-700 mb-2 flex items-center gap-1">
                  Prohibited Uses ({prohibited.length})
                </div>
                <ul className="text-sm text-gray-700 space-y-0.5">
                  {displayedProhibited.map((use, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-red-600 flex-shrink-0">•</span>
                      <span>{use}</span>
                    </li>
                  ))}
                </ul>
                {prohibited.length > INITIAL_DISPLAY_COUNT && (
                  <button
                    onClick={() => setProhibitedExpanded(!prohibitedExpanded)}
                    className="text-xs text-red-700 hover:text-red-800 hover:underline mt-2 flex items-center gap-1"
                  >
                    {prohibitedExpanded ? (
                      <>
                        <ChevronUp className="h-3 w-3" />
                        Show less
                      </>
                    ) : (
                      <>
                        <ChevronDown className="h-3 w-3" />
                        Show all {prohibited.length} prohibited
                      </>
                    )}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* View Full Table Link */}
        {legislationUrl && (
          <div className="mt-3 pt-3 border-t border-amber-200">
            <a
              href={`${legislationUrl}#pt-cg1.Zone_${zone}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-amber-600 hover:text-amber-700 underline inline-flex items-center gap-1"
            >
              View Full Land Use Table for {zone}
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}

        {/* Provenance */}
        {covered && (
          <div className="mt-3 bg-amber-50 rounded p-2 border border-amber-200">
            <p className="text-xs text-amber-800">
              Sourced from {epiName || 'LEP'} Land Use Table via{' '}
              {sourceUrl ? (
                <a href={sourceUrl} target="_blank" rel="noopener noreferrer" className="underline hover:text-amber-900">
                  legislation.nsw.gov.au
                </a>
              ) : (
                'legislation.nsw.gov.au'
              )}
              {scrapedAt && (() => {
                const d = new Date(scrapedAt);
                const daysSince = Math.floor((Date.now() - d.getTime()) / 86400000);
                return (
                  <>
                    {' · '}
                    <span className={daysSince > 90 ? 'font-semibold text-red-700' : ''}>
                      {d.toLocaleDateString('en-AU', { day: 'numeric', month: 'long', year: 'numeric' })}
                    </span>
                    {daysSince > 90 && ' — data may be stale, re-scrape recommended'}
                  </>
                );
              })()}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
