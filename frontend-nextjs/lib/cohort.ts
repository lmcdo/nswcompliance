// prior-art-checked: reuse not viable because nothing in this repo identifies a
// group of users. Four sweeps on origin/main c28b0143: (1) DB — auth.users has
// ONE row and property_reports has no owner column at all, so there is no
// existing notion of "whose"; (2) python — no service reads a cohort, class or
// group; (3) frontend — components/feedback/* capture WHAT was reported and
// never WHO by; the only grouping field, user_feedback.user_type, is a
// profession list with no student option; (4) plans/memory —
// ce-institutional-endorsement-gtm §UNIVERSITIES asks for cohort feedback and
// records no mechanism for it.
/**
 * Cohort tagging — identify a class without building accounts.
 *
 * WHY THIS EXISTS
 * ---------------
 * The university route in ce-institutional-endorsement-gtm-2026-07.md wants
 * design-partner feedback from a student cohort. Accounts are the obvious way
 * to know whose feedback is whose, and they are the wrong way: one Supabase
 * user exists (the founder), 1,347 stored reports carry no owner, and building
 * ownership before anyone has asked for it is the build-before-distribution
 * trap the idea ledger warns about.
 *
 * A cohort code in the URL does the whole job. A lecturer hands out
 * `/assessment?cohort=uts-16658`, the code sticks for that browser, and every
 * piece of feedback carries it. No signup, no password, no table.
 *
 * WHAT IT DELIBERATELY IS NOT
 * ---------------------------
 * Not identity, and not a claim about a person. Two students on one library
 * machine share a code, and one student on two devices looks like two. It
 * answers "which class did this come from", never "who sent this" — the
 * distinction MEMORY.md's no-user-identity rule exists to keep.
 */

const KEY = 'pd.cohort';
/** Conservative: lowercase, digits, dash. A code arrives via a URL a stranger
 *  can edit, and it is written to a database field. */
const VALID = /^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$/;

/**
 * The cohort for this browser, or null.
 *
 * Reads `?cohort=` first and remembers it, so the code survives the student
 * navigating away from the link the lecturer sent. Returns null rather than a
 * placeholder: an untagged visit must stay untagged, not become "unknown",
 * which would read as a cohort in the data.
 */
export function getCohort(): string | null {
  if (typeof window === 'undefined') return null;   // SSR: no URL, no storage
  try {
    const fromUrl = new URLSearchParams(window.location.search)
      .get('cohort')?.trim().toLowerCase();
    if (fromUrl && VALID.test(fromUrl)) {
      window.localStorage.setItem(KEY, fromUrl);
      return fromUrl;
    }
    const stored = window.localStorage.getItem(KEY);
    return stored && VALID.test(stored) ? stored : null;
  } catch {
    return null;   // private browsing blocks localStorage; never throw here
  }
}
