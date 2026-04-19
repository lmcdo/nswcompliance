'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const INITIAL_DISPLAY_COUNT = 5;

interface LandUseZoningCardProps {
  zone: string;
  zoneDescription?: string;
  zoneFull?: string;
  legislationUrl?: string;
  epiName?: string;
  amendment?: string;
  legislativeClause?: string;
}

export function LandUseZoningCard({
  zone,
  zoneDescription,
  zoneFull,
  legislationUrl,
  epiName,
  amendment,
  legislativeClause = 'Clause 2.3'
}: LandUseZoningCardProps) {
  // Extract zone name from description (removes zone code prefix)
  const zoneName = zoneDescription?.replace(`${zone}:`, '').trim() || zone;

  // Parse permitted/prohibited uses from the portal's "Land Use" field (zone objectives text).
  // The NSW standard instrument LEP format is consistent across all councils:
  //   "Permitted without consent: A, B, C  Permitted with consent: D, E, F  Prohibited: G, H"
  // Falls back to legislation link only if zoneFull is not available.
  function parseZoneUses(text: string): { permitted: string[]; prohibited: string[]; fromLEP: true } {
    const splitItems = (raw: string) =>
      raw.split(/[,;]/).map(s => s.trim()).filter(s => s.length > 0 && s !== 'Nil');

    const withoutConsent = text.match(/Permitted without consent[:\s]+([^.]+?)(?=Permitted with consent|Prohibited|$)/i)?.[1] ?? '';
    const withConsent    = text.match(/Permitted with consent[:\s]+([^.]+?)(?=Permitted without|Prohibited|$)/i)?.[1] ?? '';
    const prohibitedRaw  = text.match(/Prohibited[:\s]+([^.]+?)(?=Permitted|$)/i)?.[1] ?? '';

    return {
      permitted: [...splitItems(withoutConsent), ...splitItems(withConsent)],
      prohibited: splitItems(prohibitedRaw),
      fromLEP: true,
    };
  }

  const { permitted, prohibited, fromLEP } = zoneFull
    ? parseZoneUses(zoneFull)
    : { permitted: [] as string[], prohibited: [] as string[], fromLEP: false as const };

  const [permittedExpanded, setPermittedExpanded] = useState(false);
  const [prohibitedExpanded, setProhibitedExpanded] = useState(false);

  const displayedPermitted = permittedExpanded
    ? permitted
    : permitted.slice(0, INITIAL_DISPLAY_COUNT);
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
          {!fromLEP && (
            <p className="text-xs text-amber-700 mb-2">
              Uses not available — see full land use table via the link below.
            </p>
          )}
          <div className="grid grid-cols-2 gap-4">
            {/* Left: Permitted Uses */}
            <div>
              <div className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1">
                ✓ Permitted Uses {fromLEP && `(${permitted.length})`}
              </div>
              <ul className="text-sm text-gray-700 space-y-1">
                {displayedPermitted.map((use, idx) => (
                  <li key={idx} className="flex items-start gap-2">
                    <span className="text-green-600 flex-shrink-0">•</span>
                    <span>{use}</span>
                  </li>
                ))}
              </ul>
              {permitted.length > INITIAL_DISPLAY_COUNT && (
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
                      Show all {permitted.length} uses
                    </>
                  )}
                </button>
              )}
            </div>

            {/* Right: Prohibited Uses */}
            <div>
              <div className="text-xs font-semibold text-red-700 mb-2 flex items-center gap-1">
                ✗ Prohibited Uses {fromLEP && `(${prohibited.length})`}
              </div>
              <ul className="text-sm text-gray-700 space-y-1">
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
                      Show all {prohibited.length} uses
                    </>
                  )}
                </button>
              )}
            </div>
          </div>
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

        {/* Info note */}
        <div className="mt-3 bg-amber-50 rounded p-2 border border-amber-200">
          <p className="text-xs text-amber-800">
            Some uses may be permitted with consent or prohibited. Check the full LEP Land Use Table for details.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
