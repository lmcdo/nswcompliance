'use client';

/**
 * Formatted Provision Text Component
 * Renders parsed provision text with proper structure:
 * - Headings and subheadings
 * - Control markers (C1, C2, O1, etc.)
 * - Paragraphs and lists
 * - Figure references
 */

import React, { useMemo } from 'react';
import { parseProvisionText, FormattedElement, getElementClasses, ParseOptions, ProvisionTheme, hasInterleavedMapText, isMapScrambledLine } from '@/lib/provision-text-formatter';
import { preProcessProvisionText } from '@/lib/dcp-format-configs';
import { hasProvisionTable, splitProvisionTables, provisionTablesToPlainText, ProvisionTable } from '@/lib/provision-tables';

interface FormattedProvisionTextProps {
  text: string;
  className?: string;
  compact?: boolean; // Reduced spacing for inline display
  stripMarker?: string; // If provided, strip this marker from start of text (e.g., "C9")
  skipHeadings?: boolean; // Skip bold heading detection - useful when under TOC structure
  highlightQuery?: string; // Search query to highlight in the text
  theme?: ProvisionTheme; // Color theme: 'purple' (SEPP), 'green' (DCP), 'amber' (LEP)
  councilKey?: string; // formerCouncil.toLowerCase() — enables council-specific artifact cleanup
  sourceUrl?: string; // Council PDF this provision was read from — shown when text is figure-scrambled
  sourcePage?: number; // Page within that PDF
}

/**
 * DQ-78 notice. Shown above a provision whose text carries street labels lifted off a map
 * figure and interleaved into the prose. The row is still rendered in full: the ledger
 * measured that rows near the detection cut contain binding controls alongside the
 * scramble, so the reader is told what happened rather than shown less.
 *
 * Wording is factual and makes no claim about the rest of the text being right: it says
 * where the characters came from and points at the council's own document.
 */
function MapTextNotice({ sourceUrl, sourcePage }: { sourceUrl?: string; sourcePage?: number }) {
  return (
    <div
      role="note"
      data-testid="map-text-notice"
      className="mb-2 rounded border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-900"
    >
      <span className="font-medium">Some characters below came off a map image.</span>{' '}
      The council&apos;s PDF puts street labels inside the figure on this page, and the
      extractor read them into the text. Words that run together as single letters are
      those labels, not controls. Read this page in the council&apos;s document
      {sourceUrl ? (
        <>
          :{' '}
          <a
            href={sourceUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:no-underline"
          >
            open the source PDF{typeof sourcePage === 'number' ? ` (page ${sourcePage})` : ''}
          </a>
          .
        </>
      ) : (
        '.'
      )}
    </div>
  );
}

/**
 * Helper function to highlight matching text
 */
function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;

  const parts = text.split(new RegExp(`(${query})`, 'gi'));
  return parts.map((part, i) =>
    part.toLowerCase() === query.toLowerCase() ? (
      <mark key={i} className="bg-yellow-200 font-normal">
        {part}
      </mark>
    ) : (
      part
    )
  );
}

