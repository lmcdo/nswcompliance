import { NextRequest, NextResponse } from 'next/server';
import { getClient } from '@/lib/db';

export async function GET(request: NextRequest) {
  const { searchParams } = new URL(request.url);
  const council = searchParams.get('council');

  if (!council) {
    return NextResponse.json({ error: 'council param required' }, { status: 400 });
  }

  const client = await getClient();
  try {
    // needs_review lives on instrument_registry (set TRUE by legislation_monitor.py
    // when an amendment is detected, cleared by update_instrument_provisions.py once
    // a human reconciles). The UI uses it to fail closed: an instrument with a
    // detected-but-unreconciled change must NOT show as "verified/current".
    // LEFT JOIN so currency rows without a registry row (e.g. DCP) default to false.
    const { rows } = await client.query<{
      instrument_key: string;
      instrument_label: string;
      instrument_type: string;
      verified_at: string | null;
      version_label: string | null;
      source_url: string | null;
      needs_review: boolean;
    }>(
      // DQ-127: every council's LEP sits in instrument_currency with council NULL, so
      // "council IS NULL" listed 22 other councils' LEPs (each up to 7 times) under any
      // property, and the panel's dot took the worst date across all of them. NULL still
      // means statewide for SEPPs; an LEP is shown only for the council it belongs to --
      // instrument_registry.council, else the slug its key starts with -- or that
      // council's parent (marrickville -> inner_west). One row per instrument, latest check.
      `WITH me AS (
         SELECT $1::text AS slug
         UNION
         SELECT parent_lga FROM lga_registry
         WHERE slug = $1 AND parent_lga IS NOT NULL AND is_active = TRUE
       ),
       latest AS (
         SELECT DISTINCT ON (ic.instrument_key)
                ic.instrument_key, ic.instrument_label, ic.instrument_type,
                ic.verified_at, ic.version_label, ic.source_url,
                COALESCE(r.needs_review, FALSE) AS needs_review
         FROM instrument_currency ic
         LEFT JOIN instrument_registry r ON r.instrument_key = ic.instrument_key
         WHERE ic.council = $1
            OR (ic.council IS NULL AND ic.instrument_type <> 'lep')
            OR (ic.council IS NULL AND ic.instrument_type = 'lep'
                AND COALESCE(r.council, regexp_replace(ic.instrument_key, '_lep_[0-9]+$', ''))
                    IN (SELECT slug FROM me))
         ORDER BY ic.instrument_key, ic.verified_at DESC NULLS LAST
       )
       SELECT * FROM latest
       ORDER BY instrument_type, instrument_label`,
      [council],
    );

    return NextResponse.json({ currency: rows });
  } finally {
    client.release();
  }
}
