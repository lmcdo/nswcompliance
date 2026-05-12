/**
 * Generates a composite map image for bushfire PDF reports:
 * 1. NSW SIX Maps aerial base layer
 * 2. RFS BFPL overlay (semi-transparent)
 * 3. Lot boundary outline (rendered via SVG overlay on the composite)
 *
 * Returns a base64-encoded PNG, or null on failure.
 *
 * Both NSW SIX Maps and RFS BFPL expose ArcGIS MapServer /export endpoints
 * that accept the same bbox/size parameters and return PNG images.
 */

const AERIAL_URL =
  'https://maps.six.nsw.gov.au/arcgis/rest/services/sixmaps/LPI_Imagery_Best/MapServer/export'

const BFPL_URL =
  'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/export'

interface LotRings {
  // EPSG:3857 (Web Mercator) ring coordinates from NSW Planning Portal
  rings: [number, number][][]
}

interface BushfireMapOptions {
  lat: number
  lng: number
  lotGeometry?: LotRings | null
  width?: number
  height?: number
}

/**
 * Convert EPSG:3857 (Web Mercator metres) to EPSG:4326 (WGS84 degrees).
 */
function mercatorToWgs84(x: number, y: number): [number, number] {
  const R = 20037508.342789244
  const lng = (x / R) * 180.0
  const lat = (Math.atan(Math.exp((y * Math.PI) / R)) * 2 - Math.PI / 2) * (180.0 / Math.PI)
  return [lng, lat]
}

/**
 * Compute bbox from lot rings (EPSG:3857) → WGS84 with padding.
 */
function bboxFromRings(rings: [number, number][][], paddingFraction = 0.4): {
  minX: number; minY: number; maxX: number; maxY: number
} {
  const coords = rings[0].map(([x, y]) => mercatorToWgs84(x, y))
  const lngs = coords.map(c => c[0])
  const lats = coords.map(c => c[1])
  const rawMinX = Math.min(...lngs)
  const rawMaxX = Math.max(...lngs)
  const rawMinY = Math.min(...lats)
  const rawMaxY = Math.max(...lats)
  const padX = (rawMaxX - rawMinX) * paddingFraction
  const padY = (rawMaxY - rawMinY) * paddingFraction
  return {
    minX: rawMinX - padX,
    minY: rawMinY - padY,
    maxX: rawMaxX + padX,
    maxY: rawMaxY + padY,
  }
}

/**
 * Compute a fixed bbox centred on lat/lng for when no lot geometry is available.
 */
function bboxFromPoint(lat: number, lng: number): {
  minX: number; minY: number; maxX: number; maxY: number
} {
  const d = 0.001 // ~110m in each direction
  return { minX: lng - d, minY: lat - d, maxX: lng + d, maxY: lat + d }
}

async function fetchMapExport(
  url: string,
  bbox: { minX: number; minY: number; maxX: number; maxY: number },
  width: number,
  height: number,
  extraParams?: Record<string, string>,
): Promise<Buffer | null> {
  const params = new URLSearchParams({
    bbox: `${bbox.minX.toFixed(6)},${bbox.minY.toFixed(6)},${bbox.maxX.toFixed(6)},${bbox.maxY.toFixed(6)}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: `${width},${height}`,
    format: 'png',
    f: 'image',
    ...extraParams,
  })

  try {
    const res = await fetch(`${url}?${params}`, { signal: AbortSignal.timeout(15_000) })
    if (!res.ok) return null
    const ct = res.headers.get('content-type') ?? ''
    if (!ct.includes('image')) return null
    return Buffer.from(await res.arrayBuffer())
  } catch {
    return null
  }
}

/**
 * Generate an SVG overlay with lot boundary polygon for compositing.
 * Coordinates are projected into pixel space relative to the bbox.
 */
function lotBoundarySvg(
  rings: [number, number][][],
  bbox: { minX: number; minY: number; maxX: number; maxY: number },
  width: number,
  height: number,
): string {
  const coords = rings[0].map(([x, y]) => {
    const [lng, lat] = mercatorToWgs84(x, y)
    const px = ((lng - bbox.minX) / (bbox.maxX - bbox.minX)) * width
    const py = ((bbox.maxY - lat) / (bbox.maxY - bbox.minY)) * height
    return `${px.toFixed(1)},${py.toFixed(1)}`
  })

  return `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}">
    <polygon points="${coords.join(' ')}" fill="none" stroke="#0d9488" stroke-width="3" stroke-dasharray="8,4" />
  </svg>`
}

/**
 * Query RFS BFPL layer for surrounding area to provide neighbour context.
 * Returns a summary of BFPL categories found in a ~200m buffer around the point.
 */
export async function fetchNeighbourBfplContext(lat: number, lng: number): Promise<{
  categories_nearby: string[]
  surrounding_description: string
} | null> {
  const BFPL_QUERY_URL =
    'https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Fire/BFPL/MapServer/0/query'

  // ~200m buffer in degrees
  const buffer = 0.002
  const envelope = `${lng - buffer},${lat - buffer},${lng + buffer},${lat + buffer}`

  const params = new URLSearchParams({
    geometry: envelope,
    geometryType: 'esriGeometryEnvelope',
    inSR: '4326',
    spatialRel: 'esriSpatialRelIntersects',
    outFields: 'Category',
    returnGeometry: 'false',
    f: 'json',
  })

  try {
    const res = await fetch(`${BFPL_QUERY_URL}?${params}`, { signal: AbortSignal.timeout(10_000) })
    if (!res.ok) return null
    const data = await res.json()
    if (!data.features?.length) {
      return { categories_nearby: [], surrounding_description: 'No bushfire prone land mapped within ~200m' }
    }

    const categories = [...new Set(
      data.features
        .map((f: { attributes?: { Category?: string } }) => f.attributes?.Category)
        .filter(Boolean)
    )] as string[]

    const catLabels: Record<string, string> = {
      '1': 'Category 1 (highest)',
      '2': 'Category 2',
      '3': 'Category 3',
      'Vegetation Buffer': 'Vegetation Buffer',
    }

    const labels = categories.map(c => catLabels[c] || `Category ${c}`)
    const description = categories.length === 0
      ? 'No bushfire prone land mapped within ~200m'
      : `Surrounding area contains: ${labels.join(', ')}`

    return { categories_nearby: categories, surrounding_description: description }
  } catch {
    return null
  }
}

export async function fetchBushfireMapTile(options: BushfireMapOptions): Promise<{
  aerial_b64: string | null
  bfpl_b64: string | null
  lot_svg: string | null
  bbox: { minX: number; minY: number; maxX: number; maxY: number }
} | null> {
  const { lat, lng, lotGeometry, width = 600, height = 400 } = options

  if (!isFinite(lat) || !isFinite(lng)) return null

  const bbox = lotGeometry?.rings?.[0]?.length
    ? bboxFromRings(lotGeometry.rings, 0.4)
    : bboxFromPoint(lat, lng)

  // Fetch aerial and BFPL in parallel
  const [aerialBuf, bfplBuf] = await Promise.all([
    fetchMapExport(AERIAL_URL, bbox, width, height),
    fetchMapExport(BFPL_URL, bbox, width, height, {
      transparent: 'true',
      layers: 'show:0',
    }),
  ])

  const lot_svg = lotGeometry?.rings?.[0]?.length
    ? lotBoundarySvg(lotGeometry.rings, bbox, width, height)
    : null

  return {
    aerial_b64: aerialBuf ? aerialBuf.toString('base64') : null,
    bfpl_b64: bfplBuf ? bfplBuf.toString('base64') : null,
    lot_svg,
    bbox,
  }
}
