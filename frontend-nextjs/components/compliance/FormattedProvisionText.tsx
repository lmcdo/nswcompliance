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
import { parseProvisionText, FormattedElement, getElementClasses, ParseOptions, ProvisionTheme } from '@/lib/provision-text-formatter';
import { preProcessProvisionText } from '@/lib/dcp-format-configs';

interface FormattedProvisionTextProps {
  text: string;
  className?: string;
  compact?: boolean; // Reduced spacing for inline display
  stripMarker?: string; // If provided, strip this marker from start of text (e.g., "C9")
  skipHeadings?: boolean; // Skip bold heading detection - useful when under TOC structure
  highlightQuery?: string; // Search query to highlight in the text
  theme?: ProvisionTheme; // Color theme: 'purple' (SEPP), 'green' (DCP), 'amber' (LEP)
  councilKey?: string; // formerCouncil.toLowerCase() — enables council-specific artifact cleanup
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

export function FormattedProvisionText({
  text,
  className = '',
  compact = false,
  stripMarker,
  skipHeadings = false,
  highlightQuery,
  theme = 'purple',
  councilKey
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

  // Helper to apply highlighting to content
  const applyHighlight = (content: string): React.ReactNode => {
    return highlightQuery ? highlightText(content, highlightQuery) : content;
  };

  if (!elements || elements.length === 0) {
    return (
      <p className={`text-sm text-gray-700 whitespace-pre-wrap ${className}`}>
        {applyHighlight(processedText)}
      </p>
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
      {renderElements}
    </div>
  );
}

/**
 * Simple inline variant for compact displays
 */
export function FormattedProvisionTextInline({ text, theme = 'purple' }: { text: string; theme?: ProvisionTheme }) {
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
