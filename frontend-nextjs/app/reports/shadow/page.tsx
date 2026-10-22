import { notFound } from 'next/navigation'

// Shadow tool turned off 2026-10-22 by the owner: it sold an "ADG solar access" verdict
// for neighbouring houses, but ADG 4A-1 (2 hours of sun) applies to a new apartment
// building's own apartments and 3F is visual privacy, so the verdict was not a real standard.
export default function ShadowPage() {
  notFound()
}
