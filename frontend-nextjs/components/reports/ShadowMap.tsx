'use client';

import { useEffect, useRef, useMemo } from 'react';
import Map, { Source, Layer } from 'react-map-gl/maplibre';
import type { StyleSpecification, LngLatBoundsLike } from 'maplibre-gl';
// maplibre-gl.css imported in app/reports/layout.tsx (must be in a server component to avoid dynamic chunk 404)

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

interface Props {
  center: [number, number]; // [lng, lat]
  lotPolygon: GeoJSONGeometry | null;       // subject lot boundary
  shadowOnLot: GeoJSONCollection | null;    // shadow clipped to subject lot
  northProxy?: GeoJSONGeometry | null;      // northern neighbour proxy polygon (optional)
}

// ESRI World Imagery — free, no token required, widely used
const AERIAL_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: 'Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics',
      maxzoom: 19,
    },
  },
  layers: [{ id: 'esri-tiles', type: 'raster', source: 'esri' }],
};

function getBBox(lot: GeoJSONGeometry | null): LngLatBoundsLike | null {
  const coords: [number, number][] = [];

  function collectPolygon(rings: unknown[]) {
    for (const ring of rings) {
      if (Array.isArray(ring)) {
        for (const pt of ring) {
          if (Array.isArray(pt) && pt.length >= 2) {
            coords.push([pt[0] as number, pt[1] as number]);
          }
        }
      }
    }
  }

  if (!lot) return null;
  if (lot.type === 'Polygon') collectPolygon(lot.coordinates);
  if (lot.type === 'MultiPolygon') {
    for (const poly of lot.coordinates as unknown[][]) collectPolygon(poly);
  }

  if (coords.length === 0) return null;

  const lngs = coords.map(c => c[0]);
  const lats = coords.map(c => c[1]);
  return [
    [Math.min(...lngs), Math.min(...lats)],
    [Math.max(...lngs), Math.max(...lats)],
  ];
}

export function ShadowMap({ center, lotPolygon, shadowOnLot, northProxy }: Props) {
  const mapRef = useRef<{ fitBounds: (bounds: LngLatBoundsLike) => void } | null>(null);

  const lotGeoJSON = useMemo((): GeoJSONCollection | null => {
    if (!lotPolygon) return null;
    return {
      type: 'FeatureCollection',
      features: [{ type: 'Feature', geometry: lotPolygon, properties: {} }],
    };
  }, [lotPolygon]);

  const bbox = useMemo(() => getBBox(lotPolygon), [lotPolygon]);

  useEffect(() => {
    if (mapRef.current && bbox) {
      mapRef.current.fitBounds(bbox);
    }
  }, [bbox]);

  return (
    <Map
      ref={mapRef as never}
      initialViewState={bbox ? {
        bounds: bbox,
        fitBoundsOptions: { padding: 40 },
      } : {
        longitude: center[0],
        latitude: center[1],
        zoom: 19,
      }}
      style={{ width: '100%', height: '100%' }}
      mapStyle={AERIAL_STYLE}
      attributionControl={false}
      dragRotate={false}
      touchZoomRotate={false}
    >
      {/* Layer 1: Shadow clipped to subject lot — orange fill */}
      {shadowOnLot && (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        <Source id="shadow-on-lot" type="geojson" data={shadowOnLot as any}>
          <Layer
            id="shadow-on-lot-fill"
            type="fill"
            paint={{ 'fill-color': '#f97316', 'fill-opacity': 0.65 }}
          />
        </Source>
      )}

      {/* Layer 2: North proxy polygon — dashed outline only */}
      {northProxy && (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        <Source id="north-proxy" type="geojson" data={{ type: 'FeatureCollection', features: [{ type: 'Feature', geometry: northProxy, properties: {} }] } as any}>
          <Layer
            id="north-proxy-outline"
            type="line"
            paint={{ 'line-color': '#6366f1', 'line-width': 1.5, 'line-dasharray': [3, 2] }}
          />
        </Source>
      )}

      {/* Layer 3: Subject lot — teal fill + outline, rendered on top */}
      {lotGeoJSON && (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        <Source id="lot" type="geojson" data={lotGeoJSON as any}>
          <Layer
            id="lot-fill"
            type="fill"
            paint={{ 'fill-color': '#0d9488', 'fill-opacity': 0.18 }}
          />
          {/* White halo beneath teal — ensures visibility on dark roofs and green canopy */}
          <Layer
            id="lot-outline-halo"
            type="line"
            paint={{ 'line-color': '#ffffff', 'line-width': 4, 'line-opacity': 0.6 }}
          />
          <Layer
            id="lot-outline"
            type="line"
            paint={{ 'line-color': '#0d9488', 'line-width': 2 }}
          />
        </Source>
      )}
    </Map>
  );
}
