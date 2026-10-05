/**
 * SEPP (Housing) 2021 parking cards — card -> the instrument's own words, by provision id.
 *
 * The SEPP tab's parking cards state rates as JSX string literals. Two of the six
 * disagree with the stored instrument and one of those states a rate the instrument
 * does not contain at all (measured 2026-10-05, see UNSOURCED_CARDS below). Nothing
 * pins the literals, so nothing notices. This module is the data path that replaces
 * them: every card resolves to the verbatim provision rows that carry its rate, each
 * with its `regulatory_provisions.id` and page, or it resolves to nothing and says so.
 *
 * It renders the law's words rather than a number parsed out of them. A parsed rate
 * needs a reading of which paragraph is the rate, which condition qualifies it and
 * which fallback displaces it — that reading is what produced the two wrong cards.
 * Quoting the matched paragraphs, in order, with their pages, needs no reading.
 *
 * prior-art-checked: no existing surface answers this question.
 *   - DB content: `sepp_structured_requirements` (560 rows) holds complying-development
 *     exclusions + the Pattern Book — 0 rows for 5 of the 6 card topics, 1 for co-living,
 *     and `sepp_id`/`development_type_category`/`section` are populated on 7 rows of 560.
 *     `housing_sepp_standards` (45 rows) holds the LMR/dual-occ/terraces/secondary-dwelling
 *     standards; its 5 `parking_per_dwelling` rows cover dual_occupancy, multi_dwelling,
 *     residential_flat_r1r2, secondary_dwelling and terraces — none of the six card types.
 *     `regulatory_provisions` carries all of them except in-fill.
 *   - Frontend: grepped `app/api/**` and `lib/**` for parking. /api/tod/parking-rates and
 *     /api/compliance/parking answer "what is the rate for THIS property's dev type" from
 *     housing_sepp_standards + dcp_setback_controls; /api/sepp/structured-requirements
 *     serves the exclusions table; /api/provisions/by-ids and /api/sepp/full-text fetch by
 *     id or EPI name but carry no card mapping and no `pdf_page`. None resolve a card to
 *     its provision.
 *   - Python: no writer for any of this (`git grep` over services/ scripts/ src/ enrichment/
 *     for the boarding-room parking wording returns only two archived one-off inserts).
 *   - Plans/memory: ce-lep-sepp-currency-integration-PROMPT-2026-10-05.md STEP 5 AMENDMENT
 *     sections 1-2, which rule out `sepp_structured_requirements` and name
 *     `regulatory_provisions` as the store.
 */

/**
 * The extraction generation these predicates were verified against.
 *
 * Every served statewide instrument is stored TWICE — a whole-document run
 * (`*__NSW_Legislation`, extraction_timestamp 2025-10-13) and an older split run
 * (`(...)___NSW_Legislation[_section_N]`, epoch timestamps ~Sep 2025) — and both are
 * `is_current`. The whole-document generation is the one carrying `pdf_page`, which is
 * the only citation this instrument can prove (no statewide row has a populated
 * `citation_status`; see CITATION_STATUS_NOTE). Scoping to it is load-bearing, not
 * tidiness: unscoped, 5 of the 9 predicates below match 2-3 rows across generations.
 */
export const HOUSING_SEPP_DOCUMENT_ID =
  'State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation';

/**
 * Why these cards cite a page and not a clause number.
 *
 * Of 17,933 current statewide `regulatory_provisions` rows, 0 have a populated
 * `citation_status`, and of the Housing SEPP's own rows 0 have a `section_header`
 * (measured 2026-10-05). Under #1170 a clause number is shown only when proven, else
 * the page. So a card may show the instrument, the matched text and its page, and may
 * deep-link to NSW Legislation — but a clause number on one of these cards is a
 * hand-verified label on a link, never extracted data, and must not be presented as
 * though it came from the database.
 */
export const CITATION_STATUS_NOTE =
  'Page reference from the stored instrument. Clause numbers on this card are not '
  + 'database-sourced.';

export type SeppParkingCardKey =
  | 'boarding_house'
  | 'co_living'
  | 'build_to_rent'
  | 'in_fill_affordable'
  | 'seniors_independent_living'
  | 'tod_affordable';

/**
 * One paragraph of the instrument that a card needs to state its rate honestly.
 *
 * `role` is what the paragraph does, because a rate alone is not the standard: s74's
 * 0.2/0.5 applies only to development in a designated Sydney local government area
 * (`condition`) and is displaced elsewhere by the council's own rate (`fallback`).
 * A card that showed only the `rate` row would be true of the text and wrong about
 * the law.
 *
 * `match` is matched with ILIKE against `provision_text`, so `%` and `_` are wildcards.
 * Each one is a verbatim fragment of the paragraph it names and each resolves to
 * exactly ONE row within HOUSING_SEPP_DOCUMENT_ID. If the instrument is amended and the
 * wording moves, the match drops to zero rows and the card reports itself unresolved —
 * it never falls back to a literal.
 */
