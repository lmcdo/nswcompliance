/**
 * Shared aerial tile + GeoJSON polygon overlay for react-pdf reports.
 *
 * Converts GeoJSON [lng, lat] coordinates to SVG pixel positions over the
 * aerial tile PNG, using the same bbox that aerial-tile.ts fetched.
 *
 * Usage (any satellite report):
 *   <AerialWithOverlay
 *     tile_b64={data.tile_b64}
 *     center={[data.lng, data.lat]}
 *     zoom="property"
 *     layers={[
 *       { geojson: lotPolygon, fill: '#0d9488', fillOpacity: 0.15, stroke: '#0d9488', strokeWidth: 2 },
 *       { geojson: shadowOnLot, fill: '#f97316', fillOpacity: 0.55, stroke: '#ea580c', strokeWidth: 1 },
 *     ]}
 *   />
 *
 * Coordinate system: GeoJSON EPSG:4326 [lng, lat] -> SVG pixels.
 * Bbox is derived from ZOOM_PRESETS in aerial-tile.ts (single source of truth).
 */

import React from 'react';
import {
  View,
  Text,
  Image,
  Svg,
  Polygon as SvgPolygon,
  Line as SvgLine,
  Circle as SvgCircle,
  G,
} from '@react-pdf/renderer';
import { ZOOM_PRESETS } from './aerial-tile';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface GeoJSONGeometry {
  type: string;
  coordinates: unknown[];
}

interface GeoJSONFeature {
  type: 'Feature';
  geometry: GeoJSONGeometry;
  properties?: Record<string, unknown>;
}

interface GeoJSONCollection {
  type: 'FeatureCollection';
  features: GeoJSONFeature[];
}

export interface OverlayLayer {
  /** GeoJSON Polygon, MultiPolygon, or FeatureCollection. Null/undefined = skip. */
  geojson: GeoJSONGeometry | GeoJSONCollection | null | undefined;
  fill?: string;
  fillOpacity?: number;
  stroke?: string;
  strokeWidth?: number;
  /** SVG stroke-dasharray, e.g. "6,4" for dashed lines. */
  dasharray?: string;
}

interface AerialWithOverlayProps {
  tile_b64: string;
  /** [lng, lat] — must match the center used when fetching the tile. */
  center: [number, number];
  zoom?: 'property' | 'neighbourhood';
  layers?: OverlayLayer[];
  /** Optional label rendered bottom-left over the image. */
  label?: string;
  /** Attribution text below the image. */
  attribution?: string;
  /** Show north arrow. Default true. */
  northArrow?: boolean;
}

// ---------------------------------------------------------------------------
// Coordinate conversion
// ---------------------------------------------------------------------------

/**
 * Convert a GeoJSON [lng, lat] to SVG pixel coords.
 * X: lng increases rightward.  Y: lat increases upward but SVG Y increases downward.
 */
function geoToPixel(
  coord: [number, number],
  minLng: number,
  maxLat: number,
  scaleX: number,
  scaleY: number,
): [number, number] {
  return [
    (coord[0] - minLng) * scaleX,
    (maxLat - coord[1]) * scaleY,
  ];
}

/** Extract coordinate rings from a Polygon or MultiPolygon geometry. */
function extractRings(geom: GeoJSONGeometry): [number, number][][] {
  if (geom.type === 'Polygon') {
    return geom.coordinates as [number, number][][];
  }
  if (geom.type === 'MultiPolygon') {
    const rings: [number, number][][] = [];
    for (const poly of geom.coordinates as [number, number][][][]) {
      rings.push(...poly);
    }
    return rings;
  }
  return [];
}

