'use client';

import { useState, useMemo } from 'react';

const PRESET_REASONS = (topic: string) => [
  `No ${topic.replace(/_/g, ' ')} works proposed`,
  'Development type not applicable — residential use only',
  'Site condition confirmed absent per LEP mapping',
];
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import { ANCILLARY_WORKS } from '@/lib/see/ancillaryWorks';
import type { IntakeAnswers } from '@/lib/see/intake';
import type { Provision } from './PageGroupedProvisions';
import { HERITAGE_ELEMENTS, SCOPE_TOPIC_MAP, type WorksScopeAnswers } from '@/lib/see/worksScope';
import { DABundleChecklist } from './DABundleChecklist';

interface DAModeCardProps {
  devType: string;
  devWorksText: string;
  devDescriptionLocal: string;
  intakeAnswers: IntakeAnswers | null;
  daResponses: Map<number, { response_text: string | null; compliance_status: string | null }>;
  allProvisions: Provision[];
  excludableTopics: Set<string>;
  ancillaryWorks: string[];
  onAncillaryWorksChange: (works: string[]) => void;
  onDevTypeChange: (val: string) => void;
  onDevWorksChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onRunIntake?: () => void;
  /** Toggle objectives/descriptive provisions into the provision list view */
  onToggleObjectives?: () => void;
  /** Project identity — appear on SEE cover */
  clientRef: string;
  preparedBy: string;
  onClientRefChange: (val: string) => void;
  onPreparedByChange: (val: string) => void;
  /** LEP controls for inline summary */
  lepHeight?: string;
  lepFsr?: string;
  /** Property-level flags — used to surface first-class passengers */
  heritage?: boolean;
  hcaName?: string;
  precinctName?: string;
  intakeSetAt?: string | null;
  /** Provision corpus breakdown by layer — for the corpus summary */
  layerCounts?: { generic: number; use_specific: number; condition: number; precinct: number };
  genericLabel?: string;
  /** Topic-level assertions — planner-dismissed topics */
  topicAssertions: Record<string, string>;
  onAssertTopicNA: (topic: string, reason: string | null) => Promise<void>;
  /** Proposed numeric values — used for LEP compliance auto-check in SEE */
  onProposedValuesChange?: (field: 'proposed_height' | 'proposed_gfa', value: string) => void;
  /** Global progress — single source of truth from ProvisionsByTocStructure */
  globalProgress?: {
    total: number; triaged: number; chapterDismissed: number; autoChapterDismissed: number;
    topicDismissed: number; suppressed: number;
    questionnaireScoped: number; heritageElementScoped: number;
    provisionScopeTotal: number;
    scopeTotal: number; assessed: number; remaining: number;
  } | null;
  /** Works scope questionnaire answers */
  worksScopeAnswers?: WorksScopeAnswers | null;
  onWorksScopeChange?: (answers: WorksScopeAnswers) => void;
  /** Auto-derived scope from LEP permissibility data (lowest priority, user answers override) */
  lepScopeDefaults?: Partial<WorksScopeAnswers>;
  /** LEP land use slugs that are explicitly prohibited in the current zone */
  lepProhibitedDevTypes?: Set<string>;
  /** True when lep_zone_coverage.is_complete for this zone/LGA — only enforce filtering when we have full coverage data */
  lepPermCovered?: boolean;
  /** Ancillary work values that have SEPP exempt development provisions for this zone */
  seppExemptWorks?: Set<string>;
  /** Lot area in m² — used for stormwater trigger in DA bundle checklist */
  lotArea?: number | null;
}

