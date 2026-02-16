'use client';

import { useState, useEffect, useCallback } from 'react';

export interface DaResponse {
  response_text: string | null;
  compliance_status: 'complies' | 'varies' | 'not_applicable' | null;
}

interface UseDASessionReturn {
  sessionToken: string | null;
  isLoading: boolean;
  daResponses: Map<number, DaResponse>;
  refreshResponses: () => Promise<void>;
}

export function useDASession(
  address: string | null,
  formerCouncil?: string,
  zone?: string
): UseDASessionReturn {
  const [sessionToken, setSessionToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [daResponses, setDaResponses] = useState<Map<number, DaResponse>>(new Map());

  const loadResponses = useCallback(async (token: string) => {
    try {
      const res = await fetch(`/api/da-sessions?token=${encodeURIComponent(token)}`);
      if (!res.ok) return;
      const data = await res.json();
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

  return { sessionToken, isLoading, daResponses, refreshResponses };
}
