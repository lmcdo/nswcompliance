'use client';

import { useState } from 'react';
import { AddressAutocomplete } from '@/components/reports/AddressAutocomplete';
import Map, { Source, Layer, NavigationControl } from 'react-map-gl/maplibre';
import type { StyleSpecification } from 'maplibre-gl';

interface DetectedStructure {
  index: number;
  area_m2: number | null;
  bbox_pixel: number[];
  matched_prompt: string;
  is_main_dwelling: boolean;
}

interface DetectResult {
  detect_id: string;
  address: string;
  lat: number;
  lng: number;
  prop_id: string;
  lot_area_m2: number | null;
  sepp_eligible: boolean;
  sepp_ineligible_reason: string | null;
  detected_structures: DetectedStructure[];
  samgeo_structure_count: number;
  samgeo_validated: boolean;
  confirmation_required: boolean;
  tile_licence: string;
  tile_b64?: string;
  tile_width?: number;
  tile_height?: number;
  tile_bbox?: { min_lat: number; max_lat: number; min_lng: number; max_lng: number };
  lot_polygon_wgs84?: number[][][]; // [[lng, lat], ...] rings in WGS84
}

interface ConfirmResult {
  report_id: string;
  address: string;
  granny_flat_buildable: boolean;
  max_floor_area_m2: number;
  estimated_weekly_rent_aud: number | null;
  rental_yield_annual_pct: number | null;
  assumed_build_cost_aud: number | null;
  confidence: string;
  confidence_reason: string;
  data_sources: string[];
  warnings: string[];
}

type PageState = 'idle' | 'detecting' | 'confirming' | 'complete' | 'error' | 'ineligible';

const ELIGIBLE_ZONE_PREFIXES = ['R1', 'R2', 'R3', 'R4', 'R5', 'RU5'];

const CONFIDENCE_LABEL: Record<string, string> = {
  high: 'High confidence',
  medium: 'Medium confidence',
  low: 'Low confidence (pre-validation)',
};

