/**
 * GET /api/sepp/parking-provisions
 *
 * The SEPP (Housing) 2021 parking cards, each answered with the instrument's own
 * paragraphs and their `regulatory_provisions` ids. Replaces the JSX string literals in
 * StateLevelControls.tsx, two of which disagree with the stored instrument.
 *
 * The card -> provision mapping and the reason each card quotes a page rather than a
 * clause number live in `lib/sepp-parking-cards.ts`. This route is the round trip and
 * the failure semantics, nothing else.
 *
 * prior-art-checked: see the header of `lib/sepp-parking-cards.ts` for the four sweeps.
 * The nearest existing surfaces are /api/tod/parking-rates (per-property rate from
 * housing_sepp_standards + dcp_setback_controls, no card mapping, no provision ids) and
 * /api/sepp/structured-requirements (the complying-development exclusions table, which
 * holds nothing for 5 of these 6 cards). Neither can answer this.
 */

import { NextResponse } from 'next/server';
import { getClient } from '@/lib/database/pool-manager';
import {
  HOUSING_SEPP_DOCUMENT_ID,
  CITATION_STATUS_NOTE,
  allParkingMatchPatterns,
  resolveParkingCards,
  type ParkingProvisionRow,
} from '@/lib/sepp-parking-cards';

export const dynamic = 'force-dynamic';

/**
 * One query for every card.
 *
 * `document_id = $1` scopes to the whole-document extraction generation. Both
 * generations of this instrument are `is_current`, so without the scope several
 * predicates match twice and the id a card reports would depend on row order.
 *
 * `is_current` is strict here, not `IS NOT FALSE`: a NULL would mean we cannot say
 * whether the paragraph is still in force, and an unknown must not be served as the law.
 */
const PARKING_PROVISIONS_SQL = `
  SELECT id, ref_number, pdf_page, citation_status, provision_text, document_id
  FROM regulatory_provisions
  WHERE is_current
    AND source_council IS NULL
    AND document_id = $1
    AND provision_text ILIKE ANY ($2::text[])
  ORDER BY pdf_page NULLS LAST, id
`;

export async function GET() {
  let client;

  try {
    client = await getClient();

    const result = await client.query(PARKING_PROVISIONS_SQL, [
      HOUSING_SEPP_DOCUMENT_ID,
      allParkingMatchPatterns(),
    ]);

    const cards = resolveParkingCards(result.rows as ParkingProvisionRow[]);

    return NextResponse.json({
      available: true,
      documentId: HOUSING_SEPP_DOCUMENT_ID,
      citationNote: CITATION_STATUS_NOTE,
      cards,
      /**
       * A card that expected provisions and got none. Non-empty means our copy of the
       * instrument has drifted from the predicates — the cards fail closed on their own,
       * but this is the number a check can watch.
       */
      unmatchedCards: cards
        .filter((card) => !card.resolved && card.reason === 'unmatched')
        .map((card) => card.key),
    });
  } catch (error) {
    /**
     * A failed query is not "this instrument sets no parking rates". The caller gets a
     * 503 and `available: false` so it can say the rates could not be read, rather than
     * rendering six empty cards that look like an answer.
     */
    console.error('[SEPP Parking Provisions API] Error:', error);
    return NextResponse.json(
      {
        available: false,
        error: 'SEPP (Housing) 2021 parking provisions could not be read.',
        detail: error instanceof Error ? error.message : 'Unknown error',
        message:
          'This is not a finding that the SEPP sets no parking rates. The stored '
          + 'instrument was not successfully consulted.',
      },
      { status: 503 },
    );
  } finally {
    client?.release();
  }
}