function FormattedProvisionTextBody({
  text,
  className = '',
  compact = false,
  stripMarker,
  skipHeadings = false,
  highlightQuery,
  theme = 'purple',
  councilKey,
  sourceUrl,
  sourcePage
}: FormattedProvisionTextProps) {
  // Apply council-specific artifact cleanup, then strip the control marker if shown as badge
  const processedText = useMemo(() => {
    let result = councilKey ? preProcessProvisionText(text, councilKey) : text;
    if (!stripMarker) return result;
    // Pattern: marker at start, possibly with space, followed by content
    const markerPattern = new RegExp(`^\\s*${stripMarker}\\s+`, 'i');
    return result.replace(markerPattern, '');
  }, [text, stripMarker, councilKey]);

  const elements = useMemo(() => parseProvisionText(processedText, { skipHeadings }), [processedText, skipHeadings]);

  // DQ-78: street labels lifted off a map figure and interleaved through the prose.
  const figureText = useMemo(() => hasInterleavedMapText(processedText), [processedText]);

  // Helper to apply highlighting to content
  const applyHighlight = (content: string): React.ReactNode => {
    const highlighted = highlightQuery ? highlightText(content, highlightQuery) : content;
    // A line that is itself figure text is dimmed and labelled where it sits, so the
    // control beside it keeps its normal weight. Nothing is removed: the characters stay
    // selectable and copyable, because a planner checking the PDF needs to find them.
    if (figureText && isMapScrambledLine(content)) {
      return (
        <span
          data-testid="map-scrambled-line"
          title="Read off a map image in the source PDF"
          className="text-gray-400 italic"
        >
          {highlighted}
        </span>
      );
    }
    return highlighted;
  };

  if (!elements || elements.length === 0) {
    return (
      <div className={className}>
        {figureText && <MapTextNotice sourceUrl={sourceUrl} sourcePage={sourcePage} />}
        <p className="text-sm text-gray-700 whitespace-pre-wrap">
          {applyHighlight(processedText)}
        </p>
      </div>
    );
  }

  // Group control-marker + control-text pairs, and consecutive list items
  const renderElements: React.ReactNode[] = [];
  let i = 0;

  while (i < elements.length) {
    const el = elements[i];

    // Handle control marker + text grouping
    if (el.type === 'control-marker') {
      const marker = el.content;
      const controlTexts: FormattedElement[] = [];

      // Collect all following control-text elements with same marker
      let j = i + 1;
      while (j < elements.length && elements[j].type === 'control-text' && elements[j].marker === marker) {
        controlTexts.push(elements[j]);
        j++;
      }

      renderElements.push(
        <div key={`control-${i}`} className={`flex items-start gap-2 ${compact ? 'mb-2' : 'mb-3'}`}>
          <span className={getElementClasses(el, theme)}>
            {marker}
          </span>
          <div className="flex-1 space-y-1">
            {controlTexts.map((ct, idx) => (
              <p key={idx} className={getElementClasses(ct, theme)}>
                {applyHighlight(ct.content)}
              </p>
            ))}
          </div>
        </div>
      );

      i = j;
      continue;
    }

    // Handle list item grouping - group consecutive list items into proper lists
    if (el.type === 'list-item') {
      const listItems: FormattedElement[] = [];
      let listType: 'numbered' | 'roman' | 'alpha' | 'unordered' = 'unordered';

      // Determine list type from first marker
      if (el.marker?.match(/^\d+\./)) {
        listType = 'numbered';
      } else if (el.marker?.match(/^[ivxIVX]+\./)) {
        listType = 'roman';
      } else if (el.marker?.match(/^[a-zA-Z]\./)) {
        listType = 'alpha';
      } else if (el.marker?.match(/^\([a-z]\)/)) {
        listType = 'alpha'; // Parenthesized letters like (a), (b)
      }

      // Collect all consecutive list items
      while (i < elements.length && elements[i].type === 'list-item') {
        listItems.push(elements[i]);
        i++;
      }

      // Render as proper HTML list based on type
      if (listType === 'numbered') {
        renderElements.push(
          <ol key={`list-${i}`} className={`list-decimal list-inside ml-4 space-y-1 ${compact ? 'my-1' : 'my-2'}`}>
            {listItems.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-700 leading-relaxed">
                {applyHighlight(item.content)}
              </li>
            ))}
          </ol>
        );
      } else if (listType === 'roman') {
        renderElements.push(
          <ol key={`list-${i}`} className={`list-inside ml-4 space-y-1 ${compact ? 'my-1' : 'my-2'}`} style={{ listStyleType: 'lower-roman' }}>
            {listItems.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-700 leading-relaxed">
                {applyHighlight(item.content)}
              </li>
            ))}
          </ol>
        );
      } else if (listType === 'alpha') {
        renderElements.push(
          <ol key={`list-${i}`} className={`list-inside ml-4 space-y-1 ${compact ? 'my-1' : 'my-2'}`} style={{ listStyleType: 'lower-alpha' }}>
            {listItems.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-700 leading-relaxed">
                {applyHighlight(item.content)}
              </li>
            ))}
          </ol>
        );
      } else {
        // Unordered list
        renderElements.push(
          <ul key={`list-${i}`} className={`list-disc list-inside ml-4 space-y-1 ${compact ? 'my-1' : 'my-2'}`}>
            {listItems.map((item, idx) => (
              <li key={idx} className="text-sm text-gray-700 leading-relaxed">
                {applyHighlight(item.content)}
              </li>
            ))}
          </ul>
        );
      }

      continue;
    }

    // Handle other element types
    switch (el.type) {
      case 'heading':
        renderElements.push(
          <h3 key={`heading-${i}`} className={getElementClasses(el, theme)}>
            {applyHighlight(el.content)}
          </h3>
        );
        break;

      case 'subheading':
        renderElements.push(
          <h4 key={`subheading-${i}`} className={getElementClasses(el, theme)}>
            {applyHighlight(el.content)}
          </h4>
        );
        break;

      case 'paragraph':
        renderElements.push(
          <p key={`para-${i}`} className={getElementClasses(el, theme)}>
            {applyHighlight(el.content)}
          </p>
        );
        break;

      case 'figure-ref':
        renderElements.push(
          <p key={`fig-${i}`} className={getElementClasses(el, theme)}>
            {applyHighlight(el.content)}
          </p>
        );
        break;

      case 'control-text':
        // Orphan control-text (no marker) - render as paragraph
        renderElements.push(
          <p key={`ct-${i}`} className="text-sm text-gray-800 leading-relaxed mb-2 pl-10">
            {applyHighlight(el.content)}
          </p>
        );
        break;

      case 'note':
        // NB/Note callout - render as bold label with normal text content
        renderElements.push(
          <div key={`note-${i}`} className={getElementClasses(el, theme)}>
            <span className="font-bold">NB:</span> {applyHighlight(el.content)}
          </div>
        );
        break;

      default:
        renderElements.push(
          <p key={`default-${i}`} className="text-sm text-gray-700">
            {el.content}
          </p>
        );
    }

    i++;
  }

  return (
    <div className={`space-y-1 ${className}`}>
      {figureText && <MapTextNotice sourceUrl={sourceUrl} sourcePage={sourcePage} />}
      {renderElements}
    </div>
  );
}

