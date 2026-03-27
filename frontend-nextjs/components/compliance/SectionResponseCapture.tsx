'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Check, AlertCircle } from 'lucide-react';
import type { SectionResponse } from '@/hooks/useDASession';

interface SectionResponseCaptureProps {
  sectionKey: string;
  sectionTitle: string | null;
  sessionToken: string | null;
  existingResponse?: SectionResponse;
  onSaved?: (sectionKey: string, response: SectionResponse) => void;
}

const STATUS_OPTIONS = [
  { value: 'complies' as const,       label: 'Complies',  cls: 'bg-green-100 text-green-800 border-green-300 hover:bg-green-200' },
  { value: 'varies' as const,         label: 'Varies',    cls: 'bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200' },
  { value: 'not_applicable' as const, label: 'N/A',       cls: 'bg-gray-100  text-gray-600  border-gray-300  hover:bg-gray-200'  },
  { value: 'flagged' as const,        label: 'Flag',      cls: 'bg-red-50    text-red-700   border-red-300   hover:bg-red-100'   },
];

const DEFAULT_NARRATIVES: Record<string, string> = {
  complies:       'The proposed development complies with the controls in this section.',
  flagged:        'Requires further review or referral.',
};

export function SectionResponseCapture({
  sectionKey,
  sectionTitle,
  sessionToken,
  existingResponse,
  onSaved,
}: SectionResponseCaptureProps) {
  const [narrative, setNarrative] = useState(existingResponse?.narrative || '');
  const [status, setStatus] = useState<SectionResponse['status']>(existingResponse?.status || null);
  const [savedIndicator, setSavedIndicator] = useState(false);
  const [saveError, setSaveError] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // N/A without reason — a justification is professionally required for each N/A section.
  // The warning is shown inline so the planner sees it immediately, not only at export.
  const naReasonMissing = status === 'not_applicable' && !narrative.trim();

  // Sync with external existingResponse changes (session load)
  useEffect(() => {
    setNarrative(existingResponse?.narrative || '');
    setStatus(existingResponse?.status || null);
  }, [existingResponse?.narrative, existingResponse?.status]);

  const save = useCallback(async (text: string, st: SectionResponse['status']) => {
    if (!sessionToken) return;
    try {
      const res = await fetch(`/api/da-sessions/${sessionToken}/section-responses`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          section_key: sectionKey,
          section_title: sectionTitle,
          status: st || null,
          narrative: text || null,
        }),
      });
      if (res.ok) {
        setSaveError(false);
        setSavedIndicator(true);
        setTimeout(() => setSavedIndicator(false), 2000);
        onSaved?.(sectionKey, { status: st, narrative: text || null });
      } else {
        setSaveError(true);
        console.error('[SectionResponseCapture] Save failed:', res.status);
      }
    } catch (err) {
      setSaveError(true);
      console.error('[SectionResponseCapture] Save error:', err);
    }
  }, [sessionToken, sectionKey, sectionTitle, onSaved]);

  const handleNarrativeChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setNarrative(text);
    setSaveError(false);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => save(text, status), 800);
  };

  const handleStatusClick = (clicked: SectionResponse['status']) => {
    const newStatus = clicked === status ? null : clicked;
    setStatus(newStatus);
    setSaveError(false);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    // Pre-fill narrative when empty
    if (newStatus && !narrative.trim()) {
      const template = DEFAULT_NARRATIVES[newStatus] || '';
      setNarrative(template);
      save(template, newStatus);
    } else {
      save(narrative, newStatus);
    }
  };

  if (!sessionToken) {
    return (
      <div className="mt-3 pt-3 border-t border-teal-200 px-3 pb-3">
        <p className="text-xs text-gray-400 italic">Session initialising — assessment will be available shortly.</p>
      </div>
    );
  }

  return (
    <div className="mt-3 pt-3 border-t border-teal-200 bg-teal-50/40 rounded-b px-3 pb-3">
      <div className="flex items-center gap-1.5 mb-2">
        <span className="text-xs font-medium text-teal-800 mr-1">Section assessment:</span>
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleStatusClick(opt.value)}
            className={`text-xs px-2 py-0.5 rounded border font-medium transition-all ${opt.cls} ${
              status === opt.value ? 'ring-2 ring-offset-1 ring-current opacity-100' : 'opacity-60'
            }`}
          >
            {opt.label}
          </button>
        ))}
        <span className="ml-auto flex items-center gap-1 text-xs">
          {saveError && (
            <span className="flex items-center gap-1 text-red-600">
              <AlertCircle className="w-3 h-3" /> Save failed — retry
            </span>
          )}
          {savedIndicator && !saveError && (
            <span className="flex items-center gap-1 text-green-600">
              <Check className="w-3 h-3" /> Saved
            </span>
          )}
        </span>
      </div>
      <textarea
        value={narrative}
        onChange={handleNarrativeChange}
        placeholder={
          status === 'not_applicable'
            ? "Explain why this section does not apply — e.g. 'No swimming pool is proposed', 'The site is not flood prone', 'No signage is proposed'"
            : "Compliance narrative for this section — select a status to pre-fill"
        }
        rows={3}
        className={`w-full text-xs border rounded px-2 py-1.5 resize-none focus:outline-none focus:ring-1 bg-white placeholder:text-gray-400 ${
          saveError
            ? 'border-red-300 focus:ring-red-400'
            : naReasonMissing
              ? 'border-amber-300 focus:ring-amber-400'
              : 'border-gray-200 focus:ring-teal-400'
        }`}
      />
      {naReasonMissing && (
        <p className="mt-1 text-xs text-amber-700 flex items-center gap-1">
          <AlertCircle className="w-3 h-3 flex-shrink-0" />
          N/A requires a reason — council assessors must be able to verify why this section does not apply.
        </p>
      )}
    </div>
  );
}
