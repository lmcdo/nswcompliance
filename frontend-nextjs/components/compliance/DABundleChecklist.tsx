'use client';

import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { getDaBundleChecklist, summariseChecklist, type DaBundleInputs, type ChecklistStatus } from '@/lib/see/daBundleChecklist';

const STATUS_CONFIG: Record<ChecklistStatus, { label: string; cls: string; dot: string }> = {
  required:     { label: 'Required',     cls: 'bg-red-50 text-red-800 border-red-200',    dot: 'bg-red-500' },
  likely:       { label: 'Likely',       cls: 'bg-amber-50 text-amber-800 border-amber-200', dot: 'bg-amber-400' },
  not_required: { label: 'Not required', cls: 'bg-gray-50 text-gray-500 border-gray-200',  dot: 'bg-gray-300' },
  unknown:      { label: 'Confirm',      cls: 'bg-blue-50 text-blue-800 border-blue-200',  dot: 'bg-blue-400' },
};

interface DABundleChecklistProps {
  inputs: DaBundleInputs;
}

export function DABundleChecklist({ inputs }: DABundleChecklistProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  const items = getDaBundleChecklist(inputs);
  const summary = summariseChecklist(items);

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header — always visible */}
      <button
        onClick={() => setIsExpanded(v => !v)}
        className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div>
          <span className="text-sm font-medium text-gray-800">DA Documentation Bundle</span>
          <div className="flex items-center gap-3 mt-0.5">
            {summary.required > 0 && (
              <span className="text-xs text-red-700">
                <span className="font-semibold">{summary.required}</span> required
              </span>
            )}
            {summary.likely > 0 && (
              <span className="text-xs text-amber-700">
                <span className="font-semibold">{summary.likely}</span> likely
              </span>
            )}
            {summary.unknown > 0 && (
              <span className="text-xs text-blue-700">
                <span className="font-semibold">{summary.unknown}</span> confirm
              </span>
            )}
          </div>
        </div>
        <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Expanded checklist */}
      {isExpanded && (
        <div className="divide-y divide-gray-100">
          {items.map((item, i) => {
            const cfg = STATUS_CONFIG[item.status];
            return (
              <div key={i} className="px-4 py-3 flex items-start gap-3">
                {/* Status dot */}
                <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-gray-800">{item.document}</span>
                    <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${cfg.cls}`}>
                      {cfg.label}
                    </span>
                    {item.who && (
                      <span className="text-xs text-gray-400">{item.who}</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5">{item.trigger}</p>
                  {item.cost_range && (
                    <p className="text-xs text-gray-400 mt-0.5">Typical cost: {item.cost_range}</p>
                  )}
                </div>
              </div>
            );
          })}

          {/* Disclaimer */}
          <div className="px-4 py-2.5 bg-gray-50">
            <p className="text-xs text-gray-400 italic">
              Document requirements depend on the specific proposal. Confirm with Council's DA lodgement checklist and a qualified town planner before lodging.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
