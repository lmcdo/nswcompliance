import { notFound, redirect } from 'next/navigation'

// Shadow tool turned off 2026-10-22 by the owner: it sold an "ADG solar access" verdict
// for neighbouring houses, but ADG 4A-1 (2 hours of sun) applies to a new apartment
// building's own apartments and 3F is visual privacy, so the verdict was not a real standard.
//
// One exception: a buyer who opened checkout before the switch-off and paid after it is sent
// here by Stripe (?payment=success&report_id=...). Forward them to their own report page,
// which stays live for paid orders; everyone else gets 404.
export default function ShadowPage({ searchParams }: { searchParams?: Record<string, string | string[] | undefined> }) {
  const reportId = searchParams?.report_id
  if (searchParams?.payment === 'success' && typeof reportId === 'string' && /^[A-Za-z0-9_-]{1,80}$/.test(reportId)) {
    redirect(`/reports/shadow/${reportId}`)
  }
  notFound()
}
