import type { Metadata } from 'next'
import { PreDAHistoryTool } from '@/components/tools/PreDAHistoryTool'
import { ProductLanding } from '@/components/reports/ProductLanding'

export const metadata: Metadata = {
  title: 'Pre-DA Site History Report — canibuildit.com.au',
  description: 'What happened on this land before you got here? Satellite change detection, DA history, heritage overlay, and flood/fire annotations for any NSW address.',
  openGraph: {
    title: 'Pre-DA Site History — Satellite change detection for any NSW address',
    description: 'Eight years of satellite imagery analysed for physical changes, cross-referenced with DA records, heritage overlays, and natural disaster events. Free to run.',
    url: 'https://canibuildit.com.au/reports/pre-da-history',
    siteName: 'canibuildit.com.au',
    type: 'website',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Pre-DA Site History — canibuildit.com.au',
    description: 'Satellite change detection + DA history for any NSW address. Free, instant.',
  },
}

export default function PreDAHistoryPage() {
  return (
    <div className="max-w-2xl">
      <ProductLanding
        title="Pre-DA Site History Report"
        subtitle="What happened on this land before you got here?"
        hook="Before you lodge a DA, you need to know what council already knows about the site. This report cross-references eight years of satellite imagery with DA records, heritage overlays, and natural disaster events to surface anything that could affect your application — unapproved works, vegetation clearing, flood history, or heritage constraints."
        checks={[
          {
            title: 'Satellite change detection (2017–2025)',
            description: 'European Space Agency satellite embeddings compared year-on-year to detect physical changes on the lot — new structures, demolitions, vegetation removal, or surface hardening.',
          },
          {
            title: 'Vegetation and built-up indices',
            description: 'Spectral analysis from European Space Agency optical imagery measures vegetation density (NDVI) and built-up surface area (NDBI) each year. Distinguishes construction from natural events like drought.',
          },
          {
            title: 'DA and CDC event history',
            description: 'Every development application and complying development certificate lodged with council for this address, fetched from the NSW ePlanning Portal. Shows what was approved, refused, or withdrawn.',
          },
          {
            title: 'Construction and occupation certificates',
            description: 'Post-consent certificates from the NSW ePlanning Portal — confirms whether approved works were actually completed and signed off by council.',
          },
          {
            title: 'Heritage overlay',
            description: 'Point-in-polygon check against NSW Government heritage conservation area boundaries. Heritage listings require a Statement of Heritage Impact with any DA.',
          },
          {
            title: 'Neighbourhood normalisation',
            description: 'Compares your lot against the surrounding neighbourhood to filter out area-wide events — drought, bushfire haze, or seasonal variation — that affect satellite readings but are not site-specific changes.',
          },
          {
            title: 'Flood and bushfire annotations',
            description: 'Cross-references detected changes against known flood and bushfire events. A 2019 vegetation drop in the Blue Mountains is bushfire damage, not clearing — the report distinguishes the two.',
          },
          {
            title: 'Annotated year-by-year timeline',
            description: 'Each year classified as stable, minor, moderate, or major change — with DA cross-references, spectral disambiguation, and natural event annotations. The full picture in one table.',
          },
        ]}
        comparison={[
          { feature: 'Year-by-year change level (stable / minor / moderate / major)', free: true, paid: true },
          { feature: 'Heritage overlay status', free: true, paid: true },
          { feature: 'DA event count and application numbers', free: true, paid: true },
          { feature: 'Summary statistics (years analysed, notable years)', free: true, paid: true },
          { feature: 'Full annotated timeline with explanations', free: true, paid: true },
          { feature: 'NDVI/NDBI spectral analysis per year', free: false, paid: true },
          { feature: 'DA event detail (type, status, dates)', free: false, paid: true },
          { feature: 'Flood and bushfire event cross-references', free: false, paid: true },
          { feature: 'Methodology and data quality notes', free: false, paid: true },
          { feature: 'Downloadable PDF report', free: false, paid: true },
        ]}
        paidLabel="full report — $49"
        methodology="Your address is resolved to precise coordinates via the NSW Planning Portal, then queried against eight years of European Space Agency satellite imagery. Each year's image embedding is compared to the previous year and to the surrounding neighbourhood — isolating lot-specific changes from area-wide events. Vegetation and built-up spectral indices provide a second independent signal to distinguish construction from natural change. DA and certificate records from the NSW ePlanning Portal are cross-referenced by year. Heritage status is checked against NSW Government spatial boundaries."
        coverage="Satellite change detection covers all of NSW from 2017 to present. DA event history covers all councils that submit to the NSW ePlanning Portal. Heritage overlays cover areas where councils have published spatial boundaries. Some inner Sydney suburbs have sparse satellite coverage before 2024."
      />
      <PreDAHistoryTool />
    </div>
  )
}
