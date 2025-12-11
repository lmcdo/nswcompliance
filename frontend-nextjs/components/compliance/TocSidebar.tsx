'use client';

/**
 * TocSidebar - DCP Table of Contents Navigation
 *
 * Displays collapsible tree of DCP Parts and Sections
 * Allows user to navigate provisions by document structure
 */

import { useState } from 'react';
import { ChevronRight, ChevronDown, FileText, Folder, FolderOpen } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TocSection {
  section_id: string;
  section_title: string;
  provision_count: number;
  provisions: any[];
}

interface TocPart {
  part_id: string;
  part_name: string;
  provision_count: number;
  sections: Record<string, TocSection>;
}

interface TocSidebarProps {
  tocStructure: Record<string, TocPart>;
  selectedPart: string | null;
  selectedSection: string | null;
  onSelectPart: (partId: string) => void;
  onSelectSection: (partId: string, sectionId: string) => void;
  formerCouncil?: string;
}

export function TocSidebar({
  tocStructure,
  selectedPart,
  selectedSection,
  onSelectPart,
  onSelectSection,
  formerCouncil
}: TocSidebarProps) {
  const [expandedParts, setExpandedParts] = useState<Set<string>>(new Set());

  const togglePart = (partId: string) => {
    const newExpanded = new Set(expandedParts);
    if (newExpanded.has(partId)) {
      newExpanded.delete(partId);
    } else {
      newExpanded.add(partId);
    }
    setExpandedParts(newExpanded);
  };

  // Sort parts by a logical order
  const sortedParts = Object.entries(tocStructure).sort((a, b) => {
    const order = getPartOrder(a[0]);
    const orderB = getPartOrder(b[0]);
    return order - orderB;
  });

  if (sortedParts.length === 0) {
    return (
      <div className="p-4 text-sm text-gray-500 italic">
        No provisions found
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-3 border-b bg-gray-50">
        <h3 className="text-base font-bold text-gray-900">
          {formerCouncil ? `${formerCouncil} DCP` : 'DCP'}
        </h3>
        <p className="text-xs text-gray-500 mt-0.5">
          DCP Structure
        </p>
      </div>

      <nav className="p-2">
        {sortedParts.map(([partId, part]) => (
          <PartNode
            key={partId}
            part={part}
            isExpanded={expandedParts.has(partId)}
            isSelected={selectedPart === partId}
            selectedSection={selectedPart === partId ? selectedSection : null}
            onToggle={() => togglePart(partId)}
            onSelectPart={() => onSelectPart(partId)}
            onSelectSection={(sectionId) => onSelectSection(partId, sectionId)}
          />
        ))}
      </nav>
    </div>
  );
}

interface PartNodeProps {
  part: TocPart;
  isExpanded: boolean;
  isSelected: boolean;
  selectedSection: string | null;
  onToggle: () => void;
  onSelectPart: () => void;
  onSelectSection: (sectionId: string) => void;
}

function PartNode({
  part,
  isExpanded,
  isSelected,
  selectedSection,
  onToggle,
  onSelectPart,
  onSelectSection
}: PartNodeProps) {
  const sections = part?.sections || {};
  const sectionCount = Object.keys(sections).length;
  const hasMultipleSections = sectionCount > 1;

  return (
    <div className="mb-1">
      {/* Part header */}
      <div
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer transition-colors",
          "hover:bg-teal-50",
          isSelected && !selectedSection && "bg-teal-100 text-teal-900"
        )}
        onClick={() => {
          if (hasMultipleSections) {
            onToggle();
          }
          onSelectPart();
        }}
      >
        {/* Expand/collapse icon */}
        {hasMultipleSections ? (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onToggle();
            }}
            className="p-0.5 hover:bg-teal-200 rounded"
          >
            {isExpanded ? (
              <ChevronDown className="h-3.5 w-3.5 text-gray-500" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5 text-gray-500" />
            )}
          </button>
        ) : (
          <span className="w-4" />
        )}

        {/* Folder icon */}
        {isExpanded ? (
          <FolderOpen className="h-4 w-4 text-teal-600 flex-shrink-0" />
        ) : (
          <Folder className="h-4 w-4 text-teal-600 flex-shrink-0" />
        )}

        {/* Part name */}
        <span className="text-sm font-medium text-gray-800 truncate flex-1">
          {formatPartDisplay(part.part_id)}
        </span>

        {/* Count badge */}
        <span className="text-xs text-gray-500 bg-gray-100 px-1.5 py-0.5 rounded">
          {part.provision_count}
        </span>
      </div>

      {/* Sections (if expanded) */}
      {isExpanded && hasMultipleSections && (
        <div className="ml-4 mt-0.5 border-l border-gray-200 pl-2">
          {Object.entries(sections).map(([sectionId, section]) => (
            <SectionNode
              key={sectionId}
              section={section}
              isSelected={selectedSection === sectionId}
              onClick={() => onSelectSection(sectionId)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface SectionNodeProps {
  section: TocSection;
  isSelected: boolean;
  onClick: () => void;
}

function SectionNode({ section, isSelected, onClick }: SectionNodeProps) {
  const display = formatSectionDisplay(section.section_id, section.section_title);

  return (
    <div
      className={cn(
        "flex items-center gap-2 px-2 py-1 rounded cursor-pointer transition-colors",
        "hover:bg-teal-50",
        isSelected && "bg-teal-100 text-teal-900"
      )}
      onClick={onClick}
    >
      <FileText className="h-3.5 w-3.5 text-gray-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <span className="text-xs font-medium text-gray-700 block truncate">
          {display.primary}
        </span>
        {display.secondary && (
          <span className="text-[10px] text-gray-500 block truncate">
            {display.secondary}
          </span>
        )}
      </div>
      <span className="text-xs text-gray-400 flex-shrink-0">
        {section.provision_count}
      </span>
    </div>
  );
}

/**
 * Get sort order for parts
 */
function getPartOrder(partId: string): number {
  const orderMap: Record<string, number> = {
    // Marrickville
    'Part 1': 1,
    'Part 2': 2,
    'Part 3': 3,
    'Part 4': 4,
    'Part 4.1': 4.1,
    'Part 4.2': 4.2,
    'Part 5': 5,
    'Part 6': 6,
    'Part 7': 7,
    'Part 8': 8,
    'Part 9': 9,
    // Leichhardt
    'Part A': 10,
    'Part B': 11,
    'Part C': 12,
    'Part C Section 1': 12.1,
    'Part C Section 2': 12.2,
    'Part C Section 3': 12.3,
    'Part D': 13,
    'Part E': 14,
    'Part F': 15,
    'Part G': 16,
    // Ashfield
    'Chapter A': 20,
    'Chapter B': 21,
    'Chapter C': 22,
    'Chapter D': 23,
    'Chapter E1': 24,
    'Chapter F': 25,
    'Chapter F Part 1': 25.1,
    'Chapter F Part 5': 25.5,
    'Chapter F Part 7': 25.7,
    // Fallback
    'Other': 99,
    'unknown': 100,
  };

  return orderMap[partId] ?? 50;
}

/**
 * Format part ID for display (shorter version for sidebar)
 */
function formatPartDisplay(partId: string): string {
  if (!partId) return 'Other';

  // Already short enough
  if (partId.length < 20) return partId;

  // Shorten common patterns
  const shortMap: Record<string, string> = {
    'Part C Section 1': 'Part C.1',
    'Part C Section 2': 'Part C.2',
    'Part C Section 3': 'Part C.3',
    'Chapter F Part 1': 'Ch F.1',
    'Chapter F Part 5': 'Ch F.5',
    'Chapter F Part 7': 'Ch F.7',
  };

  return shortMap[partId] || partId;
}

/**
 * Fix common UTF-8 encoding artifacts (mojibake)
 */
function sanitizeText(text: string): string {
  if (!text) return text;
  return text
    // Em-dash variations
    .replace(/â€"/g, '—')
    .replace(/\u00e2\u20ac\u201c/g, '—')
    .replace(/\u00e2\u0080\u0094/g, '—')
    // Quotes
    .replace(/â€˜/g, "'")
    .replace(/â€™/g, "'")
    .replace(/â€œ/g, '"')
    .replace(/â€\u009D/g, '"')
    .replace(/\u00e2\u20ac\u0153/g, '"')
    .replace(/\u00e2\u20ac\u009d/g, '"')
    // Other
    .replace(/â€¢/g, '•')
    .replace(/â€¦/g, '…')
    .replace(/Ã©/g, 'é')
    .replace(/Ã¨/g, 'è')
    // Clean up any remaining garbage at start
    .replace(/^[â€"\s]+/, '')
    .trim();
}

/**
 * Format section for display - returns object for flexible rendering
 */
function formatSectionDisplay(sectionId: string, sectionTitle: string): { primary: string; secondary?: string } {
  const cleanTitle = sanitizeText(sectionTitle);

  // For C markers (Leichhardt), show "Control N" as primary
  if (sectionId.startsWith('C') && sectionId.match(/^C\d+$/)) {
    const num = sectionId.slice(1);
    const stripped = cleanTitle.replace(/^Control\s*/i, '').replace(/^C\d+\s*/, '');

    // If there's meaningful title text beyond just the marker
    if (stripped && stripped !== sectionId && !stripped.match(/^C\d+$/) && stripped.length > 2) {
      return {
        primary: `Ctrl ${num}`,
        secondary: stripped.length > 20 ? stripped.slice(0, 20) + '…' : stripped
      };
    }
    return { primary: `Control ${num}` };
  }

  // For numeric sections, show number + title
  if (sectionId.match(/^\d/)) {
    const shortTitle = cleanTitle.length > 22
      ? cleanTitle.slice(0, 22) + '…'
      : cleanTitle;
    return { primary: shortTitle || sectionId };
  }

  // Default: just the title (truncated)
  const display = cleanTitle.length > 25
    ? cleanTitle.slice(0, 25) + '…'
    : cleanTitle;
  return { primary: display || sectionId };
}
