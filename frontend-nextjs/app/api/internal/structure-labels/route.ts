/**
 * GET  /api/internal/structure-labels  — serve the next unlabelled lot
 * POST /api/internal/structure-labels  — record one human answer
 *
 * prior-art-checked: reuse not viable because the three existing internal
 * queues answer a different question over a different substrate. Four sweeps,
 * 2026-08-08 against origin/main af7982a8:
 *   • app/api/internal/setback-review/route.ts — reads dcp_setback_controls
 *     rows already flagged needs_review and lets a human accept or correct a
 *     NUMBER that is already on screen. It shows the machine's answer by
 *     design; this route must never show one, so its shape is the opposite of
 *     what is needed here.
 *   • app/internal/dcp-review/page.tsx — the same pattern over
 *     dcp_review_queue (provision text).
 *   • app/internal/leads/page.tsx — a read-only list of lead rows.
 *   • ProvisionsByTocStructure.tsx matched only on the words "labels" and
 *     "structure"; it renders DCP provision headings and has no relation to
 *     imagery or ground truth.
 * None of the four fetches imagery, samples a population, or writes a label.
 * There is no table to extend either: no %label%/%ground%/%annot%/%truth%
 * table exists in the database. The shared auth gate and the getPool() access
 * pattern ARE reused, deliberately, so this sits inside the same /internal
 * surface rather than beside it.
 *
 * WHY THIS ROUTE CANNOT LEAK THE DETECTOR'S ANSWER
 * ------------------------------------------------
 * The number this feeds is detection recall. It is worthless if the person
 * labelling has already seen what the machine found — that is exactly how the
 * "13 of 16 confirmations" figure came to contain zero human input: the UI
 * defaulted to the machine's own count, so the machine agreed with itself.
 *
 * The guarantee here is structural, not a promise in a comment:
 *   • This file never imports, calls, or queries anything detector-related.
 *     It does not read granny_flat_reports. It cannot, because it holds no
 *     query against it.
 *   • The GET selects an explicit column list from structure_labels only, and
 *     that table has no column capable of holding a detection.
 *   • Tiles are fetched straight from the NSW SIX Maps public tile service,
 *     not through the detection pipeline, so there is no shared code path in
 *     which a detection could ride along.
 *
 * The comparison happens later, offline, in
 * scripts/measure_structure_detection_recall.py.
 */

import { NextRequest, NextResponse } from 'next/server';
import { createHash } from 'crypto';
import { getPool } from '@/lib/db';
import { createClient } from '@/lib/supabase/server';

export const dynamic = 'force-dynamic';

/**
 * The page component gates on auth, but a page gate protects a page, not an
 * endpoint — anyone could POST here directly and inject labels that steer the
 * eventual recall figure, or mark rows skipped. Both handlers check
 * independently. Returns null when allowed, a response when not.
 */
async function denyIfUnauthenticated(): Promise<NextResponse | null> {
  if (process.env.NEXT_PUBLIC_AUTH_ENABLED !== 'true') return null;
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ error: 'unauthorised' }, { status: 401 });
  }
  return null;
}

// Mirrors services/nsw_imagery.py — same provider, zoom and grid, so the
// labeller sees the same framing the detector would get for these coordinates.
const TILE_URL =
  'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile';
const TILE_SIZE = 256;
const ZOOM = 20;
const GRID = 3; // 3x3 => 768x768px at ~10cm/pixel
const LICENCE = 'CC-BY 4.0 NSW Government — Six Maps LPI Imagery';

/** Slippy-map tile coordinates. Same maths as _lat_lng_to_tile in Python. */
function latLngToTile(lat: number, lng: number, zoom: number): [number, number] {
  const n = 2 ** zoom;
  const x = Math.floor(((lng + 180) / 360) * n);
  const latRad = (lat * Math.PI) / 180;
  const y = Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n,
  );
  return [x, y];
}

function tileUrls(lat: number, lng: number): { urls: string[]; cx: number; cy: number } {
  const [cx, cy] = latLngToTile(lat, lng, ZOOM);
  const half = Math.floor(GRID / 2);
  const urls: string[] = [];
  // Row-major, top-left to bottom-right — the order the CSS grid renders and
  // the order the hash below consumes, so the hash describes what was shown.
  for (let dy = -half; dy <= half; dy++) {
    for (let dx = -half; dx <= half; dx++) {
      urls.push(`${TILE_URL}/${ZOOM}/${cy + dy}/${cx + dx}`);
    }
  }
  return { urls, cx, cy };
}