/** Convert any supported GeoJSON input to SVG points strings. */
function toSvgPointStrings(
  input: GeoJSONGeometry | GeoJSONCollection | null | undefined,
  minLng: number,
  maxLat: number,
  scaleX: number,
  scaleY: number,
): string[] {
  if (!input) return [];

  const geometries: GeoJSONGeometry[] = [];
  if (input.type === 'FeatureCollection') {
    for (const f of (input as GeoJSONCollection).features) {
      geometries.push(f.geometry);
    }
  } else if (input.type === 'Feature' && 'geometry' in input) {
    geometries.push((input as unknown as GeoJSONFeature).geometry);
  } else {
    geometries.push(input as GeoJSONGeometry);
  }

  const result: string[] = [];
  for (const geom of geometries) {
    for (const ring of extractRings(geom)) {
      const pts = ring
        .map(c => geoToPixel(c, minLng, maxLat, scaleX, scaleY))
        .map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`)
        .join(' ');
      if (pts) result.push(pts);
    }
  }
  return result;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function AerialWithOverlay({
  tile_b64,
  center,
  zoom = 'property',
  layers = [],
  label,
  attribution = 'NSW SIX Maps (LPI_Imagery_Best) -- CC-BY 4.0 NSW Government',
  northArrow = true,
}: AerialWithOverlayProps) {
  const preset = ZOOM_PRESETS[zoom];
  const [centerLng, centerLat] = center;

  // Bbox matching aerial-tile.ts fetch
  const minLng = centerLng - preset.d_lng;
  const maxLng = centerLng + preset.d_lng;
  const minLat = centerLat - preset.d_lat;
  const maxLat = centerLat + preset.d_lat;

  // Pixels per degree
  const scaleX = preset.w / (maxLng - minLng);
  const scaleY = preset.h / (maxLat - minLat);

  const aspectRatio = preset.w / preset.h;

  return (
    <View style={{ marginBottom: 8 }}>
      <View style={{ position: 'relative', width: '100%' }}>
        <Image
          src={`data:image/png;base64,${tile_b64}`}
          style={{ width: '100%', borderRadius: 4 }}
        />
        {/* SVG overlay — positioned over the aerial image */}
        <View style={{ position: 'absolute', top: 0, left: 0, width: '100%', aspectRatio }}>
          <Svg viewBox={`0 0 ${preset.w} ${preset.h}`} style={{ width: '100%', height: '100%' }}>
            {layers.map((layer, li) => {
              if (!layer.geojson) return null;
              const pointStrings = toSvgPointStrings(
                layer.geojson, minLng, maxLat, scaleX, scaleY,
              );
              return pointStrings.map((pts, pi) =>
                layer.dasharray ? (
                  // Dashed outline — draw as line segments
                  <DashedPolygon
                    key={`l${li}-p${pi}`}
                    points={pts}
                    stroke={layer.stroke ?? '#6366f1'}
                    strokeWidth={layer.strokeWidth ?? 1.5}
                    dasharray={layer.dasharray}
                  />
                ) : (
                  <SvgPolygon
                    key={`l${li}-p${pi}`}
                    points={pts}
                    fill={layer.fill ?? 'none'}
                    fillOpacity={layer.fillOpacity ?? 0.3}
                    stroke={layer.stroke ?? 'none'}
                    strokeWidth={layer.strokeWidth ?? 0}
                  />
                ),
              );
            })}
            {/* North arrow */}
            {northArrow && (
              <G>
                <SvgCircle cx={30} cy={30} r={14} fill="rgba(0,0,0,0.6)" />
                <SvgLine x1={30} y1={20} x2={30} y2={40} stroke="white" strokeWidth={1.5} />
                <SvgLine x1={30} y1={20} x2={26} y2={26} stroke="white" strokeWidth={1.5} />
                <SvgLine x1={30} y1={20} x2={34} y2={26} stroke="white" strokeWidth={1.5} />
              </G>
            )}
          </Svg>
        </View>
        {/* Label overlay */}
        {label && (
          <View style={{
            position: 'absolute', bottom: 8, left: 8,
            backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 10,
            paddingHorizontal: 8, paddingVertical: 3,
          }}>
            <Text style={{ fontSize: 7.5, color: 'white' }}>{label}</Text>
          </View>
        )}
      </View>
      {attribution && (
        <Text style={{ fontSize: 7, color: '#6b7280', marginTop: 4 }}>
          {attribution}
        </Text>
      )}
    </View>
  );
}

// ---------------------------------------------------------------------------
// DashedPolygon — react-pdf doesn't support strokeDasharray on Polygon,
// so we draw individual line segments with dasharray.
// ---------------------------------------------------------------------------

function DashedPolygon({
  points,
  stroke,
  strokeWidth,
  dasharray,
}: {
  points: string;
  stroke: string;
  strokeWidth: number;
  dasharray: string;
}) {
  const coords = points.split(' ').map(p => {
    const [x, y] = p.split(',').map(Number);
    return [x, y] as [number, number];
  });
  return (
    <G>
      {coords.map(([x, y], i) => {
        const [nx, ny] = coords[(i + 1) % coords.length];
        return (
          <SvgLine
            key={i}
            x1={x} y1={y} x2={nx} y2={ny}
            stroke={stroke}
            strokeWidth={strokeWidth}
            strokeDasharray={dasharray}
          />
        );
      })}
    </G>
  );
}
