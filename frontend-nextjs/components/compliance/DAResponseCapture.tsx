'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Check } from 'lucide-react';
import { getTemplate, type ProvisionContext } from '@/lib/see/responseTemplates';

export interface DaResponse {
  response_text: string | null;
  compliance_status: 'complies' | 'varies' | 'not_applicable' | null;
}

interface DAResponseCaptureProps {
  provisionId: number;
  sessionToken: string | null;
  existingResponse?: DaResponse;
  onSaved?: (response: DaResponse) => void;
  /** When true: provision was auto-excluded by intake triage. Renders a locked badge instead of interactive controls. */
  isLocked?: boolean;
  /** Provision context for context-aware template selection */
  provisionContext?: ProvisionContext;
}

const STATUS_OPTIONS = [
  { value: 'complies', label: 'Complies', color: 'bg-green-100 text-green-800 border-green-300 hover:bg-green-200' },
  { value: 'varies', label: 'Varies', color: 'bg-amber-100 text-amber-800 border-amber-300 hover:bg-amber-200' },
  { value: 'not_applicable', label: 'N/A', color: 'bg-gray-100 text-gray-600 border-gray-300 hover:bg-gray-200' },
] as const;

export function DAResponseCapture({
  provisionId,
  sessionToken,
  existingResponse,
  onSaved,
  isLocked = false,
  provisionContext = {},
}: DAResponseCaptureProps) {
  const [responseText, setResponseText] = useState(existingResponse?.response_text || '');
  const [complianceStatus, setComplianceStatus] = useState<DaResponse['compliance_status']>(
    existingResponse?.compliance_status || null
  );
  const [savedIndicator, setSavedIndicator] = useState(false);
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync with external existingResponse changes (e.g. on session load)
  useEffect(() => {
    setResponseText(existingResponse?.response_text || '');
    setComplianceStatus(existingResponse?.compliance_status || null);
  }, [existingResponse?.response_text, existingResponse?.compliance_status]);

  const save = useCallback(async (text: string, status: DaResponse['compliance_status']) => {
    if (!sessionToken) return;
    try {
      const res = await fetch(`/api/da-sessions/${sessionToken}/responses`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provision_id: provisionId,
          response_text: text || null,
          compliance_status: status || null,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setSavedIndicator(true);
        setTimeout(() => setSavedIndicator(false), 2000);
        onSaved?.({
          response_text: data.response?.response_text,
          compliance_status: data.response?.compliance_status,
        });
      }
    } catch (err) {
      console.error('[DAResponseCapture] Save error:', err);
    }
  }, [sessionToken, provisionId, onSaved]);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const text = e.target.value;
    setResponseText(text);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      save(text, complianceStatus);
    }, 800);
  };

  const handleStatusClick = (status: DaResponse['compliance_status']) => {
    const newStatus = status === complianceStatus ? null : status;
    setComplianceStatus(newStatus);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    // Pre-fill template when text is empty or already contains a template value
    const isTemplate = responseText.trim() === '';
    if (newStatus && isTemplate) {
      const template = getTemplate(newStatus, provisionContext);
      setResponseText(template);
      save(template, newStatus);
    } else {
      save(responseText, newStatus);
    }
  };

  // Locked state: provision was auto-excluded by intake triage
  if (isLocked) {
    return (
      <div className="mt-2 pt-2 border-t border-gray-100 bg-gray-50/60 rounded-b px-3 pb-2">
        <span className="inline-flex items-center gap-1.5 text-xs text-gray-500 bg-gray-100 border border-gray-200 rounded px-2 py-1">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-400 inline-block" />
          N/A · set by intake
        </span>
      </div>
    );
  }

  return (
    <div className="mt-2 pt-2 border-t border-teal-100 bg-teal-50/30 rounded-b px-3 pb-2">
      {/* Status pills */}
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-xs text-gray-500 mr-1">Status:</span>
        {STATUS_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => handleStatusClick(opt.value)}
            className={`text-xs px-2 py-0.5 rounded border font-medium transition-all ${opt.color} ${
              complianceStatus === opt.value ? 'ring-2 ring-offset-1 ring-current opacity-100' : 'opacity-70'
            }`}
          >
            {opt.label}
          </button>
        ))}
        {savedIndicator && (
          <span className="ml-auto flex items-center gap-1 text-xs text-green-600">
            <Check className="w-3 h-3" /> Saved
          </span>
        )}
      </div>

      {/* Note textarea */}
      <textarea
        value={responseText}
        onChange={handleTextChange}
        placeholder="Select a status to pre-fill — edit as needed"
        rows={2}
        className="w-full text-xs border border-gray-200 rounded px-2 py-1.5 resize-none focus:outline-none focus:ring-1 focus:ring-teal-400 bg-white placeholder:text-gray-400"
      />
    </div>
  );
}
