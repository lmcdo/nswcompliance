/**
 * Stored Housing Code standards, raw rows. The browser parses them with the
 * same module as the server (lib/cdc/housing-code-standards) so the live form
 * and the API agree.
 *
 * prior-art-checked: new read-only endpoint over cdc_eligibility_standards; no existing TS route serves these rows.
 */

import { NextResponse } from 'next/server';
import { publicRow } from '@/lib/cdc/housing-code-standards';
import { loadHousingCodeStandards } from '@/lib/cdc/housing-code-standards-db';

export const dynamic = 'force-dynamic';

export async function GET() {
  const stored = await loadHousingCodeStandards();
  return NextResponse.json({ success: stored.error === null, rows: stored.rows.map(publicRow), error: stored.error });
}
