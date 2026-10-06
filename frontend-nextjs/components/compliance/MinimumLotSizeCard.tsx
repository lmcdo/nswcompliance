'use client';

import { instrumentClauseLabel } from '@/lib/citation-display';
import { Badge } from '@/components/ui/badge';

interface MinimumLotSizeCardProps {
  minimumSize: number;
  unit?: string;
  epiName?: string;
  amendment?: string;
  legislativeClause?: string;
}

export function MinimumLotSizeCard({
  minimumSize,
  unit = 'm²',
  epiName,
  amendment,
  legislativeClause
}: MinimumLotSizeCardProps) {
  // No default, and no fallback instrument: the badge below named the INNER WEST
  // LEP for a property in any council whenever the Portal response had no EPI name.
  const citation = instrumentClauseLabel(epiName, legislativeClause);

  return (
    <div className="border border-blue-200 bg-blue-50/50 rounded-lg p-4">
      {/* Top right: Blue and Green pills stacked */}
      <div className="flex justify-end mb-2">
        <div className="flex flex-col gap-1 items-end">
          {citation && (
            <Badge className="text-xs px-2 py-0.5 bg-blue-100 text-blue-800">
              {citation}
            </Badge>
          )}
          {amendment && (
            <Badge className="text-xs px-2 py-0.5 bg-green-100 text-green-800">
              {amendment}
            </Badge>
          )}
        </div>
      </div>

      {/* Main content */}
      <p className="text-sm text-gray-700">
        Minimum Lot Size for Subdivision:
      </p>
      <p className="text-lg font-bold text-gray-900 mt-1">
        {minimumSize}{unit}
      </p>

      <p className="text-xs text-gray-600 mt-2">
        Subdivision below this size is prohibited unless specifically permitted by the LEP.
      </p>
    </div>
  );
}
