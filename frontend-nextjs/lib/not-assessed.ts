// prior-art-checked: this is the ONE absence-copy module for the reports
// surface. It began as lib/shadow-scenario-availability.ts (#885) and was
// renamed here on 2026-08-08 when flood needed the same thing — extended, not
// copied, so a second wording of "we could not answer" cannot appear. Its other
// former sibling, lib/shadow-surface-change.ts, was deleted with the
// adjacent-lot check (§4h). One exported string per state, imported by every
// surface, so the PDF, the report page and the free tool cannot drift.
//
// The contract every message here keeps, in this order:
//   what we tried · why there is no answer · that it is NOT a pass and NOT a
//   fail · what the reader can do about it.

/**
 * What a customer reads when a shadow scenario produced no result.
 *
 * A scenario the model could not compute stores null in every measurement
 * field. Rendered naively that is an em dash in each cell — and an empty cell
 * reads as "fine" to someone skimming, which is the opposite of what happened.
 * The state must therefore both READ as an absence and LOOK different from a
 * result.
 *
 * Every message below says, in order: what was attempted, why there is no
 * answer, that it is neither a pass nor a fail, and what the reader can do.
 */

/** Short label for a table cell. Never an em dash, never a zero. */
export const SCENARIO_NOT_ASSESSED_LABEL = 'Not assessed';

/**
 * The reason a scenario could not be computed, as a customer-facing sentence.
 *
 * `errorNote` is the operator-facing string the pipeline stored. It is matched,
 * never rendered: it names internals ("could not be intersected", "physical
 * ceiling") that mean nothing to a reader.
 */
export function scenarioUnavailableMessage(errorNote?: string | null): string {
  const note = (errorNote ?? '').toLowerCase();

  if (note.includes('could not be intersected')) {
    return (
      "We couldn't measure the shadow on this property because the council's " +
      'recorded lot boundary is incomplete. This is not a result — we have no ' +
      'answer either way, and it is neither a pass nor a fail. You can ask the ' +
      'council to confirm the registered boundary, then re-run this report.'
    );
  }

  if (note.includes('physical maximum') || note.includes('physical ceiling')) {
    return (
      'We tried to measure how far the shadow reaches across this property, but ' +
      'the result was longer than the sun can physically cast at that time of ' +
      'day, so we discarded it. This is not a result — we have no answer either ' +
      'way, and it is neither a pass nor a fail. It usually means the recorded ' +
      'lot boundary is wrong; the council can confirm it.'
    );
  }

  return (
    'We tried to model the shadow for this date and time, but the calculation ' +
    'did not produce a usable result. This is not a result — we have no answer ' +
    'either way, and it is neither a pass nor a fail. Re-running the report ' +
    'often resolves it; if it does not, the recorded lot boundary is the usual ' +
    'cause.'
  );
}

// ── Flood: the 1% AEP (1-in-100-year) verdict ────────────────────────────────
//
// `in_100yr_flood_zone` is three-state from 2026-08-08. It used to start at
// false, so a source that could not be consulted produced a confident "not in
// a flood zone" — an active statement in the direction that causes harm, on
// the field a buyer is most likely to act on. null now means NOT ASSESSED and
// must never be rendered as "No".

/** Short label for the flood-zone highlight. Never "No", never blank. */
export const FLOOD_ZONE_NOT_ASSESSED_LABEL = 'Not assessed';

/**
 * What a customer reads when the 1% AEP question could not be answered.
 *
 * `unconsulted` is the served list of source names that were unreachable. It
 * IS rendered, so it carries customer-neutral names ("NSW EPI flood overlay"),
 * not internals.
 */
export function floodZoneUnavailableMessage(
  unconsulted?: readonly string[] | null,
): string {
  const named = (unconsulted ?? []).filter(Boolean);
  const tried =
    named.length > 0
      ? `We could not reach ${named.length === 1 ? 'this source' : 'these sources'}: ${named.join(', ')}.`
      : 'We could not reach one of the sources that maps the 1% AEP flood extent.';

  return (
    `${tried} That means we have NOT established whether this property sits ` +
    'inside the 1-in-100-year flood extent. This is not a result — it is ' +
    'neither a pass nor a fail, and it must not be read as "not in a flood ' +
    'zone". Ask the council for a Section 10.7(2) certificate, which states ' +
    'the flood status on the public record, and re-run this report later.'
  );
}

/** True when the flood-zone verdict was not established. Explicit, never falsy.
 *
 * Takes `unknown`, not `boolean | null`, on purpose. The report page reads this
 * out of an untyped JSON bag, so a cast there is a promise the compiler cannot
 * keep: a legacy row holding the STRING "false", or a 0, would satisfy
 * `boolean | null` at compile time, fail a `=== true` check, and fall through
 * to "No" — a rendered clearance from a value nobody validated. Only the two
 * real booleans are answers. Everything else is an absence.
 */
export function isFloodZoneNotAssessed(value: unknown): boolean {
  return value !== true && value !== false;
}

/** The verdict as one of exactly three states, whatever the stored shape was. */
export function readFloodZoneVerdict(value: unknown): true | false | null {
  if (value === true) return true;
  if (value === false) return false;
  return null;
}

/** True when the scenario carries no measurement because none was produced. */
export function isScenarioUnavailable(
  scenario: { status?: string | null } | null | undefined,
): boolean {
  // Absence of `status` means the row predates the typed-absence fix, and every
  // such row was computed. Only an explicit 'unavailable' counts.
  return scenario?.status === 'unavailable';
}
