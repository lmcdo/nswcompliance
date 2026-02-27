'use client';

import { useState, useEffect, useCallback } from 'react';
import type { IntakeAnswers } from '@/lib/see/intake';

export interface DaResponse {
  response_text: string | null;
  compliance_status: 'complies' | 'varies' | 'not_applicable' | null;
}

interface BulkResponseItem {
  provision_id: number;
  compliance_status: string;
  response_text?: string;
}

interface UseDASessionReturn {
  sessionToken: string | null;
  isLoading: boolean;
  daResponses: Map<number, DaResponse>;
  refreshResponses: () => Promise<void>;
  developmentDescription: string;
  saveDescription: (text: string) => Promise<void>;
  intakeAnswers: IntakeAnswers | null;
  saveIntakeAnswers: (answers: IntakeAnswers) => Promise<void>;
  bulkSaveResponses: (responses: BulkResponseItem[]) => Promise<void>;
}

export function useDASession(
  address: string | null,
  formerCouncil?: string,
  zone?: string
): UseDASessionReturn {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [daResponses, setDaResponses] = useState<Map<number, DaResponse>>(new Map());
  const [developmentDescription, setDevelopmentDescription] = useState<string>('');
  const [intakeAnswers, setIntakeAnswers] = useState<IntakeAnswers | null>(null);

  const loadResponses = useCallback(async (token: string) => {
    try {
      const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();

      // Load dev_type into description state
      setDevelopmentDescription(data.session?.dev_type || '');

      // Load proposed_values as intake answers if present
      const pv = data.session?.proposed_values;
      if (pv && typeof pv === 'object') {
        setIntakeAnswers(pv as IntakeAnswers);
      }

      const map = new Map<number, DaResponse>();
      for (const [provId, resp] of Object.entries(data.responses || {})) {
        map.set(Number(provId), resp as DaResponse);
      }
      setDaResponses(map);
    } catch (err) {
      console.error('[useDASession] Failed to load responses:', err);
    }
  }, []);

  const refreshResponses = useCallback(async () => {
    if (sessionToken) {
      await loadResponses(sessionToken);
    }
  }, [sessionToken, loadResponses]);

  const saveDescription = useCallback(async (text: string) => {
    if (!sessionToken) return;
    try {
      await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dev_type: text || null }),
      });
    } catch (err) {
      console.error('[useDASession] saveDescription error:', err);
    }
  }, [sessionToken]);

  const saveIntakeAnswers = useCallback(async (answers: IntakeAnswers) => {
    if (!sessionToken) return;
    try {
      await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ proposed_values: answers }),
      });
      setIntakeAnswers(answers);
    } catch (err) {
      console.error('[useDASession] saveIntakeAnswers error:', err);
    }
  }, [sessionToken]);

  const bulkSaveResponses = useCallback(async (responses: BulkResponseItem[]) => {
    if (!sessionToken || responses.length === 0) return;
    try {
      await fetch(`/api/da-sessions/${sessionToken}/responses/bulk`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ responses }),
      });
    } catch (err) {
      console.error('[useDASession] bulkSaveResponses error:', err);
    }
  }, [sessionToken]);

  useEffect(() => {
    if (!address) return;

    const init = async () => {
      setIsLoading(true);
      try {
        // Check localStorage for existing token
        const storageKey = `da_session_token_${address}`;
        const existing = localStorage.getItem(storageKey);

        if (existing) {
          setSessionToken(existing);
          await loadResponses(existing);
        } else {
          // Create new session
          const res = await fetch('/api/da-sessions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ address, former_council: formerCouncil, zone }),
          });
          if (res.ok) {
            const data = await res.json();
            const token = data.session_token;
            localStorage.setItem(storageKey, token);
            setSessionToken(token);
          }
        }
      } catch (err) {
        console.error('[useDASession] Init error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    init();
  }, [address, formerCouncil, zone, loadResponses]);

  return {
    sessionToken,
    isLoading,
    daResponses,
    refreshResponses,
    developmentDescription,
    saveDescription,
    intakeAnswers,
    saveIntakeAnswers,
    bulkSaveResponses,
  };
}
