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
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getProvisionDisplayTitle, isMachineGeneratedId } from '@/lib/provision-title-utils';

export interface ProvisionContent {
  id: number;
  ref_number: string;
  section_header: string;
  provision_text: string;
  document_id: string;
}

// Parse SEPP horizontal tables (e.g., Table 1 Climate zone Column 1 Column 2... 8 65% 69%...)
function parseSeppHorizontalTables(text: string): string {
  // Pattern: "Table N" followed by first column name, then "Column 1", "Column 2", etc., then data
  // Example: "Table 1 Climate zone Column 1 Column 2 Column 3 8 65% 69% 63%..."

  // More specific pattern that handles the actual SEPP table format
  const tablePattern = /(Table\s+\d+)\s+([A-Za-z\s]+?)\s+(Column\s+\d+(?:\s+Column\s+\d+)*)\s+([\d%.\s—\-]+?)(?=\n\s*\n|\n\s*\(\d+\)|\n\s*Part\s+\d+|\n\s*\d+\s+[A-Z]|$)/gi;

  return text.replace(tablePattern, (match, tableTitle, firstColName, columnHeaders, tableData) => {
    try {
      // Parse column headers
      const colHeaders = columnHeaders.match(/Column\s+\d+/gi) || [];
      const allHeaders = [firstColName.trim(), ...colHeaders];

      // Parse data - split into tokens (numbers, percentages, dashes, em-dashes)
      // Data format: "8 65% 69% 63% 56% 57% 60% 9 64% 66%..."
      // Note: Some cells might be "—" (em-dash) for no data
      const tokens = tableData.trim().split(/\s+/).filter(Boolean);

      const numCols = allHeaders.length;
      const rows: string[][] = [];

      // Group tokens into rows
      for (let i = 0; i < tokens.length; i += numCols) {
        const row = tokens.slice(i, i + numCols);
        if (row.length === numCols) {
          rows.push(row);
        }
      }

      // If we didn't get any complete rows, try again with looser parsing
      if (rows.length === 0) {
        console.warn('Failed to parse SEPP table with strict column count, trying flexible parsing');
        return match;
      }

      // Build markdown table
      let mdTable = `\n\n**${tableTitle}**\n\n`;
      mdTable += '| ' + allHeaders.join(' | ') + ' |\n';
      mdTable += '| ' + allHeaders.map(() => '---').join(' | ') + ' |\n';
      rows.forEach(row => {
        mdTable += '| ' + row.join(' | ') + ' |\n';
      });
      mdTable += '\n';

      return mdTable;
    } catch (error) {
      console.error('Error parsing SEPP table:', error);
      return match; // Return original text on error
    }
  });
}

// Convert bullet points (•) to markdown bullets
function convertBulletsToMarkdown(text: string): string {
  // Convert Unicode bullet (•) to markdown bullet (-)
  // Pattern: "•" followed by optional whitespace, then content
  text = text.replace(/•\s*/g, '- ');

  // Remove stray superscript numbers that appear at end of paragraphs
  // Pattern: standalone digit at end of line (footnote references)
  // Keep if it's part of a measurement (e.g., "20m2") but remove if standalone
  text = text.replace(/\s+\d+\s*$/gm, '');

  return text;
}

// Convert legal numbered/lettered lists to markdown format
function convertLegalListsToMarkdown(text: string): string {
  // LEP provisions use (1), (2), (3) for main points and (a), (b), (c) for sub-points
  // Pattern: "(1) The objectives..." or "(a) to ensure..."

  // Add newline before numbered subsections (1), (2), (3), etc.
  // Only if preceded by a period, closing paren, or newline (end of sentence)
  text = text.replace(/([.)\n])\s*\((\d+)\)\s+/g, '$1\n\n$2. ');

  // Add newline before lettered subsections (a), (b), (c), etc. at start or after period
  // Make them indented bullet points
  text = text.replace(/([.)\n])\s*\(([a-z])\)\s+/g, '$1\n   - ');

  // Handle (2A), (2B) style subsections
  text = text.replace(/([.)\n])\s*\((\d+[A-Z])\)\s+/g, '$1\n\n$2. ');

  return text;
}

