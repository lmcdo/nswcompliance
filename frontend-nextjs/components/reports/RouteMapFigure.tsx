// prior-art-checked: 2026-11-21. No component in frontend-nextjs draws a walking route (see lib/route-map-geometry.ts). This is an inline SVG with the street-map
// tiles as <image> elements under the routes: no map library and no new dependency, and it prints as part of the page. A tile that does not load is simply
// not drawn, so the plain background and the dots below remain. The data comes from services/lmr_route_map.py via the evidence endpoint.
import React, { useId, useMemo, useState } from 'react';
import type { RouteMap } from '@/lib/evidence-statement';
import { BASEMAP, destinationLabel, projectRouteMap } from '@/lib/route-map-geometry';

const COLOURS = { background: '#f4f1ea', busy: '#e8a33d', normal: '#2b6cb0', careful: '#1f9d55', lot: '#111827', destination: '#7c3aed' };

/** The walk to the station drawn as a line, once under the normal rule and once under the crossings-only rule. The legend and the text
 *  alternative carry every number, so the picture is never the only way to read it. A route that may not be drawn says why in text. */
export default function RouteMapFigure({ routeMap }: { routeMap: RouteMap }) {
  const uid = useId();
  const drawn = useMemo(() => (routeMap.status === 'ok' ? projectRouteMap(routeMap) : null), [routeMap]);
  const [loaded, setLoaded] = useState<Record<string, boolean>>({});   // tile key -> true when it drew, false when it failed
  const shown = (key: string) => loaded[key] !== false;
  const tilesLoaded = !!drawn && drawn.tiles.some((t) => loaded[t.key] === true);   // only the tiles under THIS map count, never a previous lot's

  if (routeMap.status !== 'ok' || !drawn) {
    return <p className="mt-2 text-gray-600">{`The route map is not drawn: ${routeMap.reason ?? 'no route could be drawn for this lot.'}`}</p>;
  }

  const dotsNote = tilesLoaded ? '' : ' Orange dots mark busy roads.';   // the dots are drawn only when no street map has loaded
  const dotsLegend = tilesLoaded ? '' : ' Orange dots: busy roads.';
  const normal = routeMap.normal ?? null;
  const careful = routeMap.careful ?? null;
  const dest = destinationLabel(routeMap.destination ?? careful?.destination ?? normal?.destination);   // a route's own destination if the top level has none
  // The nearest station can differ between the two rules: then each end is named and marked, never one end for both.
  const differ = routeMap.destinations_differ === true && !!careful && !!normal;
  const destCareful = destinationLabel(careful?.destination ?? routeMap.destination);
  const destNormal = destinationLabel(normal?.destination ?? routeMap.destination);
  // A line that stops short of the station says by how much, so it is never shorter than its distance without a reason.
  const missing = (l: typeof careful, name: string) => (l && (l.end_link_not_drawn_m ?? 0) > 0
    ? `The last ${Math.round(l.end_link_not_drawn_m ?? 0)} m of the ${name} walk, from the end of its line to the destination, are not drawn.` : null);
  const notDrawn = [missing(normal, 'normal'), missing(careful, 'crossings-only')].filter((t): t is string => !!t);
  const normalM = normal ? Math.round(normal.walk_m) : null;
  const carefulM = careful ? Math.round(careful.walk_m) : null;
  const diff = normalM !== null && carefulM !== null ? carefulM - normalM : null;
  const diffText = diff === null ? '' : diff === 0 ? ' (the same as the normal route)' : ` (${diff > 0 ? '+' : ''}${diff} m compared with the normal route)`;
  const description = [
    normalM !== null ? `The normal route is ${normalM} m.` : 'The normal route is not drawn.',
    carefulM !== null ? `The crossings-only route is ${carefulM} m${diffText}.` : 'The crossings-only route is not drawn.',
    differ ? `Both start at the lot. The normal route ends at ${destNormal}; the crossings-only route ends at ${destCareful}.${dotsNote}`
      : normal && careful ? `Both start at the lot and end at ${dest}.${dotsNote}`
        : `The walk starts at the lot and ends at ${dest}.${dotsNote}`,
  ].join(' ');
  const s = drawn.size;
  const halo = { stroke: '#ffffff', strokeWidth: 4, paintOrder: 'stroke' as const };

  return (
    <figure className="mt-3 break-inside-avoid">
      <svg viewBox={`0 0 ${s} ${s}`} role="img" aria-labelledby={`${uid}-t ${uid}-d`} className="w-full max-w-xl border" style={{ height: 'auto' }}>
        <title id={`${uid}-t`}>{differ ? `Map of the walks from the lot to ${destNormal} (normal route) and ${destCareful} (crossings-only route)` : `Map of the walk from the lot to ${dest}`}</title>
        <desc id={`${uid}-d`}>{description}</desc>
        <rect width={s} height={s} fill={COLOURS.background} />
        {drawn.tiles.filter((t) => shown(t.key)).map((t) => (
          <image key={t.key} href={t.url} x={t.x} y={t.y} width={t.size} height={t.size} preserveAspectRatio="none"
            onLoad={() => setLoaded((p) => (p[t.key] === true ? p : { ...p, [t.key]: true }))}
            onError={() => setLoaded((p) => ({ ...p, [t.key]: false }))} />
        ))}
        {/* the busy-road dots are the fallback when no street map has loaded: the street map already shows the roads */}
        {!tilesLoaded ? drawn.busy.map((b, i) => <circle key={i} cx={b.x} cy={b.y} r={3} fill={COLOURS.busy} />) : null}
        {/* the crossings-only route is drawn wider and first, the normal route thinner and dashed on top: where they share a path both show */}
        {drawn.careful ? <polyline points={drawn.careful.points} fill="none" stroke="#ffffff" strokeWidth={15} strokeLinejoin="round" strokeLinecap="round" /> : null}
        {drawn.careful ? <polyline points={drawn.careful.points} fill="none" stroke={COLOURS.careful} strokeWidth={9} strokeLinejoin="round" strokeLinecap="round" /> : null}
        {drawn.normal ? <polyline points={drawn.normal.points} fill="none" stroke={COLOURS.normal} strokeWidth={4} strokeDasharray="12 8" strokeLinejoin="round" strokeLinecap="butt" /> : null}
        <circle cx={drawn.lot.x} cy={drawn.lot.y} r={9} fill={COLOURS.lot} />
        <text x={drawn.lot.x + 14} y={drawn.lot.y - 10} fontSize={22} fill={COLOURS.lot} {...halo}>Lot</text>
        <rect x={drawn.destination.x - 9} y={drawn.destination.y - 9} width={18} height={18} fill={COLOURS.destination} />
        <text x={drawn.destination.x + 14} y={drawn.destination.y - 12} fontSize={22} fill={COLOURS.destination} {...halo}>{differ ? 'End (crossings-only)' : 'End'}</text>
        {differ && drawn.normal ? (
          <>
            <rect x={drawn.normal.end.x - 9} y={drawn.normal.end.y - 9} width={18} height={18} fill={COLOURS.destination} />
            <text x={drawn.normal.end.x + 14} y={drawn.normal.end.y + 28} fontSize={22} fill={COLOURS.destination} {...halo}>End (normal)</text>
          </>
        ) : null}
        <g transform={`translate(24 ${s - 30})`}>
          <line x1={0} y1={0} x2={drawn.scaleBar.px} y2={0} stroke={COLOURS.lot} strokeWidth={4} />
          <text x={drawn.scaleBar.px + 10} y={7} fontSize={20} fill={COLOURS.lot} {...halo}>{`${drawn.scaleBar.m} m`}</text>
        </g>
      </svg>
      <figcaption className="mt-1">
        <ul className="list-disc pl-5">
          <li>{normalM !== null ? <><strong>Normal route</strong> (blue dashed line): {normalM} m{differ ? `, ending at ${destNormal}` : ''}.</> : (routeMap.normal_note ?? 'The normal route is not drawn.')}</li>
          <li>{carefulM !== null ? <><strong>Crossings-only route</strong> (green line): {carefulM} m{diffText}{differ ? `, ending at ${destCareful}` : ''}.</> : (routeMap.careful_note ?? 'The crossings-only route is not drawn.')}</li>
          <li>{differ ? 'Black dot: where the walks start on the lot. Purple squares: where each walk ends.' + dotsLegend : `Black dot: where the walk starts on the lot. Purple square: the end of the walk, ${dest}.${dotsLegend}`}</li>
        </ul>
        {notDrawn.map((t) => <p key={t} className="mt-1">{t}</p>)}
        {routeMap.note && <p className="mt-1 text-gray-600">{routeMap.note}</p>}
        {routeMap.attribution && <p className="text-gray-600">{routeMap.attribution}</p>}
        {tilesLoaded ? <p className="text-gray-600">{BASEMAP.attribution}</p> : null}
      </figcaption>
    </figure>
  );
}
