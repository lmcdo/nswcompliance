/**
 * Council Rules copy gate.
 *
 * prior-art-checked: reuse not viable because no module exports the plan-brief flag.
 *   components/compliance/YourProjectSummary.tsx reads process.env.NEXT_PUBLIC_PLAN_BRIEF
 *   inline; the pages and scripts the guard listed (intelligence-brief, site-directory,
 *   scripts/page_integrity/site_report.py) are unrelated surfaces. Eight marketing pages
 *   need the same flag, so one shared constant stops the copy drifting from the rows.
 *
 * The plan-brief rows under "Your project" (the council plan's closest clauses per rule
 * type, quoted with the page, with "not found" stated) render only when
 * NEXT_PUBLIC_PLAN_BRIEF=on. Marketing copy that describes those rows must follow the
 * same flag, so a page never promises a row the report does not show. Anything that reads
 * PLAN_BRIEF_ON needs a fallback sentence describing what is live without it.
 */
export const PLAN_BRIEF_ON = process.env.NEXT_PUBLIC_PLAN_BRIEF === 'on';
