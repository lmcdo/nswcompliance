import { notFound } from 'next/navigation'
import type { Metadata } from 'next'

// Shadow tool turned off 2026-10-22 by the owner: it sold an "ADG solar access" verdict
// for neighbouring houses, but ADG 4A-1 (2 hours of sun) applies to a new apartment
// building's own apartments and 3F is visual privacy, so the verdict was not a real standard.
export const dynamicParams = false

export function generateStaticParams() {
  return []
}

export function generateMetadata(): Metadata {
  return { robots: { index: false } }
}

export default function ShadowLgaPage() {
  notFound()
}
