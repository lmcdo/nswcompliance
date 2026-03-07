'use client';

import { useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronUp, ExternalLink } from 'lucide-react';

const INITIAL_DISPLAY_COUNT = 5;

interface LandUseZoningCardProps {
  zone: string;
  zoneDescription?: string;
  legislationUrl?: string;
  epiName?: string;
  amendment?: string;
  legislativeClause?: string;
}

export function LandUseZoningCard({
  zone,
  zoneDescription,
  legislationUrl,
  epiName,
  amendment,
  legislativeClause = 'Clause 2.3'
}: LandUseZoningCardProps) {
  // Extract zone name from description (removes zone code prefix)
  const zoneName = zoneDescription?.replace(`${zone}:`, '').trim() || zone;

  // Common permitted uses by zone (based on standard NSW LEP templates)
  // TODO: Replace with actual API data when available
  const getPermittedUses = (zoneCode: string): { permitted: string[], prohibited: string[] } => {
    const permittedByZone: Record<string, { permitted: string[], prohibited: string[] }> = {
      'R1': {
        permitted: ['Dwelling houses', 'Environmental protection works', 'Home-based child care', 'Home businesses', 'Home occupations'],
        prohibited: ['Industries', 'Heavy industrial storage', 'Warehouse or distribution centres', 'Commercial premises']
      },
      'R2': {
        permitted: ['Dwelling houses', 'Dual occupancies', 'Secondary dwellings', 'Multi dwelling housing', 'Home-based child care', 'Home businesses', 'Places of public worship', 'Neighbourhood shops'],
        prohibited: ['Industries', 'Heavy industrial storage', 'Warehouse or distribution centres', 'Service stations']
      },
      'R3': {
        permitted: ['Dwelling houses', 'Dual occupancies', 'Multi dwelling housing', 'Residential flat buildings', 'Shop top housing', 'Boarding houses', 'Child care centres', 'Community facilities', 'Mixed use development'],
        prohibited: ['Industries', 'Heavy industrial storage', 'Warehouse or distribution centres']
      },
      'R4': {
        permitted: ['Dwelling houses', 'Dual occupancies', 'Multi dwelling housing', 'Residential flat buildings', 'Boarding houses', 'Group homes', 'Hostels', 'Respite day care centres', 'Seniors housing'],
        prohibited: ['Industries', 'Heavy industrial storage', 'Commercial premises', 'Retail premises']
      },
      'B1': {
        permitted: ['Neighbourhood shops', 'Office premises', 'Business premises', 'Medical centres', 'Restaurants or cafes', 'Shop top housing', 'Community facilities'],
        prohibited: ['Industries', 'Heavy industrial storage', 'Warehouse or distribution centres']
      },
      'B2': {
        permitted: ['Office premises', 'Retail premises', 'Commercial premises', 'Shop top housing', 'Entertainment facilities', 'Food and drink premises', 'Hotel or motel accommodation', 'Mixed use development'],
        prohibited: ['Agriculture', 'Heavy industries', 'Rural industries']
      },
      'B4': {
        permitted: ['Commercial premises', 'Hotel or motel accommodation', 'Recreation facilities (outdoor)', 'Registered clubs', 'Restaurants or cafes', 'Shop top housing'],
        prohibited: ['Heavy industries', 'Warehouse or distribution centres']
      },
      'B5': {
        permitted: ['Business premises', 'Office premises', 'Retail premises', 'Industrial retail outlets', 'Garden centres', 'Hardware and building supplies', 'Landscaping material supplies', 'Neighbourhood shops', 'Self-storage units', 'Timber yards', 'Vehicle sales or hire premises', 'Warehouse or distribution centres'],
        prohibited: ['Agriculture', 'Heavy industries', 'Offensive industries', 'Prohibited industries']
      },
      'B6': {
        permitted: ['Boat launching ramps', 'Boat sheds', 'Charter and tourism boating facilities', 'Kiosks', 'Markets', 'Passenger transport facilities', 'Recreation facilities (outdoor)', 'Restaurants or cafes', 'Retail premises', 'Water recreation structures'],
        prohibited: ['Industries', 'Warehouse or distribution centres', 'Extractive industries', 'Heavy industries']
      },
      'E1': {
        permitted: ['Centre-based child care facilities', 'Community facilities', 'Educational establishments', 'Medical centres', 'Neighbourhood shops', 'Office premises', 'Passenger transport facilities', 'Places of public worship', 'Recreation facilities (indoor)', 'Respite day care centres', 'Restricted premises', 'Retail premises', 'Shop top housing'],
        prohibited: ['Agriculture', 'Heavy industries', 'Rural industries', 'Extractive industries', 'Warehouse or distribution centres']
      },
      'E2': {
        permitted: ['Environmental protection works', 'Extensive agriculture', 'Home-based child care', 'Home businesses', 'Home occupations'],
        prohibited: ['Industries', 'Commercial premises', 'Retail premises', 'Warehouse or distribution centres', 'Service stations', 'Vehicle sales or hire premises']
      },
      'E3': {
        permitted: ['Building identification signs', 'Business identification signs', 'Environmental protection works', 'Extensive agriculture', 'Home-based child care', 'Home businesses', 'Home occupations'],
        prohibited: ['Industries', 'Commercial premises', 'Retail premises', 'Warehouse or distribution centres', 'Service stations', 'Multi dwelling housing', 'Residential flat buildings']
      },
      'E4': {
        permitted: ['Environmental facilities', 'Environmental protection works', 'Recreation areas'],
        prohibited: ['Industries', 'Commercial premises', 'Retail premises', 'Residential accommodation', 'Warehouse or distribution centres']
      },
      'IN1': {
        permitted: ['Industries', 'Warehouse or distribution centres', 'Freight transport facilities', 'Self-storage units', 'Truck depots'],
        prohibited: ['Residential accommodation', 'Retail premises', 'Sensitive uses']
      },
      'IN2': {
        permitted: ['Light industries', 'Warehouse or distribution centres', 'Neighbourhood shops', 'Hardware and building supplies', 'Landscaping material supplies'],
        prohibited: ['Residential accommodation', 'Hazardous industries', 'Heavy industries']
      },
      'RE1': {
        permitted: ['Aquaculture', 'Boat launching ramps', 'Boat sheds', 'Community facilities', 'Environmental facilities', 'Environmental protection works', 'Kiosks', 'Recreation areas', 'Recreation facilities (indoor)', 'Recreation facilities (outdoor)', 'Respite day care centres'],
        prohibited: ['Industries', 'Commercial premises', 'Retail premises', 'Residential accommodation (except with consent)', 'Warehouse or distribution centres']
      },
      'RE2': {
        permitted: ['Boat launching ramps', 'Boat sheds', 'Environmental facilities', 'Environmental protection works', 'Extensive agriculture', 'Kiosks', 'Recreation areas'],
        prohibited: ['Industries', 'Commercial premises', 'Retail premises', 'Residential accommodation', 'Warehouse or distribution centres', 'Service stations']
      },
      'SP1': {
        permitted: ['Depends on purpose shown on Land Zoning Map'],
        prohibited: ['Varies based on special purpose designation']
      },
      'SP2': {
        permitted: ['Health services facilities', 'Educational establishments', 'Emergency services facilities', 'Public administration buildings', 'Sewerage systems', 'Waste or resource management facilities', 'Water supply systems'],
        prohibited: ['Residential accommodation (except with consent)', 'Retail premises', 'Commercial premises']
      },
      'SP3': {
        permitted: ['Business premises', 'Community facilities', 'Educational establishments', 'Entertainment facilities', 'Function centres', 'Health services facilities', 'Medical centres', 'Recreation facilities (indoor)', 'Recreation facilities (outdoor)', 'Registered clubs', 'Restricted premises', 'Retail premises', 'Shop top housing'],
        prohibited: ['Agriculture', 'Heavy industries', 'Extractive industries', 'Hazardous industries']
      }
    };

    return permittedByZone[zoneCode] || {
      permitted: ['See LEP Land Use Table'],
      prohibited: ['See LEP Land Use Table']
    };
  };

  const { permitted, prohibited } = getPermittedUses(zone);

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
              {epiName || 'Inner West Local Environmental Plan 2022'} - {legislativeClause}
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
          <div className="grid grid-cols-2 gap-4">
            {/* Left: Permitted Uses */}
            <div>
              <div className="text-xs font-semibold text-green-700 mb-2 flex items-center gap-1">
                ✓ Permitted Uses ({permitted.length})
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
                ✗ Prohibited Uses ({prohibited.length})
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
