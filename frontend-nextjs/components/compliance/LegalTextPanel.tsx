'use client';

/**
 * Legal Text Slide-Out Panel
 *
 * Displays full legal text for SEPP/LEP/DCP provisions
 * Slides in from right side when provision is selected
 * Cross-browser compatible with Flexbox + Width transitions
 */

import { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Bookmark, Share2, ExternalLink } from 'lucide-react';

export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
}

export interface SelectedProvision {
  constraint: {
    type: string;
    value: string | number;
    unit?: string;
    source: {
      clause: string;
      document: string;
      authority_level: 'LEP' | 'DCP' | 'SEPP';
    };
    seppMetadata?: {
      epiName: string;
      mapType?: string;
      keywords?: string[];
    };
  };
  provisions: ProvisionContent[];
}

interface LegalTextPanelProps {
  selectedProvision: SelectedProvision | null;
  onClose: () => void;
}

export function LegalTextPanel({
  selectedProvision,
  onClose
}: LegalTextPanelProps) {
  const [loading, setLoading] = useState(false);

  if (!selectedProvision) {
    return null;
  }

  const { constraint, provisions } = selectedProvision;

  // Parse table from line-by-line format to HTML table
  const parseLineByLineTable = (section: string) => {
    const lines = section.split('\n').map(l => l.trim()).filter(Boolean);

    // Find table name
    let tableName = '';
    let startIdx = 0;
    if (lines[0]?.startsWith('Table ')) {
      tableName = lines[0];
      startIdx = 1;
    }

    // Find where columns start (lines with "Column X")
    const columnStartIdx = lines.findIndex(l => l.match(/^Column\s+\d+$/));
    if (columnStartIdx === -1) return null;

    // Header is everything from start to columns
    const headerParts = lines.slice(startIdx, columnStartIdx);
    const columnHeaders = [];

    // Collect column headers (Column 1, Column 2, etc.)
    let i = columnStartIdx;
    while (i < lines.length && lines[i].match(/^Column\s+\d+$/)) {
      columnHeaders.push(lines[i]);
      i++;
    }

    const numColumns = columnHeaders.length + 1; // +1 for first column (zone/climate)

    // Data starts after column headers
    const dataLines = lines.slice(i);

    // Group data lines into rows
    const rows: string[][] = [];
    for (let j = 0; j < dataLines.length; j += numColumns) {
      const row = dataLines.slice(j, j + numColumns);
      if (row.length === numColumns) {
        rows.push(row);
      }
    }

    if (rows.length === 0) return null;

    return (
      <div className="my-4 overflow-x-auto">
        {tableName && (
          <div className="font-semibold text-sm mb-2">{tableName}</div>
        )}
        <table className="min-w-full border-collapse border border-gray-300 text-xs bg-white">
          <thead className="bg-gray-100">
            <tr>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">
                {headerParts.join(' ')}
              </th>
              {columnHeaders.map((col, idx) => (
                <th key={idx} className="border border-gray-300 px-3 py-2 text-left font-semibold">
                  {col}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                {row.map((cell, cellIdx) => (
                  <td key={cellIdx} className="border border-gray-300 px-3 py-2">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

  // Format legal text with smart table detection
  const formatLegalText = (text: string) => {
    const sections = text.split(/\n\n+/);

    return sections.map((section, idx) => {
      const trimmed = section.trim();
      if (!trimmed) return null;

      // Check if this looks like a line-by-line table
      const hasTableData = /Column\s+\d+/.test(trimmed) || /^Table\s+\d+/m.test(trimmed);

      if (hasTableData) {
        // Try to parse as table
        const tableElement = parseLineByLineTable(trimmed);
        if (tableElement) {
          return <div key={`section-${idx}`}>{tableElement}</div>;
        }
        // Fallback to monospace if parsing fails
        return (
          <div key={`section-${idx}`} className="my-4 p-4 bg-gray-50 rounded border border-gray-200 overflow-x-auto">
            <pre className="font-mono text-xs whitespace-pre-wrap">{trimmed}</pre>
          </div>
        );
      } else {
        // Regular paragraph
        return (
          <p key={`section-${idx}`} className="mb-3 text-sm leading-relaxed font-serif whitespace-pre-wrap">
            {trimmed}
          </p>
        );
      }
    }).filter(Boolean);
  };

  // Get color scheme based on authority level
  const getColorScheme = (level: string) => {
    switch (level) {
      case 'SEPP':
        return {
          bg: 'bg-red-50',
          border: 'border-red-200',
          badge: 'bg-red-100 text-red-800',
          header: 'bg-red-100'
        };
      case 'LEP':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          badge: 'bg-blue-100 text-blue-800',
          header: 'bg-blue-100'
        };
      case 'DCP':
        return {
          bg: 'bg-green-50',
          border: 'border-green-200',
          badge: 'bg-green-100 text-green-800',
          header: 'bg-green-100'
        };
      default:
        return {
          bg: 'bg-gray-50',
          border: 'border-gray-200',
          badge: 'bg-gray-100 text-gray-800',
          header: 'bg-gray-100'
        };
    }
  };

  const colors = getColorScheme(constraint.source.authority_level);

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <Card className={`h-full flex flex-col ${colors.border} border-2 overflow-hidden`}>
        {/* Header */}
        <CardHeader className={`${colors.header} pb-3 flex-shrink-0`}>
          <div className="flex items-start justify-between">
            <div className="flex-1 pr-4">
              <div className="flex items-center gap-2 mb-2">
                <Badge className={colors.badge}>
                  {constraint.source.authority_level}
                </Badge>
                <span className="text-sm text-gray-600">
                  {constraint.source.clause}
                </span>
              </div>
              <CardTitle className="text-lg">
                {constraint.source.document}
              </CardTitle>
              <div className="text-sm text-gray-600 mt-1">
                {constraint.type.charAt(0).toUpperCase() + constraint.type.slice(1)}: {constraint.value}{constraint.unit}
              </div>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="flex-shrink-0"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>
        </CardHeader>

        {/* Scrollable Content */}
        <CardContent className="flex-1 overflow-y-auto pt-4" style={{ maxHeight: 'calc(100% - 200px)' }}>
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-gray-500">Loading legal text...</div>
            </div>
          )}

          {!loading && provisions.length === 0 && (
            <div className="text-center py-8 text-gray-500">
              <p className="italic">No detailed provisions available.</p>
              <p className="text-sm mt-2">Check the source document for full details.</p>
            </div>
          )}

          {!loading && provisions.length > 0 && (
            <div className="space-y-4">
              <h3 className="font-semibold text-sm text-gray-700 mb-3">
                Legal Text ({provisions.length} {provisions.length === 1 ? 'clause' : 'clauses'})
              </h3>

              {provisions.map((provision) => (
                <div
                  key={provision.id}
                  className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm"
                >
                  {/* Clause Header */}
                  <div className="flex items-start justify-between mb-3 pb-2 border-b border-gray-100">
                    <div>
                      <span className="font-semibold text-gray-900">
                        Clause {provision.ref_number}
                      </span>
                      {provision.section_header && (
                        <div className="text-sm font-medium text-gray-700 mt-1">
                          {provision.section_header}
                        </div>
                      )}
                    </div>
                    <span className="text-xs text-gray-500">
                      ID: {provision.id}
                    </span>
                  </div>

                  {/* Full Legal Text */}
                  <div className="text-sm text-gray-800 leading-relaxed">
                    {formatLegalText(provision.provision_text)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>

        {/* Action Footer */}
        <div className="flex-shrink-0 border-t border-gray-200 p-4 bg-gray-50">
          <div className="flex items-center justify-between gap-2">
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="gap-2">
                <Bookmark className="h-4 w-4" />
                Bookmark
              </Button>
              <Button variant="outline" size="sm" className="gap-2">
                <Share2 className="h-4 w-4" />
                Share
              </Button>
            </div>
            {constraint.source.document.includes('legislation.nsw.gov.au') && (
              <Button variant="outline" size="sm" className="gap-2">
                <ExternalLink className="h-4 w-4" />
                View Source
              </Button>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}