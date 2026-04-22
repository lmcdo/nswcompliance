import { ShadowTool } from '@/components/tools/ShadowTool'

export default function EmbedShadowPage() {
  return (
    <div className="px-4 py-5">
      <ShadowTool />
      <p className="mt-4 text-center text-xs text-gray-400">
        <a href="https://canibuildit.com.au/shadow-detector" target="_blank" rel="noopener">
          Powered by canibuildit.com.au
        </a>
      </p>
    </div>
  )
}
