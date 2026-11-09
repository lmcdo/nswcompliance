/**
 * GET /api/brief/for-property?council=hornsby&dev_type=dual_occupancy&zone=R2
 *
 * The plan's own clauses to show first, per "Your project" row, for rows that have no proven figure.
 * Reads project_brief_rows (derived: clause ids only) and joins regulatory_provisions at read time, so the
 * council's words, the page and the citation proof come from the same helpers as /api/provisions/for-property.
 *
 * prior-art-checked: /api/provisions/for-property serves every clause ranked (primary / general / secondary);
 * /api/dcp/structured-controls serves proven numeric controls. Neither serves "the best few clauses per rule type".
 *
 * OFF unless PLAN_BRIEF=on. Read-only. Nothing is hidden: this is an extra block beside the full plan.
 */
import { NextRequest, NextResponse } from 'next/server';
import { getPool } from '@/lib/db';
import { toLgaSlug } from '@/lib/lga-slug';
import { dataRateLimiter, getClientIdentifier, checkRateLimit, createRateLimitHeaders } from '@/lib/rate-limit';
import { quoteColumns, withCouncilWords } from '@/lib/council-quote';
import { withServedCitation } from '@/lib/citation-display';
import { BRIEF_ROW_LIMIT, briefClauseLabel, isBriefDevType, zoneGroup, planLink, tidyText, needsFollowOn, showsNextClauses, tablePart, tableFor, inBriefScope, dropExcluded, type StoredBriefRow } from '@/lib/plan-brief';
import briefScope from '@/shared/brief-scope.json';

