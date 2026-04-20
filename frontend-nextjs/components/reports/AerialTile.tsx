'use client';

import dynamic from 'next/dynamic';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';
// maplibre-gl.css imported in app/reports/layout.tsx (must be in a server component to avoid dynamic chunk 404)

const ESRI_AERIAL: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: 'raster',
      tiles: [
        'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; NSW Government — Six Maps LPI Imagery (CC BY 4.0)',
      maxzoom: 20,
    },
  },
  layers: [{ id: 'esri-tiles', type: 'raster', source: 'esri' }],
};

interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

interface Props {
  lat: number;
  lng: number;
  zoom?: number;
  height?: number;
  lotPolygon?: GeoJSONPolygon | null;
}

function getBounds(polygon: GeoJSONPolygon): [[number, number], [number, number]] {
  const coords = polygon.coordinates[0];
  const lngs = coords.map(c => c[0]);
  const lats = coords.map(c => c[1]);
  return [
    [Math.min(...lngs), Math.min(...lats)],
    [Math.max(...lngs), Math.max(...lats)],
  ];
}

export function AerialTile({ lat, lng, zoom = 19, height = 220, lotPolygon }: Props) {
  const lotGeoJSON = lotPolygon
    ? { type: 'FeatureCollection' as const, features: [{ type: 'Feature' as const, geometry: lotPolygon, properties: {} }] }
    : null;

  const initialViewState = lotPolygon
    ? { bounds: getBounds(lotPolygon), fitBoundsOptions: { padding: 40 } }
    : { latitude: lat, longitude: lng, zoom };

  return (
    <Map
      initialViewState={initialViewState}
      style={{ width: '100%', height }}
      mapStyle={ESRI_AERIAL}
      attributionControl={false}
    >
      <NavigationControl position="top-right" showCompass showZoom={false} />

      {lotGeoJSON && (
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        <Source id="lot" type="geojson" data={lotGeoJSON as any}>
          <Layer
            id="lot-fill"
            type="fill"
            paint={{ 'fill-color': '#0d9488', 'fill-opacity': 0.15 }}
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

export default dynamic(() => Promise.resolve(AerialTile), { ssr: false });
