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

const CHAPTER_PRESET_REASONS = (desc: string) => [
  `${desc || 'These'} provisions not applicable — works not proposed`,
  'Development type does not trigger these controls',
  'Site characteristic absent — confirmed per LEP mapping',
];

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
  dev_type_match_count?: number;
  sections: Record<string, TocSection>;
}

interface TocSidebarProps {
  tocStructure: Record<string, TocPart>;
  filteredTocStructure: Record<string, TocPart>;
  /** Per-part provision counts after filterAndDedupeProvisions — matches right panel display count */
  filteredPartCounts?: Record<string, number>;
  selectedPart: string | null;
  selectedSection: string | null;
  onSelectPart: (partId: string) => void;
  onSelectSection: (partId: string, sectionId: string) => void;
  formerCouncil?: string;
  /** DA mode — enables chapter dismiss buttons */
  isDaMode?: boolean;
  chapterAssertions?: Record<string, string>;
  /** Chapters auto-dismissed because they have zero provisions for the selected dev type */
  autoDismissedChapters?: Set<string>;
  onAssertChapter?: (chapterKey: string, reason: string | null) => Promise<void>;
  chapterProgress?: Record<string, { assessed: number; total: number }>;
  /** Selected dev type slug — enables suggestion mode when set */
  devType?: string;
  /** Human-readable dev type label for dismiss reasons */
  devTypeLabel?: string;
  /** LGA-specific term for the top structural level — "part" or "chapter" */
  topLevelTerm?: 'part' | 'chapter';
  /** How dev type affects scope for this council. sort_only = no chapter gating, suppress dismiss suggestions */
  daDevTypeRole?: 'chapter_selector' | 'subpart_selector' | 'sort_only';
}

