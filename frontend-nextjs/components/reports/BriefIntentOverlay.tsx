/**
 * Brief LLM overlay UI — intent chips + the "For your plan" card.
 *
 * prior-art-checked: no component renders the #742 overlay engine output;
 * SeppOverlayIndicator and the spatial "overlay" surfaces are environmental
 * overlays (different concept). This is the first UI for /api/brief-overlay.
 *
 * Behaviour contract (user-confirmed 2026-07-15):
 * - Gated by NEXT_PUBLIC_BRIEF_LLM_OVERLAY_ENABLED === 'true' (checked by the
 *   page before rendering this at all) AND server-side by the Railway flag —
 *   if either is off, nothing shows.
 * - Additive-only: the card renders ABOVE the dossier; every failure state is
 *   "render nothing", never an error banner over the brief.
 * - Chips appear during the stream wait (dead time); the card fetches only
 *   once the brief is complete and an intent is chosen.
 */

'use client';

import { useEffect, useMemo, useState } from 'react';

// ---------------------------------------------------------------------------
// Types mirroring services/brief_narration.RenderedOverlay JSON
// ---------------------------------------------------------------------------

interface OverlayLine {
  template_id: string;
  text: string;
  citation_ids: string[];
  citation_paths: string[];
  footnotes: number[];
  tone: 'fact' | 'warning' | 'info';
  liability_flags: string[];
}

interface OverlayGroup {
  key: string;
  header: string;
  lines: OverlayLine[];
}

interface OverlayFootnote {
  marker: number;
  source: string;
  as_at: string | null;
  confidence: string | null;
}

export interface BriefOverlay {
  headline: string;
  groups: OverlayGroup[];
  lines: OverlayLine[];
  footnotes: OverlayFootnote[];
  declined: boolean;
  caution: string | null;
}

interface OverlayApiResponse {
  enabled?: boolean;
  overlay?: BriefOverlay | null;
}

// Matches services/brief_manifest.Intent values exactly.
const INTENT_CHIPS: Array<{ value: string; label: string }> = [
  { value: 'granny_flat', label: 'Granny flat' },
  { value: 'duplex', label: 'Duplex' },
  { value: 'renovate', label: 'Renovate' },
  { value: 'knockdown_rebuild', label: 'Knock down & rebuild' },
  { value: 'buy_and_hold', label: 'Buy & hold' },
  { value: 'subdivide', label: 'Subdivide' },
  { value: 'researching', label: 'Just researching' },
];

// ---------------------------------------------------------------------------
// Intent chips — shown from the moment the brief starts streaming
// ---------------------------------------------------------------------------

