'use client';

// prior-art-checked: see app/api/internal/structure-labels/route.ts header for
// the four sweeps. SetbackReviewQueue.tsx is the closest existing component and
// was read first; its one-at-a-time queue shape is reused deliberately, but it
// renders a machine-proposed value for acceptance, which is precisely what this
// component must not do.

import { useCallback, useEffect, useRef, useState } from 'react';

type Item = {
  id: number;
  address: string;
  lat: number;
  lng: number;
  lga_name: string | null;
  zone_code: string | null;
  lot_area_m2: number | null;
};

type Tile = {
  urls: string[];
  grid: number;
  size: number;
  zoom: number;
  centre_x: number;
  centre_y: number;
  width: number;
  height: number;
  sha256: string | null;
  licence: string;
};

type Box = {
  bbox_pixel: [number, number, number, number];
  structure_type: string;
  is_main_dwelling: boolean;
};

const TYPES: { value: string; label: string; hint: string }[] = [
  { value: 'main_dwelling', label: 'Main house', hint: 'The principal dwelling' },
  { value: 'secondary_dwelling', label: 'Secondary dwelling', hint: 'Granny flat / studio with its own entry' },
  { value: 'garage_carport', label: 'Garage / carport', hint: 'Roofed vehicle space' },
  { value: 'shed', label: 'Shed', hint: 'Any outbuilding' },
  { value: 'pool', label: 'Pool', hint: 'Swimming pool' },
  { value: 'other', label: 'Other', hint: 'Roofed structure that fits nothing above' },
];

const SAMPLE_ID = 'gf-recall-001';

