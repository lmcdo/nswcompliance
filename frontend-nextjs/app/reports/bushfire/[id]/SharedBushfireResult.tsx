'use client'

import { useState } from 'react'
import { BushfireResultCard } from '@/components/tools/BushfireResultCard'
import { ToolCrossSell } from '@/components/reports/ToolCrossSell'

interface Props {
  result: {
    address: string
    lat: number
    lng: number
    run_date: string
    outputs: Record<string, unknown>
    confidence: string
    data_sources: string[]
    report_id: string
  }
  reportId: string
}

export function SharedBushfireResult({ result, reportId }: Props) {
  const [copied, setCopied] = useState(false)
  const [downloading, setDownloading] = useState(false)

  const shareUrl = typeof window !== 'undefined'
    ? `${window.location.origin}/reports/bushfire/${reportId}`
    : `/reports/bushfire/${reportId}`

  const handleCopyLink = async () => {
    await navigator.clipboard.writeText(shareUrl)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleDownloadPdf = async () => {
    setDownloading(true)
    try {
      const res = await fetch('/api/reports/bushfire/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ report_id: reportId }),
      })
      if (!res.ok) throw new Error('PDF generation failed')
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `bushfire-prescreen-${result.address.replace(/[^a-zA-Z0-9]/g, '-').slice(0, 50)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error(err)
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div>
      {/* Action buttons */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={handleCopyLink}
          className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-700 hover:bg-gray-50 transition-colors"
        >
          {copied ? 'Copied!' : 'Copy link'}
        </button>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-teal-600 text-white hover:bg-teal-700 disabled:opacity-50 transition-colors"
        >
          {downloading ? 'Generating...' : 'Download PDF'}
        </button>
      </div>

      <BushfireResultCard result={result as any} />
      <ToolCrossSell currentTool="bushfire" address={result.address} />
    </div>
  )
}