export function DAModeCard({
  devType,
  devWorksText,
  devDescriptionLocal,
  intakeAnswers,
  daResponses,
  allProvisions,
  excludableTopics,
  ancillaryWorks,
  onAncillaryWorksChange,
  onDevTypeChange,
  onDevWorksChange,
  onRunIntake,
  onToggleObjectives,
  clientRef,
  preparedBy,
  onClientRefChange,
  onPreparedByChange,
  lepHeight,
  lepFsr,
  heritage,
  hcaName,
  precinctName,
  intakeSetAt,
  layerCounts,
  genericLabel,
  topicAssertions,
  onAssertTopicNA,
  onProposedValuesChange,
  globalProgress,
  worksScopeAnswers,
  onWorksScopeChange,
  lepScopeDefaults,
  lepProhibitedDevTypes,
  lepPermCovered,
  seppExemptWorks,
  lotArea,
}: DAModeCardProps) {
  const [pendingDismiss, setPendingDismiss] = useState<string | null>(null);
  const [customReason, setCustomReason] = useState('');
  const [showWaterfall, setShowWaterfall] = useState(false);

  // Get dev type label from options
  const devTypeLabel = useMemo(() => {
    return DEV_TYPE_OPTIONS.find(opt => opt.value === devType)?.label || devType;
  }, [devType]);

  // True when the selected primary dev type is explicitly prohibited in this zone per LEP data
  const selectedDevTypeProhibited = useMemo(() => {
    const opt = DEV_TYPE_OPTIONS.find(o => o.value === devType);
    return opt?.lepSlug ? (lepProhibitedDevTypes?.has(opt.lepSlug) ?? false) : false;
  }, [devType, lepProhibitedDevTypes]);

  // Derive scope summary and heritage count (progress now comes from globalProgress prop)
  const derivedStats = useMemo(() => {
    let heritagePros = 0;

    for (const p of allProvisions) {
      const layer = p.v2_dcp_layer || p.layer;
      if (layer === 'condition') heritagePros++;
    }

    // Scope summary — excluded structural categories only (for waterfall display)
    const excludedCategories: { topic: string; count: number }[] = [];
    const excludedByCategory: Record<string, number> = {};
    for (const p of allProvisions) {
      if ((p.v2_dcp_layer || p.layer) === 'condition') continue;
      const cat = p.v2_structural_category;
      if (cat && excludableTopics.has(cat)) {
        excludedByCategory[cat] = (excludedByCategory[cat] || 0) + 1;
      }
    }
    for (const [cat, count] of Object.entries(excludedByCategory).sort((a, b) => b[1] - a[1])) {
      excludedCategories.push({ topic: cat, count });
    }

    return {
      scopeSummary: { included: [] as { topic: string; count: number }[], excluded: excludedCategories },
      heritagePros,
    };
  }, [allProvisions, excludableTopics, topicAssertions]);

  const { scopeSummary, heritagePros } = derivedStats;

  return (
    <div className="mb-4 bg-teal-50 border border-teal-200 rounded-lg overflow-hidden">

      <div className="px-4 pb-4 pt-3 space-y-3">

        {/* LEP controls summary — height and FSR inline with proposal inputs */}
        {(lepHeight || lepFsr) && (
          <div className="flex gap-4 text-xs bg-white border border-teal-100 rounded px-3 py-2 items-end">
            {lepHeight && (
              <div>
                <span className="text-gray-400">Height limit</span>
                <span className="ml-1.5 font-semibold text-gray-700">{lepHeight}</span>
              </div>
            )}
            {lepFsr && (
              <div>
                <span className="text-gray-400">FSR</span>
                <span className="ml-1.5 font-semibold text-gray-700">{lepFsr}</span>
              </div>
            )}
            {onProposedValuesChange && (
              <>
                <div className="ml-auto flex items-center gap-1">
                  <span className="text-gray-400">Proposed height</span>
                  <input
                    type="text"
                    value={intakeAnswers?.proposed_height ?? ''}
                    onChange={e => onProposedValuesChange('proposed_height', e.target.value)}
                    placeholder="m"
                    className="w-14 text-xs border border-teal-200 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 text-gray-700 placeholder:text-gray-400 text-right"
                  />
                </div>
                <div className="flex items-center gap-1">
                  <span className="text-gray-400">Proposed GFA</span>
                  <input
                    type="text"
                    value={intakeAnswers?.proposed_gfa ?? ''}
                    onChange={e => onProposedValuesChange('proposed_gfa', e.target.value)}
                    placeholder="m²"
                    className="w-16 text-xs border border-teal-200 rounded px-1.5 py-0.5 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 text-gray-700 placeholder:text-gray-400 text-right"
                  />
                </div>
              </>
            )}
          </div>
        )}

        {/* Project identity */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="block text-xs font-medium text-teal-800 mb-1">Client / site reference</label>
            <input
              type="text"
              value={clientRef}
              onChange={e => onClientRefChange(e.target.value)}
              placeholder="e.g. Smith — 120 Illawarra Rd"
              className="w-full text-sm border border-teal-200 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 text-gray-700 placeholder:text-gray-400"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-teal-800 mb-1">Prepared by</label>
            <input
              type="text"
              value={preparedBy}
              onChange={e => onPreparedByChange(e.target.value)}
              placeholder="Consultant / firm name"
              className="w-full text-sm border border-teal-200 rounded px-2.5 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 text-gray-700 placeholder:text-gray-400"
            />
          </div>
        </div>

        {/* SEE requirement warning — shown before inputs so user knows what's needed */}
        {!devDescriptionLocal.trim() && (
          <p className="text-xs text-amber-600">Select a development type and describe the works — these appear on the SEE cover page.</p>
        )}

        {/* Development type */}
        <div>
          <label className="block text-xs font-medium text-teal-800 mb-1">
            Development type <span className="text-red-400">*</span>
          </label>
          <select
            value={devType}
            onChange={e => onDevTypeChange(e.target.value)}
            className="w-full text-sm border border-teal-200 rounded px-3 py-1.5 bg-white focus:outline-none focus:ring-1 focus:ring-teal-400 text-gray-700"
          >
            <option value="">Select type…</option>
            {DEV_TYPE_OPTIONS.map(opt => {
              const isZoneProhibited = lepPermCovered && opt.lepSlug
                ? (lepProhibitedDevTypes?.has(opt.lepSlug) ?? false)
                : false;
              return (
                <option key={opt.value} value={opt.value} disabled={isZoneProhibited}>
                  {opt.label}{isZoneProhibited ? ' — not permitted in this zone' : ''}
                </option>
              );
            })}
          </select>
        </div>

        {/* Permissibility warning — shown when selected dev type is prohibited in zone per LEP data */}
        {selectedDevTypeProhibited && (
          <div className="flex items-start gap-2 bg-red-50 border border-red-300 rounded px-3 py-2 text-xs text-red-800">
            <span className="flex-shrink-0 font-bold text-red-500 mt-0.5">!</span>
            <span>
              <strong>{devTypeLabel}</strong> is prohibited in this zone under the LEP — a DA for this development type will not be approved. Review the Planning Controls tab for permitted uses in this zone.
            </span>
          </div>
        )}

        {/* Ancillary works checkboxes — shown after primary type selected */}
        {devType && (
          <div>
            <label className="block text-xs font-medium text-teal-800 mb-1.5">
              Ancillary development <span className="text-gray-400 font-normal">(select all that apply)</span>
            </label>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {ANCILLARY_WORKS.map(work => {
                const checked = ancillaryWorks.includes(work.value);
                const isExempt = seppExemptWorks?.has(work.value) ?? false;
                return (
                  <label key={work.value} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer hover:text-gray-900">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => {
                        const next = checked
                          ? ancillaryWorks.filter(v => v !== work.value)
                          : [...ancillaryWorks, work.value];
                        onAncillaryWorksChange(next);
                      }}
                      className="w-3.5 h-3.5 rounded border-teal-300 text-teal-600 focus:ring-teal-500 focus:ring-1"
                    />
                    {work.label}
                    {isExempt && (
                      <span className="text-[10px] text-purple-500 font-medium leading-none">exempt?</span>
                    )}
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Works scope questionnaire — shown after dev type is selected */}
        {devType && onWorksScopeChange && (
          <div className="pt-2 border-t border-teal-100 space-y-3">
            <p className="text-xs font-medium text-teal-800">What does this proposal involve?</p>

            {/* Use-type scope questions */}
            <div className="space-y-2">
              {SCOPE_TOPIC_MAP.map(({ field, reason: _reason }) => {
                const labels: Record<string, { q: string; hint: string }> = {
                  has_commercial:           { q: 'Commercial or retail use?', hint: 'Shop, café, office, food premises' },
                  has_boarding_house:       { q: 'Boarding house or co-living?', hint: 'Affordable rental, shared accommodation' },
                  has_multi_dwelling:       { q: 'Multi-dwelling or dual occupancy?', hint: 'Two or more dwellings on one lot' },
                  is_subdivision:           { q: 'Land subdivision?', hint: 'Creating new lots' },
                  has_child_care:           { q: 'Child care or community facility?', hint: 'Day care, school, place of worship' },
                  has_home_business:        { q: 'Home business or home industry?', hint: 'Trade, professional, or light industry from home' },
                  has_tourist_accommodation:{ q: 'Tourist or short-term accommodation?', hint: 'B&B, serviced apartment, Airbnb' },
                  has_industrial:           { q: 'Industrial or warehouse use?', hint: 'Factory, storage, logistics' },
                };
                const config = labels[field];
                if (!config) return null;
                const lepAutoValue = (lepScopeDefaults as Record<string, boolean | null | undefined> | undefined)?.[field] ?? null;
                const userSavedValue = (worksScopeAnswers as Record<string, boolean | null | undefined> | null | undefined)?.[field] ?? null;
                const current = userSavedValue !== null ? userSavedValue : lepAutoValue;
                const isLepAuto = userSavedValue === null && lepAutoValue !== null;
                return (
                  <div key={field} className="flex items-start gap-2">
                    <span className="text-xs text-gray-600 flex-1 pt-0.5">
                      {config.q}
                      <span className="text-gray-400 ml-1">({config.hint})</span>
                    </span>
                    <div className="flex gap-1 flex-shrink-0 items-center">
                      {([true, false] as const).map(val => (
                        <button
                          key={String(val)}
                          onClick={() => onWorksScopeChange({
                            ...(worksScopeAnswers ?? { heritage_elements: null, has_commercial: null, has_boarding_house: null, has_multi_dwelling: null, is_subdivision: null, has_child_care: null, has_home_business: null, has_tourist_accommodation: null, has_industrial: null }),
                            [field]: current === val ? null : val,
                          })}
                          className={`px-2 py-0.5 text-xs rounded border transition-colors ${
                            current === val
                              ? val
                                ? 'bg-amber-100 border-amber-400 text-amber-800 font-medium'
                                : isLepAuto
                                  ? 'bg-gray-100 border-gray-300 text-gray-500 font-medium'
                                  : 'bg-teal-100 border-teal-400 text-teal-800 font-medium'
                              : 'bg-white border-gray-200 text-gray-500 hover:border-gray-300'
                          }`}
                        >
                          {val ? 'Yes' : 'No'}
                        </button>
                      ))}
                      {isLepAuto && (
                        <span className="text-[10px] text-gray-400 leading-none ml-0.5">zone</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Heritage element scope — only for heritage properties */}
            {heritage && (
              <div className="pt-2 border-t border-teal-100">
                <p className="text-xs font-medium text-teal-800 mb-1.5">
                  Which building elements does this proposal affect?
                  <span className="text-gray-400 font-normal ml-1">(select all that apply)</span>
                </p>
                <div className="grid grid-cols-2 gap-x-3 gap-y-1">
                  {HERITAGE_ELEMENTS.map(({ value, label }) => {
                    const selected = worksScopeAnswers?.heritage_elements?.includes(value) ?? false;
                    return (
                      <label key={value} className="flex items-center gap-1.5 text-xs text-gray-700 cursor-pointer hover:text-gray-900">
                        <input
                          type="checkbox"
                          checked={selected}
                          onChange={() => {
                            const current = worksScopeAnswers?.heritage_elements ?? [];
                            const next = selected
                              ? current.filter(e => e !== value)
                              : [...current, value];
                            onWorksScopeChange({
                              ...(worksScopeAnswers ?? { heritage_elements: null, has_commercial: null, has_boarding_house: null, has_multi_dwelling: null, is_subdivision: null, has_child_care: null, has_home_business: null, has_tourist_accommodation: null, has_industrial: null }),
                              heritage_elements: next,
                            });
                          }}
                          className="w-3.5 h-3.5 rounded border-teal-300 text-teal-600 focus:ring-teal-500 focus:ring-1"
                        />
                        {label}
                      </label>
                    );
                  })}
                </div>
                {(worksScopeAnswers?.heritage_elements?.length ?? 0) > 0 && (
                  <p className="text-xs text-teal-600 mt-1.5">
                    Heritage chapter will show controls for selected elements only.
                    General controls always shown.
                  </p>
                )}
              </div>
            )}
          </div>
        )}

        {/* Works description */}
        <div>
          <label className="block text-xs font-medium text-teal-800 mb-1">
            Works description <span className="text-red-400">*</span>
          </label>
          <textarea
            value={devWorksText}
            onChange={onDevWorksChange}
            placeholder="Dimensions, materials, location on site — e.g. Open-sided timber structure, 4.2m × 3.6m, 2.4m height, within the front setback"
            rows={2}
            className="w-full text-sm border border-teal-200 rounded px-3 py-2 resize-none focus:outline-none focus:ring-1 focus:ring-teal-400 bg-white placeholder:text-gray-400"
          />
        </div>

        {/* SEE description preview */}
        {devDescriptionLocal.trim() && (
          <div className="text-xs bg-white border border-teal-100 rounded px-2.5 py-1.5 text-gray-700">
            <span className="font-medium text-teal-600">SEE will read: </span>
            {devDescriptionLocal}
          </div>
        )}

        {/* Scope summary */}
        <div className="pt-2 border-t border-teal-100 space-y-1">
          {/* Previously-dismissed topics — undo only (topic assertions from prior sessions) */}
          {Object.entries(topicAssertions).map(([topic, reason]) => (
            <div key={topic} className="flex items-center gap-2 text-xs text-gray-400">
              <span className="w-3 font-bold">⊘</span>
              <span className="capitalize line-through flex-1">{topic.replace(/_/g, ' ')}</span>
              <span className="text-gray-300 truncate max-w-32" title={reason}>{reason}</span>
              <button onClick={() => onAssertTopicNA(topic, null)}
                className="text-xs text-teal-500 hover:text-teal-700 flex-shrink-0">undo</button>
            </div>
          ))}
          {/* Section count — primary scope signal */}
          {globalProgress && (
            <>
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-teal-800">Sections to assess:</span>
                <span className="text-xs font-bold text-teal-900">{globalProgress.scopeTotal}</span>
              </div>
              {globalProgress.triaged > 0 && (
                <div className="text-xs text-gray-400">
                  + {globalProgress.triaged} provisions excluded for your dev type
                </div>
              )}
            </>
          )}
          {/* Prompt to refine scope if questionnaire not yet run */}
          {!intakeAnswers && (
            <div className="flex items-center justify-between pt-0.5">
              <span className="text-xs text-gray-500">
                {ancillaryWorks.length > 0 ? 'Scope set from your selections' : 'Refine scope for your works'}
              </span>
              <button onClick={onRunIntake}
                className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800 ml-3 flex-shrink-0">
                {ancillaryWorks.length > 0 ? 'Review →' : 'Refine →'}
              </button>
            </div>
          )}
          {intakeSetAt && (
            <p className="text-xs text-gray-400">Scope set {intakeSetAt}</p>
          )}
        </div>

        {/* Corpus + progress */}
        {layerCounts && (
          <div className="pt-2 border-t border-teal-100 space-y-1.5">
            {/* Corpus breakdown by source */}
            <div>
              <div className="flex items-baseline gap-1.5 text-xs mb-0.5">
                <span className="font-semibold text-gray-700">All</span>
                <span className="text-gray-400">({layerCounts.generic + layerCounts.use_specific + layerCounts.condition + layerCounts.precinct})</span>
              </div>
              <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-xs text-gray-500 pl-2">
                {layerCounts.generic > 0 && (
                  <span>{genericLabel || 'LGA-wide'} ({layerCounts.generic})</span>
                )}
                {layerCounts.use_specific > 0 && (
                  <span>Zone-Specific ({layerCounts.use_specific})</span>
                )}
                {layerCounts.condition > 0 && (
                  <span>Heritage ({layerCounts.condition})</span>
                )}
                {layerCounts.precinct > 0 && (
                  <span>{precinctName || 'Precinct'} ({layerCounts.precinct})</span>
                )}
              </div>
            </div>
          </div>
        )}

      </div>

      {/* Progress bar + hero remaining count */}
      {globalProgress && globalProgress.scopeTotal > 0 && (
        <div className="px-4 py-3 border-t border-teal-200 bg-white/50 space-y-2">
          {/* Hero: progress bar + remaining count */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-2 bg-gray-200 rounded-full">
              <div
                className={`h-2 rounded-full transition-all ${
                  globalProgress.remaining === 0 ? 'bg-green-500' : 'bg-teal-500'
                }`}
                style={{ width: `${Math.round((globalProgress.assessed / globalProgress.scopeTotal) * 100)}%` }}
              />
            </div>
            <span className="text-lg font-bold text-gray-800 tabular-nums min-w-[3ch] text-right">
              {globalProgress.remaining}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-500">
              {globalProgress.remaining} of {globalProgress.scopeTotal} section{globalProgress.scopeTotal !== 1 ? 's' : ''} remaining
            </span>
            {globalProgress.remaining === 0 && (
              <span className="text-xs font-medium text-green-600">All assessed</span>
            )}
          </div>

          {/* Scope reduction waterfall — ALWAYS visible for audit trail */}
          {(globalProgress.triaged > 0 || globalProgress.chapterDismissed > 0 ||
            globalProgress.autoChapterDismissed > 0 ||
            globalProgress.topicDismissed > 0 || globalProgress.suppressed > 0 ||
            (globalProgress.questionnaireScoped ?? 0) > 0 || (globalProgress.heritageElementScoped ?? 0) > 0) && (
            <>
              <div className="bg-amber-50 border border-amber-200 rounded px-3 py-2 space-y-2">
                {/* Header */}
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-amber-900">How your scope was reduced</span>
                  <button
                    onClick={() => setShowWaterfall(v => !v)}
                    className="text-xs text-amber-600 hover:text-amber-800 ml-auto flex items-center gap-1"
                  >
                    <span className="text-[10px]">{showWaterfall ? '▾' : '▸'}</span>
                    {showWaterfall ? 'Hide' : 'Show'} details
                  </button>
                </div>

                {/* Summary line — always visible. All counts are provisions, scopeTotal is sections. */}
                <div className="text-xs text-amber-700 font-medium">
                  {`${globalProgress.total} total → ${globalProgress.provisionScopeTotal} provisions in scope (${globalProgress.scopeTotal} sections)`}
                </div>

                {/* Waterfall breakdown — expandable */}
                {showWaterfall && (
                  <div className="text-xs text-amber-700 space-y-1 pt-1 border-t border-amber-200 pl-2">
                    {globalProgress.triaged > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.triaged} have no provisions for your dev type</div>
                        {/* Show which topics were excluded */}
                        {(() => {
                          const excludedTopicCounts: Record<string, number> = {};
                          allProvisions.forEach(p => {
                            const cat = p.v2_structural_category;
                            if (cat && excludableTopics.has(cat)) {
                              excludedTopicCounts[cat] = (excludedTopicCounts[cat] || 0) + 1;
                            }
                          });
                          const excluded = Object.entries(excludedTopicCounts)
                            .sort((a, b) => b[1] - a[1])
                            .map(([t, c]) => `${t} (${c})`)
                            .join(', ');
                          return excluded ? (
                            <div className="text-amber-600 text-[11px] ml-1">Excluded: {excluded}</div>
                          ) : null;
                        })()}
                        <div className="text-amber-600 text-[11px] italic">Topics with 0 provisions for {devTypeLabel || 'your development type'}</div>
                      </div>
                    )}
                    {globalProgress.chapterDismissed > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.chapterDismissed} in chapters you dismissed</div>
                        <div className="text-amber-600 text-[11px] italic">You dismissed entire DCP chapters from scope</div>
                      </div>
                    )}
                    {globalProgress.autoChapterDismissed > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.autoChapterDismissed} in chapters auto-excluded</div>
                        <div className="text-amber-600 text-[11px] italic">No provisions in these chapters apply to your development type</div>
                      </div>
                    )}
                    {globalProgress.topicDismissed > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.topicDismissed} in topics you dismissed</div>
                        <div className="text-amber-600 text-[11px] italic">You stated these topics don't apply (e.g. &ldquo;No new signage&rdquo;)</div>
                      </div>
                    )}
                    {globalProgress.suppressed > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.suppressed} objectives &amp; heritage descriptive provisions</div>
                        <div className="text-amber-600 text-[11px] italic">
                          Policy statements (objectives = intent; heritage descriptives = character guidance).
                          Not individually assessed — they don&apos;t require binary Complies/Varies/N/A responses.{' '}
                          <button
                            onClick={() => { if (onToggleObjectives) onToggleObjectives(); }}
                            className="text-amber-700 hover:underline font-medium"
                          >
                            (Can toggle to view them)
                          </button>
                        </div>
                      </div>
                    )}
                    {(globalProgress.questionnaireScoped ?? 0) > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.questionnaireScoped} use-type provisions out of scope</div>
                        <div className="text-amber-600 text-[11px] italic">Excluded by LEP zone restrictions or questionnaire answers (commercial, boarding house, multi-dwelling, etc.)</div>
                      </div>
                    )}
                    {(globalProgress.heritageElementScoped ?? 0) > 0 && (
                      <div>
                        <div className="font-medium">− {globalProgress.heritageElementScoped} heritage provisions for elements not in scope</div>
                        <div className="text-amber-600 text-[11px] italic">Heritage controls for building elements not involved in your proposal</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </>
          )}
        </div>
      )}

      {/* DA Bundle Checklist — shown when dev type is selected */}
      {devType && (
        <div className="px-4 pb-4 pt-2">
          <DABundleChecklist
            inputs={{
              devType,
              isHeritage: heritage,
              hcaName: hcaName ?? null,
              lotArea: lotArea ?? null,
              floodProne: intakeAnswers?.flood_prone,
              bushfireProne: intakeAnswers?.bushfire_prone,
              contaminatedLand: intakeAnswers?.contaminated_land,
            }}
          />
        </div>
      )}
    </div>
  );
}
