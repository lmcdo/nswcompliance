// prior-art-checked: this is now the ONLY shadow absence-copy module. Its former
// sibling lib/shadow-surface-change.ts was deleted with the adjacent-lot check
// (§4h, 2026-08-07), so there is nothing left to merge with or duplicate. One
// exported string per state, imported by every surface, so the PDF, the report
// page and the free tool cannot drift into three wordings of the same absence.

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

/** True when the scenario carries no measurement because none was produced. */
export function isScenarioUnavailable(
  scenario: { status?: string | null } | null | undefined,
): boolean {
  // Absence of `status` means the row predates the typed-absence fix, and every
  // such row was computed. Only an explicit 'unavailable' counts.
  return scenario?.status === 'unavailable';
}