/**
 * Hash the tile bytes as fetched BY THE SERVER, in render order.
 *
 * WHAT THIS IS AND IS NOT — the honest version. An earlier comment here called
 * it "evidence of what was on screen". It is not, and overclaiming inside the
 * evidence layer is the failure this whole exercise exists to avoid. The
 * browser makes its OWN request for each tile; if the mosaic is refreshed
 * between the two fetches, or a tile fails to load in the browser but not
 * here, the labeller saw something this hash does not describe.
 *
 * What it IS: a record of the tile bytes the server could retrieve for these
 * coordinates at this moment. That is genuinely useful — it dates the imagery
 * and would expose a wholesale mosaic refresh between labelling and detection
 * — and it is weaker than "what was on screen".
 *
 * Making it exact would mean proxying these bytes to the browser and rendering
 * the proxied copy, so one fetch serves both. That is the right fix and is not
 * done here; it is recorded in the QA report rather than implied away.
 *
 * Returns null on any fetch failure rather than a hash of partial bytes — a
 * hash silently covering 7 of 9 tiles would be worse than no hash.
 */
async function hashTiles(urls: string[]): Promise<string | null> {
  try {
    const buffers = await Promise.all(
      urls.map(async (u) => {
        const r = await fetch(u, {
          headers: { 'User-Agent': 'PlotDetect/1.0 (structure labelling)' },
          cache: 'no-store',
        });
        if (!r.ok) throw new Error(`tile ${r.status}`);
        return Buffer.from(await r.arrayBuffer());
      }),
    );
    const h = createHash('sha256');
    for (const b of buffers) h.update(b);
    return h.digest('hex');
  } catch {
    return null;
  }
}

export async function GET(req: NextRequest) {
  const denied = await denyIfUnauthenticated();
  if (denied) return denied;

  const sampleId = req.nextUrl.searchParams.get('sample_id') || 'gf-recall-001';
  try {
    const pool = getPool();

    // Explicit column list. structure_labels holds no detector output, and
    // naming the columns keeps it that way if the table ever gains one.
    const { rows } = await pool.query(
      `SELECT id, address, lat, lng, lga_name, zone_code, lot_area_m2
         FROM structure_labels
        WHERE sample_id = $1 AND status = 'pending'
        ORDER BY id
        LIMIT 1`,
      [sampleId],
    );

    const progress = await pool.query(
      `SELECT status, count(*)::int AS n
         FROM structure_labels WHERE sample_id = $1 GROUP BY status`,
      [sampleId],
    );
    const counts: Record<string, number> = {};
    for (const r of progress.rows) counts[r.status] = r.n;

    if (rows.length === 0) {
      return NextResponse.json({ done: true, item: null, counts });
    }

    const item = rows[0];
    const { urls, cx, cy } = tileUrls(Number(item.lat), Number(item.lng));
    const tileSha = await hashTiles(urls);

    return NextResponse.json({
      done: false,
      counts,
      item: {
        id: item.id,
        address: item.address,
        lat: Number(item.lat),
        lng: Number(item.lng),
        lga_name: item.lga_name,
        zone_code: item.zone_code,
        // == null, not === null: the driver can return undefined for an
        // absent numeric, and Number(undefined) is NaN, which would render as
        // "NaN m²" beside the address. Loose equality catches both.
        lot_area_m2: item.lot_area_m2 == null ? null : Number(item.lot_area_m2),
      },
      tile: {
        urls,
        grid: GRID,
        size: TILE_SIZE,
        zoom: ZOOM,
        centre_x: cx,
        centre_y: cy,
        width: GRID * TILE_SIZE,
        height: GRID * TILE_SIZE,
        sha256: tileSha, // null when any tile failed — never a partial hash
        licence: LICENCE,
      },
    });
  } catch (err) {
    console.error('[structure-labels GET]', err);
    return NextResponse.json({ error: 'lookup failed' }, { status: 500 });
  }
}

type LabelBox = {
  bbox_pixel: [number, number, number, number];
  structure_type: string;
  is_main_dwelling: boolean;
};

const STRUCTURE_TYPES = new Set([
  'main_dwelling',
  'secondary_dwelling',
  'garage_carport',
  'shed',
  'pool',
  'other',
]);

