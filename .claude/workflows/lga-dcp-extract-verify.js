export const meta = {
  name: 'lga-dcp-extract-verify',
  description: 'Extract a new LGA DCP part-by-part in parallel (cheap model), verify each part against its source pages with a fresh-context Opus checker (fidelity gate + missed-control scan), then stage confirmed provisions for human commit. Never writes to the DB; never fabricates provisions.',
  phases: [
    { title: 'Scope',   detail: 'read LGA config + TOC, build the part work-list', model: 'opus' },
    { title: 'Extract', detail: 'one worker per DCP part, runs the enrichment extractors' },
    { title: 'Verify',  detail: 'fresh checker per part: fidelity + missed mandatory controls', model: 'opus' },
    { title: 'Merge',   detail: 'single staging report; nothing auto-committed', model: 'opus' },
  ],
}

// args: { lga: "waverley", maxParts: 6, parts?: [<partId>...],
//         extractModel?: "sonnet"|"haiku"|"opus", verifyModel?: "opus"|"sonnet" }
const LGA          = (args && args.lga) || 'waverley'
const MAX_PARTS    = (args && args.maxParts) || 6
const EXTRACT_MODEL = (args && args.extractModel) || 'sonnet'  // cheap worker
const VERIFY_MODEL  = (args && args.verifyModel)  || 'opus'    // the checker never grades its own exam

const PART = {
  type: 'object', additionalProperties: false,
  properties: {
    partId:     { type: 'string' },
    title:      { type: 'string' },
    pageRange:  { type: 'string' },
    precinctIds:{ type: 'array', items: { type: 'string' } },
    sourcePdfs: { type: 'array', items: { type: 'string' } },
  }, required: ['partId', 'pageRange', 'sourcePdfs'],
}
const SCOPE = { type: 'object', additionalProperties: false,
  properties: { parts: { type: 'array', items: PART }, notes: { type: 'string' } },
  required: ['parts'] }

const EXTRACT = { type: 'object', additionalProperties: false, properties: {
  partId: { type: 'string' },
  provisions: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    provision_text: { type: 'string' }, pdf_page: { type: 'integer' }, source_ref: { type: 'string' },
    effective_date: { type: 'string' }, v2_is_actionable: { type: 'boolean' },
    v2_provision_type: { type: 'string' }, v2_has_numeric_value: { type: 'boolean' },
    v2_topic: { type: 'string' }, v2_marker: { type: 'string' },
    v2_applicable_dev_types: { type: 'array', items: { type: 'string' } },
  }, required: ['provision_text', 'pdf_page', 'v2_is_actionable'] } },
  needs_human: { type: 'array', items: { type: 'string' } },
}, required: ['partId', 'provisions'] }

const VERDICT = { type: 'object', additionalProperties: false, properties: {
  partId: { type: 'string' },
  confirmed: { type: 'integer' }, rejected: { type: 'integer' }, needs_human: { type: 'integer' },
  fidelity_pass: { type: 'boolean' },
  missed_controls: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    pdf_page: { type: 'integer' }, quote: { type: 'string' }, why: { type: 'string' } }, required: ['pdf_page', 'quote'] } },
  rejects: { type: 'array', items: { type: 'object', additionalProperties: false, properties: {
    provision_text: { type: 'string' }, reason: { type: 'string' } }, required: ['reason'] } },
}, required: ['partId', 'confirmed', 'fidelity_pass'] }

// ---- Phase 1: SCOPE (serial — the critical-path head) ----
phase('Scope')
const scope = await agent(
`You are scoping DCP extraction for LGA "${LGA}". READ ONLY, no writes.
Read enrichment/config/${LGA}_config.py, docs/DCP_SCOPE_CONFIG_REFERENCE.md,
and the DCP table of contents (scripts/extract_toc.py output or dcp_table_of_contents).
Map the DCP into discrete PARTS (chapter/precinct level), each with its page range and the
matching per-page PDFs under ${LGA}/DCPpdfimages/. Return the part work-list. Do NOT extract yet.`,
  { phase: 'Scope', schema: SCOPE, model: 'opus', effort: 'high' })

