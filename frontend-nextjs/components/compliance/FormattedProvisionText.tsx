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
import { parseProvisionText, FormattedElement, getElementClasses, ParseOptions } from '@/lib/provision-text-formatter';

interface FormattedProvisionTextProps {
  text: string;
  className?: string;
  compact?: boolean; // Reduced spacing for inline display
  stripMarker?: string; // If provided, strip this marker from start of text (e.g., "C9")
  skipHeadings?: boolean; // Skip bold heading detection - useful when under TOC structure
}

export function FormattedProvisionText({
  text,
  className = '',
  compact = false,
  stripMarker,
  skipHeadings = false
}: FormattedProvisionTextProps) {
  // Strip the marker from the beginning of text if it's already shown as a badge
  const processedText = useMemo(() => {
    if (!stripMarker) return text;
    // Pattern: marker at start, possibly with space, followed by content
    const markerPattern = new RegExp(`^\\s*${stripMarker}\\s+`, 'i');
    return text.replace(markerPattern, '');
  }, [text, stripMarker]);

  const elements = useMemo(() => parseProvisionText(processedText, { skipHeadings }), [processedText, skipHeadings]);

  if (!elements || elements.length === 0) {
    return (
      <p className={`text-sm text-gray-700 whitespace-pre-wrap ${className}`}>
        {processedText}
      </p>
    );
  }

  // Group control-marker + control-text pairs for better rendering
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
          <span className={getElementClasses(el)}>
            {marker}
          </span>
          <div className="flex-1 space-y-1">
            {controlTexts.map((ct, idx) => (
              <p key={idx} className={getElementClasses(ct)}>
                {ct.content}
              </p>
            ))}
          </div>
        </div>
      );

      i = j;
      continue;
    }

    // Handle other element types
    switch (el.type) {
      case 'heading':
        renderElements.push(
          <h3 key={`heading-${i}`} className={getElementClasses(el)}>
            {el.content}
          </h3>
        );
        break;

      case 'subheading':
        renderElements.push(
          <h4 key={`subheading-${i}`} className={getElementClasses(el)}>
            {el.content}
          </h4>
        );
        break;

      case 'paragraph':
        renderElements.push(
          <p key={`para-${i}`} className={getElementClasses(el)}>
            {el.content}
          </p>
        );
        break;

      case 'list-item':
        renderElements.push(
          <div key={`list-${i}`} className="flex items-start gap-2 text-sm text-gray-700 leading-relaxed mb-1 ml-2">
            <span className="text-purple-600 font-medium flex-shrink-0 min-w-[24px]">
              {el.marker || '•'}
            </span>
            <span>{el.content}</span>
          </div>
        );
        break;

      case 'figure-ref':
        renderElements.push(
          <p key={`fig-${i}`} className={getElementClasses(el)}>
            {el.content}
          </p>
        );
        break;

      case 'control-text':
        // Orphan control-text (no marker) - render as paragraph
        renderElements.push(
          <p key={`ct-${i}`} className="text-sm text-gray-800 leading-relaxed mb-2 pl-10">
            {el.content}
          </p>
        );
        break;

      case 'note':
        // NB/Note callout - render as bold text on newline
        renderElements.push(
          <p key={`note-${i}`} className={getElementClasses(el)}>
            <span className="font-bold">NB:</span> {el.content}
          </p>
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
export function FormattedProvisionTextInline({ text }: { text: string }) {
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

  return (
    <span className="text-sm text-gray-700">
      {markers.length > 0 && (
        <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-purple-100 text-purple-700 font-bold text-xs mr-2">
          {markers[0].content}
        </span>
      )}
      {mainContent?.content || text.slice(0, 200)}
      {text.length > 200 && '...'}
    </span>
  );
}
