'use client';

import dynamic from 'next/dynamic';
import Map from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

const ESRI_AERIAL: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: 'Tiles &copy; Esri',
      maxzoom: 19,
    },
  },
  layers: [{ id: 'esri-tiles', type: 'raster', source: 'esri' }],
};

interface Props {
  lat: number;
  lng: number;
  zoom?: number;
  height?: number;
}

export function AerialTile({ lat, lng, zoom = 19, height = 220 }: Props) {
  return (
    <Map
      initialViewState={{ latitude: lat, longitude: lng, zoom }}
      style={{ width: '100%', height }}
      mapStyle={ESRI_AERIAL}
      attributionControl={false}
      interactive={false}
    />
  );
}

export default dynamic(() => Promise.resolve(AerialTile), { ssr: false });
