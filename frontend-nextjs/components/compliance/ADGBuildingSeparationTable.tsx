import React, { useState, useEffect } from 'react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Info, ChevronDown, ExternalLink } from 'lucide-react';

interface ADGBuildingSeparationTableProps {
  buildingHeight: number;
  developmentType: string;
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
  };
  notes: string[];
}

export function ADGBuildingSeparationTable({
  buildingHeight,
  developmentType
}: ADGBuildingSeparationTableProps) {
  const [data, setData] = useState<ADGStandards | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchADGStandards = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `/api/setbacks/adg?building_height=${buildingHeight}&development_type=${developmentType}`
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
    };

    fetchADGStandards();
  }, [buildingHeight, developmentType]);

  if (loading) {
    return (
      <div className="animate-pulse space-y-3">
        <div className="h-4 bg-gray-200 rounded w-3/4"></div>
        <div className="h-20 bg-gray-200 rounded"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-red-600 text-sm">
        Error loading ADG standards: {error}
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="space-y-4">
      {/* Alert: Statutory requirement */}
      <Alert className="border-red-200 bg-red-50">
        <Info className="h-4 w-4 text-red-600" />
        <AlertTitle className="text-red-900">Statutory Requirement</AlertTitle>
        <AlertDescription className="text-red-800">
          Mandatory under {data.source.authority}. Not discretionary.
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
        <p>
          <a
            href={data.source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 underline"
          >
            View Official PDF (Page {data.source.page})
            <ExternalLink className="h-3 w-3" />
          </a>
        </p>
      </div>
    </div>
  );
}
