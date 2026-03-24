'use client';

import { useState, useMemo, useLayoutEffect, useRef } from 'react';
import { Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import {
  INTAKE_QUESTIONS,
  DEFAULT_INTAKE_ANSWERS,
  AUTO_ANSWER_SOURCES,
  getExcludableTopics,
  type IntakeAnswers,
} from '@/lib/see/intake';
import { ANCILLARY_WORKS } from '@/lib/see/ancillaryWorks';

/** Fields that are auto-derived from scope (ancillary works checkboxes) */
const SCOPE_DERIVED_FIELDS = new Set<keyof IntakeAnswers>([
  ...ANCILLARY_WORKS.filter(w => w.intakeField).map(w => w.intakeField!) as (keyof IntakeAnswers)[],
  'new_impervious_surfaces', // always auto-derived from primary type + ancillary
]);

interface DAIntakeModalProps {
  open: boolean;
  onApply: (answers: IntakeAnswers) => Promise<void>;
  onSkip: () => void;
  provisions?: Array<{ v2_topic?: string | null; v2_dcp_layer?: string | null; layer?: string | null; v2_structural_category?: string | null }>;
  /** Pre-populate answers when reconfiguring (from a prior applied session) */
  initialAnswers?: IntakeAnswers;
  /** Property-level flags for first-class passenger display */
  heritage?: boolean;
  hcaName?: string;
  precinctName?: string;
  /** Whether ancillary works checkboxes are active (enables review mode) */
  hasAncillaryScope?: boolean;
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
  initialAnswers,
  heritage,
  hcaName,
  precinctName,
  hasAncillaryScope = false,
}: DAIntakeModalProps) {
  const [answers, setAnswers] = useState<IntakeAnswers>(
    initialAnswers ? { ...initialAnswers } : { ...DEFAULT_INTAKE_ANSWERS }
  );
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [confirmedAnswers, setConfirmedAnswers] = useState<IntakeAnswers | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  // Tracks which auto-answered fields the planner has manually overridden
  const [overriddenFields, setOverriddenFields] = useState<Set<keyof IntakeAnswers>>(new Set());

  // Reset all internal state whenever the modal transitions from closed → open,
  // so stale confirmation/error state never bleeds into a fresh open.
  // useLayoutEffect fires before paint → no visible flash.
  const prevOpenRef = useRef(false);
  const initialAnswersRef = useRef(initialAnswers);
  initialAnswersRef.current = initialAnswers;
  useLayoutEffect(() => {
    if (open && !prevOpenRef.current) {
      const ia = initialAnswersRef.current;
      setAnswers(ia ? { ...ia } : { ...DEFAULT_INTAKE_ANSWERS });
      setShowConfirmation(false);
      setConfirmedAnswers(null);
      setIsSubmitting(false);
      setSubmitError(null);
      setOverriddenFields(new Set());
    }
    prevOpenRef.current = open;
  }, [open]);

  const setAnswer = (field: keyof IntakeAnswers, value: AnswerValue) => {
    setAnswers(prev => ({ ...prev, [field]: value }));
  };

  // Single memo for excludable topics — used by all three derived counts below
  const excludableTopics = useMemo(
    () => getExcludableTopics(answers),
    [answers]
  );

  const excludedCount = useMemo(() => {
    if (excludableTopics.size === 0) return 0;
    return provisions.filter(p => {
      const cat = p.v2_structural_category;
      return cat && excludableTopics.has(cat);
    }).length;
  }, [excludableTopics, provisions]);

  // Excluded structural categories for confirmation screen display
  const excludedCategoryCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of provisions) {
      const cat = p.v2_structural_category;
      if (cat && excludableTopics.has(cat)) {
        counts[cat] = (counts[cat] || 0) + 1;
      }
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [excludableTopics, provisions]);

  const applicableCount = useMemo(() => {
    return provisions.filter(p => {
      const cat = p.v2_structural_category;
      return !cat || !excludableTopics.has(cat);
    }).length;
  }, [excludableTopics, provisions]);

  const handleApply = () => {
    setConfirmedAnswers(answers);
    setShowConfirmation(true);
  };

  const handleDone = async () => {
    if (!confirmedAnswers || isSubmitting) return;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      await onApply(confirmedAnswers);
      // parent calls setShowIntakeModal(false) on success — no state reset needed here
    } catch {
      setSubmitError('Failed to save. Check your connection and try again.');
      setIsSubmitting(false);
    }
  };

  /** Check if a field is auto-answered from property data (either 'yes' or 'no') */
  const isPropertyAutoAnswered = (field: keyof IntakeAnswers) =>
    AUTO_ANSWER_SOURCES[field] &&
    (initialAnswers?.[field] === 'no' || initialAnswers?.[field] === 'yes') &&
    !overriddenFields.has(field);

  /** Check if a field is auto-derived from scope (ancillary checkboxes) */
  const isScopeDerived = (field: keyof IntakeAnswers) =>
    hasAncillaryScope && SCOPE_DERIVED_FIELDS.has(field) && !overriddenFields.has(field);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) onSkip(); }}>
      <DialogContent className="max-w-lg flex flex-col max-h-[90vh]">
        {showConfirmation ? (
          /* Confirmation screen */
          <div className="py-2">
            <div className="flex items-center gap-2 mb-1">
              <span className="w-5 h-5 rounded-full bg-teal-500 flex items-center justify-center flex-shrink-0">
                <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </span>
              <h2 className="text-lg font-semibold text-gray-900">Scope configured</h2>
            </div>
            <p className="text-sm text-gray-500 mb-4 ml-7">
              <span className="font-semibold text-gray-700">{applicableCount}</span> provisions apply to this assessment.
            </p>

            {/* First-class passengers */}
            <div className="ml-7 space-y-1 mb-4">
              {heritage && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-teal-500 font-bold text-xs">✓</span>
                  <span className="font-medium text-gray-700">Heritage{hcaName ? ` — ${hcaName}` : ' Conservation Area'}</span>
                  <span className="text-gray-400 text-xs ml-auto">
                    {provisions.filter(p => (p.v2_dcp_layer || p.layer) === 'condition').length} provisions
                  </span>
                </div>
              )}
              {precinctName && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-teal-500 font-bold text-xs">✓</span>
                  <span className="font-medium text-gray-700">{precinctName}</span>
                </div>
              )}
              {excludedCategoryCounts.map(([cat, count]) => (
                <div key={cat} className="flex items-center gap-2 text-sm">
                  <span className="text-gray-400 font-bold text-xs">✕</span>
                  <span className="text-gray-400 capitalize line-through">{cat.replace(/_/g, ' ')}</span>
                  <span className="text-gray-400 text-xs ml-auto">{count} removed</span>
                </div>
              ))}
            </div>

            {submitError && (
              <p className="text-sm text-red-600 mb-3">{submitError}</p>
            )}

            <button
              onClick={handleDone}
              disabled={isSubmitting}
              className="w-full rounded-lg bg-teal-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-teal-700 transition-colors disabled:opacity-60 flex items-center justify-center gap-2"
            >
              {isSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
              Done
            </button>
          </div>
        ) : (
          /* Intake questions — with scope-derived review mode */
          <>
            <DialogHeader>
              <DialogTitle className="font-serif text-xl">
                {hasAncillaryScope ? 'Review scope' : 'Set your scope'}
              </DialogTitle>
              <p className="text-sm text-gray-500 mt-1">
                {hasAncillaryScope
                  ? 'These answers were set from your works selections. Override any if needed, then apply.'
                  : 'Answer these questions to remove provisions that don\'t apply. If unsure, choose "Don\'t know" — provisions are only removed when clearly inapplicable.'
                }
              </p>
            </DialogHeader>

            <div className="mt-4 space-y-4 overflow-y-auto flex-1 pr-1">
              {/* Scope-derived section — fields answered from ancillary checkboxes */}
              {hasAncillaryScope && (() => {
                const scopeFields = INTAKE_QUESTIONS.filter(q =>
                  SCOPE_DERIVED_FIELDS.has(q.field) && !overriddenFields.has(q.field)
                );
                if (scopeFields.length === 0) return null;
                return (
                  <div className="rounded-lg border border-teal-100 bg-teal-50/40 px-4 py-3">
                    <p className="text-xs font-semibold text-teal-700 uppercase tracking-wide mb-2">
                      Derived from ancillary development
                    </p>
                    <div className="space-y-2">
                      {scopeFields.map(q => (
                        <div key={q.field} className="flex items-start justify-between gap-3">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm text-gray-700 leading-snug">{q.question}</p>
                          </div>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
                              answers[q.field] === 'yes'
                                ? 'bg-teal-100 border-teal-400 text-teal-800'
                                : 'bg-gray-200 border-gray-400 text-gray-700'
                            }`}>
                              {answers[q.field] === 'yes' ? 'Yes' : answers[q.field] === 'no' ? 'No' : 'Unknown'}
                            </span>
                            <button
                              onClick={() => setOverriddenFields(prev => new Set([...prev, q.field]))}
                              className="text-xs text-teal-500 hover:text-teal-700 underline underline-offset-2"
                            >
                              Override
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })()}

              {/* Auto-confirmed section — fields answered from property data */}
              {(() => {
                const autoFields = (Object.entries(AUTO_ANSWER_SOURCES) as [keyof IntakeAnswers, typeof AUTO_ANSWER_SOURCES[keyof IntakeAnswers]][])
                  .filter(([field, src]) => {
                    if (!src || overriddenFields.has(field)) return false;
                    const v = initialAnswers?.[field];
                    return v === 'no' || v === 'yes';
                  });
                if (autoFields.length === 0) return null;
                return (
                  <div className="rounded-lg border border-blue-100 bg-blue-50/40 px-4 py-3">
                    <p className="text-xs font-semibold text-blue-700 uppercase tracking-wide mb-2">
                      Pre-confirmed from property data
                    </p>
                    <div className="space-y-2">
                      {autoFields.map(([field, src]) => {
                        const q = INTAKE_QUESTIONS.find(q => q.field === field);
                        const label = q?.question ?? field.replace(/_/g, ' ');
                        const autoValue = initialAnswers?.[field];
                        const isYes = autoValue === 'yes';
                        return (
                          <div key={field} className="flex items-start justify-between gap-3">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm text-gray-700 leading-snug">{label}</p>
                              <p className={`text-xs mt-0.5 ${isYes ? 'text-amber-600' : 'text-blue-600'}`}>{src!.citation}</p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <span className={`text-xs px-2 py-0.5 rounded border font-medium ${
                                isYes
                                  ? 'bg-amber-50 border-amber-400 text-amber-700'
                                  : 'bg-gray-200 border-gray-400 text-gray-700'
                              }`}>
                                {isYes ? 'Yes' : 'No'}
                              </span>
                              <button
                                onClick={() => {
                                  setOverriddenFields(prev => new Set([...prev, field]));
                                }}
                                className="text-xs text-blue-500 hover:text-blue-700 underline underline-offset-2"
                              >
                                Override
                              </button>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                );
              })()}

              {/* Manual questions — hide scope-derived and auto-answered unless overridden */}
              {INTAKE_QUESTIONS.map(q => {
                if (isPropertyAutoAnswered(q.field)) return null;
                if (isScopeDerived(q.field)) return null;
                return (
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
              );
              })}
            </div>

            <div className="flex items-center justify-between border-t border-gray-100 pt-4 flex-shrink-0">
              <div className="text-sm text-gray-500">
                {excludedCount > 0 ? (
                  <span className="inline-flex items-center gap-1.5">
                    <span className="w-2 h-2 rounded-full bg-gray-400 inline-block" />
                    <strong>{excludedCount}</strong> provision{excludedCount !== 1 ? 's' : ''} will be removed
                  </span>
                ) : (
                  <span className="text-gray-400">No provisions removed yet</span>
                )}
              </div>
              <div className="flex items-center gap-3">
                <button
                  onClick={onSkip}
                  className="text-sm text-gray-500 hover:text-gray-700 underline underline-offset-2"
                >
                  {hasAncillaryScope ? 'Close' : 'Skip for now'}
                </button>
                <button
                  onClick={handleApply}
                  className="rounded-full bg-teal-600 px-5 py-2 text-sm font-medium text-white hover:bg-teal-700 transition-colors"
                >
                  Apply
                </button>
              </div>
            </div>
          </>
        )}
      </DialogContent>
    </Dialog>
  );
}
