import { ShadowTool } from '@/components/tools/ShadowTool'
import { getWidgetPartner } from '@/lib/widget-partners'
import { PartnerAttribution } from '@/components/embed/PartnerAttribution'

export default function EmbedShadowPage({
  searchParams,
}: {
  searchParams: { ref?: string | string[] }
}) {
  // Branding resolves ONLY by ?ref=<slug> against the in-repo registry; an
  // unknown or missing ref renders the unbranded check (PR #790 posture).
  const partner = getWidgetPartner(searchParams.ref)
  return (
    <div className="px-4 py-5">
      <PartnerAttribution partnerName={partner?.name ?? null} checkLabel="overshadowing check" />
      <ShadowTool embedRef={partner?.slug} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://plotdetect.com.au/shadow-detector" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
