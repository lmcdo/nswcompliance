'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import type { IntakeAnswers } from '@/lib/see/intake';
import { assembleDescription } from '@/lib/see/devTypes';
import type { WorksScopeAnswers } from '@/lib/see/worksScope';

export interface DaResponse {
  response_text: string | null;
  compliance_status: 'complies' | 'varies' | 'not_applicable' | null;
}

export interface SectionResponse {
  status: 'complies' | 'varies' | 'not_applicable' | 'flagged' | null;
  narrative: string | null;
  section_title?: string | null;
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
  updateSingleResponse: (provisionId: number, response: DaResponse) => void;
  sectionResponses: Map<string, SectionResponse>;
  updateSingleSectionResponse: (sectionKey: string, response: SectionResponse) => void;
  saveSectionResponse: (sectionKey: string, sectionTitle: string | null, response: SectionResponse) => Promise<void>;
  developmentDescription: string;
  saveDescription: (text: string) => Promise<void>;
  intakeAnswers: IntakeAnswers | null;
  saveIntakeAnswers: (answers: IntakeAnswers) => Promise<void>;
  ancillaryWorks: string[];
  primaryDevType: string;
  savedWorksText: string;
  saveScope: (primaryType: string, ancillary: string[], worksText: string, intake: IntakeAnswers) => Promise<void>;
  topicAssertions: Record<string, string>;
  saveTopicAssertion: (topic: string, reason: string | null) => Promise<void>;
  chapterAssertions: Record<string, string>;
  saveChapterAssertion: (chapterKey: string, reason: string | null) => Promise<void>;
  bulkSaveResponses: (responses: BulkResponseItem[]) => Promise<void>;
  worksScopeAnswers: WorksScopeAnswers | null;
  saveWorksScopeAnswers: (answers: WorksScopeAnswers) => Promise<void>;
  exportedAt: string | null;
  error: Error | null;
}

/** Build a v3 envelope — pure function, no hook needed */
function buildEnvelope(
  intake: IntakeAnswers | null,
  ancillary: string[],
  topics: Record<string, string>,
  chapters: Record<string, string>,
  primaryDevType?: string,
  worksScope?: WorksScopeAnswers | null,
  worksText?: string,
) {
  return {
    _v: 3,
    ...(primaryDevType !== undefined ? { primary_dev_type: primaryDevType } : {}),
    ...(worksText !== undefined ? { works_text: worksText } : {}),
    ancillary_works: ancillary,
    intake: intake,
    topic_assertions: topics,
    chapter_assertions: chapters,
    ...(worksScope !== undefined ? { works_scope: worksScope } : {}),
  };
}

