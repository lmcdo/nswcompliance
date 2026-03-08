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
  onRunIntake: () => void;
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
  /** Global progress — single source of truth from ProvisionsByTocStructure */
  globalProgress?: {
    total: number; triaged: number; chapterDismissed: number;
    topicDismissed: number; suppressed: number;
    scopeTotal: number; assessed: number; remaining: number;
  } | null;
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
  globalProgress,
}: DAModeCardProps) {
  const [pendingDismiss, setPendingDismiss] = useState<string | null>(null);
  const [customReason, setCustomReason] = useState('');
  const [showWaterfall, setShowWaterfall] = useState(false);

  // Derive scope summary and heritage count (progress now comes from globalProgress prop)
  const derivedStats = useMemo(() => {
    let heritagePros = 0;

    for (const p of allProvisions) {
      const layer = p.v2_dcp_layer || p.layer;
      if (layer === 'condition') heritagePros++;
    }

    // Scope summary — non-condition-layer provisions only
    const includedTopics: { topic: string; count: number }[] = [];
    const excludedTopics: { topic: string; count: number }[] = [];
    const scopeByTopic: Record<string, number> = {};
    for (const p of allProvisions) {
      if ((p.v2_dcp_layer || p.layer) === 'condition') continue;
      const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
      if (!t) continue;
      scopeByTopic[t] = (scopeByTopic[t] || 0) + 1;
    }
    for (const [topic, count] of Object.entries(scopeByTopic).sort((a, b) => b[1] - a[1])) {
      if (excludableTopics.has(topic)) {
        excludedTopics.push({ topic, count });
      } else {
        includedTopics.push({ topic, count });
      }
    }

    return {
      scopeSummary: { included: includedTopics, excluded: excludedTopics },
      heritagePros,
    };
  }, [allProvisions, excludableTopics, topicAssertions]);

  const { scopeSummary, heritagePros } = derivedStats;

  return (
    <div className="mb-4 bg-teal-50 border border-teal-200 rounded-lg overflow-hidden">

      <div className="px-4 pb-4 pt-3 space-y-3">

        {/* LEP controls summary — height and FSR inline */}
        {(lepHeight || lepFsr) && (
          <div className="flex gap-4 text-xs bg-white border border-teal-100 rounded px-3 py-2">
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
            {DEV_TYPE_OPTIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Ancillary works checkboxes — shown after primary type selected */}
        {devType && (
          <div>
            <label className="block text-xs font-medium text-teal-800 mb-1.5">
              Ancillary development <span className="text-gray-400 font-normal">(select all that apply)</span>
            </label>
            <div className="grid grid-cols-2 gap-x-3 gap-y-1">
              {ANCILLARY_WORKS.map(work => {
                const checked = ancillaryWorks.includes(work.value);
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
                  </label>
                );
              })}
            </div>
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

        {/* Scope summary — shown after intake, replaces simple "intake completed" line */}
        {intakeAnswers ? (
          <div className="pt-2 border-t border-teal-100">
            <div className="flex items-center justify-between mb-0.5">
              <span className="text-xs font-medium text-teal-800">Topics to assess</span>
              <button
                onClick={onRunIntake}
                className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800"
              >
                Reconfigure
              </button>
            </div>
            <p className="text-xs text-gray-400 mb-2">
              Click Reconfigure to change your development type or ancillary development. To exclude a topic category, hover it and click ×.
            </p>

            <div className="space-y-1">
              {/* Heritage — always first if property has HCA */}
              {heritage && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-teal-500 font-bold w-3">✓</span>
                  <span className="font-medium text-gray-700">
                    Heritage{hcaName ? ` — ${hcaName}` : ' Conservation Area'}
                  </span>
                  <span className="text-gray-400 ml-auto">{heritagePros}</span>
                </div>
              )}
              {/* Precinct — second if applies */}
              {precinctName && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-teal-500 font-bold w-3">✓</span>
                  <span className="font-medium text-gray-700">{precinctName}</span>
                </div>
              )}
              {/* Other included topics — dismissible */}
              {scopeSummary.included
                .filter(({ topic }) => !topic.includes('heritage') && !topicAssertions[topic])
                .slice(0, 8)
                .map(({ topic, count }) => (
                  <div key={topic}>
                    <div className="flex items-center gap-2 text-xs group">
                      <span className="text-teal-500 font-bold w-3">✓</span>
                      <span className="text-gray-600 capitalize flex-1">{topic.replace(/_/g, ' ')}</span>
                      <span className="text-gray-400">{count}</span>
                      <button
                        onClick={() => setPendingDismiss(topic)}
                        className="opacity-0 group-hover:opacity-100 text-gray-300 hover:text-red-400 transition-opacity ml-1 text-xs"
                        title="Dismiss — does not apply to this project"
                      >×</button>
                    </div>
                    {pendingDismiss === topic && (
                      <div className="ml-5 mt-1 mb-1 bg-white border border-gray-200 rounded p-2 space-y-1">
                        {PRESET_REASONS(topic).map(r => (
                          <button key={r} onClick={() => { onAssertTopicNA(topic, r); setPendingDismiss(null); }}
                            className="block w-full text-left text-xs px-2 py-1 rounded hover:bg-gray-50 text-gray-600">
                            {r}
                          </button>
                        ))}
                        <div className="flex gap-1 pt-1">
                          <input value={customReason} onChange={e => setCustomReason(e.target.value)}
                            placeholder="Other reason…" className="flex-1 text-xs border rounded px-2 py-1" />
                          <button onClick={() => { if (customReason.trim()) { onAssertTopicNA(topic, customReason.trim()); setPendingDismiss(null); setCustomReason(''); }}}
                            className="text-xs px-2 py-1 bg-teal-600 text-white rounded hover:bg-teal-700">OK</button>
                        </div>
                        <button onClick={() => setPendingDismiss(null)} className="text-xs text-gray-400 hover:text-gray-600">Cancel</button>
                      </div>
                    )}
                  </div>
                ))}
              {/* Asserted-out topics — planner dismissed */}
              {Object.entries(topicAssertions).map(([topic, reason]) => (
                <div key={topic} className="flex items-center gap-2 text-xs text-gray-400">
                  <span className="w-3 font-bold">⊘</span>
                  <span className="capitalize line-through flex-1">{topic.replace(/_/g, ' ')}</span>
                  <span className="text-gray-300 truncate max-w-32" title={reason}>{reason}</span>
                  <button onClick={() => onAssertTopicNA(topic, null)}
                    className="text-xs text-teal-500 hover:text-teal-700 flex-shrink-0">undo</button>
                </div>
              ))}
              {/* Nudge strip — visible until first assertion made */}
              {Object.keys(topicAssertions).length === 0 && scopeSummary.included.filter(t => !t.topic.includes('heritage')).length > 2 && (
                <div className="mt-2 px-2.5 py-2 bg-white border border-teal-200 rounded text-xs text-teal-700 leading-relaxed">
                  <span className="font-semibold">Topics that don{"'"}t apply?</span>{' '}Hover and click{' '}<span className="font-mono font-bold">{'\u00d7'}</span>{' \u2014 '}state the basis (e.g. &ldquo;No pool works proposed&rdquo;) and the entire category is professionally excluded. Your stated reason is recorded in the SEE, which is the correct way to handle non-applicable topics.
                </div>
              )}
              {/* Excluded — always visible */}
              {scopeSummary.excluded.length > 0 && (
                <div className="pt-0.5">
                  <p className="text-xs text-gray-400 mb-0.5 pl-1">
                    {scopeSummary.excluded.length} topic{scopeSummary.excluded.length !== 1 ? 's' : ''} not applicable to your works
                  </p>
                  <div className="space-y-0.5 ml-1">
                    {scopeSummary.excluded.map(({ topic, count }) => (
                      <div key={topic} className="flex items-center gap-2 text-xs text-gray-400">
                        <span className="w-3 text-gray-300 font-bold">✕</span>
                        <span className="capitalize line-through">{topic.replace(/_/g, ' ')}</span>
                        <span className="ml-auto">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
            {intakeSetAt && (
              <p className="text-xs text-gray-400 mt-2">Scope set {intakeSetAt}</p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between pt-1 border-t border-teal-100">
            <span className="text-xs text-gray-500">
              {ancillaryWorks.length > 0 ? 'Scope set from your selections — review to override' : 'Filter out provisions that don\'t apply'}
            </span>
            <button
              onClick={onRunIntake}
              className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800 ml-3 flex-shrink-0"
            >
              {ancillaryWorks.length > 0 ? 'Review scope →' : 'Set scope →'}
            </button>
          </div>
        )}

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
              {globalProgress.remaining} of {globalProgress.scopeTotal} remaining
            </span>
            {globalProgress.remaining === 0 && (
              <span className="text-xs font-medium text-green-600">All assessed</span>
            )}
          </div>

          {/* Collapsible waterfall */}
          {(globalProgress.triaged > 0 || globalProgress.chapterDismissed > 0 ||
            globalProgress.topicDismissed > 0 || globalProgress.suppressed > 0) && (
            <>
              <button
                onClick={() => setShowWaterfall(v => !v)}
                className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
              >
                <span className="text-[10px]">{showWaterfall ? '▾' : '▸'}</span>
                How your scope was reduced
              </button>
              {showWaterfall && (
                <div className="text-xs text-gray-400 space-y-0.5 pl-2">
                  <div>{globalProgress.total} provisions in DCP for this property</div>
                  {globalProgress.triaged > 0 && (
                    <div className="pl-2">− {globalProgress.triaged} not applicable to your works</div>
                  )}
                  {globalProgress.chapterDismissed > 0 && (
                    <div className="pl-2">− {globalProgress.chapterDismissed} in dismissed chapters</div>
                  )}
                  {globalProgress.topicDismissed > 0 && (
                    <div className="pl-2">− {globalProgress.topicDismissed} in dismissed topics</div>
                  )}
                  {globalProgress.suppressed > 0 && (
                    <div className="pl-2">− {globalProgress.suppressed} objectives/descriptive</div>
                  )}
                  <div className="font-medium text-gray-600 pt-0.5 border-t border-gray-200">
                    = {globalProgress.scopeTotal} in your assessment scope
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}
