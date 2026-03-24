"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Shield, ExternalLink, AlertTriangle } from "lucide-react"

interface HCAData {
  id: string;
  name: string;
  significance: string;
  legislativeClause: string;
  epiName: string;
  layClass: string;
}

interface HeritageDetailsProps {
  heritage?: {
    isHeritage: boolean;
    heritageType?: string;
    heritageItemName?: string;
    heritageItemNumber?: string;
    heritageClause?: string;
    heritageSignificance?: string;
    heritageLegislationUrl?: string;
  };
  propertyGeometry?: {
    x: number;
    y: number;
  };
  lga?: string;
  formerCouncil?: string;
  onViewDCPHeritage?: () => void;
}

/** Council-specific heritage context for HCA cards */
const COUNCIL_HERITAGE_CONTEXT: Record<string, { dcpRef: string; hcaExplanation: string }> = {
  Ashfield: {
    dcpRef: 'Ashfield DCP 2016, Chapter E1',
    hcaExplanation: 'General heritage controls apply to all Heritage Conservation Areas in the former Ashfield area. An Area Character Statement describing this HCA\'s character is available in the DCP.'
  },
  Leichhardt: {
    dcpRef: 'Leichhardt DCP 2013, Part C Section 1',
    hcaExplanation: 'General heritage controls apply to all Heritage Conservation Areas in the former Leichhardt area. There are no HCA-specific controls in the Leichhardt DCP.'
  },
  Marrickville: {
    dcpRef: 'Marrickville DCP 2011, Section 8',
    hcaExplanation: 'Heritage controls may include both general requirements and HCA-specific controls with a Statement of Significance. Check the DCP tab for controls applicable to this area.'
  }
};

