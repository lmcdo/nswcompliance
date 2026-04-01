import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Info, ChevronDown, ExternalLink, FileText } from 'lucide-react';

interface ADGBuildingSeparationTableProps {
  buildingHeight?: number | null;
  developmentType: string;
  onBuildingHeightChange?: (height: number | null) => void;
}

interface ADGStandards {
  applies: boolean;
  building_height_meters: number;
  height_category: string;
  storey_range: string;
  development_type: string;
  setbacks: {
    side: {
      habitable_rooms_and_balconies: number | null;
      non_habitable_rooms: number | null;
    };
    rear: {
      habitable_rooms_and_balconies: number | null;
      non_habitable_rooms: number | null;
    };
  };
  additional_requirements: string[];
  source: {
    document: string;
    section: string;
    design_criteria: string;
    authority: string;
    legal_status: string;
    url: string;
    page: number;
    pdfUrl?: string | null;
  };
  notes: string[];
}

export function ADGBuildingSeparationTable({
  buildingHeight,
  developmentType,
  onBuildingHeightChange
}: ADGBuildingSeparationTableProps) {
  const [data, setData] = useState<ADGStandards | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [localHeight, setLocalHeight] = useState<string>(buildingHeight?.toString() || '');

  // Sync local state with prop
  useEffect(() => {
    if (buildingHeight !== null && buildingHeight !== undefined) {
      setLocalHeight(buildingHeight.toString());
    }
  }, [buildingHeight]);

  // Fetch ADG standards when we have a valid building height (debounced)
  useEffect(() => {
    const height = buildingHeight ?? parseFloat(localHeight);
    if (!height || isNaN(height) || height <= 0) {
      setData(null);
      setLoading(false);
      return;
    }

    // Debounce: wait 400ms after user stops changing value
    const timeoutId = setTimeout(async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/setbacks/adg?building_height=${height}&development_type=${developmentType}`
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const result = await response.json();

        if (!result.applies) {
          setData(null);
          return;
        }

        setData(result);
      } catch (err) {
        console.error('[ADGBuildingSeparationTable] Failed to fetch ADG standards:', err);
        setError(err instanceof Error ? err.message : 'Failed to fetch ADG standards');
      } finally {
        setLoading(false);
      }
    }, 400);

    return () => clearTimeout(timeoutId);
  }, [buildingHeight, localHeight, developmentType]);

  const handleHeightChange = (value: string) => {
    setLocalHeight(value);
    const numValue = parseFloat(value);
    if (onBuildingHeightChange) {
      onBuildingHeightChange(isNaN(numValue) ? null : numValue);
    }
  };

  const effectiveHeight = buildingHeight ?? parseFloat(localHeight);
  const hasValidHeight = effectiveHeight && !isNaN(effectiveHeight) && effectiveHeight > 0;

  // Always show the card with height input
  return (
    <div className="space-y-4">
      {/* Building Height Input - always visible */}
      <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
        <label className="text-sm font-semibold text-purple-900 block mb-2">
          Proposed Building Height (meters)
        </label>
        <div className="flex items-center gap-3">
          <input
            type="number"
            step="0.1"
            min="0"
            max="100"
            value={localHeight}
            onChange={(e) => handleHeightChange(e.target.value)}
            className="w-32 px-3 py-2 border border-purple-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-purple-500"
            placeholder="e.g., 18"
          />
          <span className="text-sm text-purple-700">meters</span>
          {hasValidHeight && (
            <span className="text-xs text-purple-600 bg-purple-100 px-2 py-1 rounded">
              {effectiveHeight <= 12 ? 'Low-rise (≤4 storeys)' :
               effectiveHeight <= 25 ? 'Mid-rise (5-8 storeys)' :
               'High-rise (9+ storeys)'}
            </span>
          )}
        </div>
        <p className="text-xs text-purple-600 mt-2">
          Enter your proposed building height to calculate ADG setback requirements
        </p>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="animate-pulse space-y-3">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="text-red-600 text-sm">
          Error loading ADG standards: {error}
        </div>
      )}

      {/* Prompt to enter height if not provided */}
      {!hasValidHeight && !loading && (
        <div className="text-center py-6 text-gray-500 bg-gray-50 rounded-lg border border-dashed border-gray-300">
          <p className="text-sm">Enter a building height above to see ADG setback requirements</p>
        </div>
      )}

      {/* ADG Data Display */}
      {data && hasValidHeight && !loading && (
        <>
      {/* Alert: Statutory requirement */}
      <Alert className="border-red-200 bg-red-50">
        <Info className="h-4 w-4 text-red-600" />
        <AlertTitle className="text-red-900">These setbacks are required by law</AlertTitle>
        <AlertDescription className="text-red-800">
          Council cannot approve smaller setbacks. Your design must meet these minimums.
        </AlertDescription>
      </Alert>

      {/* Building height category */}
      <div className="bg-white border border-gray-200 rounded-lg p-3">
        <p className="text-sm font-semibold text-gray-900">
          Building Height Category: {data.height_category}
        </p>
        <p className="text-xs text-gray-600 mt-1">
          ({data.storey_range}) - Height: {data.building_height_meters}m
        </p>
      </div>

      {/* Setbacks table */}
      <div className="border rounded-lg overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-gray-50">
              <TableHead className="font-semibold">Boundary</TableHead>
              <TableHead className="font-semibold">Room Type</TableHead>
              <TableHead className="font-semibold">Minimum Setback</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow>
              <TableCell className="font-medium">Side</TableCell>
              <TableCell>Habitable rooms & balconies</TableCell>
              <TableCell className="font-bold text-red-700 text-lg">
                {data.setbacks.side.habitable_rooms_and_balconies}m
              </TableCell>
            </TableRow>
            <TableRow className="bg-gray-50">
              <TableCell className="font-medium">Side</TableCell>
              <TableCell className="text-sm text-gray-600">
                Non-habitable (bathrooms, laundries, storage)
              </TableCell>
              <TableCell className="font-semibold">
                {data.setbacks.side.non_habitable_rooms}m
              </TableCell>
            </TableRow>
            <TableRow>
              <TableCell className="font-medium">Rear</TableCell>
              <TableCell>Habitable rooms & balconies</TableCell>
              <TableCell className="font-bold text-red-700 text-lg">
                {data.setbacks.rear.habitable_rooms_and_balconies}m
              </TableCell>
            </TableRow>
            <TableRow className="bg-gray-50">
              <TableCell className="font-medium">Rear</TableCell>
              <TableCell className="text-sm text-gray-600">
                Non-habitable (bathrooms, laundries, storage)
              </TableCell>
              <TableCell className="font-semibold">
                {data.setbacks.rear.non_habitable_rooms}m
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </div>

      {/* Additional requirements (collapsible) */}
      {data.additional_requirements && data.additional_requirements.length > 0 && (
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-2 text-sm font-medium text-gray-700 hover:text-gray-900">
            <ChevronDown className="h-4 w-4" />
            Additional Requirements ({data.additional_requirements.length})
          </CollapsibleTrigger>
          <CollapsibleContent className="space-y-2 pt-2 pl-6">
            {data.additional_requirements.map((req, i) => (
              <p key={i} className="text-sm text-gray-700">
                • {req}
              </p>
            ))}
          </CollapsibleContent>
        </Collapsible>
      )}

      {/* Source citation */}
      <div className="border-t pt-3 space-y-1 text-xs text-gray-600">
        <p>
          <strong className="text-gray-900">Source:</strong> {data.source.document}
        </p>
        <p>
          <strong className="text-gray-900">Section:</strong> {data.source.section} - {data.source.design_criteria}
        </p>
        <p>
          <strong className="text-gray-900">Authority:</strong> {data.source.authority}
        </p>
        <p>
          <strong className="text-gray-900">Legal Status:</strong>{' '}
          <span className="text-red-600 font-semibold">{data.source.legal_status}</span>
        </p>
        <div className="flex items-center gap-3 pt-1">
          {data.source.pdfUrl && (
            <button
              onClick={() => window.open(`${data.source.pdfUrl}#page=${data.source.page}`, '_blank')}
              className="p-1.5 rounded hover:bg-purple-100 transition-colors"
              title={`View PDF page ${data.source.page}`}
            >
              <FileText className="w-5 h-5 text-purple-500 hover:text-purple-700" />
            </button>
          )}
          <a
            href={data.source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
          >
            Open Full PDF
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
      </div>

        </>
      )}
    </div>
  );
}