export default function GrannyFlatPage() {
  const [address, setAddress] = useState('');
  const [inputAddress, setInputAddress] = useState(''); // user's typed input, preserved for display
  const [ineligibleEvidence, setIneligibleEvidence] = useState(''); // authoritative reference shown in ineligible state
  const [state, setState] = useState<PageState>('idle');
  const [detectResult, setDetectResult] = useState<DetectResult | null>(null);
  const [confirmedCount, setConfirmedCount] = useState(1);
  const [finalResult, setFinalResult] = useState<ConfirmResult | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [calcBuildCost, setCalcBuildCost] = useState(2500);
  const [calcWeeklyRent, setCalcWeeklyRent] = useState(450);

  const handleDetect = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!address.trim()) return;

    setInputAddress(address.trim());
    setState('detecting');
    setDetectResult(null);
    setFinalResult(null);
    setErrorMsg('');

    try {
      // Step 1: enqueue detect job (returns immediately with jobId)
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ address, action: 'detect' }),
      });
      const json = await res.json();
      if (!res.ok) {
        if (json.ineligible) {
          setErrorMsg(json.error ?? 'This property is not eligible.');
          setIneligibleEvidence(json.evidence ?? '');
          setState('ineligible');
          return;
        }
        throw new Error(json.error || 'Detection failed');
      }

      const jobId: string = json.jobId;

      // Step 2: poll until detect result is written to DB (max 3 min)
      const poll = async (attempts = 0): Promise<void> => {
        if (attempts >= 90) {
          throw new Error('Detection timed out after 3 minutes. Please try again.');
        }
        const pollRes = await fetch(`/api/satellite/granny-flat?jobId=${jobId}`);
        const pollJson = await pollRes.json();

        if (pollJson.status === 'error') {
          throw new Error(pollJson.error || 'Detection failed — please try again.');
        }
        if (pollJson.status === 'detected') {
          const detectData = pollJson.data;
          setDetectResult(detectData);
          if (detectData.samgeo_validated && detectData.detected_structures?.length > 0) {
            setConfirmedCount(detectData.detected_structures.length);
          } else {
            setConfirmedCount(1);
          }
          setState('confirming');
          return;
        }

        // Still pending — try again in 2s
        await new Promise((r) => setTimeout(r, 2000));
        return poll(attempts + 1);
      };

      await poll();
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const handleConfirm = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!detectResult) return;

    setState('detecting'); // reuse spinner
    setFinalResult(null);
    setErrorMsg('');

    try {
      const res = await fetch('/api/satellite/granny-flat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: detectResult.address,
          action: 'confirm',
          detect_id: detectResult.detect_id,
          confirmed_structure_count: confirmedCount,
          samgeo_structure_count: detectResult.samgeo_structure_count,
          postcode: address.match(/\b(\d{4})\b/)?.[1] ?? null,
        }),
      });

      const json = await res.json();
      if (!res.ok) throw new Error(json.error || 'Calculation failed');

      setFinalResult(json);
      setState('complete');
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : 'Unknown error');
      setState('error');
    }
  };

  const isRunning = state === 'detecting';

  return (
    <div className="max-w-2xl">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Granny Flat Yield Predictor</h1>
        <p className="mt-1.5 text-sm text-gray-500">
          Detect existing structures from aerial imagery, calculate the buildable envelope under SEPP Housing 2021, and estimate weekly rental yield.
        </p>
      </div>

      {/* Step 1: address entry */}
      {(state === 'idle' || state === 'error') && (
        <form onSubmit={handleDetect} className="space-y-4 mb-6">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Property address</label>
            <AddressAutocomplete
              value={address}
              onChange={setAddress}
              onSelect={(addr) => setAddress(addr)}
              className="w-full px-4 py-2.5 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent"
              disabled={isRunning}
            />
          </div>
          {state === 'error' && (
            <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-sm text-red-700">
              {errorMsg}
            </div>
          )}

          <button
            type="submit"
            disabled={isRunning || !address.trim()}
            className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Detect structures
          </button>
        </form>
      )}

      {/* Ineligible — permanent result, no retry button */}
      {state === 'ineligible' && (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          <div className="p-6 flex items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-gray-900">{inputAddress}</p>
            </div>
            <span className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-red-100 text-red-800">
              Not eligible
            </span>
          </div>
          {ineligibleEvidence && (
            <div className="px-6 py-3 bg-gray-50">
              <p className="text-xs text-gray-500 mb-0.5">Property record</p>
              <p className="text-xs font-mono text-gray-700">{ineligibleEvidence}</p>
            </div>
          )}
          <div className="p-6">
            <p className="text-sm text-gray-700">{errorMsg}</p>
          </div>
          <div className="px-6 py-4">
            <button
              type="button"
              onClick={() => { setState('idle'); setErrorMsg(''); setIneligibleEvidence(''); setAddress(''); }}
              className="text-sm text-teal-600 hover:text-teal-700 underline"
            >
              Search another address
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {state === 'detecting' && (
        <div className="bg-white rounded-xl border border-gray-200 p-8 flex flex-col items-center text-center">
          <div className="w-8 h-8 border-2 border-teal-600 border-t-transparent rounded-full animate-spin mb-4" />
          <p className="text-sm font-medium text-gray-700">Fetching aerial imagery and detecting structures...</p>
          <p className="text-xs text-gray-400 mt-1">This takes 15–30 seconds.</p>
        </div>
      )}

      {/* Step 2: confirmation */}
      {state === 'confirming' && detectResult && (
        <ConfirmationPanel
          detectResult={detectResult}
          inputAddress={inputAddress}
          confirmedCount={confirmedCount}
          onCountChange={setConfirmedCount}
          onConfirm={handleConfirm}
          onBack={() => { setState('idle'); setDetectResult(null); }}
        />
      )}

      {/* Step 3: result */}
      {state === 'complete' && finalResult && (
        <div className="space-y-5">
          <ResultCard result={finalResult} inputAddress={inputAddress} onReset={() => { setState('idle'); setDetectResult(null); setFinalResult(null); setAddress(''); }} />
          <YieldCalculator
            maxFloorAreaM2={finalResult.max_floor_area_m2}
            buildCost={calcBuildCost}
            weeklyRent={calcWeeklyRent}
            onBuildCostChange={setCalcBuildCost}
            onWeeklyRentChange={setCalcWeeklyRent}
          />
        </div>
      )}

      {/* FAQs — always shown below the tool */}
      <GrannyFlatFAQs />
    </div>
  );
}

const SIX_MAPS_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    sixmaps: {
      type: 'raster',
      tiles: ['https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      attribution: '&copy; NSW Government — Six Maps LPI Imagery (CC BY 4.0)',
      maxzoom: 20,
    },
  },
  layers: [{ id: 'sixmaps-tiles', type: 'raster', source: 'sixmaps' }],
};