// Truncated text component with "Show more..." button - using ReactMarkdown
function TruncatedFormattedText({
  text,
  wordLimit = 200,
  onImageClick
}: {
  text: string;
  wordLimit?: number;
  onImageClick?: (src: string) => void;
}) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Check if text contains HTML tables (from database)
  const containsHtmlTable = text.includes('<table');

  if (containsHtmlTable) {
    // Render HTML tables directly (database stores tables as HTML, not markdown)
    // Apply styling by wrapping in a div with global styles
    return (
      <div className="text-sm text-gray-800 leading-relaxed prose prose-sm max-w-none my-4">
        <style dangerouslySetInnerHTML={{
          __html: `
            .dcp-table-wrapper table {
              width: 100%;
              border-collapse: collapse;
              margin: 8px 0;
              font-size: 0.75rem;
              background-color: white;
              border: 1px solid #d1d5db;
            }
            .dcp-table-wrapper td,
            .dcp-table-wrapper th {
              border: 1px solid #d1d5db;
              padding: 8px 12px;
              text-align: left;
              vertical-align: top;
            }
            .dcp-table-wrapper th {
              background-color: #f3f4f6;
              font-weight: 600;
              color: #111827;
            }
            .dcp-table-wrapper tr:nth-child(even) {
              background-color: #f9fafb;
            }
            .dcp-table-wrapper tr:hover {
              background-color: #f3f4f6;
            }
          `
        }} />
        <div
          className="dcp-table-wrapper overflow-x-auto"
          dangerouslySetInnerHTML={{ __html: text }}
        />
      </div>
    );
  }

  // Convert SEPP tables to markdown format BEFORE processing
  text = parseSeppHorizontalTables(text);

  // Convert bullet points to markdown format
  text = convertBulletsToMarkdown(text);

  // Convert legal numbered/lettered lists to markdown format
  text = convertLegalListsToMarkdown(text);

  // Count words to determine if truncation is needed
  // Split on whitespace but preserve paragraph breaks (\n\n)
  const words = text.split(/[ \t]+/); // Split only on spaces/tabs, NOT newlines
  const shouldTruncate = words.length > wordLimit;

  // Truncate the TEXT before passing to ReactMarkdown
  // Preserve formatting by rejoining with original spacing
  const displayText = shouldTruncate && !isExpanded
    ? words.slice(0, wordLimit).join(' ') + '...'
    : text;

  return (
    <div className="text-sm text-gray-800 leading-relaxed prose prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          img: ({ node, ...props }) => (
            <img
              {...props}
              className="max-w-full h-auto my-4 rounded border shadow-sm cursor-pointer hover:opacity-80 transition-opacity"
              alt={props.alt || 'Diagram'}
              onClick={() => onImageClick?.(props.src || '')}
              title="Click to enlarge"
            />
          ),
          h1: ({ node, ...props }) => (
            <h1 className="text-lg font-bold mt-4 mb-2" {...props} />
          ),
          h2: ({ node, ...props }) => (
            <h2 className="text-base font-bold mt-3 mb-2" {...props} />
          ),
          p: ({ node, ...props }) => (
            <p className="mb-2 leading-relaxed" {...props} />
          ),
          ul: ({ node, ...props }) => (
            <ul className="list-disc ml-4 mb-2 space-y-1" {...props} />
          ),
          ol: ({ node, ...props }) => (
            <ol className="list-decimal ml-4 mb-2 space-y-1" {...props} />
          ),
          table: ({ node, ...props }) => (
            <div className="my-4 overflow-x-auto">
              <table className="min-w-full border-collapse border border-gray-300 text-xs" {...props} />
            </div>
          ),
          thead: ({ node, ...props }) => (
            <thead className="bg-gray-100" {...props} />
          ),
          tbody: ({ node, ...props }) => (
            <tbody {...props} />
          ),
          tr: ({ node, ...props }) => (
            <tr className="even:bg-gray-50 odd:bg-white" {...props} />
          ),
          th: ({ node, ...props }) => (
            <th className="border border-gray-300 px-3 py-2 text-left font-semibold" {...props} />
          ),
          td: ({ node, ...props }) => (
            <td className="border border-gray-300 px-3 py-2" {...props} />
          ),
        }}
      >
        {displayText}
      </ReactMarkdown>
      {shouldTruncate && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-blue-600 hover:text-blue-800 mt-2 font-medium block"
        >
          {isExpanded ? 'Show less' : 'Show more...'}
        </button>
      )}
    </div>
  );
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
    provision_id?: number;
  };
  provisions: ProvisionContent[];
  // Phase 2 additions
  crossReferences?: Array<{
    referenceType: string;
    referenceNumber: string;
    referenceText: string;
    targetProvisionId: number | null;
    targetReference: string | null;
    resolutionStatus: string;
    isMandatory: boolean;
  }>;
  controlCodes?: string[];
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
  const [detectedFigures, setDetectedFigures] = useState<any[]>([]);
  const [expandedFigures, setExpandedFigures] = useState<string[]>([]);
  const [figureContent, setFigureContent] = useState<Record<string, any>>({});
  const [loadingFigures, setLoadingFigures] = useState<Set<string>>(new Set());
  const [zoomedImage, setZoomedImage] = useState<string | null>(null);

  // Auto-detect figures AND expand short provisions from provision text
  // DISABLED: API endpoint not working for all documents, provisions already have full text with embedded images
  // Hook must be declared before any conditional return to satisfy rules-of-hooks.
  useEffect(() => {
    const provisions = selectedProvision?.provisions;
    const detectFiguresAndExpandShortProvisions = async () => {
      if (!provisions || provisions.length === 0) return;

      const firstProvision = provisions[0];
      if (!firstProvision.document_id || !firstProvision.id) return;

      // DISABLED: This API call fails for most documents
      // The provision_text already contains full text with markdown images
      // Images are now rendered via ReactMarkdown in TruncatedFormattedText
      /*
      try {
        // Auto-detect figure references
        const response = await fetch(
          `/api/documents/${firstProvision.document_id}/extract-section?provision_id=${firstProvision.id}&auto=true`
        );

        if (response.ok) {
          const data = await response.json();
          if (data.success && data.data.sections.length > 0) {
            setDetectedFigures(data.data.sections);
          }
        }

        // If provision text is short or truncated, fetch full document
        // Most DCP provisions in DB are truncated to 500 chars
        if (firstProvision.provision_text.length < 600 && firstProvision.document_id) {
          const docResponse = await fetch(
            `/api/documents/${firstProvision.document_id}`
          );

          if (docResponse.ok) {
            const docData = await docResponse.json();
            if (docData.success) {
              // Store full document as expanded content
              setFigureContent(prev => ({
                ...prev,
                [`full_doc_${firstProvision.document_id}`]: {
                  sectionRef: 'Full Document',
                  content: docData.data.fullText,
                  images: [],
                  imageCount: docData.data.metadata.imageCount,
                  hasImages: docData.data.metadata.imageCount > 0
                }
              }));
              // Auto-expand
              setExpandedFigures(prev => [...prev, `full_doc_${firstProvision.document_id}`]);
            }
          }
        }
      } catch (error) {
        console.error('Error detecting figures:', error);
      }
      */
    };

    detectFiguresAndExpandShortProvisions();
  }, [selectedProvision]);

  if (!selectedProvision) {
    return null;
  }

  const { constraint, provisions } = selectedProvision;

  // Toggle figure expansion
  const toggleFigure = async (figureRef: string) => {
    if (expandedFigures.includes(figureRef)) {
      // Collapse
      setExpandedFigures(prev => prev.filter(f => f !== figureRef));
    } else {
      // Expand - fetch content if not already loaded
      if (!figureContent[figureRef]) {
        setLoadingFigures(prev => new Set(prev).add(figureRef));

        try {
          const firstProvision = provisions[0];
          const response = await fetch(
            `/api/documents/${firstProvision.document_id}/extract-section?figure=${figureRef}`
          );

          if (response.ok) {
            const data = await response.json();
            if (data.success && data.data.sections.length > 0) {
              setFigureContent(prev => ({
                ...prev,
                [figureRef]: data.data.sections[0]
              }));
            }
          }
        } catch (error) {
          console.error('Error loading figure:', error);
        } finally {
          setLoadingFigures(prev => {
            const next = new Set(prev);
            next.delete(figureRef);
            return next;
          });
        }
      }

      setExpandedFigures(prev => [...prev, figureRef]);
    }
  };

  // Parse alternating line table (e.g., Site area / FSR tables in LEP)
  // Format: Line 1=Header1, Line 2=Header2, Line 3=Data1, Line 4=Data2, etc.
  const parseAlternatingLineTable = (section: string) => {
    const lines = section.split('\n').map(l => l.trim()).filter(Boolean);

    if (lines.length < 4) return null; // Need at least 2 headers + 2 data values

    // First two lines MUST be table headers (short, specific keywords)
    const header1 = lines[0];
    const header2 = lines[1];

    // Strict header validation
    const isTableHeader1 = /^(Site area|Minimum lot size|Zone|Climate zone)$/i.test(header1);
    const isTableHeader2 = /^(Maximum floor space ratio|Maximum building height|Minimum lot size|Column \d+)$/i.test(header2);

    if (!isTableHeader1 || !isTableHeader2) return null;

    // Data lines start at index 2
    const dataLines = lines.slice(2);

    // Must have even number of data lines (pairs)
    if (dataLines.length % 2 !== 0) return null;

    // Validate data lines: Should be SHORT (not full sentences)
    // Table data is typically: "< 150m2", "0.9:1", "≥ 150 < 300m2"
    // NOT: "(b) on land identified as..." (clause text)
    const allDataValid = dataLines.every(line => {
      // Reject clause markers
      if (/^\([a-z0-9]+\)/i.test(line)) return false;

      // Reject long sentences (table data is concise)
      if (line.length > 50) return false;

      // Reject lines with common clause words
      if (/identified|shown|specified|purposes|may be|must be/i.test(line)) return false;

      return true;
    });

    if (!allDataValid) return null;

    // Group into rows
    const rows: string[][] = [];
    for (let i = 0; i < dataLines.length; i += 2) {
      rows.push([dataLines[i], dataLines[i + 1]]);
    }

    return (
      <div className="my-4 overflow-x-auto">
        <table className="min-w-full border-collapse border border-gray-300 text-xs bg-white">
          <thead className="bg-gray-100">
            <tr>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">{header1}</th>
              <th className="border border-gray-300 px-3 py-2 text-left font-semibold">{header2}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx} className={rowIdx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                <td className="border border-gray-300 px-3 py-2">{row[0]}</td>
                <td className="border border-gray-300 px-3 py-2">{row[1]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  };

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

  // Add non-breaking spaces to prevent awkward line breaks in legal text
  const preventAwkwardBreaks = (text: string): string => {
    // Common legal measurement patterns: "X m", "X km", "X ha", etc.
    // Pattern: number + unit (with optional space) - keep together
    text = text.replace(/(\d+(?:\.\d+)?)\s*(m²|m2|km²|km2|ha|m|km|mm|cm)(?=\s|$|,|\.)/gi, '$1\u00A0$2');

    // Ratio patterns: "X:Y" - keep together with surrounding numbers
    text = text.replace(/(\d+(?:\.\d+)?)\s*:\s*(\d+)/g, '$1:\u00A0$2');

    // Keep preposition + article + noun together: "of the", "on the", "in the", "to the"
    text = text.replace(/\b(of|on|in|to|at|by|for|with|from)\s+(the|a|an)\s+/gi, '$1 $2\u00A0');

    // Keep compound proper nouns together: "Height of Buildings Map", "Floor Space Ratio Map"
    // Pattern: Capitalized word + "of" + Capitalized word (+ optional "Map")
    text = text.replace(/\b([A-Z][a-z]+)\s+of\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?(?:\s+Map)?)\b/g,
      (match) => match.replace(/\s+/g, '\u00A0'));

    // Keep "Area X", "Zone X", "Column X", "Clause X" together
    text = text.replace(/\b(Area|Zone|Column|Clause|Section|Schedule|Part|Division|Chapter)\s+(\d+[A-Z]?)/gi, '$1\u00A0$2');

    // Keep quoted references together: "Area 1", "Area 2"
    text = text.replace(/[""]([^"""]+)[""]/g, (match) => match.replace(/\s+/g, '\u00A0'));

    return text;
  };

  // Remove document metadata and footer text (version info, page numbers, etc.)
  const removeDocumentMetadata = (text: string): string => {
    // Remove "Current version for [date] to date (accessed [date] at [time])" lines
    // Pattern: "Current version for" + any date text + "accessed" + any date/time
    text = text.replace(/Current version for[^\n]*\(accessed[^\n]*\)\s*/gi, '');

    // Remove "Page X of Y" or "Page X" lines
    // Pattern: "Page" + number + optional "of" + number
    text = text.replace(/^Page\s+\d+(\s+of\s+\d+)?\s*$/gim, '');

    // Remove standalone document names that might appear as headers/footers
    // Pattern: Line with document name followed by [NSW] or [NSW Legislation]
    text = text.replace(/^[^\n]+\[NSW[^\]]*\]\s*$/gim, '');

    // Remove date stamps at end of lines (common in legislation)
    // Pattern: dates in format "24 April 2025" or "24/04/2025"
    text = text.replace(/\s*\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\s*$/gim, '');

    // Clean up multiple consecutive newlines left by removals
    text = text.replace(/\n{3,}/g, '\n\n');

    return text;
  };

  // Fix PDF extraction line breaks (remove hyphenation and join broken lines)
  const fixPdfLineBreaks = (text: string): string => {
    let originalLength = text.length;

    // Step 1: Fix hyphenated line breaks (word- at end of line)
    // Pattern: word character + hyphen + optional whitespace + newline + optional whitespace + word character
    // Replace with: joined word (no hyphen, no newline)
    text = text.replace(/([a-zA-Z])-\s*[\r\n]+\s*([a-zA-Z])/g, '$1$2');

    // Step 2: Join broken lines within sentences
    // Pattern: lowercase letter/comma at end of line + newline + lowercase letter at start
    // But NOT if the next line starts with a clause marker
    text = text.replace(/([a-z,])\s*[\r\n]+\s*([a-z](?!\)))/g, '$1 $2');

    // Step 3: Clean up any remaining awkward single-word breaks
    // Pattern: word + newline + single word + newline (often happens with "the", "of", etc.)
    text = text.replace(/\b(the|of|on|in|to|for|and|or)\s*[\r\n]+\s*/gi, '$1 ');

    console.log('[fixPdfLineBreaks] Processed text, length changed from', originalLength, 'to', text.length);

    return text;
  };

  // Format legal subsections - ensure (a), (b), (1), (2) etc. are on new lines
  const formatLegalSubsections = (text: string): string => {
    // Add newline before subsection markers: (a), (b), (c), (1), (2), (3), etc.
    // BUT only if it's actually starting a new clause, not a reference

    // Strategy: Add newline if the clause marker is followed by text that looks like
    // the start of a clause (lowercase words like "to", "the", "for", etc.)
    // Don't add newline if it's followed by words like "does", "is", "applies" (references)

    // Pattern 1: Clause markers that START a clause (followed by typical clause words)
    // e.g., "(a) to ensure", "(b) for the purposes", "(1) The following"
    text = text.replace(/([^\n.,;:])\s+(\([a-z0-9]+\))\s+(to|for|the|a|an|if|where|on|in|with|by|development|building|land)\s/gi, '$1\n$2 $3 ');

    // Pattern 2: Don't break references - if preceded by short context words
    // e.g., "Subclause (2A) does not", "clause (3) is satisfied", "section (4) applies"
    // These should stay on same line

    return text;
  };

  // Format SEPP legal text - convert legal clause structure to paragraph breaks
  // SEPP text has single newlines at clause boundaries but ReactMarkdown needs double newlines
  const formatSeppLegalText = (text: string): string => {
    // SEPP Schedule text has numbered clauses and lettered subclauses
    // Structure: "1   Clause title\n(1) First requirement\n(a)  detail\n(b)  detail\n(2) Second requirement"
    // We need to add paragraph breaks (double newlines) at major clause boundaries

    // Step 1: Add paragraph break before numbered clause titles (e.g., "1   Toilets, showers and taps")
    // Pattern: newline + digit(s) + non-breaking spaces + text (clause title)
    // Note: \xa0 is non-breaking space (common in SEPP text from PDF extraction)
    text = text.replace(/\n(\d+[\xa0\s]{2,}[A-Z][^\n]+)/g, '\n\n$1');

    // Step 2: Add paragraph break before main subsections (1), (2), (3), etc.
    // But NOT before lettered subclauses (a), (b), (c) which are details under the main clause
    text = text.replace(/\n(\(\d+\)[\xa0\s]+)/g, '\n\n$1');

    // Step 3: Add line break (not paragraph) before lettered subclauses (a), (b), (c)
    // These should be indented details under the main clause, not separate paragraphs
    // Single newline is fine here - keeps them grouped with parent clause
    text = text.replace(/([^\n])[\xa0\s]+(\([a-z]\)[\xa0\s]+)/g, '$1\n$2');

    // Step 4: Add paragraph break before "Part X" section headers
    text = text.replace(/\n(Part\s+\d+[^\n]+)/g, '\n\n$1');

    // Step 5: Add paragraph break before section headings (e.g., "section 2.1")
    text = text.replace(/\n(section\s+\d+\.\d+)/gi, '\n\n$1');

    // Step 6: Clean up excessive newlines (more than 2)
    text = text.replace(/\n{3,}/g, '\n\n');

    return text;
  };

  // Format legal text with smart table detection (line-by-line scan for embedded tables)
  const formatLegalText = (text: string) => {
    const lines = text.split('\n');
    const elements: React.ReactNode[] = [];
    let currentParagraph: string[] = [];
    let i = 0;
    let elementKey = 0;

    const flushParagraph = () => {
      if (currentParagraph.length > 0) {
        let para = currentParagraph.join('\n').trim();
        para = formatLegalSubsections(para); // Add newlines for (a), (b), etc.
        para = preventAwkwardBreaks(para); // Then add non-breaking spaces
        if (para) {
          elements.push(
            <p
              key={`para-${elementKey++}`}
              className="mb-3 text-sm leading-relaxed font-serif whitespace-pre-line"
              style={{
                textWrap: 'pretty' as any,
                hyphens: 'auto',
                overflowWrap: 'break-word'
              }}
            >
              {para}
            </p>
          );
        }
        currentParagraph = [];
      }
    };

    while (i < lines.length) {
      const line = lines[i].trim();

      // Check if this line starts a table (table header patterns)
      const isTableHeader1 = /^(Site area|Minimum lot size|Zone|Climate zone)$/i.test(line);
      const nextLine = i + 1 < lines.length ? lines[i + 1].trim() : '';
      const isTableHeader2 = /^(Maximum floor space ratio|Maximum building height|Minimum lot size|Column \d+)$/i.test(nextLine);

      if (isTableHeader1 && isTableHeader2) {
        // Found table start! Flush current paragraph
        flushParagraph();

        // Collect table lines
        const tableLines = [line, nextLine];
        i += 2;

        // Collect data lines (short, no clause markers, pairs)
        while (i < lines.length) {
          const dataLine = lines[i].trim();

          // Stop if we hit clause marker or long text
          if (/^\([a-z0-9]+\)/i.test(dataLine) || dataLine.length > 50 || /identified|shown|specified|purposes|may be|must be/i.test(dataLine)) {
            break;
          }

          // Stop if empty or looks like next section
          if (!dataLine || /^\d+\.\d+[A-Z]?$/.test(dataLine)) {
            break;
          }

          tableLines.push(dataLine);
          i++;
        }

        // Parse collected table
        const tableText = tableLines.join('\n');
        const table = parseAlternatingLineTable(tableText);

        if (table) {
          elements.push(<div key={`table-${elementKey++}`}>{table}</div>);
        } else {
          // Failed to parse, treat as paragraph
          currentParagraph.push(tableText);
        }
      } else {
        // Not a table, add to current paragraph
        currentParagraph.push(lines[i]);
        i++;
      }
    }

    // Flush remaining paragraph
    flushParagraph();

    return elements;
  };

  // Get color scheme based on authority level
  const getColorScheme = (level: string) => {
    switch (level) {
      case 'SEPP':
        return {
          bg: 'bg-orange-50',
          border: 'border-orange-500',
          badge: 'bg-orange-100 text-orange-800',
          header: 'bg-orange-100'
        };
      case 'LEP':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-500',
          badge: 'bg-blue-100 text-blue-800',
          header: 'bg-blue-100'
        };
      case 'DCP':
        return {
          bg: 'bg-green-50',
          border: 'border-green-500',
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

              {provisions.map((provision) => {
                // Clean provision text - remove document metadata if present
                let cleanedText = provision.provision_text;

                // Remove document name/path from start (matches pattern: "Document Name.pdf")
                cleanedText = cleanedText.replace(/^[^\n]+\.(pdf|PDF)\s*\n/, '');

                // Remove standalone clause number if it duplicates the header
                // Pattern: Line starting with just the clause number (e.g., "4.4\n")
                const clausePattern = new RegExp(`^${provision.ref_number.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s*\n`, 'i');
                cleanedText = cleanedText.replace(clausePattern, '');

                // Fix PDF line breaks FIRST (before other formatting)
                cleanedText = fixPdfLineBreaks(cleanedText);

                // Remove document metadata (page numbers, version info, etc.)
                cleanedText = removeDocumentMetadata(cleanedText);

                // Apply SEPP-specific formatting if this is a SEPP provision
                // SEPP provisions have Schedule ref_numbers or formal_Schedule provision_type
                const isSeppSchedule = provision.ref_number?.includes('Schedule') ||
                                      constraint.source.authority_level === 'SEPP';
                if (isSeppSchedule) {
                  cleanedText = formatSeppLegalText(cleanedText);
                }

                // Clean up LaTeX/MinerU artifacts
                // Remove LaTeX commands like $\textcircled { 9 }$
                cleanedText = cleanedText.replace(/\$\\text[a-z]+\s*\{[^}]*\}\s*\$/gi, '');

                // Remove table of contents style lines (e.g., "9.29.1 Existing character... . 1")
                cleanedText = cleanedText.replace(/^\d+\.\d+(\.\d+)?\s+[A-Za-z][^\n]*\.{3,}.*$/gm, '');

                // Remove "Part X Strategic Context...." lines
                cleanedText = cleanedText.replace(/^Part\s+\$?\\?[^\n]*Strategic Context[^\n]*$/gm, '');

                // Remove logo images (e.g., Inner West Council logo at start of provisions)
                cleanedText = cleanedText.replace(/!\[.*?\]\(images\/[a-f0-9]{64}\.jpg\)\s*/gi, '');

                // Remove duplicate markdown headings that repeat the section number/title
                // Pattern: # 9.29 South Western Marrickville (Precinct 29)
                // These are redundant with the section_header already displayed
                cleanedText = cleanedText.replace(/^#+\s*\d+(\.\d+)*[A-Z]?\s+[^\n]+$/gm, '');

                // Remove context/character description sections (not actual regulations)
                // Strategy: Remove entire sections with character descriptions (heading + content)

                // Remove "Existing character" and "Desired future character" sections
                // This pattern matches: heading + all content until next heading or end
                cleanedText = cleanedText.replace(/^#+\s*\d+\.\d+(\.\d+)?\s+(Existing|Desired future)\s+character[^\n]*\n([\s\S]*?)(?=\n#+\s*\d+\.\d+|\n#+\s*[A-Z]|$)/gim, '');

                // Remove any standalone character description headings that remain
                cleanedText = cleanedText.replace(/^#+\s*\d+\.\d+(\.\d+)?\s+(Existing|Desired future)\s+character[^\n]*$/gm, '');

                // Remove "Map of precinct" headings (the images will remain)
                cleanedText = cleanedText.replace(/^#+\s*Map of precinct\s*$/gm, '');

                // Remove any standalone heading that looks like "# 9.29.1 Existing character..."
                // This catches cases where the section regex didn't match
                cleanedText = cleanedText.replace(/^#+\s*\d+\.\d+(\.\d+)?\s+(?:Existing|Desired future|character)[^\n]*$/gim, '');

                // Clean up multiple consecutive newlines
                cleanedText = cleanedText.replace(/\n{3,}/g, '\n\n');

                // Extract document source from document_id if present
                const docSource = provision.document_id?.includes('.pdf')
                  ? provision.document_id.split('___')[0]?.replace(/_/g, ' ') || provision.document_id
                  : null;

                return (
                  <div
                    key={provision.id}
                    className="bg-white p-4 rounded-lg border border-gray-200 shadow-sm"
                  >
                    {/* Clause Header */}
                    <div className="mb-3 pb-2 border-b border-gray-100">
                      <div className="flex items-baseline gap-2">
                        <span className="font-semibold text-gray-900">
                          {getProvisionDisplayTitle(provision)}
                        </span>
                      </div>
                      {/* Document Source (if available) */}
                      {docSource && (
                        <div className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                          <span className="font-mono">{docSource}</span>
                        </div>
                      )}
                      {/* Extract precinct/section from document_id if ref_number is descriptive */}
                      {provision.document_id && !/^\d+(\.\d+)*[A-Z]?$/.test(provision.ref_number) && (
                        <div className="text-xs text-blue-600 mt-1">
                          Source: {provision.document_id.replace(/___/g, ' - ').replace(/_/g, ' ')}
                        </div>
                      )}
                    </div>

                    {/* Full Legal Text */}
                    <TruncatedFormattedText
                      text={cleanedText}
                      wordLimit={200}
                      onImageClick={setZoomedImage}
                    />

                    {/* Auto-Expanded Section Content (for short provisions) */}
                    {(() => {
                      const sectionKey = `section_${provision.ref_number}`;
                      const fullDocKey = `full_doc_${provision.document_id}`;
                      const expandedSection = figureContent[sectionKey] || figureContent[fullDocKey];

                      if (expandedSection && provision.provision_text.length < 600) {
                        return (
                          <Card className="mt-3 bg-green-50 border-green-200">
                            <CardContent className="pt-4">
                              <div className="flex justify-between items-start mb-2">
                                <h4 className="font-semibold text-sm text-green-900">
                                  📄 Full Section {provision.ref_number}
                                </h4>
                              </div>
                              <div className="text-sm text-gray-800 prose prose-sm max-w-none bg-white p-4 rounded border">
                                <ReactMarkdown
                                  remarkPlugins={[remarkGfm]}
                                  components={{
                                    img: ({ node, ...props }) => (
                                      <img
                                        {...props}
                                        className="max-w-full h-auto my-4 rounded border shadow-sm"
                                        alt={props.alt || 'Diagram'}
                                      />
                                    ),
                                    h1: ({ node, ...props }) => (
                                      <h1 className="text-lg font-bold mt-4 mb-2" {...props} />
                                    ),
                                    h2: ({ node, ...props }) => (
                                      <h2 className="text-base font-bold mt-3 mb-2" {...props} />
                                    ),
                                    p: ({ node, ...props }) => (
                                      <p className="mb-2 leading-relaxed" {...props} />
                                    ),
                                    ul: ({ node, ...props }) => (
                                      <ul className="list-disc ml-4 mb-2 space-y-1" {...props} />
                                    ),
                                    ol: ({ node, ...props }) => (
                                      <ol className="list-decimal ml-4 mb-2 space-y-1" {...props} />
                                    ),
                                  }}
                                >
                                  {expandedSection.content}
                                </ReactMarkdown>
                              </div>
                              {expandedSection.images.length > 0 && (
                                <div className="mt-2 text-xs text-gray-600 flex items-center gap-1">
                                  <span className="font-medium">📊 {expandedSection.imageCount} diagram(s) included above</span>
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        );
                      }
                      return null;
                    })()}

                    {/* Figure/Diagram References (NEW) */}
                    {detectedFigures.length > 0 && (
                      <div className="mt-4 pt-3 border-t border-gray-100">
                        <div className="text-xs font-semibold text-gray-600 mb-2">Referenced Figures:</div>
                        <div className="flex flex-wrap gap-2">
                          {detectedFigures.map((fig) => (
                            <Button
                              key={fig.sectionRef}
                              size="sm"
                              variant="outline"
                              onClick={() => toggleFigure(fig.sectionRef)}
                              disabled={loadingFigures.has(fig.sectionRef)}
                              className="text-xs"
                            >
                              📊 Figure {fig.sectionRef}
                              {fig.hasImages && ' 🖼️'}
                              {expandedFigures.includes(fig.sectionRef) ? ' ▼' : ' ▶'}
                            </Button>
                          ))}
                        </div>

                        {/* Expanded Figure Content */}
                        {expandedFigures.map(figRef => {
                          const content = figureContent[figRef];
                          if (!content || figRef.startsWith('section_')) return null;

                          return (
                            <Card key={figRef} className="mt-3 bg-blue-50 border-blue-200">
                              <CardContent className="pt-4">
                                <div className="flex justify-between items-start mb-2">
                                  <h4 className="font-semibold text-sm text-blue-900">
                                    📊 Figure {content.sectionRef}
                                    {content.hasImages && ' (includes diagram)'}
                                  </h4>
                                  <Button
                                    size="sm"
                                    variant="ghost"
                                    onClick={() => toggleFigure(figRef)}
                                    className="h-6 w-6 p-0"
                                  >
                                    <X className="h-4 w-4" />
                                  </Button>
                                </div>
                                <div className="text-sm text-gray-700 prose prose-sm max-w-none bg-white p-4 rounded border">
                                  <ReactMarkdown
                                    remarkPlugins={[remarkGfm]}
                                    components={{
                                      img: ({ node, ...props }) => (
                                        <img
                                          {...props}
                                          className="max-w-full h-auto my-4 rounded border shadow-sm"
                                          alt={props.alt || 'Diagram'}
                                        />
                                      ),
                                      h2: ({ node, ...props }) => (
                                        <h2 className="text-base font-semibold mt-2 mb-2" {...props} />
                                      ),
                                      p: ({ node, ...props }) => (
                                        <p className="mb-2 leading-relaxed" {...props} />
                                      ),
                                    }}
                                  >
                                    {content.content}
                                  </ReactMarkdown>
                                </div>
                              </CardContent>
                            </Card>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* Phase 2: Cross-References Section */}
              {selectedProvision.crossReferences && selectedProvision.crossReferences.length > 0 && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h3 className="font-semibold text-sm text-gray-700 mb-3">
                    Cross-References ({selectedProvision.crossReferences.length})
                  </h3>
                  <div className="space-y-2">
                    {selectedProvision.crossReferences.map((ref, idx) => (
                      <div
                        key={idx}
                        className={`text-xs p-2 rounded border ${
                          ref.resolutionStatus === 'resolved'
                            ? 'bg-green-50 border-green-200'
                            : 'bg-gray-50 border-gray-200'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex items-center gap-2">
                            <span className={`font-medium ${ref.isMandatory ? 'text-red-600' : 'text-gray-700'}`}>
                              {ref.referenceType.toUpperCase()} {ref.referenceNumber}
                            </span>
                            {ref.isMandatory && (
                              <Badge className="bg-red-100 text-red-800 text-xs">Mandatory</Badge>
                            )}
                          </div>
                          {ref.resolutionStatus === 'resolved' && ref.targetReference && (
                            <span className="text-green-600 text-xs">→ {ref.targetReference}</span>
                          )}
                        </div>
                        {ref.referenceText && (
                          <div className="text-gray-600 mt-1 italic">"{ref.referenceText}"</div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Phase 2: Control Codes Section */}
              {selectedProvision.controlCodes && selectedProvision.controlCodes.length > 0 && (
                <div className="mt-6 pt-4 border-t border-gray-200">
                  <h3 className="font-semibold text-sm text-gray-700 mb-3">
                    Control Codes ({selectedProvision.controlCodes.length})
                  </h3>
                  <div className="flex flex-wrap gap-2">
                    {selectedProvision.controlCodes.map((code, idx) => (
                      <Badge key={idx} className="bg-blue-100 text-blue-800">
                        {code}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
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
              {/* View Full DCP Document Button (NEW) */}
              {provisions.length > 0 && provisions[0].document_id && (
                <Button
                  variant="outline"
                  size="sm"
                  className="gap-2"
                  onClick={async () => {
                    const docId = provisions[0].document_id;
                    window.open(`/api/documents/${docId}`, '_blank');
                  }}
                >
                  📄 Full Chapter
                </Button>
              )}
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

      {/* Image Zoom Modal */}
      {zoomedImage && (
        <div
          className="fixed inset-0 z-50 bg-black bg-opacity-90 flex items-center justify-center p-4"
          onClick={() => setZoomedImage(null)}
        >
          <div className="relative max-w-7xl max-h-full">
            <button
              onClick={() => setZoomedImage(null)}
              className="absolute -top-10 right-0 text-white hover:text-gray-300 text-xl font-bold"
            >
              <X className="h-8 w-8" />
            </button>
            <img
              src={zoomedImage}
              alt="Zoomed diagram"
              className="max-w-full max-h-[90vh] object-contain rounded"
              onClick={(e) => e.stopPropagation()}
            />
            <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-70 text-white text-sm p-2 text-center">
              Click outside image to close
            </div>
          </div>
        </div>
      )}
    </div>
  );
}