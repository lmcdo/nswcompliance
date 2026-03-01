'use client';

import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { DEV_TYPE_OPTIONS } from '@/lib/see/devTypes';
import type { IntakeAnswers } from '@/lib/see/intake';

interface DAModeCardProps {
  devType: string;
  devWorksText: string;
  devDescriptionLocal: string;
  intakeAnswers: IntakeAnswers | null;
  intakeSkipped: boolean;
  daResponses: Map<number, { response_text: string | null; compliance_status: string | null }>;
  allProvisions: any[];
  excludableTopics: Set<string>;
  onDevTypeChange: (val: string) => void;
  onDevWorksChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onRunIntake: () => void;
}

export function DAModeCard({
  devType,
  devWorksText,
  devDescriptionLocal,
  intakeAnswers,
  intakeSkipped,
  daResponses,
  allProvisions,
  excludableTopics,
  onDevTypeChange,
  onDevWorksChange,
  onRunIntake,
}: DAModeCardProps) {
  const [showTopicBreakdown, setShowTopicBreakdown] = useState(false);

  const completionStats = useMemo(() => {
    const intakeExcluded = allProvisions.filter(p => {
      const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
      return t && excludableTopics.has(t);
    }).length;
    const assessed = daResponses.size - intakeExcluded;
    const remaining = allProvisions.length - daResponses.size;
    return {
      assessed: Math.max(0, assessed),
      intakeExcluded,
      remaining: Math.max(0, remaining),
      total: allProvisions.length,
    };
  }, [allProvisions, daResponses, excludableTopics]);

  const topicProgress = useMemo(() => {
    const byTopic: Record<string, { total: number; assessed: number; excluded: boolean }> = {};
    for (const p of allProvisions) {
      const topic = (p.v2_topic || 'general').toLowerCase().replace(/ /g, '_');
      if (!byTopic[topic]) byTopic[topic] = { total: 0, assessed: 0, excluded: false };
      byTopic[topic].total++;
      if (daResponses.has(p.id)) byTopic[topic].assessed++;
      if (excludableTopics.has(topic)) byTopic[topic].excluded = true;
    }
    return Object.entries(byTopic).sort((a, b) => b[1].total - a[1].total);
  }, [allProvisions, daResponses, excludableTopics]);

  return (
    <div className="mb-4 bg-teal-50 border border-teal-200 rounded-lg overflow-hidden">
      <div className="px-4 py-2.5 flex items-center gap-2 text-sm text-teal-800">
        <span className="w-2 h-2 rounded-full bg-teal-500 inline-block flex-shrink-0" />
        <span className="font-medium">DA Mode</span>
        <span className="text-teal-600 text-xs">— compliance notes saved to your session</span>
      </div>

      <div className="px-4 pb-3 border-t border-teal-100 space-y-2 mt-2">

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

        {/* Description preview / gate message */}
        {devDescriptionLocal.trim() ? (
          <div className="text-xs bg-white border border-teal-100 rounded px-2.5 py-1.5 text-gray-700">
            <span className="font-medium text-teal-600">SEE will read: </span>
            {devDescriptionLocal}
          </div>
        ) : (
          <p className="text-xs text-amber-600">Select a type and describe the works to enable the SEE Draft export.</p>
        )}

        {/* Intake status + re-run */}
        <div className="flex items-center justify-between pt-0.5">
          {intakeAnswers ? (
            <span className="text-xs text-teal-700">
              <span className="font-medium">Intake completed</span>
              <span className="text-teal-600"> — provisions triaged across full property set</span>
            </span>
          ) : intakeSkipped ? (
            <span className="text-xs text-gray-500">Intake skipped — no automatic exclusions</span>
          ) : (
            <span className="text-xs text-gray-400">Intake not yet completed</span>
          )}
          <button
            onClick={onRunIntake}
            className="text-xs text-teal-600 underline underline-offset-2 hover:text-teal-800 ml-3 flex-shrink-0"
          >
            {intakeAnswers ? 'Re-run intake' : 'Run intake'}
          </button>
        </div>

        {/* Completion dashboard */}
        {completionStats.total > 0 && (
          <div className="pt-1.5 border-t border-teal-100">
            <div className="flex items-center gap-4 text-xs">
              <span className="flex items-center gap-1 text-teal-700">
                <span className="text-teal-500 font-bold">✓</span>
                <span className="font-medium">{completionStats.assessed}</span> assessed
              </span>
              <span className="flex items-center gap-1 text-gray-500">
                <span className="font-bold">○</span>
                <span className="font-medium">{completionStats.intakeExcluded}</span> intake-excluded
              </span>
              <span className="flex items-center gap-1 text-amber-600">
                <span className="font-bold">●</span>
                <span className="font-medium">{completionStats.remaining}</span> not yet reviewed
              </span>
            </div>

            {/* Topic breakdown toggle */}
            <button
              onClick={() => setShowTopicBreakdown(v => !v)}
              className="mt-1.5 flex items-center gap-1 text-xs text-teal-600 hover:text-teal-800"
            >
              {showTopicBreakdown ? (
                <><ChevronUp className="w-3 h-3" /> Hide topic breakdown</>
              ) : (
                <><ChevronDown className="w-3 h-3" /> Show topic breakdown</>
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
                          <span className="text-gray-400 italic">excluded</span>
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