export function TocSidebar({
  tocStructure,
  filteredTocStructure,
  filteredPartCounts,
  selectedPart,
  selectedSection,
  onSelectPart,
  onSelectSection,
  formerCouncil,
  isDaMode,
  chapterAssertions,
  autoDismissedChapters,
  onAssertChapter,
  chapterProgress,
  devType,
  devTypeLabel,
  topLevelTerm = 'part',
  daDevTypeRole,
}: TocSidebarProps) {
  const [expandedParts, setExpandedParts] = useState<Set<string>>(new Set());
  const [pendingDismiss, setPendingDismiss] = useState<string | null>(null);
  const [customReason, setCustomReason] = useState('');

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
  const sortedParts = Object.entries(tocStructure).filter(([id]) => id !== 'Other').sort((a, b) => {
    const order = getPartOrder(a[0]);
    const orderB = getPartOrder(b[0]);
    return order - orderB;
  });

  // Infer parent-child relationships from part IDs (no hardcoding required)
  const partParents = inferPartParents(sortedParts.map(([id]) => id));
  const rootParts = sortedParts.filter(([id]) => !partParents[id]);
  const childParts = (parentId: string) => sortedParts.filter(([id]) => partParents[id] === parentId);

  // Dev-type suggestion: chapters where dev_type_match_count === 0 and not already dismissed.
  // Suppressed for sort_only councils (e.g. Leichhardt) where dev type is a relevance sort only —
  // all chapters apply regardless of dev type; suggesting dismissal would be architecturally wrong.
  const suggestedDismissals = isDaMode && devType && daDevTypeRole !== 'sort_only'
    ? sortedParts
        .filter(([partId, part]) => {
          if (chapterAssertions?.[partId]) return false; // already manually dismissed
          if (autoDismissedChapters?.has(partId)) return false; // already auto-dismissed
          if (part.dev_type_match_count === undefined) return false; // no dev type stats
          return part.dev_type_match_count === 0 && (filteredPartCounts?.[partId] ?? 0) > 0;
        })
        .map(([partId]) => partId)
    : [];

  const handleBatchDismiss = async () => {
    const reason = `Development type (${devTypeLabel || devType}) does not apply to this chapter`;
    for (const partId of suggestedDismissals) {
      await onAssertChapter?.(partId, reason);
    }
  };

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
        <p className="text-xs font-bold uppercase tracking-wide text-gray-500 mb-0.5">
          DCP Structure
        </p>
        <h3 className="text-sm font-semibold text-gray-800 leading-tight">
          {formerCouncil === 'Ashfield' ? 'Ashfield DCP 2016'
            : formerCouncil === 'Leichhardt' ? 'Leichhardt DCP 2013'
            : formerCouncil === 'Marrickville' ? 'Marrickville DCP 2011'
            : formerCouncil === 'Waverley' ? 'Waverley DCP 2022'
            : formerCouncil === 'Woollahra' ? 'Woollahra DCP 2015'
            : formerCouncil === 'City of Sydney' ? 'Sydney DCP 2012'
            : formerCouncil === 'Ku-ring-gai' ? 'Ku-ring-gai DCP 2024'
            : formerCouncil ? `${formerCouncil} DCP`
            : 'DCP'}
        </h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Select a {topLevelTerm} to begin
        </p>
      </div>

      {/* Batch dismiss banner — quantifies provision reduction */}
      {suggestedDismissals.length > 0 && (() => {
        const skippableProvisions = suggestedDismissals.reduce(
          (sum, partId) => sum + (filteredPartCounts?.[partId] ?? tocStructure[partId]?.provision_count ?? 0), 0
        );
        // Get chapter names + labels for display
        const chapterLabels = suggestedDismissals
          .map(partId => {
            const display = formatPartDisplay(partId);
            return `${display.label}${display.desc ? ` ${display.desc}` : ''}`;
          })
          .join(', ');
        return (
          <div className="mx-2 mt-2 p-2.5 bg-amber-50 border border-amber-200 rounded-md">
            <p className="text-xs text-amber-800 leading-relaxed space-y-1">
              <div>
                <span className="font-semibold">{chapterLabels}</span>
              </div>
              <div>
                {skippableProvisions} provisions — 0 applicable to{' '}
                <span className="font-semibold">{devTypeLabel || 'your development type'}</span>
              </div>
            </p>
            {skippableProvisions > 0 && (
              <button
                onClick={handleBatchDismiss}
                className="mt-2 text-xs font-medium px-2.5 py-1 bg-amber-100 hover:bg-amber-200 text-amber-800 rounded transition-colors"
              >
                Dismiss {suggestedDismissals.length === 1 ? 'this chapter' : `all ${suggestedDismissals.length} chapters`}
              </button>
            )}
          </div>
        );
      })()}

      {/* Resume button — DA mode, session in progress, jump to first unassessed chapter */}
      {isDaMode && chapterProgress && (() => {
        const resumePart = sortedParts.find(([id]) => {
          if (chapterAssertions?.[id]) return false;
          if (autoDismissedChapters?.has(id)) return false;
          const prog = chapterProgress[id];
          return prog && prog.total > 0 && prog.assessed < prog.total;
        });
        if (!resumePart) return null;
        const [resumeId] = resumePart;
        const { label } = formatPartDisplay(resumeId);
        const prog = chapterProgress[resumeId];
        const isStarted = prog.assessed > 0;
        return (
          <div className="mx-2 mt-2">
            <button
              onClick={() => onSelectPart(resumeId)}
              className="w-full text-left text-xs px-2.5 py-1.5 bg-teal-600 hover:bg-teal-700 text-white rounded-md transition-colors font-medium flex items-center justify-between"
            >
              <span>{isStarted ? 'Continue' : 'Start'}: {label}</span>
              <span className="opacity-75">→</span>
            </button>
          </div>
        );
      })()}

      {/* Total provisions applicable — positioned before TOC for clarity */}
      {(() => {
        const total = Object.values(filteredPartCounts || {}).reduce((sum, count) => sum + count, 0);
        return total > 0 ? (
          <div className="mx-2 mt-3 mb-2 p-2 bg-teal-50 border border-teal-200 rounded">
            <p className="text-xs font-semibold text-teal-900">
              {total} provisions applicable to your work
            </p>
          </div>
        ) : null;
      })()}

      <nav className="p-2">
        {rootParts.map(([partId, part]) => (
          <PartTree
            key={partId}
            partId={partId}
            part={part}
            tocStructure={tocStructure}
            filteredTocStructure={filteredTocStructure}
            filteredPartCounts={filteredPartCounts}
            expandedParts={expandedParts}
            selectedPart={selectedPart}
            selectedSection={selectedSection}
            onToggle={togglePart}
            onSelectPart={onSelectPart}
            onSelectSection={onSelectSection}
            isDaMode={isDaMode}
            chapterAssertions={chapterAssertions}
            autoDismissedChapters={autoDismissedChapters}
            onAssertChapter={onAssertChapter}
            chapterProgress={chapterProgress}
            suggestedDismissals={suggestedDismissals}
            pendingDismiss={pendingDismiss}
            setPendingDismiss={setPendingDismiss}
            customReason={customReason}
            setCustomReason={setCustomReason}
            childParts={childParts}
            depth={0}
            daDevTypeRole={daDevTypeRole}
          />
        ))}
      </nav>
    </div>
  );
}