export function useDASession(
  address: string | null,
  formerCouncil?: string,
  zone?: string
): UseDASessionReturn {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [daResponses, setDaResponses] = useState<Map<number, DaResponse>>(new Map());
  const [sectionResponses, setSectionResponses] = useState<Map<string, SectionResponse>>(new Map());
  const [developmentDescription, setDevelopmentDescription] = useState<string>('');
  const [intakeAnswers, setIntakeAnswers] = useState<IntakeAnswers | null>(null);
  const [ancillaryWorks, setAncillaryWorks] = useState<string[]>([]);
  const [primaryDevType, setPrimaryDevType] = useState<string>('');
  const [savedWorksText, setSavedWorksText] = useState<string>('');
  const [topicAssertions, setTopicAssertions] = useState<Record<string, string>>({});
  const [chapterAssertions, setChapterAssertions] = useState<Record<string, string>>({});
  const [worksScopeAnswers, setWorksScopeAnswers] = useState<WorksScopeAnswers | null>(null);
  const [exportedAt, setExportedAt] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Refs for latest state — avoids stale closures in save callbacks
  const intakeRef = useRef(intakeAnswers);
  intakeRef.current = intakeAnswers;
  const ancillaryRef = useRef(ancillaryWorks);
  ancillaryRef.current = ancillaryWorks;
  const topicAssertionsRef = useRef(topicAssertions);
  topicAssertionsRef.current = topicAssertions;
  const chapterAssertionsRef = useRef(chapterAssertions);
  chapterAssertionsRef.current = chapterAssertions;
  const worksScopeRef = useRef(worksScopeAnswers);
  worksScopeRef.current = worksScopeAnswers;

  const loadResponses = useCallback(async (token: string) => {
    try {
      const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();

      // Load dev_type into description state
      setDevelopmentDescription(data.session?.dev_type || '');
      setExportedAt(data.session?.exported_at ?? null);

      // Load proposed_values — supports v3/v2 envelope or legacy flat IntakeAnswers
      const pv = data.session?.proposed_values;
      if (pv && typeof pv === 'object') {
        if ((pv as any)._v === 3) {
          setIntakeAnswers((pv as any).intake ?? null);
          setAncillaryWorks((pv as any).ancillary_works ?? []);
          setPrimaryDevType((pv as any).primary_dev_type ?? '');
          setSavedWorksText((pv as any).works_text ?? '');
          setTopicAssertions((pv as any).topic_assertions ?? {});
          setChapterAssertions((pv as any).chapter_assertions ?? {});
          setWorksScopeAnswers((pv as any).works_scope ?? null);
        } else if ((pv as any)._v === 2) {
          setIntakeAnswers((pv as any).intake ?? null);
          setAncillaryWorks([]);  // v2 has no ancillary data
          setTopicAssertions((pv as any).topic_assertions ?? {});
          setChapterAssertions((pv as any).chapter_assertions ?? {});
        } else {
          setIntakeAnswers(pv as IntakeAnswers);   // legacy format
          setAncillaryWorks([]);
          setTopicAssertions({});
          setChapterAssertions({});
        }
      }

      const map = new Map<number, DaResponse>();
      for (const [provId, resp] of Object.entries(data.responses || {})) {
        map.set(Number(provId), resp as DaResponse);
      }
      setDaResponses(map);

      const sectionMap = new Map<string, SectionResponse>();
      for (const [key, resp] of Object.entries(data.section_responses || {})) {
        sectionMap.set(key, resp as SectionResponse);
      }
      setSectionResponses(sectionMap);
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

  const updateSingleResponse = useCallback((provisionId: number, response: DaResponse) => {
    setDaResponses(prev => {
      const next = new Map(prev);
      next.set(provisionId, response);
      return next;
    });
  }, []);

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
    const envelope = buildEnvelope(answers, ancillaryRef.current, topicAssertionsRef.current, chapterAssertionsRef.current);
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save intake answers');
    setIntakeAnswers(answers);
  }, [sessionToken]);

  /** Save full scope: primary type + ancillary + works text + derived intake */
  const saveScope = useCallback(async (
    primaryType: string,
    ancillary: string[],
    worksText: string,
    intake: IntakeAnswers,
  ) => {
    if (!sessionToken) return;
    const envelope = buildEnvelope(intake, ancillary, topicAssertionsRef.current, chapterAssertionsRef.current, primaryType, undefined, worksText);
    const description = assembleDescription(primaryType, ancillary, worksText);

    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        dev_type: description || null,
        proposed_values: envelope,
      }),
    });
    if (!res.ok) throw new Error('Failed to save scope');
    setIntakeAnswers(intake);
    setAncillaryWorks(ancillary);
    setSavedWorksText(worksText);
  }, [sessionToken]);

  const saveTopicAssertion = useCallback(async (topic: string, reason: string | null) => {
    if (!sessionToken) return;
    const current = topicAssertionsRef.current;
    const next = { ...current };
    if (reason === null) { delete next[topic]; } else { next[topic] = reason; }
    const envelope = buildEnvelope(intakeRef.current, ancillaryRef.current, next, chapterAssertionsRef.current);
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save topic assertion');
    setTopicAssertions(next);
  }, [sessionToken]);

  const saveChapterAssertion = useCallback(async (chapterKey: string, reason: string | null) => {
    if (!sessionToken) return;
    const current = chapterAssertionsRef.current;
    const next = { ...current };
    if (reason === null) { delete next[chapterKey]; } else { next[chapterKey] = reason; }
    const envelope = buildEnvelope(intakeRef.current, ancillaryRef.current, topicAssertionsRef.current, next, undefined, worksScopeRef.current);
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save chapter assertion');
    setChapterAssertions(next);
  }, [sessionToken]);

  const saveWorksScopeAnswers = useCallback(async (answers: WorksScopeAnswers) => {
    if (!sessionToken) return;
    const envelope = buildEnvelope(intakeRef.current, ancillaryRef.current, topicAssertionsRef.current, chapterAssertionsRef.current, undefined, answers);
    const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(sessionToken)}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ proposed_values: envelope }),
    });
    if (!res.ok) throw new Error('Failed to save works scope');
    setWorksScopeAnswers(answers);
  }, [sessionToken]);

  const updateSingleSectionResponse = useCallback((sectionKey: string, response: SectionResponse) => {
    setSectionResponses(prev => {
      const next = new Map(prev);
      next.set(sectionKey, response);
      return next;
    });
  }, []);

  const saveSectionResponse = useCallback(async (
    sectionKey: string,
    sectionTitle: string | null,
    response: SectionResponse,
  ) => {
    if (!sessionToken) return;
    const res = await fetch(`/api/da-sessions/${sessionToken}/section-responses`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        section_key: sectionKey,
        section_title: sectionTitle,
        status: response.status || null,
        narrative: response.narrative || null,
      }),
    });
    if (!res.ok) throw new Error('Failed to save section response');
    updateSingleSectionResponse(sectionKey, { ...response, section_title: sectionTitle });
  }, [sessionToken, updateSingleSectionResponse]);

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
    updateSingleResponse,
    sectionResponses,
    updateSingleSectionResponse,
    saveSectionResponse,
    developmentDescription,
    saveDescription,
    intakeAnswers,
    saveIntakeAnswers,
    ancillaryWorks,
    primaryDevType,
    savedWorksText,
    saveScope,
    topicAssertions,
    saveTopicAssertion,
    chapterAssertions,
    saveChapterAssertion,
    bulkSaveResponses,
    worksScopeAnswers,
    saveWorksScopeAnswers,
    exportedAt,
    error,
  };
}