export default function StructureLabeller() {
  const [item, setItem] = useState<Item | null>(null);
  const [tile, setTile] = useState<Tile | null>(null);
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [lotOutline, setLotOutline] = useState<[number, number][] | null>(null);
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [boxes, setBoxes] = useState<Box[]>([]);
  const [drawing, setDrawing] = useState<null | { x0: number; y0: number; x1: number; y1: number }>(null);
  const [pendingType, setPendingType] = useState<string>('shed');
  const [labeller, setLabeller] = useState('');

  const startedAt = useRef<number>(Date.now());
  const surfaceRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    const saved = window.localStorage.getItem('structure_labeller_name');
    if (saved) setLabeller(saved);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    setBoxes([]);
    setDrawing(null);
    try {
      const r = await fetch(`/api/internal/structure-labels?sample_id=${SAMPLE_ID}`);
      const d = await r.json();
      if (!r.ok) throw new Error(d?.error || 'load failed');
      setCounts(d.counts || {});
      setDone(Boolean(d.done));
      setItem(d.item ?? null);
      setTile(d.tile ?? null);
      setLotOutline(d.lot_outline ?? null);
      startedAt.current = Date.now();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'load failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // --- drawing ---------------------------------------------------------
  function pointIn(e: React.MouseEvent): { x: number; y: number } | null {
    const el = surfaceRef.current;
    if (!el || !tile) return null;
    const rect = el.getBoundingClientRect();
    // Rendered size may differ from natural size; convert to tile pixels so
    // the stored bbox is in the SAME space as the detector's bbox_pixel.
    const scaleX = tile.width / rect.width;
    const scaleY = tile.height / rect.height;
    return {
      x: Math.round((e.clientX - rect.left) * scaleX),
      y: Math.round((e.clientY - rect.top) * scaleY),
    };
  }

  function onDown(e: React.MouseEvent) {
    const p = pointIn(e);
    if (!p) return;
    setDrawing({ x0: p.x, y0: p.y, x1: p.x, y1: p.y });
  }

  function onMove(e: React.MouseEvent) {
    if (!drawing) return;
    const p = pointIn(e);
    if (!p) return;
    setDrawing({ ...drawing, x1: p.x, y1: p.y });
  }

  function onUp() {
    if (!drawing) return;
    const x0 = Math.min(drawing.x0, drawing.x1);
    const y0 = Math.min(drawing.y0, drawing.y1);
    const x1 = Math.max(drawing.x0, drawing.x1);
    const y1 = Math.max(drawing.y0, drawing.y1);
    setDrawing(null);
    // Ignore stray clicks: a 3px box is a misclick, not a building.
    if (x1 - x0 < 8 || y1 - y0 < 8) return;
    setBoxes((b) => [
      ...b,
      {
        bbox_pixel: [x0, y0, x1, y1],
        structure_type: pendingType,
        is_main_dwelling: pendingType === 'main_dwelling',
      },
    ]);
  }

  // --- saving ----------------------------------------------------------
  async function submit(status: 'labelled' | 'skipped', skipReason?: string) {
    if (!item) return;
    if (!labeller.trim()) {
      setError('Enter your name first — a label with no author is not evidence.');
      return;
    }
    if (status === 'labelled' && !lotOutline) {
      // Refuse rather than accept a guess. Labels drawn without knowing the
      // lot boundary would be scored against a detector that DOES know it, so
      // they would not measure recall — they would measure the disagreement
      // between two different questions.
      setError(
        'No lot boundary for this parcel — cannot label it. Skip it instead. ' +
        'Labelling without the boundary would score structures on neighbouring ' +
        'land against this lot.',
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      window.localStorage.setItem('structure_labeller_name', labeller.trim());
      const r = await fetch('/api/internal/structure-labels', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          id: item.id,
          status,
          labels: status === 'labelled' ? boxes : undefined,
          skip_reason: skipReason,
          labelled_by: labeller.trim(),
          seconds_spent: Math.round((Date.now() - startedAt.current) / 1000),
          tile: tile
            ? {
                sha256: tile.sha256,
                width: tile.width,
                height: tile.height,
                licence: tile.licence,
                zoom: tile.zoom,
                grid: tile.grid,
                centre_x: tile.centre_x,
                centre_y: tile.centre_y,
              }
            : undefined,
        }),
      });
      const d = await r.json();
      if (!r.ok) throw new Error(d?.error || 'save failed');
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'save failed');
    } finally {
      setSaving(false);
    }
  }

  const total =
    (counts.pending || 0) + (counts.labelled || 0) + (counts.skipped || 0);
  const finished = (counts.labelled || 0) + (counts.skipped || 0);

  if (loading) {
    return <div className="p-8 text-slate-600">Loading…</div>;
  }

  if (done) {
    return (
      <div className="p-8 max-w-2xl">
        <h1 className="text-xl font-semibold text-slate-900 mb-2">
          Sample complete
        </h1>
        <p className="text-slate-600">
          {counts.labelled || 0} labelled, {counts.skipped || 0} skipped.
        </p>
        <p className="text-sm text-slate-500 mt-4">
          Now run{' '}
          <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs">
            python scripts/measure_structure_detection_recall.py --sample-id {SAMPLE_ID}
          </code>{' '}
          to compare these answers against the detector. The pass mark is
          already committed in that file and must not be changed to fit the
          result.
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-5xl">
      <div className="flex items-baseline justify-between mb-1">
        <h1 className="text-xl font-semibold text-slate-900">Structure labelling</h1>
        <span className="text-sm text-slate-500">
          {finished} of {total}
        </span>
      </div>

      <p className="text-sm text-slate-600 mb-4 max-w-3xl">
        Mark <strong>every roofed structure you can see</strong> on this block.
        Drag a box around each one, then pick what it is. If the block has
        nothing but the house, mark the house and save — an empty answer is a
        real answer. You are not being shown what the scan found, deliberately:
        the whole point is to get a reading that does not agree with the machine
        by construction.
      </p>

      {error && (
        <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-800">
          {error}
        </div>
      )}

      {item && (
        <div className="mb-3 text-sm text-slate-600">
          <span className="font-medium text-slate-900">{item.address}</span>
          {item.lga_name && <> · {item.lga_name}</>}
          {item.zone_code && <> · {item.zone_code}</>}
          {item.lot_area_m2 !== null && <> · {Math.round(item.lot_area_m2)} m²</>}
        </div>
      )}

      <div className="flex flex-wrap gap-2 mb-3">
        {TYPES.map((t) => (
          <button
            key={t.value}
            type="button"
            onClick={() => setPendingType(t.value)}
            title={t.hint}
            className={`px-3 py-1.5 rounded-lg text-sm border transition-colors ${
              pendingType === t.value
                ? 'bg-teal-600 text-white border-teal-600'
                : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tile && (
        <>
          <div
            ref={surfaceRef}
            onMouseDown={onDown}
            onMouseMove={onMove}
            onMouseUp={onUp}
            onMouseLeave={() => setDrawing(null)}
            className="relative select-none cursor-crosshair border border-slate-300 rounded-lg overflow-hidden"
            style={{ width: '100%', maxWidth: tile.width, aspectRatio: '1 / 1' }}
          >
            <div
              className="grid absolute inset-0"
              style={{ gridTemplateColumns: `repeat(${tile.grid}, 1fr)` }}
            >
              {tile.urls.map((u) => (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  key={u}
                  src={u}
                  alt=""
                  draggable={false}
                  className="w-full h-full object-cover"
                />
              ))}
            </div>

            {/* The sampled lot. Without this the labeller cannot tell which
                structures belong to the property being scored — the tile spans
                roughly 77 m and covers several parcels in a dense suburb. */}
            {lotOutline && (
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox={`0 0 ${tile.width} ${tile.height}`}
                preserveAspectRatio="none"
              >
                <polygon
                  points={lotOutline.map(([x, y]) => `${x},${y}`).join(' ')}
                  fill="rgba(56,189,248,0.10)"
                  stroke="#38bdf8"
                  strokeWidth={4}
                  strokeDasharray="10 6"
                />
              </svg>
            )}

            {/* Committed boxes */}
            {boxes.map((b, i) => (
              <div
                key={i}
                className="absolute border-2 border-teal-400 bg-teal-400/20 pointer-events-none"
                style={{
                  left: `${(b.bbox_pixel[0] / tile.width) * 100}%`,
                  top: `${(b.bbox_pixel[1] / tile.height) * 100}%`,
                  width: `${((b.bbox_pixel[2] - b.bbox_pixel[0]) / tile.width) * 100}%`,
                  height: `${((b.bbox_pixel[3] - b.bbox_pixel[1]) / tile.height) * 100}%`,
                }}
              />
            ))}

            {/* In-progress box */}
            {drawing && (
              <div
                className="absolute border-2 border-amber-400 bg-amber-400/20 pointer-events-none"
                style={{
                  left: `${(Math.min(drawing.x0, drawing.x1) / tile.width) * 100}%`,
                  top: `${(Math.min(drawing.y0, drawing.y1) / tile.height) * 100}%`,
                  width: `${(Math.abs(drawing.x1 - drawing.x0) / tile.width) * 100}%`,
                  height: `${(Math.abs(drawing.y1 - drawing.y0) / tile.height) * 100}%`,
                }}
              />
            )}
          </div>
          <p className="mt-1 text-xs text-slate-400">{tile.licence}</p>
        </>
      )}

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <div className="text-sm text-slate-600">
          {boxes.length} marked
          {boxes.length > 0 && (
            <button
              type="button"
              onClick={() => setBoxes((b) => b.slice(0, -1))}
              className="ml-2 text-teal-700 underline"
            >
              undo last
            </button>
          )}
        </div>

        <input
          value={labeller}
          onChange={(e) => setLabeller(e.target.value)}
          placeholder="your name"
          className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm"
        />

        <button
          type="button"
          disabled={saving}
          onClick={() => submit('labelled')}
          className="px-4 py-2 rounded-lg bg-teal-600 text-white text-sm font-medium disabled:opacity-50"
        >
          {saving ? 'Saving…' : 'Save and next'}
        </button>

        <button
          type="button"
          disabled={saving}
          onClick={() => submit('skipped', 'imagery unusable')}
          className="px-3 py-2 rounded-lg border border-slate-300 text-sm text-slate-600"
          title="Cloud, deep shadow, or the tile failed to load"
        >
          Can&apos;t tell — skip
        </button>
      </div>
    </div>
  );
}
