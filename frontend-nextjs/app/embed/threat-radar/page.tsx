import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'
import { getWidgetPartner } from '@/lib/widget-partners'
import { PartnerAttribution } from '@/components/embed/PartnerAttribution'

export default function EmbedThreatRadarPage({
  searchParams,
}: {
  searchParams: { ref?: string | string[] }
}) {
  // Branding resolves ONLY by ?ref=<slug> against the in-repo registry; an
  // unknown or missing ref renders the unbranded check (PR #790 posture).
  const partner = getWidgetPartner(searchParams.ref)
  return (
    <div className="px-4 py-5">
      <PartnerAttribution partnerName={partner?.name ?? null} checkLabel="development activity check" />
      <ThreatRadarTool embedRef={partner?.slug} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://plotdetect.com.au/threat-radar" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