export function BriefIntentBar({
  intent,
  onIntentChange,
  briefReady,
}: {
  intent: string | null;
  onIntentChange: (intent: string) => void;
  briefReady: boolean;
}) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 shadow-sm px-5 py-4">
      <p className="text-sm font-medium text-slate-900">What&apos;s your plan here?</p>
      <p className="text-xs text-slate-500 mt-0.5">
        {briefReady
          ? 'Pick one to pull the facts that matter for it to the top.'
          : 'Pick one while the brief builds — the matching facts will surface when it finishes.'}
      </p>
      <div className="flex flex-wrap gap-2 mt-3">
        {INTENT_CHIPS.map((chip) => (
          <button
            key={chip.value}
            type="button"
            onClick={() => onIntentChange(chip.value)}
            aria-pressed={intent === chip.value}
            className={
              intent === chip.value
                ? 'text-xs px-3 py-1.5 rounded-full border border-teal-600 bg-teal-600 text-white'
                : 'text-xs px-3 py-1.5 rounded-full border border-slate-300 text-slate-700 hover:border-teal-500 hover:text-teal-700'
            }
          >
            {chip.label}
          </button>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Overlay card — fetches once (brief complete + intent chosen), renders lines
// ---------------------------------------------------------------------------

type FetchState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'done'; overlay: BriefOverlay | null };

export function BriefOverlayCard({
  briefPayload,
  intent,
  persona = 'homeowner',
}: {
  /** Assembled brief dict (metadata + sections + complete) — null until complete. */
  briefPayload: Record<string, unknown> | null;
  intent: string | null;
  persona?: string;
}) {
  const [state, setState] = useState<FetchState>({ status: 'idle' });

  // Key the fetch on (address, intent) so switching chips re-fetches and a
  // new address resets cleanly.
  const fetchKey = useMemo(() => {
    if (!briefPayload || !intent) return null;
    return `${String(briefPayload.address ?? '')}::${intent}`;
  }, [briefPayload, intent]);

  useEffect(() => {
    if (!fetchKey || !briefPayload || !intent) return;
    let ignore = false;
    setState({ status: 'loading' });

    (async () => {
      try {
        const res = await fetch('/api/brief-overlay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ brief: briefPayload, persona, intent }),
        });
        const data: OverlayApiResponse = res.ok ? await res.json() : {};
        if (!ignore) {
          setState({ status: 'done', overlay: data.overlay ?? null });
        }
      } catch {
        // Additive-only: failure renders nothing.
        if (!ignore) setState({ status: 'done', overlay: null });
      }
    })();

    return () => {
      ignore = true;
    };
    // fetchKey encodes address+intent; briefPayload/persona ride along with it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fetchKey]);

  if (!fetchKey) return null;

  if (state.status === 'loading') {
    return (
      <div className="bg-white rounded-lg border border-slate-200 shadow-sm px-5 py-4">
        <p className="text-sm text-slate-500 animate-pulse">
          Pulling the facts that matter for your plan…
        </p>
      </div>
    );
  }

  if (state.status !== 'done' || !state.overlay) return null;

  const { headline, groups, lines, footnotes, declined, caution } = state.overlay;
  // Older engine responses (pre-polish) carry only flat lines — render them
  // as a single unlabelled group so the two shapes never diverge visually.
  const renderGroups: OverlayGroup[] =
    groups && groups.length > 0 ? groups : [{ key: 'all', header: '', lines: lines ?? [] }];

  return (
    <div
      className={
        declined
          ? 'bg-amber-50 rounded-lg border border-amber-200 shadow-sm px-5 py-4 space-y-3'
          : 'bg-white rounded-lg border border-teal-200 shadow-sm px-5 py-4 space-y-3'
      }
    >
      <div>
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {declined ? 'About this question' : 'For your plan'}
        </p>
        {headline && <p className="text-sm font-medium text-slate-900 mt-1">{headline}</p>}
        {caution && (
          <p className="text-xs text-amber-700 mt-1.5 bg-amber-50 border border-amber-200 rounded px-2 py-1.5">
            {caution}
          </p>
        )}
      </div>
      {renderGroups.map((group) => (
        <div key={group.key}>
          {group.header && (
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-1.5">
              {group.header}
            </p>
          )}
          <div className="space-y-1.5">
            {group.lines.map((line, i) => (
              <p
                key={`${line.template_id}-${i}`}
                className={
                  line.tone === 'warning'
                    ? 'text-sm text-amber-800'
                    : 'text-sm text-slate-700'
                }
              >
                {line.text}
                {/* Real space before markers so a sentence-final "0.6." never
                    copies out as "0.6.1" when the sup digit flattens. */}
                {line.footnotes.length > 0 && ' '}
                {line.footnotes.map((mark) => {
                  const fn = footnotes.find((f) => f.marker === mark);
                  return (
                    <sup key={mark}>
                      <button
                        type="button"
                        className="ml-0.5 text-[10px] text-teal-600 hover:text-teal-800"
                        title={
                          fn
                            ? `${fn.source}${fn.as_at ? ` · as at ${fn.as_at}` : ''}${fn.confidence ? ` · ${fn.confidence}` : ''} — click to open the full card`
                            : 'source'
                        }
                        onClick={() => scrollToCitation(line.citation_paths)}
                      >
                        {mark}
                      </button>
                    </sup>
                  );
                })}
              </p>
            ))}
          </div>
        </div>
      ))}
      {footnotes.length > 0 && (
        <p className="text-[11px] text-slate-400 border-t border-slate-100 pt-2">
          {footnotes.map((fn) => (
            <span key={fn.marker} className="mr-3 inline-block">
              <sup>{fn.marker}</sup> {fn.source}
              {fn.as_at ? ` · ${fn.as_at}` : ''}
            </span>
          ))}
        </p>
      )}
      <p className="text-[11px] text-slate-400">
        Facts selected from this brief&apos;s own data — every sentence carries its
        source. Full details in the section cards below.
      </p>
    </div>
  );
}

/**
 * Jump to the section card a citation belongs to: the first path segment of a
 * cited manifest entry is the section key, matching the id anchors the brief
 * page puts on each SectionCard (id="brief-section-<key>").
 */
function scrollToCitation(citationPaths: string[]) {
  const seg = citationPaths[0]?.split('.')[0]?.replace(/\[\d+\]$/, '');
  const target =
    (seg && document.getElementById(`brief-section-${seg}`)) ||
    document.getElementById('brief-dossier');
  target?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// ---------------------------------------------------------------------------
// Payload assembly — mirrors how the Python SSE events compose a brief dict
// ---------------------------------------------------------------------------

export function assembleBriefPayload(args: {
  metadata: Record<string, unknown> | null;
  sections: Array<{ section: string; data: unknown }>;
  complete: Record<string, unknown> | null;
  briefType: string | null;
}): Record<string, unknown> | null {
  const { metadata, sections, complete, briefType } = args;
  if (!metadata || !metadata.address || sections.length === 0) return null;

  const payload: Record<string, unknown> = {
    address: metadata.address,
    lat: metadata.lat ?? null,
    lng: metadata.lng ?? null,
    run_date: metadata.run_date ?? null,
    brief_type: briefType ?? 'development',
  };
  for (const s of sections) {
    // Satellite sub-sections stream as 'satellite.bushfire' etc. — nest them
    // so the manifest paths match the server-side brief shape.
    if (s.section.startsWith('satellite.')) {
      const key = s.section.slice('satellite.'.length);
      const sat = (payload.satellite ?? {}) as Record<string, unknown>;
      sat[key] = s.data;
      payload.satellite = sat;
    } else {
      payload[s.section] = s.data;
    }
  }
  if (complete) {
    payload.compound_constraints = complete.compound_constraints ?? [];
    payload.gaps = complete.gaps ?? [];
  }
  return payload;
}