let parts = (scope?.parts || [])
if (args?.parts?.length) parts = parts.filter(p => args.parts.includes(p.partId))
const deferred = parts.slice(MAX_PARTS)
parts = parts.slice(0, MAX_PARTS)
if (deferred.length) log(`Pilot cap ${MAX_PARTS}: DEFERRED ${deferred.length} parts -> ${deferred.map(p => p.partId).join(', ')}. Re-run with higher maxParts to cover them.`)
if (!parts.length) { log('No parts scoped — check the config/TOC.'); return { error: 'no_parts' } }
log(`Extract model=${EXTRACT_MODEL}, verify model=${VERIFY_MODEL}. Parts: ${parts.map(p => p.partId).join(', ')}`)

// ---- Phase 2+3: EXTRACT (cheap) then VERIFY (Opus, fresh context), pipelined per part ----
const results = await pipeline(
  parts,
  (p) => agent(
`Extract DCP provisions for part "${p.partId}" (pages ${p.pageRange}) of LGA "${LGA}".
Use the existing pipeline, NOT your own judgement of the rules:
  - run enrichment extractors (numeric_extractor, actionable_classifier /
    gemini_actionability_classifier, layer_topic_tagger, marker_extractor, applicability_tagger)
    driven by enrichment/config/${LGA}_config.py, over pages ${p.pageRange}.
Capture their structured output as provisions. Keep source_ref + effective_date on every one.
HARD RULES: never invent, approximate, or complete a provision. If a page is unreadable or
ambiguous, put it in needs_human and move on — do NOT guess. No DB writes.`,
    { label: `extract:${p.partId}`, phase: 'Extract', schema: EXTRACT, model: EXTRACT_MODEL, effort: 'medium' }),

  (ext, p) => agent(
`You are an INDEPENDENT verifier for DCP part "${p.partId}", LGA "${LGA}". You did NOT do the
extraction and must not trust it. Re-read the SOURCE pages yourself: ${p.sourcePdfs.join(', ')}
(pages ${p.pageRange}). Then:
  1. FIDELITY (real signal): run scripts/dcp_fidelity_gate.py / verify_extraction_fidelity.py
     against these provisions. Every provision_text must actually appear on its cited page.
  2. HALLUCINATION: reject any provision whose text is not on the page.
  3. MISSED CONTROLS (false negatives): scan the source pages for mandatory language
     (must / shall / numeric limits) that the extraction did NOT capture; list each in missed_controls.
  4. CLASSIFICATION: is each v2_is_actionable / numeric / marker defensible from the clause text?
Return counts + fidelity_pass + missed_controls + rejects. You VERIFY ONLY — never rewrite provisions.
Extraction to check:\n${JSON.stringify(ext).slice(0, 12000)}`,
    { label: `verify:${p.partId}`, phase: 'Verify', schema: VERDICT, model: VERIFY_MODEL, effort: 'high' })
)

// ---- Phase 4: MERGE (serial) — stage for HUMAN commit, never auto-write ----
phase('Merge')
const verdicts = results.filter(Boolean)
const totals = verdicts.reduce((a, v) => ({
  confirmed: a.confirmed + (v.confirmed || 0), rejected: a.rejected + (v.rejected || 0),
  needs_human: a.needs_human + (v.needs_human || 0), missed: a.missed + (v.missed_controls?.length || 0),
  fidelity_fail: a.fidelity_fail + (v.fidelity_pass ? 0 : 1),
}), { confirmed: 0, rejected: 0, needs_human: 0, missed: 0, fidelity_fail: 0 })

const report = await agent(
`Write a staging report for LGA "${LGA}" DCP extraction. Parts: ${parts.map(p => p.partId).join(', ')}.
Per-part verdicts:\n${JSON.stringify(verdicts).slice(0, 16000)}
Produce: (a) a per-part table of confirmed/rejected/needs_human + fidelity pass/fail,
(b) the full list of missed_controls (these are the dangerous false negatives — surface every one),
(c) a staging JSON of CONFIRMED provisions ready for scripts/dcp_commit_approved.py.
State clearly at the top: NOTHING is committed to Supabase by this run — a human must review,
back up the DB, and run the commit step. Do not perform any DB write.`,
  { phase: 'Merge', model: 'opus', effort: 'high' })

log(`${LGA} pilot: ${totals.confirmed} confirmed, ${totals.rejected} rejected, ${totals.needs_human} need human, ${totals.missed} missed controls, ${totals.fidelity_fail} parts failed fidelity.`)
return { lga: LGA, parts: parts.map(p => p.partId), deferred: deferred.map(p => p.partId), totals, report }