/** Convert a pixel bbox to a GeoJSON polygon using the tile's geographic bounds. */
function bboxToGeoJSON(
  bbox_pixel: number[],
  tile_bbox: { min_lat: number; max_lat: number; min_lng: number; max_lng: number },
  tile_w: number,
  tile_h: number,
): GeoJSON.Feature {
  const [px0, py0, px1, py1] = bbox_pixel;
  const lngAt = (px: number) => tile_bbox.min_lng + (px / tile_w) * (tile_bbox.max_lng - tile_bbox.min_lng);
  const latAt = (py: number) => tile_bbox.max_lat - (py / tile_h) * (tile_bbox.max_lat - tile_bbox.min_lat);
  return {
    type: 'Feature',
    properties: {},
    geometry: {
      type: 'Polygon',
      coordinates: [[
        [lngAt(px0), latAt(py0)],
        [lngAt(px1), latAt(py0)],
        [lngAt(px1), latAt(py1)],
        [lngAt(px0), latAt(py1)],
        [lngAt(px0), latAt(py0)],
      ]],
    },
  };
}

function StructureMap({
  lat,
  lng,
  tile_bbox,
  tile_width,
  tile_height,
  structures,
  lot_polygon_wgs84,
  licence,
}: {
  lat: number;
  lng: number;
  tile_bbox?: { min_lat: number; max_lat: number; min_lng: number; max_lng: number };
  tile_width?: number;
  tile_height?: number;
  structures: DetectedStructure[];
  lot_polygon_wgs84?: number[][][];
  licence: string;
}) {
  const tw = tile_width ?? 512;
  const th = tile_height ?? 512;

  const mainFeatures: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };
  const otherFeatures: GeoJSON.FeatureCollection = { type: 'FeatureCollection', features: [] };

  if (tile_bbox) {
    for (const s of structures) {
      const feat = bboxToGeoJSON(s.bbox_pixel, tile_bbox, tw, th);
      if (s.is_main_dwelling) mainFeatures.features.push(feat);
      else otherFeatures.features.push(feat);
    }
  }

  const lotFeature: GeoJSON.FeatureCollection | null = lot_polygon_wgs84
    ? {
        type: 'FeatureCollection',
        features: [{
          type: 'Feature',
          properties: {},
          geometry: { type: 'Polygon', coordinates: lot_polygon_wgs84 },
        }],
      }
    : null;

  return (
    <div className="mb-4">
      <div className="rounded-lg overflow-hidden border border-gray-200" style={{ height: 380 }}>
        <Map
          initialViewState={{ latitude: lat, longitude: lng, zoom: 19 }}
          mapStyle={SIX_MAPS_STYLE}
          attributionControl={false}
        >
          <NavigationControl position="top-right" showCompass showZoom />
          {lotFeature && (
            <Source id="lot-boundary" type="geojson" data={lotFeature}>
              <Layer id="lot-boundary-line" type="line" paint={{ 'line-color': '#14b8a6', 'line-width': 2.5 }} />
            </Source>
          )}
          {tile_bbox && (
            <>
              <Source id="struct-main" type="geojson" data={mainFeatures}>
                <Layer id="struct-main-fill" type="fill" paint={{ 'fill-color': '#ef4444', 'fill-opacity': 0.15 }} />
                <Layer id="struct-main-line" type="line" paint={{ 'line-color': '#ef4444', 'line-width': 2 }} />
              </Source>
              <Source id="struct-other" type="geojson" data={otherFeatures}>
                <Layer id="struct-other-fill" type="fill" paint={{ 'fill-color': '#facc15', 'fill-opacity': 0.15 }} />
                <Layer id="struct-other-line" type="line" paint={{ 'line-color': '#facc15', 'line-width': 2 }} />
              </Source>
            </>
          )}
        </Map>
      </div>
      <p className="text-xs text-gray-400 mt-1">{licence}</p>
    </div>
  );
}

