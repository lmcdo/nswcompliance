'use client';

import { useState } from 'react';

interface Props {
  label?: string;
  apiPath: string;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data?: Record<string, any>;
  /** HMAC token issued by the satellite route — required for server-side verification. */
  reportToken?: string;
  /** When set, sends { report_id } at top level (Path A — paid report from DB). */
  reportId?: string;
}

/**
 * Generic "Download PDF" button for satellite tool result pages.
 * POSTs { data, report_token } to apiPath and triggers a browser file download.
 * The report_token is an HMAC signed by the satellite route and verified server-side
 * before PDF rendering — prevents generating PDFs from arbitrary injected data.
 */
export function DownloadPdfButton({
  label = 'Download PDF report',
  apiPath,
  data,
  reportToken,
  reportId,
}: Props) {
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState('');

  const handleClick = async () => {
    setDownloading(true);
    setError('');
    try {
      const res = await fetch(apiPath, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(
          reportId
            ? { report_id: reportId }
            : { data, report_token: reportToken }
        ),
      });
      if (!res.ok) {
        const json = await res.json().catch(() => ({}));
        throw new Error(json.error || `PDF generation failed (${res.status})`);
      }
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      // Use filename from Content-Disposition if present
      const cd = res.headers.get('Content-Disposition') ?? '';
      const match = cd.match(/filename="([^"]+)"/);
      a.download = match?.[1] ?? 'report.pdf';
      a.href = url;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="mt-3">
      <button
        type="button"
        onClick={handleClick}
        disabled={downloading}
        className="w-full py-2.5 px-4 bg-white border border-gray-200 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {downloading ? (
          <>
            <span className="w-4 h-4 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
            Generating PDF…
          </>
        ) : (
          <>
            <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
            </svg>
            {label}
          </>
        )}
      </button>
      {error && (
        <p className="text-xs text-red-600 mt-1.5">{error}</p>
      )}
    </div>
  );
}