export interface SeppParkingProvisionRef {
  role: 'rate' | 'condition' | 'fallback' | 'lead_in';
  match: string;
  /** The row this resolved to when the predicate was written, for review diffs only. */
  verifiedProvisionId: number;
  verifiedPdfPage: number;
}

export interface SeppParkingCard {
  key: SeppParkingCardKey;
  label: string;
  /** `instrument_registry.instrument_key`, for the currency badge to key off. */
  instrumentKey: 'sepp_housing_2021';
  /**
   * Hand-verified section label for the NSW Legislation deep link, or null to link the
   * whole instrument. NOT database-sourced — see CITATION_STATUS_NOTE. Null where the
   * section could not be verified against the law in force.
   */
  legislationAnchor: string | null;
  refs: SeppParkingProvisionRef[];
}

/**
 * Cards whose rate has NO source in the stored instrument.
 *
 * In-fill affordable housing is Chapter 2, Part 2, Division 1. Its non-discretionary
 * development standards section (s19, page 9) carries no parking rate, and neither does
 * any other paragraph of the division: of the 38 rows in this instrument that mention
 * "parking space", the only one on pages 5-11 that states a rate is the boarding-house
 * rate at page 11 (measured 2026-10-05). The card currently shows "0.2 parking spaces
 * per dwelling in an accessible area, 0.5 otherwise", which is the build-to-rent rate
 * from s74 at page 35.
 *
 * Whether the law in force grants in-fill affordable housing a parking standard that our
 * 2025-10-13 extraction missed cannot be settled from this machine: legislation.nsw.gov.au
 * returns a Cloudflare challenge to scripted fetches and there is no local PDF
 * (`documents.pdf_path` points at `docs/sepps/...`, which is not in the repo). Until it is
 * read from the law in force, the card states no rate.
 */
export const UNSOURCED_CARDS: Readonly<Record<string, string>> = {
  in_fill_affordable:
    'No non-discretionary parking standard for in-fill affordable housing was found in '
    + 'the stored instrument. Parking for this development type is set by the council '
    + 'development control plan — see the DCP Provisions tab.',
};

export const SEPP_PARKING_CARDS: readonly SeppParkingCard[] = [
  {
    key: 'boarding_house',
    label: 'Boarding Houses',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: 'sec.24',
    refs: [
      {
        role: 'rate',
        verifiedProvisionId: 40310,
        verifiedPdfPage: 11,
        match: '%parking spaces for each boarding room%',
      },
    ],
  },
  {
    key: 'co_living',
    label: 'Co-Living Housing',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: 'sec.68',
    refs: [
      {
        role: 'rate',
        verifiedProvisionId: 40570,
        verifiedPdfPage: 32,
        match: '%parking spaces for each private room%',
      },
    ],
  },
  {
    // The card this replaces showed per-bedroom tiers (0.2 / 0.5 / 1 per dwelling by
    // bedroom count). The instrument states a flat rate for this type and conditions it
    // on the local government area; the tiers belong to other divisions of the SEPP.
    key: 'build_to_rent',
    label: 'Build-to-Rent Housing',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: 'sec.74',
    refs: [
      {
        role: 'condition',
        verifiedProvisionId: 40604,
        verifiedPdfPage: 35,
        match: '%for development carried out wholly or partly on land in a designated Sydney local government area%',
      },
      {
        role: 'rate',
        verifiedProvisionId: 40605,
        verifiedPdfPage: 35,
        match: '%0.2 parking spaces for each dwelling%',
      },
      {
        role: 'fallback',
        verifiedProvisionId: 40606,
        verifiedPdfPage: 36,
        match: '%required under the relevant development control plan or local environmental plan for a residential flat building%',
      },
    ],
  },
  {
    key: 'in_fill_affordable',
    label: 'In-Fill Affordable Housing',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: null,
    refs: [],
  },
  {
    key: 'seniors_independent_living',
    label: 'Seniors Independent Living',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: 'sec.108',
    refs: [
      {
        role: 'rate',
        verifiedProvisionId: 40722,
        verifiedPdfPage: 47,
        match: '%at least 1 parking space for every 5 dwellings%',
      },
      {
        role: 'rate',
        verifiedProvisionId: 40723,
        verifiedPdfPage: 47,
        match: '%at least 0.5 parking spaces for each bedroom%',
      },
    ],
  },
  {
    // The card this replaces prefixed these rates with "In accessible area:". The
    // instrument attaches no accessible-area condition to them — they apply to the
    // affordable housing dwellings that s156 requires, wherever the development is.
    key: 'tod_affordable',
    label: 'Affordable Housing in TOD Areas',
    instrumentKey: 'sepp_housing_2021',
    legislationAnchor: null,
    refs: [
      {
        role: 'lead_in',
        verifiedProvisionId: 41014,
        verifiedPdfPage: 72,
        match: '%must provide the following number of parking spaces for each affordable housing dwelling%',
      },
      {
        role: 'rate',
        verifiedProvisionId: 41015,
        verifiedPdfPage: 72,
        match: '%containing 1 bedroom—0.4 parking space,%',
      },
    ],
  },
] as const;