/**
 * Simple inline variant for compact displays
 */
/**
 * DQ-125: a provision can carry the extractor's HTML tables. They are parsed into rows and cells and
 * shown as a table (never injected as HTML); the prose around them renders as before.
 */
function ProvisionTableView({ table }: { table: ProvisionTable }) {
  return (
    <div className="my-3 overflow-x-auto" data-testid="provision-table">
      <table className="min-w-full text-sm text-gray-700 border border-gray-200">
        {table.head.length > 0 && (
          <thead className="bg-gray-50">
            {table.head.map((row, r) => (
              <tr key={r}>
                {row.map((cell, c) => (
                  <th key={c} scope="col" className="px-2 py-1 text-left font-medium border-b border-gray-200">
                    {cell}
                  </th>
                ))}
              </tr>
            ))}
          </thead>
        )}
        <tbody>
          {table.body.map((row, r) => (
            <tr key={r} className="border-t border-gray-100">
              {row.map((cell, c) => (
                <td key={c} className="px-2 py-1 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function FormattedProvisionText(props: FormattedProvisionTextProps) {
  const segments = useMemo(
    () => (hasProvisionTable(props.text) ? splitProvisionTables(props.text) : null),
    [props.text]
  );
  if (!segments) return <FormattedProvisionTextBody {...props} />;
  return (
    <div className={props.className}>
      {segments.map((seg, idx) =>
        seg.kind === 'table' ? (
          <ProvisionTableView key={idx} table={seg.table} />
        ) : (
          <FormattedProvisionTextBody
            key={idx}
            {...props}
            className=""
            text={seg.text}
            stripMarker={idx === 0 ? props.stripMarker : undefined}
          />
        )
      )}
    </div>
  );
}

export function FormattedProvisionTextInline({ text: rawText, theme = 'purple' }: { text: string; theme?: ProvisionTheme }) {
  // DQ-125: an inline preview prints text only, so any table is written as plain rows.
  const text = useMemo(() => provisionTablesToPlainText(rawText), [rawText]);
  // Always skip headings for inline display - provision text shouldn't have bold headings
  const elements = useMemo(() => parseProvisionText(text, { skipHeadings: true }), [text]);

  if (!elements || elements.length === 0) {
    return <span className="text-sm text-gray-700">{text}</span>;
  }

  // Find first control text or paragraph
  const mainContent = elements.find(
    el => el.type === 'control-text' || el.type === 'paragraph'
  );

  const markers = elements.filter(el => el.type === 'control-marker');

  // Theme-specific colors for inline badges
  const themeColors = {
    purple: 'bg-purple-100 text-purple-700',
    green: 'bg-green-100 text-green-700',
    amber: 'bg-amber-100 text-amber-700'
  };

  return (
    <span className="text-sm text-gray-700">
      {markers.length > 0 && (
        <span className={`inline-flex items-center justify-center w-6 h-6 rounded-full ${themeColors[theme]} font-bold text-xs mr-2`}>
          {markers[0].content}
        </span>
      )}
      {mainContent?.content || text.slice(0, 200)}
      {text.length > 200 && '...'}
    </span>
  );
}