/**
 * Recursive renderer — renders a part and any inferred children indented below it.
 * No DCP-specific knowledge required; hierarchy is inferred from part IDs.
 */
function PartTree({
  partId, part, tocStructure, filteredTocStructure, filteredPartCounts,
  expandedParts, selectedPart, selectedSection,
  onToggle, onSelectPart, onSelectSection,
  isDaMode, chapterAssertions, autoDismissedChapters, onAssertChapter, chapterProgress,
  suggestedDismissals, pendingDismiss, setPendingDismiss, customReason, setCustomReason,
  childParts, depth, daDevTypeRole,
}: {
  partId: string; part: TocPart;
  tocStructure: Record<string, TocPart>;
  filteredTocStructure: Record<string, TocPart>;
  filteredPartCounts?: Record<string, number>;
  expandedParts: Set<string>; selectedPart: string | null; selectedSection: string | null;
  onToggle: (id: string) => void; onSelectPart: (id: string) => void;
  onSelectSection: (partId: string, sectionId: string) => void;
  isDaMode?: boolean; chapterAssertions?: Record<string, string>;
  autoDismissedChapters?: Set<string>;
  onAssertChapter?: (key: string, reason: string | null) => Promise<void>;
  chapterProgress?: Record<string, { assessed: number; total: number }>;
  suggestedDismissals: string[]; pendingDismiss: string | null;
  setPendingDismiss: (id: string | null) => void;
  customReason: string; setCustomReason: (v: string) => void;
  childParts: (parentId: string) => [string, TocPart][];
  depth: number;
  daDevTypeRole?: 'chapter_selector' | 'subpart_selector' | 'sort_only';
}) {
  const filteredPart = filteredTocStructure[partId];
  const hasProvisions = !!(filteredPartCounts?.[partId] ?? filteredPart?.provision_count);
  const hasAnyProvisions = part.provision_count > 0;
  const isManuallyAsserted = isDaMode === true && !!chapterAssertions?.[partId];
  const isAutoDismissed = isDaMode === true && (autoDismissedChapters?.has(partId) ?? false);
  const isAsserted = isManuallyAsserted || isAutoDismissed;
  const assertedReason = chapterAssertions?.[partId] ?? (isAutoDismissed ? 'No provisions for this development type' : undefined);
  const { desc: partDesc } = formatPartDisplay(partId);
  const children = childParts(partId);

  return (
    <div style={depth > 0 ? { paddingLeft: `${depth * 12}px` } : undefined}>
      <PartNode
        part={part}
        filteredPart={filteredPart}
        filteredPartCounts={filteredPartCounts}
        hasProvisions={hasProvisions}
        hasAnyProvisions={hasAnyProvisions}
        isExpanded={expandedParts.has(partId)}
        isSelected={selectedPart === partId}
        selectedSection={selectedPart === partId ? selectedSection : null}
        onToggle={() => onToggle(partId)}
        onSelectPart={() => { if (!isAsserted) onSelectPart(partId); }}
        onSelectSection={(sectionId) => { if (!isAsserted) onSelectSection(partId, sectionId); }}
        isDaMode={isDaMode}
        isAsserted={isAsserted}
        assertedReason={assertedReason}
        onDismiss={() => setPendingDismiss(partId)}
        onUndo={isManuallyAsserted ? () => onAssertChapter?.(partId, null) : undefined}
        chapterProgress={chapterProgress}
        isSuggestedForDismissal={suggestedDismissals.includes(partId)}
        daDevTypeRole={daDevTypeRole}
      />
      {pendingDismiss === partId && (
        <div className="ml-5 mt-1 mb-2 bg-white border border-gray-200 rounded p-2 space-y-1 shadow-sm">
          {CHAPTER_PRESET_REASONS(partDesc || '').map(r => (
            <button key={r}
              onClick={() => { onAssertChapter?.(partId, r); setPendingDismiss(null); }}
              className="block w-full text-left text-xs px-2 py-1 rounded hover:bg-gray-50 text-gray-600">
              {r}
            </button>
          ))}
          <div className="flex gap-1 pt-1">
            <input value={customReason} onChange={e => setCustomReason(e.target.value)}
              placeholder="Other reason..." className="flex-1 text-xs border rounded px-2 py-1" />
            <button onClick={() => { if (customReason.trim()) { onAssertChapter?.(partId, customReason.trim()); setPendingDismiss(null); setCustomReason(''); } }}
              className="text-xs px-2 py-1 bg-teal-600 text-white rounded hover:bg-teal-700">OK</button>
          </div>
          <button onClick={() => setPendingDismiss(null)} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
        </div>
      )}
      {/* Render inferred children indented */}
      {children.map(([childId, childPart]) => (
        <PartTree key={childId} partId={childId} part={childPart}
          tocStructure={tocStructure} filteredTocStructure={filteredTocStructure}
          filteredPartCounts={filteredPartCounts} expandedParts={expandedParts}
          selectedPart={selectedPart} selectedSection={selectedSection}
          onToggle={onToggle} onSelectPart={onSelectPart} onSelectSection={onSelectSection}
          isDaMode={isDaMode} chapterAssertions={chapterAssertions}
          autoDismissedChapters={autoDismissedChapters}
          onAssertChapter={onAssertChapter} chapterProgress={chapterProgress}
          suggestedDismissals={suggestedDismissals} pendingDismiss={pendingDismiss}
          setPendingDismiss={setPendingDismiss} customReason={customReason}
          setCustomReason={setCustomReason} childParts={childParts} depth={depth + 1}
          daDevTypeRole={daDevTypeRole}
        />
      ))}
    </div>
  );
}

