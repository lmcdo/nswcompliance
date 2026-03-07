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
  topicAssertions: Record<string, string>;
  saveTopicAssertion: (topic: string, reason: string | null) => Promise<void>;
  chapterAssertions: Record<string, string>;
  saveChapterAssertion: (chapterKey: string, reason: string | null) => Promise<void>;
  bulkSaveResponses: (responses: BulkResponseItem[]) => Promise<void>;
  error: Error | null;
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
  const [topicAssertions, setTopicAssertions] = useState<Record<string, string>>({});
  const [chapterAssertions, setChapterAssertions] = useState<Record<string, string>>({});
  const [error, setError] = useState<Error | null>(null);

  const loadResponses = useCallback(async (token: string) => {
    try {
      const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();

      // Load dev_type into description state
      setDevelopmentDescription(data.session?.dev_type || '');

      // Load proposed_values — supports v2 envelope or legacy flat IntakeAnswers
      const pv = data.session?.proposed_values;
      if (pv && typeof pv === 'object') {
        if ((pv as any)._v === 2) {
          setIntakeAnswers((pv as any).intake ?? null);
          setTopicAssertions((pv as any).topic_assertions ?? {});
          setChapterAssertions((pv as any).chapter_assertions ?? {});
        } else {
          setIntakeAnswers(pv as IntakeAnswers);   // legacy format
          setTopicAssertions({});
          setChapterAssertions({});
        }
      }

      const map = new Map<number, DaResponse>();
      for (const [provId, resp] of Object.entries(data.responses || {})) {
        map.set(Number(provId), resp as DaResponse);
      }
      setDaResponses(map);
    } catch (err) {
      console.error('[useDASession] Failed to load responses:', err);
      setError(err instanceof Error ? err : new Error(String(err)));
    }
  }, []);

  const refreshResponses = useCallback(async () => {
    if (sessionToken) {
      await loadResponses(sessionToken);
    }
  }, [sessionToken, loadResponses]);

  const saveDescription = useCallback(async (text: string) => {
    if (!sessionToken) return;
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ dev_type: text || null }),
    });
    if (!res.ok) throw new Error('Failed to save description');
  }, [sessionToken]);

  const saveIntakeAnswers = useCallback(async (answers: IntakeAnswers) => {
    if (!sessionToken) return;
    const envelope = { _v: 2, intake: answers, topic_assertions: topicAssertions, chapter_assertions: chapterAssertions };
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save intake answers');
    setIntakeAnswers(answers);
  }, [sessionToken, topicAssertions, chapterAssertions]);

  const saveTopicAssertion = useCallback(async (topic: string, reason: string | null) => {
    if (!sessionToken) return;
    const next = { ...topicAssertions };
    if (reason === null) { delete next[topic]; } else { next[topic] = reason; }
    const envelope = { _v: 2, intake: intakeAnswers, topic_assertions: next, chapter_assertions: chapterAssertions };
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save topic assertion');
    setTopicAssertions(next);
  }, [sessionToken, topicAssertions, chapterAssertions, intakeAnswers]);

  const saveChapterAssertion = useCallback(async (chapterKey: string, reason: string | null) => {
    if (!sessionToken) return;
    const next = { ...chapterAssertions };
    if (reason === null) { delete next[chapterKey]; } else { next[chapterKey] = reason; }
    const envelope = { _v: 2, intake: intakeAnswers, topic_assertions: topicAssertions, chapter_assertions: next };
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save chapter assertion');
    setChapterAssertions(next);
  }, [sessionToken, chapterAssertions, topicAssertions, intakeAnswers]);

  const bulkSaveResponses = useCallback(async (responses: BulkResponseItem[]) => {
    if (!sessionToken || responses.length === 0) return;
    const res = await fetch(`/api/da-sessions/${sessionToken}/responses/bulk`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ responses }),
    });
    if (!res.ok) throw new Error('Failed to save triage responses');
    setDaResponses(prev => {
      const next = new Map(prev);
      for (const r of responses) {
        next.set(r.provision_id, {
          compliance_status: r.compliance_status as DaResponse['compliance_status'],
          response_text: r.response_text ?? null,
        });
      }
      return next;
    });
  }, [sessionToken]);

  useEffect(() => {
    if (!address) return;

    const controller = new AbortController();

    const init = async () => {
      setIsLoading(true);
      try {
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
            signal: controller.signal,
          });
          if (res.ok) {
            const data = await res.json();
            const token = data.session_token;
            localStorage.setItem(storageKey, token);
            setSessionToken(token);
          }
        }
      } catch (err) {
        if (err instanceof Error && err.name === 'AbortError') return;
        console.error('[useDASession] Init error:', err);
        setError(err instanceof Error ? err : new Error(String(err)));
      } finally {
        setIsLoading(false);
      }
    };

    init();
    return () => controller.abort();
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
    topicAssertions,
    saveTopicAssertion,
    chapterAssertions,
    saveChapterAssertion,
    bulkSaveResponses,
    error,
  };
}
