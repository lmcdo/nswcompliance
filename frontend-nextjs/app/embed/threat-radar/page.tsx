import { ThreatRadarTool } from '@/components/tools/ThreatRadarTool'

export default function EmbedThreatRadarPage({
  searchParams,
}: {
  searchParams: { ref?: string }
}) {
  return (
    <div className="px-4 py-5">
      <ThreatRadarTool embedRef={searchParams.ref} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://verify.plotdetect.com.au/threat-radar" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
