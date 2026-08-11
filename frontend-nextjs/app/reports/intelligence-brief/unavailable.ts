// "Why is this empty" copy for the Intelligence Brief — pure helpers extracted
// from page.tsx so the wording is unit-testable, the same way provenance.ts was.
//
// Every branch returns BOTH a short label and a plain-English detail. Callers
// must render the detail: a bare "None here" or "Not assessed" cannot tell the
// reader whether anything was actually checked, which is the absence-vs-failure
// ambiguity this mapping exists to remove.
//
// SECTION_LABELS lives in page.tsx and is passed in as `sectionDescription`
// rather than imported, to keep this module free of page-level constants.

// ---------------------------------------------------------------------------
// Honest "why is this empty" mapping. NEVER show the raw internal reason
// string ("Layer not ingested for this LGA", "Premium data not requested") to
// a user — translate it into one of five plain states with an honest tone:
//   clear    — we checked, there's nothing here (good news for the owner)
//   optional — an add-on that wasn't requested
//   pending  — we haven't assessed this for this area yet (an honest gap)
//   error    — a genuine retrieval failure
//   neutral  — simply not part of this report
// ---------------------------------------------------------------------------
export type UnavailableTone = 'clear' | 'optional' | 'pending' | 'error' | 'neutral';

// Satellite layers are opt-in behind the "Include satellite analysis" checkbox —
// so the real reason they're blank is that the box wasn't ticked, and the real
// path is to tick it and re-run. (Verified against include_satellite gating.)
const SATELLITE_SECTIONS = new Set([
  'satellite.bushfire', 'satellite.flood', 'satellite.climate_disclosure',
  'satellite.granny_flat', 'satellite.terrain', 'satellite.solar',
]);

export interface Unavailable { label: string; detail: string; tone: UnavailableTone; }

export function describeUnavailable(
  reason?: string | null,
  section?: string,
  satelliteRan = false,
  sectionDescription?: string,
): Unavailable {
  const r = (reason ?? '').toLowerCase();
  const isSatellite = !!section && (SATELLITE_SECTIONS.has(section) || section === 'satellite.bushfire');
  // What this layer actually assesses, so a "no" explains itself (e.g.
  // "bushfire attack level and vegetation category") rather than a bare "none".
  const what = sectionDescription ? sectionDescription.toLowerCase() : '';

  // Satellite opt-in layers.
  if (isSatellite) {
    // If satellite analysis WAS requested but this layer is empty, it couldn't be
    // produced for this property — say that plainly, don't blame the user's tickbox
    // and don't imply a false finding ("no structures" on a clearly built lot).
    if (satelliteRan) {
      // Surface the real failure reason (e.g. a missing model or a DEM/raster
      // error) so the cause is diagnosable, not hidden behind a generic line.
      const why = reason && !r.includes('not requested') ? ` (${String(reason).slice(0, 180)})` : '';
      return {
        label: 'Couldn’t complete',
        detail: `We couldn’t complete ${what ? `the ${what} analysis` : 'this analysis'} for this property${why}. Try running the brief again.`,
        tone: 'pending',
      };
    }
    return {
      label: 'Not run',
      detail: `Tick “Include satellite analysis” above and re-run to add ${what || 'this layer'}.`,
      tone: 'optional',
    };
  }
  // Pre-DA site history. Distinguish "not requested" (tick the box) from
  // "requested but didn't finish" (it ran and timed out / failed) — don't tell a
  // user who already ticked the box to tick it again.
  if (section === 'satellite.pre_da_history' || r.includes('premium') || r.includes('site history')) {
    if (r.includes('not requested')) {
      return {
        label: 'Not run',
        detail: 'Tick “Include site history (slower)” above and run the brief again to add this.',
        tone: 'optional',
      };
    }
    // A genuine timeout — it ran out of time. Tell the user to retry.
    if (r.includes('timeout') || r.includes("didn't finish") || r.includes('did not finish')) {
      return {
        label: 'Couldn’t complete',
        detail: 'The site-history analysis didn’t finish in time for this property — please run the brief again.',
        tone: 'pending',
      };
    }
    // It errored fast (e.g. a backend model/service issue) — surface the real
    // reason so it can be diagnosed, rather than pretending it timed out.
    const why = reason ? String(reason).slice(0, 160) : '';
    return {
      label: 'Couldn’t complete',
      detail: `The site-history analysis couldn’t run for this property — this is a backend issue, not your input${why ? ` (${why})` : ''}.`,
      tone: 'pending',
    };
  }
  // No reason recorded on a field this brief's sections DO promise (e.g. the VG
  // land value when the valuation lookup returned nothing) — that's a retrieval
  // miss, not an out-of-scope field. Say so, and route to a retry.
  if (!r) {
    return {
      label: 'Unavailable',
      detail: 'This field could not be retrieved on this run — run the brief again to retry.',
      tone: 'error',
    };
  }
  // Only a genuine resolution failure ("No prop_id resolved") is the user's
  // address problem. A bare "could not ..." from any backend layer used to land
  // here too, so a council we simply haven't onboarded (e.g. Wingecarribee DCP)
  // rendered as "Address not matched — check the address".
  if (r.includes('prop_id') || r.includes('address not')) {
    return {
      label: 'Address not matched',
      detail: 'We could not match this address to a property in the NSW register — check the address.',
      tone: 'error',
    };
  }
  if (r.includes('not ingested') || r.includes('not yet') || r.includes('not onboarded')) {
    return {
      label: 'Not assessed',
      detail: `${what ? `This council's ${what} isn't in our dataset yet` : 'This layer is not yet mapped for this council'} — confirm directly with the council or the NSW Planning Portal.`,
      tone: 'pending',
    };
  }
  if (r.startsWith('no ') || r.includes('none found') || r.includes('at this location')) {
    return {
      label: 'None here',
      detail: `Checked${what ? ` for ${what}` : ''} — none recorded at this property.`,
      tone: 'clear',
    };
  }
  // The ONLY branch that may say "not part of this brief": the layer was
  // genuinely not requested (an opt-in that wasn't ticked).
  if (r.includes('not requested')) {
    return { label: 'Not included', detail: 'An optional add-on, not part of this brief.', tone: 'neutral' };
  }
  if (r.includes('fail') || r.includes('unavailable') || r.includes('error') || r.includes('timeout') || r.includes('timed out')) {
    return {
      label: 'Unavailable',
      detail: `The source for ${what || 'this layer'} did not respond — run the brief again to retry.`,
      tone: 'error',
    };
  }
  // Unrecognised reason on a promised field — a retrieval miss, never "not part
  // of this brief" (the section header promised it).
  return {
    label: 'Unavailable',
    detail: 'This field could not be retrieved on this run — run the brief again to retry.',
    tone: 'error',
  };
}
