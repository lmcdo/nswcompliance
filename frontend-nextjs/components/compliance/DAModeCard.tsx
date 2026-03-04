'use client';

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
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
}

export function DAModeCard({
  devType,
  devWorksText,
  devDescriptionLocal,
  intakeAnswers,
  daResponses,
  allProvisions,
  excludableTopics,
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
}: DAModeCardProps) {
  const [showTopicBreakdown, setShowTopicBreakdown] = useState(false);
  const [showExcluded, setShowExcluded] = useState(false);

  // Single pass over allProvisions to derive all stats
  const derivedStats = useMemo(() => {
    const byTopic: Record<string, { total: number; assessed: number; excluded: boolean }> = {};
    const excludedIds = new Set<number>();
    let heritagePros = 0;

    for (const p of allProvisions) {
      const layer = p.v2_dcp_layer || p.layer;
      if (layer === 'condition') heritagePros++;

      const topic = (p.v2_topic || 'general').toLowerCase().replace(/ /g, '_');
      if (!byTopic[topic]) byTopic[topic] = { total: 0, assessed: 0, excluded: false };
      byTopic[topic].total++;
      if (daResponses.has(p.id)) byTopic[topic].assessed++;
      if (excludableTopics.has(topic)) {
        byTopic[topic].excluded = true;
        excludedIds.add(p.id);
      }
    }

    // Assessed = responses whose provision is NOT intake-excluded
    let intakeExcludedResponseCount = 0;
    for (const id of daResponses.keys()) {
      if (excludedIds.has(id)) intakeExcludedResponseCount++;
    }
    const assessed = Math.max(0, daResponses.size - intakeExcludedResponseCount);
    const remaining = Math.max(0, allProvisions.length - daResponses.size);

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
      completionStats: {
        assessed,
        intakeExcluded: intakeExcludedResponseCount,
        remaining,
        total: allProvisions.length,
      },
      topicProgress: Object.entries(byTopic).sort((a, b) => b[1].total - a[1].total),
      scopeSummary: { included: includedTopics, excluded: excludedTopics },
      heritagePros,
    };
  }, [allProvisions, daResponses, excludableTopics]);

  const { completionStats, topicProgress, scopeSummary, heritagePros } = derivedStats;

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
        {devDescriptionLocal.trim() ? (
          <div className="text-xs bg-white border border-teal-100 rounded px-2.5 py-1.5 text-gray-700">
            <span className="font-medium text-teal-600">SEE will read: </span>
            {devDescriptionLocal}
          </div>
        ) : (
          <p className="text-xs text-amber-600">Select a type and describe the works to enable SEE export.</p>
        )}

        {/* Scope summary — shown after intake, replaces simple "intake completed" line */}
        {intakeAnswers ? (
          <div className="pt-2 border-t border-teal-100">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-medium text-teal-800">Your applicable scope</span>
              <button
                onClick={onRunIntake}
                className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800"
              >
                Reconfigure
              </button>
            </div>

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
              {/* Other included topics */}
              {scopeSummary.included
                .filter(({ topic }) => !topic.includes('heritage'))
                .slice(0, 5)
                .map(({ topic, count }) => (
                  <div key={topic} className="flex items-center gap-2 text-xs">
                    <span className="text-teal-500 font-bold w-3">✓</span>
                    <span className="text-gray-600 capitalize">{topic.replace(/_/g, ' ')}</span>
                    <span className="text-gray-400 ml-auto">{count}</span>
                  </div>
                ))}
              {/* Excluded — collapsible toggle */}
              {scopeSummary.excluded.length > 0 && (
                <div className="pt-0.5">
                  <button
                    onClick={() => setShowExcluded(v => !v)}
                    className="text-xs text-gray-400 hover:text-gray-600 flex items-center gap-1"
                  >
                    {showExcluded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    {scopeSummary.excluded.length} topic{scopeSummary.excluded.length !== 1 ? 's' : ''} removed by triage
                  </button>
                  {showExcluded && (
                    <div className="mt-1 space-y-0.5 ml-1">
                      {scopeSummary.excluded.map(({ topic, count }) => (
                        <div key={topic} className="flex items-center gap-2 text-xs text-gray-400">
                          <span className="w-3 text-gray-300 font-bold">✕</span>
                          <span className="capitalize line-through">{topic.replace(/_/g, ' ')}</span>
                          <span className="ml-auto">{count}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
            {intakeSetAt && (
              <p className="text-xs text-gray-400 mt-2">Scope set {intakeSetAt}</p>
            )}
          </div>
        ) : (
          <div className="flex items-center justify-between pt-1 border-t border-teal-100">
            <span className="text-xs text-gray-500">Run triage to remove inapplicable provisions</span>
            <button
              onClick={onRunIntake}
              className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800 ml-3 flex-shrink-0"
            >
              Run triage →
            </button>
          </div>
        )}

        {/* Completion dashboard */}
        {completionStats.total > 0 && (
          <div className="pt-2 border-t border-teal-100">
            <div className="flex items-center gap-3 text-xs">
              <span className="text-amber-700 font-semibold">
                {completionStats.remaining} to assess
              </span>
              <span className="text-gray-300">·</span>
              <span className="text-teal-600">{completionStats.assessed} done</span>
              {completionStats.intakeExcluded > 0 && (
                <>
                  <span className="text-gray-300">·</span>
                  <span className="text-gray-400">{completionStats.intakeExcluded} excluded</span>
                </>
              )}
            </div>

            <button
              onClick={() => setShowTopicBreakdown(v => !v)}
              className="mt-1.5 flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800"
            >
              {showTopicBreakdown ? (
                <><ChevronUp className="w-3 h-3" /> Hide topic progress</>
              ) : (
                <><ChevronDown className="w-3 h-3" /> Show topic progress</>
              )}
            </button>

            {showTopicBreakdown && (
              <div className="mt-2 space-y-1">
                {topicProgress.map(([topic, stats]) => {
                  const pct = stats.total > 0 ? (stats.assessed / stats.total) * 100 : 0;
                  const displayTopic = topic.replace(/_/g, ' ');
                  return (
                    <div key={topic} className="flex items-center gap-2 text-xs">
                      <span className="w-28 text-gray-600 truncate capitalize flex-shrink-0">{displayTopic}</span>
                      <div className="flex-1 bg-gray-200 rounded-full h-1.5 min-w-0">
                        <div
                          className={`h-1.5 rounded-full transition-all ${stats.excluded ? 'bg-gray-400' : 'bg-teal-500'}`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-gray-500 flex-shrink-0 w-12 text-right">
                        {stats.excluded ? (
                          <span className="text-gray-400 italic">out</span>
                        ) : (
                          `${stats.assessed}/${stats.total}`
                        )}
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
}
