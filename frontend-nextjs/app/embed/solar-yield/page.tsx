import { SolarYieldTool } from '@/components/tools/SolarYieldTool'

export default function EmbedSolarYieldPage({
  searchParams,
}: {
  searchParams: { ref?: string }
}) {
  return (
    <div className="px-4 py-5">
      <SolarYieldTool embedRef={searchParams.ref} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://verify.plotdetect.com.au/solar-potential" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