const EXCLUDED = new Set<number>(briefScope.excluded_provision_ids);
const TABLE_SHOWN_MAX = 6000;   // a matched table longer than this is not shown (it is never cut)

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  if (process.env.PLAN_BRIEF !== 'on') {
    return NextResponse.json({ enabled: false, rows: [] }, { headers: { 'Cache-Control': 'no-store' } });
  }
  const rate = await checkRateLimit(getClientIdentifier(request), dataRateLimiter, 30, 60000);
  if (!rate.success) {
    return NextResponse.json({ error: 'Rate limit exceeded. Please try again in a minute.' }, { status: 429, headers: createRateLimitHeaders(rate) });
  }

  const sp = request.nextUrl.searchParams;
  const council = toLgaSlug(sp.get('council'));
  const devType = sp.get('dev_type');
  if (!council || !isBriefDevType(devType)) {
    return NextResponse.json({ enabled: true, rows: [], reason: 'council or project type not supported' }, { headers: { 'Cache-Control': 'no-store' } });
  }
  const group = zoneGroup(sp.get('zone'));
  // Only where the first five clauses per topic have been read against the council's own headings (shared/brief-scope.json).
  if (!inBriefScope(briefScope, council, devType, group)) {
    return NextResponse.json({ enabled: true, council, dev_type: devType, zone_group: group, rows: [], reason: 'not yet checked for this council, project type or zone' }, { headers: { 'Cache-Control': 'no-store' } });
  }

  const client = await getPool().connect();
  try {
    // The exact zone group only: the 'ANY' build was not read against the council's headings, so it is not a fallback.
    const sql = `
      SELECT b.row_type, b.rank, b.verdict,
             rp.id, rp.ref_number, rp.section_header, rp.source_chapter_key, rp.provision_text, rp.pdf_page, rp.printed_page_label, rp.page_check, rp.source_council,
             ${quoteColumns('rp')}
        FROM project_brief_rows b
        JOIN regulatory_provisions rp ON rp.id = b.provision_id
       WHERE b.council = $1 AND b.dev_type = $2 AND b.zone_group = $3
         AND rp.is_current = TRUE AND rp.v2_is_actionable = TRUE
         AND b.rank <= ${BRIEF_ROW_LIMIT}
       ORDER BY b.row_type, b.rank`;
    const result = await client.query(sql, [council, devType, group]);

    // The plan's own address per chapter: our R2 copy first (the page anchor is only right against the PDF we paginated), then the council's.
    const chapterKeys = Array.from(new Set(result.rows.map((r: any) => r.source_chapter_key).filter(Boolean)));
    const chapterUrls: Record<string, string> = {};
    const chapterLabels: Record<string, string> = {};
    if (chapterKeys.length > 0) {
      const reg = await client.query(
        `SELECT chapter_key, r2_public_pdf_url, council_url, council_page_url, chapter_label FROM dcp_chapter_registry
          WHERE council = $1 AND is_active = TRUE AND chapter_key = ANY($2::text[])`,
        [council, chapterKeys]);
      for (const x of reg.rows) { const u = x.r2_public_pdf_url || x.council_url || x.council_page_url; if (u) chapterUrls[x.chapter_key] = u; if (x.chapter_label) chapterLabels[x.chapter_key] = String(x.chapter_label); }
    }
    // A fragment or an opener shows the clauses that follow it on the page, so the figure is visible without opening the plan.
    const followOn: Record<number, string[]> = {};
    await Promise.all(result.rows.map(async (r: any) => {
      if (!needsFollowOn(String(r.provision_text ?? '')) || r.pdf_page == null || !r.source_chapter_key) return;
      const nx = await client.query(
        `SELECT provision_text FROM regulatory_provisions
          WHERE source_council = $1 AND source_chapter_key = $2 AND is_current = TRUE AND v2_is_actionable = TRUE
            AND id > $3 AND pdf_page BETWEEN $4 AND $4 + 1
          ORDER BY id LIMIT 25`,
        [r.source_council, r.source_chapter_key, r.id, r.pdf_page]);
      // A clause that names a table shows that table (its rows were extracted onto a nearby clause, e.g. Hornsby 3.1.2 a -> the end of 3.1.2 h);
      // anything else shows the next three clauses as before.
      const table = /\btable\b/i.test(String(r.provision_text ?? ''))
        ? tableFor(String(r.provision_text ?? ''), nx.rows.map((n: any) => tablePart(String(n.provision_text ?? ''))).filter((t: string | null): t is string => !!t))
        : null;
      // No table found: only a clause the old rule already sent on shows the next clauses; one that is new (names a table, states no figure) shows nothing.
      if (!table && !showsNextClauses(String(r.provision_text ?? ''))) return;
      // A table is shown whole or not at all: a cut that lands mid-row would drop an exception or a larger figure without saying so.
      if (table && table.length > TABLE_SHOWN_MAX) return;
      const lines = table
        ? [tidyText(table, table.length)].filter(Boolean)
        : nx.rows.slice(0, 3).map((n: any) => tidyText(n.provision_text, 500)).filter(Boolean);
      if (lines.length > 0) followOn[Number(r.id)] = lines;
    }));

    const rows: StoredBriefRow[] = result.rows.map((r: any) => {
      const clauseLabel = briefClauseLabel(r.section_header, r.ref_number);
      const served: any = withServedCitation(withCouncilWords(r), clauseLabel);
      const link = planLink(r.source_chapter_key ? chapterUrls[r.source_chapter_key] : null, r.pdf_page != null ? Number(r.pdf_page) : null);
      return {
        row_type: r.row_type,
        rank: Number(r.rank),
        item: {
          id: Number(r.id),
          verdict: r.verdict === 'APPLIES' ? 'APPLIES' : 'MIGHT',
          text: tidyText(served.provision_text),
          page: r.pdf_page != null ? Number(r.pdf_page) : null,
          pageLabel: r.printed_page_label ?? null,
          clauseLabel: served.clause_label ?? null,
          sectionHeader: r.section_header ?? null,
          chapterKey: r.source_chapter_key ?? null,
          chapterLabel: r.source_chapter_key ? (chapterLabels[r.source_chapter_key] ?? null) : null,
          pageProven: r.page_check === 'on_page',   // migration 079: the page really holds this clause
          url: link?.href ?? null,
          urlPage: link?.page ?? null,
          continues: followOn[Number(r.id)],
        },
      };
    });
    return NextResponse.json({ enabled: true, council, dev_type: devType, zone_group: group, rows: dropExcluded(rows, EXCLUDED) }, { headers: { 'Cache-Control': 'no-store' } });
  } finally {
    client.release();
  }
}
