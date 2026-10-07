// prior-art-checked: no existing extracted-value review write API in the repo
// (audited 2026-07-02). Mirrors the /api/dcp-review verdict pattern (named
// reviewer + audit trail) but applies the decision to the live, versioned
// dcp_setback_controls row. Every action is single-row and reversible:
//   confirm — clear needs_review (value kept), stamp reviewed_at + reason
//   remove  — is_current=FALSE (reversible soft-retire), stamp reason
//   fix     — SUPERSEDE: retire the old row (is_current=FALSE) and INSERT a
//             corrected row (is_current=TRUE) in one transaction, so history is
//             preserved and it is reversible. A corrected value MUST cite a
//             source (section_ref) — no value enters without a citation.
//
// dcp_setback_controls has no reviewed_by column (that lives on the separate
// dcp_review_queue), so the named reviewer + action + timestamp are recorded in
// review_reason. A structured reviewed_by column is a later enhancement.
import { NextResponse } from 'next/server';
import { getPool } from '@/lib/database/pool-manager';
import { requireReviewer } from '@/lib/internal-reviewer';

type Action = 'confirm' | 'remove' | 'fix';
const ACTIONS: readonly Action[] = ['confirm', 'remove', 'fix'];

/** A numeric coercion that treats '', null, undefined as absent (not 0). */
function optionalNumber(v: unknown): number | null {
  if (v === null || v === undefined || v === '') return null;
  const n = typeof v === 'number' ? v : Number(v);
  return Number.isFinite(n) ? n : null;
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  // Every action here writes a SERVED dcp_setback_controls row (`fix` inserts one), so it
  // is accepted only from an allowlisted reviewer (lib/internal-reviewer.ts).
  const { reviewer, denied } = await requireReviewer();
  if (denied) return denied;

  const { id } = await params;
  const numericId = Number(id);
  if (!Number.isInteger(numericId) || numericId <= 0) {
    return NextResponse.json({ error: 'invalid id' }, { status: 400 });
  }

  const body = (await req.json().catch(() => ({}))) as Record<string, unknown>;
  const action = body.action as Action;
  if (!ACTIONS.includes(action)) {
    return NextResponse.json(
      { error: `invalid action — expected one of ${ACTIONS.join(', ')}` },
      { status: 400 },
    );
  }

  const stamp = new Date().toISOString();
  const note = typeof body.note === 'string' && body.note.trim() ? body.note.trim() : null;
  const pool = getPool();

  try {
    // ── confirm: value verified, clear the flag ──────────────────────────────
    if (action === 'confirm') {
      const reason = `[review keep by ${reviewer} @ ${stamp}] ${note ?? 'value matches its cited clause'}`;
      const { rowCount } = await pool.query(
        `UPDATE dcp_setback_controls
            SET needs_review = FALSE, reviewed_at = NOW(), review_reason = $1
          WHERE id = $2 AND is_current = TRUE AND needs_review = TRUE`,
        [reason, numericId],
      );
      if (!rowCount) {
        return NextResponse.json({ error: 'not found or already resolved' }, { status: 404 });
      }
      return NextResponse.json({ ok: true, id: numericId, action, reviewer });
    }

    // ── remove: value not traceable to source — reversible soft-retire ───────
    if (action === 'remove') {
      const reason = `[review remove by ${reviewer} @ ${stamp}] ${note ?? 'value not present in / not traceable to cited clause'}`;
      const { rowCount } = await pool.query(
        `UPDATE dcp_setback_controls
            SET is_current = FALSE, needs_review = FALSE, reviewed_at = NOW(), review_reason = $1
          WHERE id = $2 AND is_current = TRUE`,
        [reason, numericId],
      );
      if (!rowCount) {
        return NextResponse.json({ error: 'not found or already resolved' }, { status: 404 });
      }
      return NextResponse.json({ ok: true, id: numericId, action, reviewer });
    }

    // ── fix: supersede with a corrected, cited value ─────────────────────────
    // A corrected regulatory value must cite its source and carry at least one
    // numeric bound — no value enters the table without a citation.
    const valueMin = optionalNumber(body.value_min);
    const valueMax = optionalNumber(body.value_max);
    const sectionRef = typeof body.section_ref === 'string' ? body.section_ref.trim() : '';
    const sourceText = typeof body.source_text === 'string' ? body.source_text.trim() : '';
    if (valueMin == null && valueMax == null) {
      return NextResponse.json(
        { error: 'fix requires a corrected value (value_min and/or value_max)' },
        { status: 400 },
      );
    }
    if (!sectionRef) {
      return NextResponse.json(
        { error: 'fix requires a source citation (section_ref) — no value without a source' },
        { status: 400 },
      );
    }

    const client = await pool.connect();
    try {
      await client.query('BEGIN');
      const { rows } = await client.query(
        `SELECT provision_id, lga, dev_type, control_type, unit, condition,
                applicability, source_chapter_key, value_min, value_max
           FROM dcp_setback_controls
          WHERE id = $1 AND is_current = TRUE
          FOR UPDATE`,
        [numericId],
      );
      if (!rows.length) {
        await client.query('ROLLBACK');
        return NextResponse.json({ error: 'not found or already resolved' }, { status: 404 });
      }
      const old = rows[0];

      await client.query(
        `UPDATE dcp_setback_controls
            SET is_current = FALSE, needs_review = FALSE, reviewed_at = NOW(),
                review_reason = $1
          WHERE id = $2`,
        [
          `[superseded by ${reviewer} @ ${stamp}] was min=${old.value_min ?? '—'} max=${old.value_max ?? '—'}; replaced by corrected row`,
          numericId,
        ],
      );

      const inserted = await client.query(
        `INSERT INTO dcp_setback_controls
           (provision_id, lga, dev_type, control_type, value_min, value_max,
            unit, condition, applicability, source_text, section_ref,
            source_chapter_key, is_current, needs_review, reviewed_at, review_reason)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12, TRUE, FALSE, NOW(), $13)
         RETURNING id`,
        [
          old.provision_id, old.lga, old.dev_type, old.control_type,
          valueMin, valueMax, old.unit, old.condition, old.applicability,
          sourceText || null, sectionRef, old.source_chapter_key,
          `[corrected by ${reviewer} @ ${stamp}] supersedes id=${numericId}${note ? `; ${note}` : ''}`,
        ],
      );
      await client.query('COMMIT');
      return NextResponse.json({
        ok: true,
        id: numericId,
        action,
        reviewer,
        new_id: inserted.rows[0].id,
      });
    } catch (e) {
      await client.query('ROLLBACK').catch(() => {});
      throw e;
    } finally {
      client.release();
    }
  } catch (e) {
    const message = e instanceof Error ? e.message : 'update failed';
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
