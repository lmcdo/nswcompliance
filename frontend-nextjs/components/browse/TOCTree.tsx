'use client';

/**
 * TOC Tree Component
 * Hierarchical display of table of contents with provision counts
 */

import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Loader2, FileText } from 'lucide-react';

interface TOCSection {
  sectionNumber: string;
  sectionTitle: string;
  pageStart: number;
  pageEnd: number | null;
  partNumber: number;
  depth: number;
  parentSection: string | null;
  provisionCount: number;
  documentId: string;
}

interface TOCTreeProps {
  documentId: string;
  onSectionSelect: (section: { sectionNumber: string; sectionTitle: string }) => void;
  selectedSection: { sectionNumber: string; sectionTitle: string } | null;
}

export function TOCTree({ documentId, onSectionSelect, selectedSection }: TOCTreeProps) {
  const [sections, setSections] = useState<TOCSection[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [collapsedSections, setCollapsedSections] = useState<Set<string>>(new Set());

  useEffect(() => {
    fetchTOC();
  }, [documentId]);

  const fetchTOC = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/api/browse/toc', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ documentId }),
      });

      const data = await response.json();

      if (data.success) {
        setSections(data.data.sections);
      } else {
        setError(data.details || 'Failed to load table of contents');
      }
    } catch (err) {
      setError('Network error: Failed to fetch TOC');
    } finally {
      setLoading(false);
    }
  };

  const toggleCollapse = (sectionNumber: string) => {
    const newCollapsed = new Set(collapsedSections);
    if (newCollapsed.has(sectionNumber)) {
      newCollapsed.delete(sectionNumber);
    } else {
      newCollapsed.add(sectionNumber);
    }
    setCollapsedSections(newCollapsed);
  };

  const getChildren = (parentNumber: string) => {
    return sections.filter(s => s.parentSection === parentNumber);
  };

  const hasChildren = (sectionNumber: string) => {
    return sections.some(s => s.parentSection === sectionNumber);
  };

  const isCollapsed = (sectionNumber: string) => {
    return collapsedSections.has(sectionNumber);
  };

  const renderSection = (section: TOCSection) => {
    const isSelected = selectedSection?.sectionNumber === section.sectionNumber;
    const hasChildSections = hasChildren(section.sectionNumber);
    const isCollapsedSection = isCollapsed(section.sectionNumber);
    const indentLevel = section.depth - 2; // depth 2 = no indent, depth 3 = 1 level, etc.

    return (
      <div key={section.sectionNumber}>
        {/* Section Button */}
        <div
          className={`flex items-start gap-2 px-3 py-2 hover:bg-gray-50 cursor-pointer transition-colors ${
            isSelected ? 'bg-blue-50 border-l-4 border-blue-500' : 'border-l-4 border-transparent'
          }`}
          style={{ paddingLeft: `${indentLevel * 16 + 12}px` }}
          onClick={() => onSectionSelect({ sectionNumber: section.sectionNumber, sectionTitle: section.sectionTitle })}
        >
          {/* Collapse Toggle */}
          {hasChildSections && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleCollapse(section.sectionNumber);
              }}
              className="flex-shrink-0 p-0.5 hover:bg-gray-200 rounded transition-colors"
            >
              {isCollapsedSection ? (
                <ChevronRight size={14} className="text-gray-500" />
              ) : (
                <ChevronDown size={14} className="text-gray-500" />
              )}
            </button>
          )}

          {/* Section Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-baseline gap-2">
              <span className={`font-medium ${isSelected ? 'text-blue-700' : 'text-gray-900'} whitespace-nowrap`}>
                {section.sectionNumber}
              </span>
              <span className={`text-sm ${isSelected ? 'text-blue-600' : 'text-gray-700'} truncate`}>
                {section.sectionTitle}
              </span>
            </div>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-xs text-gray-500">
                {section.provisionCount} provision{section.provisionCount !== 1 ? 's' : ''}
              </span>
              {section.pageEnd && (
                <span className="text-xs text-gray-400">
                  • pp. {section.pageStart}-{section.pageEnd}
                </span>
              )}
            </div>
          </div>
        </div>

        {/* Children */}
        {hasChildSections && !isCollapsedSection && (
          <div>
            {getChildren(section.sectionNumber).map(child => renderSection(child))}
          </div>
        )}
      </div>
    );
  };

  // Get root sections (those without parents or depth 2)
  const rootSections = sections.filter(s => !s.parentSection || s.depth === 2);

  if (loading) {
    return (
      <div className="p-8 flex flex-col items-center justify-center">
        <Loader2 size={32} className="text-blue-500 animate-spin mb-3" />
        <p className="text-sm text-gray-600">Loading table of contents...</p>
      </div>
    );
  }

  if (error) {
    // Check if it's a "not found" error (document has no TOC)
    const isNoTOC = error.includes('No TOC found') || error.includes('not found');

    if (isNoTOC) {
      return (
        <div className="p-6 text-center">
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <FileText size={32} className="mx-auto text-amber-400 mb-3" />
            <h4 className="font-medium text-amber-800 mb-2">No Table of Contents</h4>
            <p className="text-sm text-amber-700 mb-3">
              This document doesn't have an extracted TOC, but you can still browse all provisions.
            </p>
            <p className="text-xs text-amber-600">
              All provisions from this section will be displayed without subsection navigation.
            </p>
          </div>
        </div>
      );
    }

    // Network or other error
    return (
      <div className="p-6 text-center">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <p className="text-sm text-red-700">{error}</p>
          <button
            onClick={fetchTOC}
            className="mt-3 text-xs text-red-600 hover:text-red-800 underline"
          >
            Try again
          </button>
        </div>
      </div>
    );
  }

  if (sections.length === 0) {
    return (
      <div className="p-8 text-center">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
          <FileText size={32} className="mx-auto text-amber-400 mb-3" />
          <h4 className="font-medium text-amber-800 mb-2">No Table of Contents</h4>
          <p className="text-sm text-amber-700">
            This document doesn't have an extracted TOC structure.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-y-auto max-h-[calc(100vh-250px)]">
      <div className="py-2">
        {rootSections.map(section => renderSection(section))}
      </div>

      {/* Footer */}
      <div className="border-t p-3 bg-gray-50 text-center">
        <p className="text-xs text-gray-500">
          {sections.length} section{sections.length !== 1 ? 's' : ''} •{' '}
          {sections.reduce((sum, s) => sum + s.provisionCount, 0)} total provisions
        </p>
      </div>
    </div>
  );
}
