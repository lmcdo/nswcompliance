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
  filteredTocStructure: Record<string, TocPart>;
  selectedPart: string | null;
  selectedSection: string | null;
  onSelectPart: (partId: string) => void;
  onSelectSection: (partId: string, sectionId: string) => void;
  formerCouncil?: string;
}

export function TocSidebar({
  tocStructure,
  filteredTocStructure,
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
        {sortedParts.map(([partId, part]) => {
          const filteredPart = filteredTocStructure[partId];
          const hasProvisions = !!filteredPart && filteredPart.provision_count > 0;

          return (
            <PartNode
              key={partId}
              part={part}
              filteredPart={filteredPart}
              hasProvisions={hasProvisions}
              isExpanded={expandedParts.has(partId)}
              isSelected={selectedPart === partId}
              selectedSection={selectedPart === partId ? selectedSection : null}
              onToggle={() => togglePart(partId)}
              onSelectPart={() => onSelectPart(partId)}
              onSelectSection={(sectionId) => onSelectSection(partId, sectionId)}
            />
          );
        })}
      </nav>
    </div>
  );
}

interface PartNodeProps {
  part: TocPart;
  filteredPart?: TocPart;
  hasProvisions: boolean;
  isExpanded: boolean;
  isSelected: boolean;
  selectedSection: string | null;
  onToggle: () => void;
  onSelectPart: () => void;
  onSelectSection: (sectionId: string) => void;
}

