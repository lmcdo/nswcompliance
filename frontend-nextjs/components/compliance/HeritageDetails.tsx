"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Shield, ExternalLink, AlertTriangle } from "lucide-react"

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
}

export function HeritageDetails({ heritage }: HeritageDetailsProps) {
  // Don't render if not heritage listed
  if (!heritage || !heritage.isHeritage) {
    return null;
  }

  // Determine if State or Local heritage based on significance
  const isStateHeritage = heritage.heritageSignificance?.toLowerCase() === 'state';
  const badgeColor = isStateHeritage ? 'bg-red-100 text-red-800 border-red-300' : 'bg-blue-100 text-blue-800 border-blue-300';

  return (
    <Card className="border-blue-300 bg-blue-50/30">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-blue-700" />
            <CardTitle className="text-base text-blue-900">Heritage Listed Property</CardTitle>
          </div>
          <Badge className={`${badgeColor} font-semibold`}>
            {heritage.heritageSignificance || 'Heritage'} Significance
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Heritage Item Name */}
        {heritage.heritageItemName && (
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <div className="text-xs font-semibold text-gray-600 mb-1">Heritage Item</div>
            <div className="text-sm font-bold text-gray-900">{heritage.heritageItemName}</div>
          </div>
        )}

        {/* Heritage Details Grid */}
        <div className="grid grid-cols-2 gap-2">
          {/* Item Number */}
          {heritage.heritageItemNumber && (
            <div className="bg-white rounded-lg p-2.5 border border-blue-100">
              <div className="text-xs text-gray-600 mb-0.5">Item Number</div>
              <div className="text-sm font-semibold text-gray-900">{heritage.heritageItemNumber}</div>
            </div>
          )}

          {/* Heritage Type */}
          {heritage.heritageType && (
            <div className="bg-white rounded-lg p-2.5 border border-blue-100">
              <div className="text-xs text-gray-600 mb-0.5">Heritage Type</div>
              <div className="text-sm font-semibold text-gray-900">{heritage.heritageType}</div>
            </div>
          )}
        </div>

        {/* Legislative Clause */}
        {heritage.heritageClause && (
          <div className="bg-white rounded-lg p-3 border border-blue-200">
            <div className="text-xs font-semibold text-gray-600 mb-1">Legislative Control</div>
            <div className="text-sm font-bold text-gray-900">{heritage.heritageClause}</div>
            {heritage.heritageLegislationUrl && (
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
              Additional approval pathways and design controls apply under {heritage.heritageClause || 'LEP heritage provisions'}.
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
      </CardContent>
    </Card>
  );
}