export async function POST(req: NextRequest) {
  const denied = await denyIfUnauthenticated();
  if (denied) return denied;

  try {
    const body = await req.json();
    const { id, status, labels, skip_reason, labelled_by, seconds_spent, tile } =
      body ?? {};

    if (typeof id !== 'number') {
      return NextResponse.json({ error: 'id required' }, { status: 400 });
    }
    if (status !== 'labelled' && status !== 'skipped') {
      return NextResponse.json(
        { error: "status must be 'labelled' or 'skipped'" },
        { status: 400 },
      );
    }
    if (!labelled_by || typeof labelled_by !== 'string') {
      // The DB CHECK enforces this too; rejecting here gives a usable message
      // instead of a constraint violation.
      return NextResponse.json({ error: 'labelled_by required' }, { status: 400 });
    }

    if (status === 'skipped') {
      if (!skip_reason || typeof skip_reason !== 'string') {
        return NextResponse.json(
          { error: 'skip_reason required when skipping' },
          { status: 400 },
        );
      }
      const pool = getPool();
      // RETURNING + rowCount: the WHERE is conditional on status='pending', so
      // a second labeller submitting the same id updates nothing. Returning
      // ok:true there would advance their UI and silently discard a human
      // answer — the most expensive kind of loss in this whole exercise,
      // because the answer cannot be reconstructed.
      const skipRes = await pool.query(
        `UPDATE structure_labels
            SET status = 'skipped', skip_reason = $2, labelled_by = $3,
                labelled_at = now(), seconds_spent = $4
          WHERE id = $1 AND status = 'pending'
        RETURNING id`,
        [id, skip_reason, labelled_by, seconds_spent ?? null],
      );
      if (skipRes.rowCount === 0) {
        return NextResponse.json(
          { error: 'already answered by someone else — your answer was not saved' },
          { status: 409 },
        );
      }
      return NextResponse.json({ ok: true });
    }

    // status === 'labelled'. An EMPTY array is a valid, meaningful answer:
    // "I looked and there is nothing here". It must be accepted, or every
    // empty lot would be re-served forever and the labeller could never
    // finish — and, worse, the sample would silently over-represent lots that
    // happen to have structures.
    if (!Array.isArray(labels)) {
      return NextResponse.json(
        { error: 'labels must be an array (empty is a valid answer)' },
        { status: 400 },
      );
    }

    for (const l of labels as LabelBox[]) {
      const b = l?.bbox_pixel;
      if (!Array.isArray(b) || b.length !== 4 || b.some((v) => !Number.isFinite(v))) {
        return NextResponse.json(
          { error: 'each label needs bbox_pixel as 4 finite numbers' },
          { status: 400 },
        );
      }
      if (!STRUCTURE_TYPES.has(l?.structure_type)) {
        return NextResponse.json(
          { error: `unknown structure_type: ${l?.structure_type}` },
          { status: 400 },
        );
      }
      // The recall script trusts is_main_dwelling to exclude the house from
      // the truth set. If it were absent, non-boolean, or inconsistent with
      // structure_type, the main house would be counted as a secondary
      // structure the detector "missed" and recall would be corrupted.
      // Enforced rather than derived so a malformed client cannot slip one in.
      if (typeof l?.is_main_dwelling !== 'boolean') {
        return NextResponse.json(
          { error: 'is_main_dwelling must be a boolean' },
          { status: 400 },
        );
      }
      if (l.is_main_dwelling !== (l.structure_type === 'main_dwelling')) {
        return NextResponse.json(
          {
            error:
              'is_main_dwelling must be true for structure_type main_dwelling and false otherwise',
          },
          { status: 400 },
        );
      }
    }

    const pool = getPool();
    const res = await pool.query(
      `UPDATE structure_labels
          SET status = 'labelled',
              labels = $2::jsonb,
              labelled_by = $3,
              labelled_at = now(),
              seconds_spent = $4,
              tile_sha256 = $5,
              tile_width = $6,
              tile_height = $7,
              tile_licence = $8,
              tile_zoom = $9,
              tile_grid = $10,
              tile_centre_x = $11,
              tile_centre_y = $12
        WHERE id = $1 AND status = 'pending'
      RETURNING id`,
      [
        id,
        JSON.stringify(labels),
        labelled_by,
        seconds_spent ?? null,
        tile?.sha256 ?? null,
        tile?.width ?? null,
        tile?.height ?? null,
        tile?.licence ?? null,
        tile?.zoom ?? null,
        tile?.grid ?? null,
        tile?.centre_x ?? null,
        tile?.centre_y ?? null,
      ],
    );

    // Same reasoning as the skip path: a zero-row update means someone else
    // already answered this lot. Saying ok would throw away a human reading.
    if (res.rowCount === 0) {
      return NextResponse.json(
        { error: 'already answered by someone else — your answer was not saved' },
        { status: 409 },
      );
    }

    return NextResponse.json({ ok: true });
  } catch (err) {
    console.error('[structure-labels POST]', err);
    return NextResponse.json({ error: 'save failed' }, { status: 500 });
  }
}