/** Every ILIKE pattern the cards need, for a single round trip. */
export function allParkingMatchPatterns(): string[] {
  return SEPP_PARKING_CARDS.flatMap((card) => card.refs.map((ref) => ref.match));
}

/** A row as the route selects it. */
export interface ParkingProvisionRow {
  id: number;
  ref_number: string | null;
  pdf_page: number | null;
  citation_status: string | null;
  provision_text: string;
  document_id: string;
}

export interface ResolvedParkingProvision {
  role: SeppParkingProvisionRef['role'];
  provisionId: number;
  refNumber: string | null;
  pdfPage: number | null;
  /** True when the row carries a proven clause citation. Always false today. */
  citationProven: boolean;
  text: string;
}

export type ResolvedParkingCard =
  | {
      key: SeppParkingCardKey;
      label: string;
      instrumentKey: string;
      legislationAnchor: string | null;
      resolved: true;
      provisions: ResolvedParkingProvision[];
    }
  | {
      key: SeppParkingCardKey;
      label: string;
      instrumentKey: string;
      legislationAnchor: string | null;
      resolved: false;
      /**
       * 'unsourced' — the instrument has no such standard; the explanation is settled
       * and lives in UNSOURCED_CARDS. 'unmatched' — the card expects provisions and the
       * query returned none, so the wording has moved or the extraction has changed.
       * They are not the same and must not render the same: the first is an answer about
       * the law, the second is a defect in our copy of it.
       */
      reason: 'unsourced' | 'unmatched';
      message: string;
      /** Patterns that found nothing, so an unmatched card is diagnosable. */
      missing: string[];
    };

/** ILIKE, over text already in memory. Only `%` and `_` are special. */
export function ilikeMatches(text: string, pattern: string): boolean {
  let regex = '';
  for (const ch of pattern) {
    if (ch === '%') regex += '[\\s\\S]*';
    else if (ch === '_') regex += '[\\s\\S]';
    else regex += ch.replace(/[.*+?^${}()|[\]\\]/, '\\$&');
  }
  return new RegExp(`^${regex}$`, 'i').test(text);
}

/**
 * Group the rows one query returned onto the cards that asked for them.
 *
 * A card is `resolved` only when EVERY one of its refs found a row. A partial match is
 * reported unmatched rather than rendered, because the missing ref is as likely to be
 * the condition or the fallback as the rate, and a rate shown without its condition is
 * the defect this module exists to remove.
 *
 * Rows from the other extraction generation are dropped here as well as in the route's
 * `document_id = $1`. The older split run carries several of these paragraphs with the
 * same wording and no `pdf_page`, so a mixed result set would make the id and page a
 * card reports depend on row order — and the page is the only citation these cards can
 * prove. One guard in the SQL would be enough right until a second caller forgets it.
 */
export function resolveParkingCards(allRows: ParkingProvisionRow[]): ResolvedParkingCard[] {
  const rows = allRows.filter((row) => row.document_id === HOUSING_SEPP_DOCUMENT_ID);

  return SEPP_PARKING_CARDS.map((card): ResolvedParkingCard => {
    const head = {
      key: card.key,
      label: card.label,
      instrumentKey: card.instrumentKey,
      legislationAnchor: card.legislationAnchor,
    };

    if (card.refs.length === 0) {
      return {
        ...head,
        resolved: false,
        reason: 'unsourced',
        message:
          UNSOURCED_CARDS[card.key]
          ?? 'This card states no rate: none was found in the stored instrument.',
        missing: [],
      };
    }

    const provisions: ResolvedParkingProvision[] = [];
    const missing: string[] = [];

    for (const ref of card.refs) {
      const row = rows.find((candidate) => ilikeMatches(candidate.provision_text, ref.match));
      if (!row) {
        missing.push(ref.match);
        continue;
      }
      provisions.push({
        role: ref.role,
        provisionId: row.id,
        refNumber: row.ref_number,
        pdfPage: row.pdf_page,
        citationProven: row.citation_status === 'verified',
        text: row.provision_text,
      });
    }

    if (missing.length > 0) {
      return {
        ...head,
        resolved: false,
        reason: 'unmatched',
        message:
          `${card.label}: ${missing.length} of ${card.refs.length} provisions for this `
          + 'card are no longer in the stored instrument. The rate is not shown rather '
          + 'than shown from a stale copy.',
        missing,
      };
    }

    return { ...head, resolved: true, provisions };
  });
}
