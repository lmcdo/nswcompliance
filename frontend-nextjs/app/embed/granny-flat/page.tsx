import { GrannyFlatTool } from '@/components/tools/GrannyFlatTool'

export default function EmbedGrannyFlatPage({
  searchParams,
}: {
  searchParams: { ref?: string }
}) {
  return (
    <div className="px-4 py-5">
      <GrannyFlatTool embedRef={searchParams.ref} />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://verify.plotdetect.com.au/granny-flat" target="_blank" rel="noopener">
          Powered by PlotDetect
        </a>
      </p>
    </div>
  )
}