function YieldCalculator({
  maxFloorAreaM2,
  buildCost,
  weeklyRent,
  onBuildCostChange,
  onWeeklyRentChange,
}: {
  maxFloorAreaM2: number;
  buildCost: number;
  weeklyRent: number;
  onBuildCostChange: (v: number) => void;
  onWeeklyRentChange: (v: number) => void;
}) {
  const totalCost = buildCost * maxFloorAreaM2;
  const annualRent = weeklyRent * 52;
  const grossYield = (annualRent / totalCost * 100).toFixed(1);
  const payback = (totalCost / annualRent).toFixed(1);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-4">Build &amp; profit calculator</p>
      <div className="grid grid-cols-2 gap-5 mb-5">
        <div>
          <label className="block text-xs text-gray-500 mb-2">Build cost per m²</label>
          <input
            type="range" min={1800} max={4500} step={100}
            value={buildCost}
            onChange={(e) => onBuildCostChange(Number(e.target.value))}
            className="w-full accent-teal-600"
          />
          <span className="text-sm font-medium text-gray-700">${buildCost.toLocaleString()}/m²</span>
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-2">Weekly rent</label>
          <input
            type="range" min={250} max={750} step={25}
            value={weeklyRent}
            onChange={(e) => onWeeklyRentChange(Number(e.target.value))}
            className="w-full accent-teal-600"
          />
          <span className="text-sm font-medium text-gray-700">${weeklyRent}/wk</span>
        </div>
      </div>
      <div className="grid grid-cols-4 gap-3 bg-gray-50 rounded-lg p-4">
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Build cost</p>
          <p className="text-base font-semibold text-gray-900">${(totalCost / 1000).toFixed(0)}k</p>
          <p className="text-xs text-gray-400">{maxFloorAreaM2} m² CDC max</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Annual rent</p>
          <p className="text-base font-semibold text-gray-900">${annualRent.toLocaleString()}</p>
          <p className="text-xs text-gray-400">gross</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Gross yield</p>
          <p className="text-base font-semibold text-teal-700">{grossYield}%</p>
          <p className="text-xs text-gray-400">p.a.</p>
        </div>
        <div>
          <p className="text-xs text-gray-400 mb-0.5">Payback</p>
          <p className="text-base font-semibold text-gray-900">{payback} yrs</p>
          <p className="text-xs text-gray-400">undiscounted</p>
        </div>
      </div>
      <p className="text-xs text-gray-400 mt-3">
        Illustrative only. Excludes DA/CDC fees, finance, vacancy, and maintenance. Verify rent against NSW Fair Trading bond data.
      </p>
    </div>
  );
}

