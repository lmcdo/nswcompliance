'use client';

import { useEffect, useState } from 'react';
import type { LawFacts, LawFactsResponse } from '@/lib/law-facts';

// prior-art-checked: no existing hook calls /api/law-facts (grep hooks/ components/, 2026-11-07); modelled on hooks/useLmrGates.ts.

export interface UseLawFactsResult {
  facts: LawFacts | null;
  loading: boolean;
  failed: boolean;
}

/** One fetch per page load, shared by every component: the figures do not depend on the property. */
let cached: Promise<LawFactsResponse | null> | null = null;

function load(): Promise<LawFactsResponse | null> {
  if (!cached) {
    cached = fetch('/api/law-facts')
      .then((r) => (r.ok ? (r.json() as Promise<LawFactsResponse>) : null))
      .then((j) => (j && j.available === true && j.facts ? j : null))
      .catch(() => null);
  }
  return cached;
}

/** Test seam: forget the shared fetch. */
export function resetLawFactsCache(): void {
  cached = null;
}

/** The stored state-law figures. On any failure `facts` stays null and `failed` is true, so callers print no figure. */
export function useLawFacts(): UseLawFactsResult {
  const [state, setState] = useState<UseLawFactsResult>({ facts: null, loading: true, failed: false });
  useEffect(() => {
    let live = true;
    load().then((j) => {
      if (!live) return;
      // A failure must be retried on the next mount rather than stuck for the whole session.
      if (j == null) cached = null;
      setState(j ? { facts: j.facts, loading: false, failed: false } : { facts: null, loading: false, failed: true });
    });
    return () => {
      live = false;
    };
  }, []);
  return state;
}