interface PartNodeProps {
  part: TocPart;
  filteredPart?: TocPart;
  filteredPartCounts?: Record<string, number>;
  hasProvisions: boolean;
  hasAnyProvisions?: boolean;
  isExpanded: boolean;
  isSelected: boolean;
  selectedSection: string | null;
  onToggle: () => void;
  onSelectPart: () => void;
  onSelectSection: (sectionId: string) => void;
  isDaMode?: boolean;
  isAsserted?: boolean;
  assertedReason?: string;
  onDismiss?: () => void;
  onUndo?: () => void;
  chapterProgress?: Record<string, { assessed: number; total: number }>;
  isSuggestedForDismissal?: boolean;
  daDevTypeRole?: 'chapter_selector' | 'subpart_selector' | 'sort_only';
}

function PartNode({
  part,
  filteredPart,
  filteredPartCounts,
  hasProvisions,
  hasAnyProvisions,
  isExpanded,
  isSelected,
  selectedSection,
  onToggle,
  onSelectPart,
  onSelectSection,
  isDaMode,
  isAsserted,
  assertedReason,
  onDismiss,
  onUndo,
  chapterProgress,
  isSuggestedForDismissal,
  daDevTypeRole,
}: PartNodeProps) {
  const filteredCount = filteredPartCounts?.[part.part_id] ?? filteredPart?.provision_count ?? 0;
  const sections = part?.sections || {};
  const sectionCount = Object.keys(sections).length;
  const hasMultipleSections = sectionCount > 1;

  return (
    <div className="mb-1">
      {/* Part header */}
      <div
        className={cn(
          "flex items-center gap-1 px-2 py-1.5 rounded-md cursor-pointer transition-colors group",
          isAsserted ? "opacity-50" : hasProvisions ? "hover:bg-teal-50" : "hover:bg-gray-100 opacity-40",
          isSelected && !selectedSection && !isAsserted && "bg-teal-100 text-teal-900"
        )}
        onClick={() => {
          if (isAsserted) return;
          if (hasMultipleSections) onToggle();
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

        {/* DA mode: progress state dot */}
        {isDaMode && !isAsserted && (() => {
          const prog = chapterProgress?.[part.part_id];
          if (!prog || prog.total === 0) return null;
          const done = prog.assessed === prog.total;
          const started = prog.assessed > 0;
          return (
            <span
              className={`w-2 h-2 rounded-full flex-shrink-0 ${done ? 'bg-green-500' : started ? 'bg-amber-400' : 'bg-gray-300'}`}
              title={done ? 'All sections assessed' : started ? `${prog.assessed} of ${prog.total} assessed` : 'Not started'}
            />
          );
        })()}

        {/* Part name with description */}
        <div className="flex-1 min-w-0">
          {(() => {
            const { label } = formatPartDisplay(part.part_id);
            const subtitle = part.part_name && part.part_name !== part.part_id ? part.part_name : null;
            return (
              <div>
                <span className={cn(
                  "text-sm",
                  isSelected ? "font-bold" : "font-medium",
                  hasProvisions ? "text-gray-800" : "text-gray-400"
                )}>
                  {label}
                </span>
                {subtitle && (
                  <span className={cn("text-xs block", hasProvisions ? "text-gray-500" : "text-gray-400")}>
                    {subtitle}
                  </span>
                )}
              </div>
            );
          })()}
        </div>

        {/* Asserted-out indicator OR dismiss button (DA mode) */}
        {isAsserted ? (
          onUndo ? (
            <button
              onClick={(e) => { e.stopPropagation(); onUndo(); }}
              className="text-xs text-teal-500 hover:text-teal-700 flex-shrink-0 px-1"
              title="Restore chapter to assessment scope"
            >
              undo
            </button>
          ) : null
        ) : isDaMode && hasProvisions ? (
          <button
            onClick={(e) => { e.stopPropagation(); onDismiss?.(); }}
            className="text-gray-300 hover:text-red-400 transition-colors flex-shrink-0 text-base leading-none px-1"
            title="Dismiss — does not apply to this project"
          >
            ×
          </button>
        ) : null}

        {/* Count badge — non-DA mode only */}
        {!isDaMode && !isAsserted && (hasProvisions ? (
          <span className="text-xs text-gray-700 bg-gray-200 px-1.5 py-0.5 rounded font-medium">
            {filteredCount}
          </span>
        ) : (
          <span className="text-xs text-gray-400 bg-gray-100 px-1.5 py-0.5 rounded">
            0
          </span>
        ))}
      </div>
      {/* DA mode: progress bar OR match ratio below chapter name */}
      {isDaMode && !isAsserted && (() => {
        const prog = chapterProgress?.[part.part_id];
        const total = prog?.total ?? 0;
        const assessed = prog?.assessed ?? 0;

        // For suggested-for-dismissal chapters that have not been started,
        // show match ratio instead of progress bar
        if (isSuggestedForDismissal && assessed === 0 && part.dev_type_match_count !== undefined && daDevTypeRole !== 'sort_only') {
          return (
            <div className="ml-9 mt-0.5 mb-0.5">
              <span className="text-[10px] text-amber-600" title={`None of the ${filteredCount} provisions in this chapter apply to your development type`}>
                0 of {filteredCount} apply to your type
              </span>
            </div>
          );
        }

        if (total === 0) return null;
        const pct = Math.round((assessed / total) * 100);
        const done = assessed === total;
        return (
          <div className="ml-9 mt-0.5 mb-0.5 flex items-center gap-2">
            <div className="flex-1 h-1 bg-gray-200 rounded-full max-w-[80px]">
              <div
                className={`h-1 rounded-full transition-all ${done ? 'bg-green-500' : 'bg-teal-500'}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span
              className={`text-xs flex-shrink-0 ${done ? 'text-green-600 font-medium' : 'text-gray-500'}`}
              title={`${assessed} of ${total} provisions assessed in this chapter`}
            >
              {assessed} of {total} assessed
            </span>
          </div>
        );
      })()}
      {/* Asserted reason shown below part row */}
      {isAsserted && assertedReason && (
        <p className="ml-9 text-xs text-gray-400 italic truncate pb-0.5" title={assertedReason}>
          {assertedReason}
        </p>
      )}

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
                isDaMode={isDaMode}
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
  isDaMode?: boolean;
}

function SectionNode({ section, filteredSection, hasProvisions, isSelected, onClick, isDaMode }: SectionNodeProps) {
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
      <span className={cn(
        "text-xs break-words pr-2",
        isSelected ? "font-bold" : "",
        hasProvisions ? "text-gray-700" : "text-gray-400"
      )}>
        {display.primary}
        {display.secondary && (
          <span className={cn("ml-1", hasProvisions ? "text-gray-500" : "text-gray-400")}>{display.secondary}</span>
        )}
      </span>
      {hasProvisions ? (
        <span className="text-xs text-gray-700 flex-shrink-0 font-medium">
          {isDaMode ? section.provision_count : (filteredSection?.provision_count || 0)}
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
 * Infer parent-child relationships from part IDs without any DCP-specific knowledge.
 * Rule: partB is a child of partA if partA is a strict prefix of partB
 * (i.e. partB starts with partA followed by a space or separator).
 * Works for: "Chapter F" → "Chapter F Part 1", "Part C" → "Part C Section 2", etc.
 * Returns a map of partId → parentId (undefined = root).
 */
export function inferPartParents(partIds: string[]): Record<string, string | undefined> {
  const parents: Record<string, string | undefined> = {};
  // Sort by length descending so we find the most specific (longest) parent first
  const sorted = [...partIds].sort((a, b) => b.length - a.length);
  for (const partId of sorted) {
    parents[partId] = undefined;
    for (const candidate of sorted) {
      if (candidate === partId) continue;
      if (candidate.length >= partId.length) continue;
      // candidate is a prefix if partId starts with candidate + a non-alphanumeric separator
      if (partId.startsWith(candidate) && /^[\s\-_]/.test(partId.slice(candidate.length))) {
        parents[partId] = candidate;
        break;
      }
    }
  }
  return parents;
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
    // Fallback
    'Other': 99,
    'unknown': 100,
  };

  if (orderMap[partId] !== undefined) return orderMap[partId];

  // Waverley-style codes: letter + number (B1, B15, C1, E7, F4, ...)
  const waverleyMatch = partId.match(/^([A-Z])(\d+)$/);
  if (waverleyMatch) {
    const letter = waverleyMatch[1].charCodeAt(0) - 'A'.charCodeAt(0); // B=1, C=2, D=3, E=4, F=5
    return 30 + letter * 20 + parseInt(waverleyMatch[2]);
  }

  // Generic "Chapter X Part N" → parent order + sub-part fraction (e.g. "Chapter F Part 10" → 25.10)
  const legacyChapterPart = partId.match(/^Chapter ([A-Z]\d*) Part (\d+)$/);
  if (legacyChapterPart) {
    const parentOrder = getPartOrder(`Chapter ${legacyChapterPart[1]}`);
    return parentOrder + parseInt(legacyChapterPart[2]) / 100;
  }

  // Generic "Part X Section N" → parent order + sub-part fraction (e.g. "Part C Section 4" → 12.04)
  const legacyPartSection = partId.match(/^Part ([A-Z]) Section (\d+)$/);
  if (legacyPartSection) {
    const parentOrder = getPartOrder(`Part ${legacyPartSection[1]}`);
    return parentOrder + parseInt(legacyPartSection[2]) / 100;
  }

  // Slug-style chapter keys: chapter-b3-general-development, chapter-e1-heritage, ...
  const chapterSlug = partId.match(/^chapter-([a-z])(\d*)/);
  if (chapterSlug) {
    const letter = chapterSlug[1].charCodeAt(0) - 'a'.charCodeAt(0);
    return 200 + letter * 20 + (parseInt(chapterSlug[2]) || 0);
  }

  // Slug-style part keys: part-b-connections, part-c-s2-urban-character, part4-s1-low-density
  const partSlugLetter = partId.match(/^part-([a-z])/);
  if (partSlugLetter) {
    const letter = partSlugLetter[1].charCodeAt(0) - 'a'.charCodeAt(0);
    const sec = partId.match(/-s(\d+)/)?.[1];
    return 100 + letter * 20 + (parseInt(sec || '0') || 0);
  }
  const partSlugNum = partId.match(/^part(\d+)/);
  if (partSlugNum) return parseInt(partSlugNum[1]);

  return 50;
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
  // Waverley DCP 2022 (v2_dcp_part codes B1–B17, C1–C2, D1–D2, E1–E7, F1–F5)
  'B1': { label: 'B1', desc: 'Waste' },
  'B2': { label: 'B2', desc: 'Ecologically Sustainable Dev' },
  'B3': { label: 'B3', desc: 'Landscaping & Biodiversity' },
  'B4': { label: 'B4', desc: 'Coastal Risk Management' },
  'B5': { label: 'B5', desc: 'Water Management' },
  'B6': { label: 'B6', desc: 'Accessibility & Adaptability' },
  'B7': { label: 'B7', desc: 'Transport' },
  'B8': { label: 'B8', desc: 'Heritage' },
  'B9': { label: 'B9', desc: 'Safety' },
  'B10': { label: 'B10', desc: 'Public Art' },
  'B11': { label: 'B11', desc: 'Design Excellence' },
  'B12': { label: 'B12', desc: 'Subdivision' },
  'B13': { label: 'B13', desc: 'Excavation' },
  'B14': { label: 'B14', desc: 'Advertising & Signage' },
  'B15': { label: 'B15', desc: 'Public Domain' },
  'B16': { label: 'B16', desc: 'Inter-War Buildings' },
  'B17': { label: 'B17', desc: 'Social Impact Assessment' },
  'C1': { label: 'C1', desc: 'Low Density Residential' },
  'C2': { label: 'C2', desc: 'Other Residential Development' },
  'D1': { label: 'D1', desc: 'Commercial & Retail' },
  'D2': { label: 'D2', desc: 'Outdoor Dining' },
  'E1': { label: 'E1', desc: 'Bondi Junction' },
  'E2': { label: 'E2', desc: 'Bondi Beachfront Area' },
  'E3': { label: 'E3', desc: 'Local Village Centres' },
  'E4': { label: 'E4', desc: 'Special Character Areas' },
  'E5': { label: 'E5', desc: '113 Macpherson St Bronte' },
  'E6': { label: 'E6', desc: '194–214 Oxford Street' },
  'E7': { label: 'E7', desc: 'Edina Estate' },
  'F1': { label: 'F1', desc: 'Shared Residential Accommodation' },
  'F2': { label: 'F2', desc: 'Tourist & Visitor Accommodation' },
  'F3': { label: 'F3', desc: 'Child Care Centres' },
  'F4': { label: 'F4', desc: 'Places of Public Worship' },
  'F5': { label: 'F5', desc: 'Horticulture' },
  // Woollahra DCP 2022 (source_chapter_key slugs used as partId)
  'chapter-a1-introduction': { label: 'Chapter A1', desc: 'Introduction' },
  'chapter-a3-definitions': { label: 'Chapter A3', desc: 'Definitions' },
  'chapter-b1-residential-precincts': { label: 'Chapter B1', desc: 'Residential Precincts' },
  'chapter-b2-neighbourhood-hcas': { label: 'Chapter B2', desc: 'Neighbourhood HCAs' },
  'chapter-b3-general-development': { label: 'Chapter B3', desc: 'General Development Controls' },
  'chapter-b4-housing-accessible-areas': { label: 'Chapter B4', desc: 'Housing — Accessible Areas' },
  'chapter-c1-paddington-hca': { label: 'Chapter C1', desc: 'Paddington HCA' },
  'chapter-c2-woollahra-hca': { label: 'Chapter C2', desc: 'Woollahra HCA' },
  'chapter-c3-watsons-bay-hca': { label: 'Chapter C3', desc: "Watson's Bay HCA" },
  'chapter-d4-edgecliff-centre': { label: 'Chapter D4', desc: 'Edgecliff Centre' },
  'chapter-e1-parking-access': { label: 'Chapter E1', desc: 'Parking & Access' },
  'chapter-e2-stormwater-flood': { label: 'Chapter E2', desc: 'Stormwater & Flooding' },
  'chapter-e3-tree-management': { label: 'Chapter E3', desc: 'Tree Management' },
  'chapter-e5-waste-management': { label: 'Chapter E5', desc: 'Waste Management' },
  'chapter-e6-sustainability': { label: 'Chapter E6', desc: 'Sustainability' },
  // Ashfield (source_chapter_key slugs)
  'chapter-e1-heritage': { label: 'Chapter E1', desc: 'Heritage' },
  'chapter-c-sustainability': { label: 'Chapter C', desc: 'Sustainability' },
  'chapter-d-precinct-guidelines': { label: 'Chapter D', desc: 'Precinct Guidelines' },
  'chapter-f-dev-category': { label: 'Chapter F', desc: 'Development Categories' },
  'chapter-g-definitions': { label: 'Chapter G', desc: 'Definitions' },
  'preliminary': { label: 'Preliminary', desc: '' },
};

/**
 * Format part ID for display (shorter version for sidebar)
 * Returns { label, desc } for two-line display
 */
export function formatPartDisplay(partId: string): { label: string; desc?: string } {
  if (!partId) return { label: 'Other' };

  // Handle "unknown" gracefully
  if (partId === 'unknown' || partId === 'Unknown') {
    return { label: 'General', desc: 'Miscellaneous Provisions' };
  }

  // Check for known part with description
  if (PART_DESCRIPTIONS[partId]) {
    return PART_DESCRIPTIONS[partId] as { label: string; desc?: string };
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
  if (shortMap[partId]) return { label: shortMap[partId] };

  // Generic "Chapter X Part N" → Ch X.N  (e.g. "Chapter F Part 10" → "Ch F.10")
  const chapterPartN = partId.match(/^Chapter ([A-Z]\d*) Part (\d+)$/);
  if (chapterPartN) return { label: `Ch ${chapterPartN[1]}.${chapterPartN[2]}` };

  // Generic "Part X Section N" → Part X.N  (e.g. "Part C Section 4" → "Part C.4")
  const partSectionN = partId.match(/^Part ([A-Z]) Section (\d+)$/);
  if (partSectionN) return { label: `Part ${partSectionN[1]}.${partSectionN[2]}` };

  // Generic "Part N.M" decimal → Part N.M  (e.g. "Part 4.3")
  const partDecimal = partId.match(/^Part (\d+\.\d+)$/);
  if (partDecimal) return { label: `Part ${partDecimal[1]}` };

  // Auto-format slug-style keys (source_chapter_key used as partId)
  // chapter-{code}-{desc}: e.g. chapter-b3-general-development, chapter-c-sustainability
  const chapterSlug = partId.match(/^chapter-([a-z]\d*(?:\.\d+)?)-(.+)$/);
  if (chapterSlug) {
    const code = chapterSlug[1].toUpperCase();
    const desc = chapterSlug[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Chapter ${code}`, desc };
  }
  // part-{letter}-s{n}-{desc}: part-c-s2-urban-character → Part C.2 — Urban Character
  const partSectionSlug = partId.match(/^part-([a-z])-s(\d+)-(.+)$/);
  if (partSectionSlug) {
    const desc = partSectionSlug[3].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${partSectionSlug[1].toUpperCase()}.${partSectionSlug[2]}`, desc };
  }
  // part-{letter}-{desc}: part-b-connections, part-d-energy
  const partLetterSlug = partId.match(/^part-([a-z])-(.+)$/);
  if (partLetterSlug) {
    const desc = partLetterSlug[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${partLetterSlug[1].toUpperCase()}`, desc };
  }
  // part{n}-p{m}-{desc}: part9-p06-petersham-south → Part 9 — Petersham South
  const partNumPrecinct = partId.match(/^part(\d+)-p\d+-(.+)$/);
  if (partNumPrecinct) {
    const desc = partNumPrecinct[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${partNumPrecinct[1]}`, desc };
  }
  // part{n}-s{m}-{desc}: part4-s1-low-density → Part 4.1
  const partNumSection = partId.match(/^part(\d+)-s(\d+)-(.+)$/);
  if (partNumSection) {
    const desc = partNumSection[3].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${partNumSection[1]}.${partNumSection[2]}`, desc };
  }
  // part{n}-{desc}: part1-statutory-info, part3-subdivision
  const partNumSlug = partId.match(/^part(\d+)-(.+)$/);
  if (partNumSlug) {
    const desc = partNumSlug[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${partNumSlug[1]}`, desc };
  }
  // appendix-{code}-{desc}
  const appendixSlug = partId.match(/^appendix-([a-z\d]+)-(.+)$/);
  if (appendixSlug) {
    const desc = appendixSlug[2].replace(/-/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Appendix ${appendixSlug[1].toUpperCase()}`, desc };
  }

  // KRG-style underscore slugs: part_4_1_secondary_dwellings, part_12_signage, part_2_site_analysis
  // Decimal check must come first: part_4_1_foo → Part 4.1, part_4_foo → Part 4
  const krgPartDecimal = partId.match(/^part_(\d+)_(\d+)_(.+)$/);
  if (krgPartDecimal) {
    const desc = krgPartDecimal[3].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${krgPartDecimal[1]}.${krgPartDecimal[2]}`, desc };
  }
  const krgPart = partId.match(/^part_(\d+)_(.+)$/);
  if (krgPart) {
    const desc = krgPart[2].replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    return { label: `Part ${krgPart[1]}`, desc };
  }

  return { label: partId };
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
