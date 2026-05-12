/**
 * POST /api/reports/bushfire/generate
 *
 * Generates a free one-page bushfire pre-screen PDF.
 * Call path: { report_id } — fetches from property_reports by UUID.
 *
 * Returns application/pdf stream.
 */

import { NextRequest, NextResponse } from 'next/server'
import { renderToBuffer } from '@react-pdf/renderer'
import React from 'react'
import { BushfireReportDocument, type BushfirePdfData } from '@/lib/pdf/bushfire-report'
import { getLogoBase64 } from '@/lib/pdf/logo'
import { fetchBushfireMapTile, fetchNeighbourBfplContext } from '@/lib/pdf/bushfire-map-tile'
import { createClient } from '@supabase/supabase-js'

const getSupabase = () => createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_ROLE_KEY!,
)

export const dynamic = 'force-dynamic'
export const maxDuration = 30

export async function POST(req: NextRequest) {
  let body: { report_id?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body' }, { status: 400 })
  }

  if (!body.report_id) {
    return NextResponse.json({ error: 'report_id is required' }, { status: 400 })
  }

  const { data: row, error } = await getSupabase()
    .from('property_reports')
    .select('address, lat, lng, run_date, outputs, inputs, confidence, data_sources')
    .eq('id', body.report_id.trim())
    .eq('product', 'bushfire')
    .single()

  if (error || !row) {
    return NextResponse.json({ error: 'Report not found' }, { status: 404 })
  }

  const outputs = (row.outputs || {}) as Record<string, unknown>
  const compliance = (outputs.compliance || {}) as Record<string, unknown>
  const inputs = (row.inputs || {}) as Record<string, unknown>
  const lotGeometry = (inputs.lot_geometry as { rings: [number, number][][] } | null) ?? null

  const [mapTile, logo_b64, neighbourContext] = await Promise.all([
    (row.lat && row.lng)
      ? fetchBushfireMapTile({ lat: row.lat, lng: row.lng, lotGeometry, width: 600, height: 400 })
      : Promise.resolve(null),
    Promise.resolve(getLogoBase64()),
    (row.lat && row.lng)
      ? fetchNeighbourBfplContext(row.lat, row.lng)
      : Promise.resolve(null),
  ])

  const data: BushfirePdfData = {
    address: row.address,
    run_date: row.run_date,
    lat: row.lat,
    lng: row.lng,
    fire_signal: (outputs.fire_signal as string) || 'unavailable',
    is_bushfire_prone: outputs.is_bushfire_prone as boolean | null,
    designation_category: (outputs.designation_category as string) || null,
    designation_guideline: (outputs.designation_guideline as string) || null,
    estimated_bal_band: (outputs.estimated_bal_band as string) || null,
    bal_assessment_likely_required: outputs.bal_assessment_likely_required as boolean | null,
    rfs_referral_required: (compliance.rfs_referral_required as boolean) ?? null,
    cdc_pathway_available: (compliance.cdc_pathway_available as boolean) ?? null,
    clearing_10_50_entitled: (compliance.clearing_10_50_entitled as boolean) ?? null,
    clearing_10_50_exceptions: (compliance.clearing_10_50_exceptions as string) || null,
    estimated_consultant_costs: (compliance.estimated_consultant_costs as string) || null,
    data_currency: (outputs.data_currency as string) || 'unknown',
    confidence: row.confidence || 'medium',
    data_sources: row.data_sources || ['NSW Rural Fire Service Bush Fire Prone Land Map'],
    logo_b64,
    aerial_b64: mapTile?.aerial_b64 ?? null,
    bfpl_b64: mapTile?.bfpl_b64 ?? null,
    lot_svg: mapTile?.lot_svg ?? null,
    neighbour_context: neighbourContext?.surrounding_description ?? null,
  }

  let pdfBuffer: Buffer
  try {
    pdfBuffer = await renderToBuffer(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      React.createElement(BushfireReportDocument, { data }) as any
    )
  } catch (err) {
    console.error('[bushfire/generate] PDF render error:', err)
    return NextResponse.json({ error: 'PDF generation failed' }, { status: 500 })
  }

  const slug = row.address.slice(0, 30).replace(/[^a-z0-9]/gi, '-').toLowerCase()
  const filename = `bushfire-prescreen-${slug}.pdf`

  return new NextResponse(new Uint8Array(pdfBuffer), {
    status: 200,
    headers: {
      'Content-Type': 'application/pdf',
      'Content-Disposition': `attachment; filename="${filename}"`,
      'Content-Length': String(pdfBuffer.length),
    },
  })
}
