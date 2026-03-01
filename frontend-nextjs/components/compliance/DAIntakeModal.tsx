'use client';

import { useState, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  INTAKE_QUESTIONS,
  DEFAULT_INTAKE_ANSWERS,
  getExcludableTopics,
  type IntakeAnswers,
} from '@/lib/see/intake';

interface DAIntakeModalProps {
  open: boolean;
  /** Called with confirmed answers when user clicks Apply. */
  onApply: (answers: IntakeAnswers) => void;
  /** Called when user clicks Skip — no answers saved. */
  onSkip: () => void;
  /** Total number of provisions currently visible, used for the N/A count estimate. */
  totalProvisions?: number;
  /** The full provision list for computing exact N/A count. */
  provisions?: Array<{ v2_topic?: string | null }>;
}

type AnswerValue = 'yes' | 'no' | 'unknown';

const ANSWER_OPTIONS: { value: AnswerValue; label: string }[] = [
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' },
  { value: 'unknown', label: "Don't know" },
];

export function DAIntakeModal({
  open,
  onApply,
  onSkip,
  provisions = [],
}: DAIntakeModalProps) {
  const [answers, setAnswers] = useState<IntakeAnswers>({ ...DEFAULT_INTAKE_ANSWERS });

  const setAnswer = (field: keyof IntakeAnswers, value: AnswerValue) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  // Live count of provisions that will be auto-excluded given current answers
  const excludedCount = useMemo(() => {
    const excludable = getExcludableTopics(answers);
    if (excludable.size === 0) return 0;
    return provisions.filter(p => {
      const t = (p.v2_topic || '').toLowerCase().replace(/ /g, '_');
      return t && excludable.has(t);
    }).length;
  }, [answers, provisions]);

  const handleApply = () => {
    onApply(answers);
    // Reset for next open (e.g. if user re-opens)
    setAnswers({ ...DEFAULT_INTAKE_ANSWERS });
  };

  return (
    <Dialog open={open} onOpenChange={() => {/* controlled — user must Apply or Skip */}}>
      <DialogContent
        className="max-w-lg"
        onPointerDownOutside={e => e.preventDefault()}
        onEscapeKeyDown={e => e.preventDefault()}
      >
        <DialogHeader>
          <DialogTitle className="font-serif text-xl">Describe your development</DialogTitle>
          <p className="text-sm text-gray-500 mt-1">
            Answer these factual questions to automatically triage inapplicable provisions.
            Provisions are only excluded when their trigger is factually impossible — if unsure, choose "Don't know".
          </p>
        </DialogHeader>

        <div className="mt-4 space-y-4">
          {INTAKE_QUESTIONS.map(q => (
            <div key={q.field} className="rounded-lg border border-gray-100 bg-gray-50/50 px-4 py-3">
              <p className="text-sm font-medium text-gray-800">{q.question}</p>
              <p className="text-xs text-gray-500 mt-0.5 mb-2">{q.detail}</p>
              <div className="flex gap-2">
                {ANSWER_OPTIONS.map(opt => (
                  <button
                    key={opt.value}
                    onClick={() => setAnswer(q.field, opt.value)}
                    className={`text-xs px-3 py-1 rounded border font-medium transition-all ${
                      answers[q.field] === opt.value
                        ? opt.value === 'no'
                          ? 'bg-gray-200 border-gray-400 text-gray-800 ring-2 ring-offset-1 ring-gray-400'
                          : opt.value === 'yes'
                          ? 'bg-teal-100 border-teal-400 text-teal-800 ring-2 ring-offset-1 ring-teal-400'
                          : 'bg-blue-50 border-blue-300 text-blue-700 ring-2 ring-offset-1 ring-blue-300'
                        : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="mt-5 flex items-center justify-between border-t border-gray-100 pt-4">
          <div className="text-sm text-gray-500">
            {excludedCount > 0 ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />
                <strong>{excludedCount}</strong> provision{excludedCount !== 1 ? 's' : ''} across all topics will be set N/A
              </span>
            ) : (
              <span className="text-gray-400">No provisions excluded yet</span>
            )}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={onSkip}
              className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2"
            >
              Skip for now
            </button>
            <button
              onClick={handleApply}
              className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
            >
              Apply triage
            </button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
