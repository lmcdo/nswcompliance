import { ShadowTool } from '@/components/tools/ShadowTool'

export default function EmbedShadowPage({
  searchParams,
}: {
  searchParams: { ref?: string }
}) {
  return (
    <div className="px-4 py-5">
      <ShadowTool embedRef={searchParams.ref} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://verify.plotdetect.com.au/shadow-detector" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