const GRANNY_FLAT_FAQS = [
  {
    q: 'What is the minimum lot size for a granny flat in NSW?',
    a: 'Under SEPP Housing 2021 (cl 53), a secondary dwelling approved as complying development requires a minimum site area of 450 m². A DA pathway may be available on smaller lots at council\'s discretion, subject to zone permissibility.',
  },
  {
    q: 'What is the maximum size of a granny flat under SEPP Housing 2021?',
    a: 'The maximum floor area for a secondary dwelling approved as complying development is 60 m² (SEPP Housing 2021 cl 4.18). A DA pathway allows larger floor areas subject to council DCP controls — typically up to 20–25% of the principal dwelling\'s floor area.',
  },
  {
    q: 'Do I need a DA or CDC to build a granny flat?',
    a: 'If the lot meets all SEPP Housing 2021 requirements (area, zoning, no heritage/flood/biodiversity exclusions), you can lodge a CDC — which is cheaper and faster than a DA. A CDC is approved by a private certifier in about 20 days. A DA goes to council and typically takes 60–90 days.',
  },
  {
    q: 'Can a granny flat be rented to anyone?',
    a: 'Yes. As of 2023, NSW removed the requirement that secondary dwellings be occupied by a family member. You can rent to any tenant at market rent.',
  },
  {
    q: 'What setbacks apply to a granny flat under the CDC pathway?',
    a: 'Under SEPP Housing 2021 Schedule 3 Subdivision 4: rear setback minimum 3 m, side setbacks 0.9 m for the first 8 m height and 1.5 m above that, minimum 3 m separation from the principal dwelling. Your council\'s DCP may impose stricter controls on the DA pathway.',
  },
  {
    q: 'Why does this tool use aerial imagery to detect structures?',
    a: 'SEPP Housing 2021 requires at most one secondary dwelling per lot. By detecting existing roofed structures on 10 cm NSW SIX Maps aerial imagery, this tool gives a more accurate buildability estimate than relying on lot area alone — existing garages, sheds, and ancillary structures all affect the available building envelope.',
  },
  {
    q: 'What does the yield calculator assume?',
    a: 'The calculator uses the actual CDC maximum floor area for this property (up to 60 m²), your selected build cost per m², and your selected weekly rent. Gross yield is annual rent divided by build cost. It excludes DA/CDC fees, finance costs, vacancy, and ongoing maintenance. Net yields are typically 1–2% lower.',
  },
];

function GrannyFlatFAQs() {
  return (
    <div className="mt-12 space-y-5 pb-12">
      <h2 className="text-xl font-semibold text-gray-900">Granny flats in NSW — common questions</h2>
      {GRANNY_FLAT_FAQS.map((faq, i) => (
        <div key={i} className="border-b border-gray-100 pb-4">
          <p className="font-medium text-gray-900 text-sm">{faq.q}</p>
          <p className="text-sm text-gray-500 mt-1">{faq.a}</p>
        </div>
      ))}

      {/* Legislative basis — trust references matching GrannyFlatTool */}
      <div className="text-xs text-gray-400 pt-4 space-y-1.5">
        <p className="font-medium text-gray-500">Legislative basis</p>
        <p><span className="text-gray-500">Lot area</span> — SEPP (Housing) 2021 cl 53(2)(a): detached secondary dwelling minimum site area 450 m² [complying development]; cl 52 [development consent].</p>
        <p><span className="text-gray-500">Zone</span> — SEPP (Housing) 2021 cl 50, read with definition of &ldquo;residential zone&rdquo; in cl 49: R1, R2, R3, R4, R5/RU5 where dwelling houses are permissible under the applicable LEP.</p>
        <p><span className="text-gray-500">Heritage</span> — CDC pathway: SEPP (Housing) 2021 cl 54(3)(c) excludes heritage items and draft heritage items; DA pathway: applicable LEP cl 5.10 (Standard Instrument). Heritage Map sourced from NSW Planning Portal.</p>
        <p><span className="text-gray-500">Flood control lot</span> — SEPP (Housing) 2021 cl 58: complying development must not be carried out on flood storage areas, floodways, flow paths, high hazard areas, or high risk areas. Spatial data: 12 LGAs covered — shown as unknown outside coverage.</p>
        <p><span className="text-gray-500">Biodiversity</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes land mapped on the NSW Biodiversity Values Map (Biodiversity Conservation Act 2016). Spatial data: NSW DCCEEW.</p>
        <p><span className="text-gray-500">Acid sulfate soils</span> — SEPP (Exempt and Complying Development Codes) 2008 cl 1.19(1) excludes Class 1 and Class 2 acid sulfate soils; DA pathway: applicable LEP cl 7.1 (Standard Instrument).</p>
        <p className="pt-1 border-t border-gray-100 mt-2">DCP setback, height, floor space ratio, and landscaping controls not assessed here. This tool is indicative only — verify with a qualified town planner before lodging a DA or CDC.</p>
      </div>
    </div>
  );
}