export function HeritageDetails({ heritage, propertyGeometry, lga, formerCouncil, onViewDCPHeritage }: HeritageDetailsProps) {
  const [hcaData, setHcaData] = useState<HCAData | null>(null);
  const [hcaLoading, setHcaLoading] = useState(false);

  // Fetch HCA data if we have property coordinates
  useEffect(() => {
    if (propertyGeometry && propertyGeometry.x !== 0 && propertyGeometry.y !== 0 && lga) {
      setHcaLoading(true);

      fetch('/api/heritage/hca-check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          x: propertyGeometry.x,
          y: propertyGeometry.y,
          lga: lga
        })
      })
      .then(res => res.json())
      .then(data => {
        if (data.success && data.data.inHCA) {
          setHcaData(data.data.hca);
        }
      })
      .catch(err => {
        console.error('[HeritageDetails] Failed to fetch HCA data:', err);
      })
      .finally(() => {
        setHcaLoading(false);
      });
    }
  }, [propertyGeometry, lga]);

  // Don't render if NEITHER heritage item NOR HCA
  if ((!heritage || !heritage.isHeritage) && !hcaData) {
    return null;
  }

  // Detect if the Planning API heritage data is actually an HCA (not a specific heritage item)
  const isHeritageDataActuallyHCA = heritage?.heritageType?.toLowerCase().includes('conservation area');

  // Check if we have actual heritage item data (not HCA)
  const hasSpecificHeritageItem = heritage?.isHeritage &&
    (heritage.heritageItemName || heritage.heritageItemNumber) &&
    !isHeritageDataActuallyHCA;

  // Determine if State or Local heritage based on significance
  const isStateHeritage = heritage?.heritageSignificance?.toLowerCase() === 'state';
  const badgeColor = isStateHeritage ? 'bg-red-100 text-red-800 border-red-300' : 'bg-blue-100 text-blue-800 border-blue-300';

  // If Planning API returned HCA data (not a specific item), prefer HCA API data if available
  // Otherwise use Planning API HCA data
  if (isHeritageDataActuallyHCA && !hasSpecificHeritageItem) {
    const displayHCA = hcaData || {
      name: heritage?.heritageItemName || '',
      id: heritage?.heritageItemNumber || '',
      significance: heritage?.heritageSignificance || 'Local',
      legislativeClause: heritage?.heritageClause || 'Clause 5.10',
      layClass: heritage?.heritageType || 'Conservation Area',
      epiName: ''
    };

    return (
      <Card className="border-amber-300 bg-amber-50/30">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-700" />
              <CardTitle className="text-base text-amber-900">Heritage Conservation Area</CardTitle>
            </div>
            <Badge className="bg-amber-100 text-amber-800 border-amber-300 font-semibold">
              {displayHCA.significance}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="bg-white rounded-lg p-2 border border-amber-200">
            <div className="text-xs font-semibold text-amber-600 mb-0.5">Heritage Conservation Area</div>
            <div className="text-sm font-bold text-amber-900">{displayHCA.name}</div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Legislative Control</div>
              <div className="text-sm font-semibold text-amber-900 mb-1.5">{displayHCA.legislativeClause} Inner West LEP 2022</div>
              {heritage?.heritageLegislationUrl && (
                <a
                  href={heritage.heritageLegislationUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-blue-600 hover:text-blue-800 underline flex items-center gap-1 mb-1 text-left"
                >
                  View LEP Heritage Provisions
                  <ExternalLink className="h-3 w-3" />
                </a>
              )}
              {onViewDCPHeritage && (
                <button
                  onClick={onViewDCPHeritage}
                  className="text-xs text-green-700 hover:text-green-800 underline flex items-center gap-1 font-medium text-left"
                >
                  View DCP heritage controls below
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}
            </div>
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Heritage ID</div>
              <div className="text-sm font-semibold text-amber-900">{displayHCA.id}</div>
            </div>
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Type</div>
              <div className="text-sm font-semibold text-amber-900">{displayHCA.layClass}</div>
            </div>
          </div>

          <div className="bg-amber-100 border border-amber-300 rounded-lg p-2 flex gap-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-700 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900">
              Development within this Heritage Conservation Area requires assessment against
              heritage conservation principles under {displayHCA.legislativeClause}.
              <div className="mt-1.5 pt-1.5 border-t border-amber-200 text-amber-800">
                {formerCouncil && COUNCIL_HERITAGE_CONTEXT[formerCouncil] ? (
                  <><strong>DCP controls:</strong> {COUNCIL_HERITAGE_CONTEXT[formerCouncil].hcaExplanation}</>
                ) : (
                  <><strong>Note:</strong> For HCA-specific controls (materials, setbacks, design), see <strong>DCP tab → Heritage</strong>.</>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // If ONLY HCA from HCA API (no heritage data from Planning API), show simplified HCA-only card
  if (!hasSpecificHeritageItem && hcaData && !heritage?.isHeritage) {
    return (
      <Card className="border-amber-300 bg-amber-50/30">
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-center gap-2">
              <Shield className="h-5 w-5 text-amber-700" />
              <CardTitle className="text-base text-amber-900">Heritage Conservation Area</CardTitle>
            </div>
            <Badge className="bg-amber-100 text-amber-800 border-amber-300 font-semibold">
              {hcaData.significance}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="bg-white rounded-lg p-2 border border-amber-200">
            <div className="text-xs font-semibold text-amber-600 mb-0.5">Heritage Conservation Area</div>
            <div className="text-sm font-bold text-amber-900">{hcaData.name}</div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Legislative Control</div>
              <div className="text-sm font-semibold text-amber-900 mb-1.5">{hcaData.legislativeClause} Inner West LEP 2022</div>
              {onViewDCPHeritage && (
                <button
                  onClick={onViewDCPHeritage}
                  className="text-xs text-green-700 hover:text-green-800 underline flex items-center gap-1 font-medium text-left"
                >
                  View DCP heritage controls below
                  <svg className="h-3 w-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>
              )}
            </div>
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Heritage ID</div>
              <div className="text-sm font-semibold text-amber-900">{hcaData.id}</div>
            </div>
            <div className="bg-white rounded-lg p-2 border border-amber-100">
              <div className="text-xs text-amber-600 mb-0.5">Type</div>
              <div className="text-sm font-semibold text-amber-900">{hcaData.layClass}</div>
            </div>
          </div>

          <div className="bg-amber-100 border border-amber-300 rounded-lg p-2 flex gap-2">
            <AlertTriangle className="h-3.5 w-3.5 text-amber-700 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900">
              Development within this Heritage Conservation Area requires assessment against
              heritage conservation principles under {hcaData.legislativeClause}.
              <div className="mt-1.5 pt-1.5 border-t border-amber-200 text-amber-800">
                {formerCouncil && COUNCIL_HERITAGE_CONTEXT[formerCouncil] ? (
                  <><strong>DCP controls:</strong> {COUNCIL_HERITAGE_CONTEXT[formerCouncil].hcaExplanation}</>
                ) : (
                  <><strong>Note:</strong> For HCA-specific controls (materials, setbacks, design), see <strong>DCP tab → Heritage</strong>.</>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  // Show full heritage item card (with optional HCA section at bottom)
  return (
    <Card className="border-blue-300 bg-blue-50/30">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-700" />
            <CardTitle className="text-base text-blue-900">Heritage Listed Property</CardTitle>
          </div>
          <Badge className={`${badgeColor} font-semibold`}>
            {heritage?.heritageSignificance || 'Heritage'} Significance
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Heritage Item Name */}
        {heritage?.heritageItemName && (
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <div className="text-xs font-semibold text-gray-600 mb-1">Heritage Item</div>
            <div className="text-sm font-bold text-gray-900">{heritage.heritageItemName}</div>
          </div>
        )}

        {/* Heritage Details Grid */}
        <div className="grid grid-cols-2 gap-2">
          {/* Item Number */}
          {heritage?.heritageItemNumber && (
            <div className="bg-white rounded-lg p-2.5 border border-blue-100">
              <div className="text-xs text-gray-600 mb-0.5">Item Number</div>
              <div className="text-sm font-semibold text-gray-900">{heritage.heritageItemNumber}</div>
            </div>
          )}

          {/* Heritage Type */}
          {heritage?.heritageType && (
            <div className="bg-white rounded-lg p-2.5 border border-blue-100">
              <div className="text-xs text-gray-600 mb-0.5">Heritage Type</div>
              <div className="text-sm font-semibold text-gray-900">{heritage.heritageType}</div>
            </div>
          )}
        </div>

        {/* Legislative Clause */}
        {heritage?.heritageClause && (
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <div className="text-xs font-semibold text-gray-600 mb-1">Legislative Control</div>
            <div className="text-sm font-bold text-gray-900">{heritage.heritageClause}</div>
            {heritage?.heritageLegislationUrl && (
              <a
                href={heritage.heritageLegislationUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1 mt-1.5"
              >
                View LEP Heritage Provisions
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        )}

        {/* Heritage Development Impact Warning */}
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 flex gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-xs text-amber-900">
            <div className="font-semibold mb-1">Heritage Development Controls Apply</div>
            <div className="text-amber-800">
              Development on heritage-listed properties requires heritage impact assessment.
              General heritage design controls apply under {heritage?.heritageClause || 'LEP heritage provisions'}
              {formerCouncil && COUNCIL_HERITAGE_CONTEXT[formerCouncil] ? ` — see ${COUNCIL_HERITAGE_CONTEXT[formerCouncil].dcpRef} in the DCP tab` : ''}.
            </div>
          </div>
        </div>

        {/* Additional Heritage Resources */}
        <div className="pt-2 border-t border-blue-200">
          <div className="text-xs text-gray-600 mb-2">Heritage Resources:</div>
          <div className="flex flex-col gap-1.5">
            <a
              href="https://www.heritage.nsw.gov.au/"
              target="_blank"
              rel="noopener noreferrer"
              className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
            >
              NSW Heritage Office
              <ExternalLink className="h-3 w-3" />
            </a>
            {isStateHeritage && (
              <a
                href="https://www.heritage.nsw.gov.au/search-for-heritage/"
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:text-blue-800 underline inline-flex items-center gap-1"
              >
                State Heritage Register
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>

        {/* Heritage Conservation Area Section (if present and not duplicate) */}
        {/* Only show HCA section if we have a specific heritage item AND the property is also in an HCA */}
        {hcaData && hasSpecificHeritageItem && (
          <div className="pt-3 border-t border-blue-200">
            <div className="bg-amber-50 border border-amber-300 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Shield className="h-4 w-4 text-amber-700" />
                <div className="text-sm font-bold text-amber-900">Also Within Heritage Conservation Area</div>
                <Badge className="bg-amber-100 text-amber-800 border-amber-300 text-xs">
                  {hcaData.significance}
                </Badge>
              </div>

              <div className="space-y-2">
                <div className="text-sm font-semibold text-amber-900">{hcaData.name}</div>

                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-amber-700">Heritage ID:</span>
                    <span className="ml-1 font-semibold text-amber-900">{hcaData.id}</span>
                  </div>
                  <div>
                    <span className="text-amber-700">Type:</span>
                    <span className="ml-1 font-semibold text-amber-900">{hcaData.layClass}</span>
                  </div>
                </div>

                <div className="text-xs">
                  <span className="text-amber-700">Legislative Control:</span>
                  <span className="ml-1 font-semibold text-amber-900">{hcaData.legislativeClause}</span>
                </div>

                <div className="text-xs italic text-amber-800 mt-2 pt-2 border-t border-amber-200">
                  This property is subject to additional heritage conservation area controls under {hcaData.legislativeClause}.
                </div>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
