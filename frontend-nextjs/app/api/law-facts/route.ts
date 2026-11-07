/**
 * GET /api/law-facts
 *
 * The state-law figures the TOD panel shows, read from the `law_facts` table (one row per fact: clause, PDF page, the
 * sentence, law version date). Replaces figures typed into the page. Reads state law only: it never touches the rules
 * table or any council-plan table (checked by scripts/check_clean_feature_boundary.py).
 *
 * Failure is a 503 with `available: false`, never an empty 200: an unreadable table is not "the law sets no figure".
 *
 * prior-art-checked: modelled on app/api/sepp/parking-provisions/route.ts (same pool, same 503 semantics); that route reads
 * regulatory_provisions and holds none of these figures.
 */
import { NextResponse } from 'next/server';
import { getClient } from '@/lib/database/pool-manager';
import { LAW_FACT_KEYS, rowsToFacts, type LawFactRow } from '@/lib/law-facts';

export const dynamic = 'force-dynamic';

/** The instrument key law_facts uses; the same key instrument_registry uses for this policy. */
const INSTRUMENT_KEY = 'sepp_housing_2021';

/** `is_current` strict: a NULL would mean we cannot say the figure is still in force. */
const LAW_FACTS_SQL = `
  SELECT fact_key, value, value_number, unit, clause, pdf_page, quote, law_version_date
  FROM law_facts
  WHERE is_current
    AND instrument_key = $1
    AND fact_key = ANY($2::text[])
`;

export async function GET() {
  let client;
  try {
    client = await getClient();
    const result = await client.query(LAW_FACTS_SQL, [INSTRUMENT_KEY, [...LAW_FACT_KEYS]]);
    const facts = rowsToFacts(result.rows as LawFactRow[]);
    return NextResponse.json({ available: true, instrument: INSTRUMENT_KEY, facts });
  } catch (error) {
    console.error('[law-facts API] Error:', error);
    return NextResponse.json(
      {
        available: false,
        instrument: INSTRUMENT_KEY,
        facts: {},
        message: 'The stored law figures could not be read. This is not a finding that the law sets no figure.',
      },
      { status: 503 },
    );
  } finally {
    client?.release();
  }
}