function ConfirmationPanel({
  detectResult,
  inputAddress,
  confirmedCount,
  onCountChange,
  onConfirm,
  onBack,
}: {
  detectResult: DetectResult;
  inputAddress: string;
  confirmedCount: number;
  onCountChange: (n: number) => void;
  onConfirm: (e: React.FormEvent) => void;
  onBack: () => void;
}) {
  const canonical = detectResult.address;
  const showCanonical = canonical && canonical.toLowerCase() !== inputAddress.toLowerCase();
  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <h2 className="font-semibold text-gray-900">{inputAddress || canonical}</h2>
        {showCanonical && (
          <p className="text-xs text-gray-400 mt-0.5">Matched to: {canonical}</p>
        )}
        {detectResult.lot_area_m2 != null && (
          <p className="text-sm text-gray-500 mt-0.5">
            Lot area: {detectResult.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m²
          </p>
        )}
        {detectResult.lot_area_m2 != null && detectResult.lot_area_m2 > 2000 && (
          <div className="mt-3 bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <span className="font-medium">Large lot area</span> — {detectResult.lot_area_m2.toLocaleString('en-AU', { maximumFractionDigits: 0 })} m² is unusually large for a single dwelling house. If this is a strata parent lot or a multi-dwelling development site, SEPP Housing 2021 secondary dwelling provisions do not apply.
          </div>
        )}
        {!detectResult.sepp_eligible && detectResult.sepp_ineligible_reason && (
          <div className="mt-3 bg-red-50 border border-red-200 rounded-lg p-3 text-xs text-red-700">
            {detectResult.sepp_ineligible_reason}
          </div>
        )}
      </div>

      <div className="p-6">
        <StructureMap
          lat={detectResult.lat}
          lng={detectResult.lng}
          tile_bbox={detectResult.tile_bbox}
          tile_width={detectResult.tile_width}
          tile_height={detectResult.tile_height}
          structures={detectResult.detected_structures}
          lot_polygon_wgs84={detectResult.lot_polygon_wgs84}
          licence={detectResult.tile_licence}
        />

        {!detectResult.samgeo_validated ? (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800 mb-4">
            Aerial detection is in pre-validation mode. Please verify the structure count manually using the SIX Maps viewer before proceeding.
          </div>
        ) : detectResult.detected_structures.length > 0 ? (
          <div className="mb-4">
            {(() => {
              const valid = detectResult.detected_structures.filter(
                (s) => s.area_m2 == null || s.area_m2 < (detectResult.lot_area_m2 ?? Infinity) * 1.5
              );
              return (
                <>
                  <p className="text-sm font-medium text-gray-700 mb-2">
                    {valid.length} structure{valid.length !== 1 ? 's' : ''} detected on lot
                  </p>
                  <div className="space-y-1">
                    {valid.map((s) => (
                      <div key={s.index} className="flex items-center gap-2 text-xs text-gray-600">
                        <span className="w-2 h-2 rounded-full bg-teal-400 shrink-0" />
                        {s.is_main_dwelling ? 'Main dwelling' : `Structure ${s.index + 1}`}
                        {s.area_m2 != null && ` — ~${s.area_m2} m²`}
                        <span className="text-gray-400 capitalize">({s.matched_prompt})</span>
                      </div>
                    ))}
                  </div>
                </>
              );
            })()}
          </div>
        ) : (
          <p className="text-sm text-gray-500 mb-4">No structures detected — enter count manually.</p>
        )}

        <form onSubmit={onConfirm} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Confirmed number of structures on lot
            </label>
            <input
              type="number"
              min={1}
              max={10}
              value={confirmedCount}
              onChange={(e) => onCountChange(parseInt(e.target.value, 10) || 1)}
              className="w-24 px-3 py-2 rounded-lg border border-gray-300 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
            />
            <p className="text-xs text-gray-400 mt-1">
              Count all roofed structures: main dwelling, garage, shed, any secondary dwelling.
            </p>
          </div>

          <div className="flex gap-3">
            <button
              type="submit"
              className="px-5 py-2.5 bg-teal-600 text-white text-sm font-medium rounded-lg hover:bg-teal-700 transition-colors"
            >
              Calculate yield
            </button>
            <button
              type="button"
              onClick={onBack}
              className="px-5 py-2.5 bg-white text-gray-600 text-sm font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition-colors"
            >
              Back
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ResultCard({ result, inputAddress, onReset }: { result: ConfirmResult; inputAddress: string; onReset: () => void }) {
  const weeklyRent = result.estimated_weekly_rent_aud;
  const annualRent = weeklyRent ? weeklyRent * 52 : null;
  const displayAddr = inputAddress || result.address;

  return (
    <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
      <div className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-semibold text-gray-900">{displayAddr}</h2>
            <p className="text-xs text-gray-400 mt-0.5">
              {CONFIDENCE_LABEL[result.confidence] ?? result.confidence}
            </p>
            {result.confidence_reason && (
              <p className="text-xs text-gray-500 mt-1 max-w-sm">{result.confidence_reason}</p>
            )}
          </div>
          <span
            className={`shrink-0 text-xs font-medium px-2 py-1 rounded-full ${
              result.granny_flat_buildable
                ? 'bg-green-100 text-green-800'
                : 'bg-red-100 text-red-800'
            }`}
          >
            {result.granny_flat_buildable ? 'Eligible under SEPP' : 'Not eligible'}
          </span>
        </div>
      </div>

      {result.granny_flat_buildable && (
        <div className="grid grid-cols-3 divide-x divide-gray-100">
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Max floor area</p>
            <p className="text-lg font-semibold text-gray-900">{result.max_floor_area_m2} m²</p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Est. weekly rent</p>
            <p className="text-lg font-semibold text-gray-900">
              {weeklyRent ? `$${weeklyRent.toLocaleString('en-AU', { maximumFractionDigits: 0 })}/wk` : 'N/A'}
            </p>
          </div>
          <div className="p-5">
            <p className="text-xs text-gray-400 mb-1">Yield on build cost</p>
            <p className="text-lg font-semibold text-gray-900">
              {result.rental_yield_annual_pct ? `${result.rental_yield_annual_pct}%` : 'N/A'}
            </p>
            {result.assumed_build_cost_aud && (
              <p className="text-xs text-gray-400 mt-0.5">
                On ${result.assumed_build_cost_aud.toLocaleString('en-AU')} build cost
              </p>
            )}
          </div>
        </div>
      )}

      {result.warnings.length > 0 && (
        <div className="px-6 py-4 bg-amber-50 space-y-1">
          {result.warnings.map((w, i) => (
            <p key={i} className="text-xs text-amber-800">{w}</p>
          ))}
        </div>
      )}

      <div className="px-6 py-4 flex items-center justify-between">
        <p className="text-xs text-gray-400">
          Data: {result.data_sources.join(' · ')}
        </p>
        <button
          onClick={onReset}
          className="text-xs text-teal-600 hover:text-teal-700 underline"
        >
          New address
        </button>
      </div>
    </div>
  );
}