function PartNode({
  part,
  filteredPart,
  hasProvisions,
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
          hasProvisions ? "hover:bg-teal-50" : "hover:bg-gray-100 opacity-50",
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
              <ChevronDown className={cn("h-3 w-3", hasProvisions ? "text-gray-500" : "text-gray-400")} />
            ) : (
              <ChevronRight className={cn("h-3 w-3", hasProvisions ? "text-gray-500" : "text-gray-400")} />
            )}
          </button>
        ) : (
          <span className="w-4" />
        )}

        {/* Folder icon */}
        {isExpanded ? (
          <FolderOpen className={cn("h-3.5 w-3.5 flex-shrink-0", hasProvisions ? "text-teal-600" : "text-gray-400")} />
        ) : (
          <Folder className={cn("h-3.5 w-3.5 flex-shrink-0", hasProvisions ? "text-teal-600" : "text-gray-400")} />
        )}

        {/* Part name with description */}
        <div className="flex-1 min-w-0">
          {(() => {
            const { label, desc } = formatPartDisplay(part.part_id);
            return (
              <div>
                <span className={cn("text-sm font-medium", hasProvisions ? "text-gray-800" : "text-gray-400")}>
                  {label}
                </span>
                {desc && (
                  <span className={cn("text-xs block", hasProvisions ? "text-gray-500" : "text-gray-400")}>
                    {desc}
                  </span>
                )}
              </div>
            );
          })()}
        </div>

        {/* Count badge - show filtered count if available, otherwise show 0 */}
        {hasProvisions ? (
          <span className="text-xs text-gray-700 bg-gray-200 px-1.5 py-0.5 rounded font-medium">
            {filteredPart?.provision_count || 0}
          </span>
        ) : (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            0
          </span>
        )}
      </div>

      {/* Sections (if expanded) */}
      {isExpanded && hasMultipleSections && (
        <div className="mt-0.5">
          {Object.entries(sections).map(([sectionId, section]) => {
            const filteredSection = filteredPart?.sections?.[sectionId];
            const sectionHasProvisions = !!filteredSection && filteredSection.provision_count > 0;

            return (
              <SectionNode
                key={sectionId}
                section={section}
                filteredSection={filteredSection}
                hasProvisions={sectionHasProvisions}
                isSelected={selectedSection === sectionId}
                onClick={() => onSelectSection(sectionId)}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}

interface SectionNodeProps {
  section: TocSection;
  filteredSection?: TocSection;
  hasProvisions: boolean;
  isSelected: boolean;
  onClick: () => void;
}

function SectionNode({ section, filteredSection, hasProvisions, isSelected, onClick }: SectionNodeProps) {
  const display = formatSectionDisplay(section.section_id, section.section_title);

  return (
    <div
      className={cn(
        "flex items-start justify-between px-2 py-1 rounded cursor-pointer transition-colors",
        hasProvisions ? "hover:bg-teal-50" : "hover:bg-gray-100 opacity-50",
        isSelected && "bg-teal-100 text-teal-900"
      )}
      onClick={onClick}
    >
      <span className={cn("text-xs break-words pr-2", hasProvisions ? "text-gray-700" : "text-gray-400")}>
        {display.primary}
        {display.secondary && (
          <span className={cn("ml-1", hasProvisions ? "text-gray-500" : "text-gray-400")}>{display.secondary}</span>
        )}
      </span>
      {hasProvisions ? (
        <span className="text-xs text-gray-700 flex-shrink-0 font-medium">
          {filteredSection?.provision_count || 0}
        </span>
      ) : (
        <span className="text-xs text-gray-400 flex-shrink-0">
          0
        </span>
      )}
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
 * Part descriptions for councils (concise labels for sidebar)
 */
const PART_DESCRIPTIONS: Record<string, Record<string, string>> = {
  // Marrickville DCP - All Parts
  'Part 1': { label: 'Part 1', desc: 'Introduction' },
  'Part 2': { label: 'Part 2', desc: 'Site Planning' },
  'Part 3': { label: 'Part 3', desc: 'Land Use & Activity' },
  'Part 4': { label: 'Part 4', desc: 'Residential Development' },
  'Part 4.1': { label: 'Part 4.1', desc: 'Dwelling Houses' },
  'Part 4.2': { label: 'Part 4.2', desc: 'Dual Occupancy' },
  'Part 5': { label: 'Part 5', desc: 'Residential Flat Buildings' },
  'Part 6': { label: 'Part 6', desc: 'Mixed Use & Commercial' },
  'Part 7': { label: 'Part 7', desc: 'Industrial Development' },
  'Part 8': { label: 'Part 8', desc: 'Heritage' },
  'Part 9': { label: 'Part 9', desc: 'Precinct Character' },
  // Leichhardt
  'Part C Section 1': { label: 'Part C.1', desc: 'General Controls' },
  'Part C Section 2': { label: 'Part C.2', desc: 'Neighbourhood Controls' },
  'Part D': { label: 'Part D', desc: 'Energy & Waste' },
  'Part E': { label: 'Part E', desc: 'Water Management' },
  'Part F': { label: 'Part F', desc: 'Food & Environment' },
  'Part G': { label: 'Part G', desc: 'Site-Specific Controls' },
  'Part G Section 1': { label: 'Part G.1', desc: 'Norton St Precinct' },
  // Ashfield
  'Chapter A': { label: 'Chapter A', desc: 'General Controls' },
  'Chapter C': { label: 'Chapter C', desc: 'Residential' },
  'Chapter D': { label: 'Chapter D', desc: 'Village Precincts' },
  'Chapter E1': { label: 'Chapter E1', desc: 'Heritage' },
  'Chapter F': { label: 'Chapter F', desc: 'Dev Categories' },
  'Chapter F Part 1': { label: 'Ch F.1', desc: 'Dual Occ & Multi' },
  'Chapter F Part 5': { label: 'Ch F.5', desc: 'Residential Flat' },
  'Chapter F Part 7': { label: 'Ch F.7', desc: 'Other Uses' },
};

/**
 * Format part ID for display (shorter version for sidebar)
 * Returns { label, desc } for two-line display
 */
function formatPartDisplay(partId: string): { label: string; desc?: string } {
  if (!partId) return { label: 'Other' };

  // Handle "unknown" gracefully
  if (partId === 'unknown' || partId === 'Unknown') {
    return { label: 'General', desc: 'Miscellaneous Provisions' };
  }

  // Check for known part with description
  if (PART_DESCRIPTIONS[partId]) {
    return PART_DESCRIPTIONS[partId];
  }

  // Shorten common patterns (legacy)
  const shortMap: Record<string, string> = {
    'Part C Section 1': 'Part C.1',
    'Part C Section 2': 'Part C.2',
    'Part C Section 3': 'Part C.3',
    'Chapter F Part 1': 'Ch F.1',
    'Chapter F Part 5': 'Ch F.5',
    'Chapter F Part 7': 'Ch F.7',
  };

  return { label: shortMap[partId] || partId };
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
 * No truncation - let CSS handle text wrapping
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
        secondary: stripped
      };
    }
    return { primary: `Control ${num}` };
  }

  // For numeric sections, show number + title (full text, wrap if needed)
  if (sectionId.match(/^\d/)) {
    return { primary: cleanTitle || sectionId };
  }

  // Default: just the title (full text, wrap if needed)
  return { primary: cleanTitle || sectionId };
}
