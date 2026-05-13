"use client"

import { useState, useEffect } from "react"

export function LandingVisibility({ children }: { children: React.ReactNode }) {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const handler = () => setHidden(true)
    window.addEventListener("landing-search", handler)
    return () => window.removeEventListener("landing-search", handler)
  }, [])

  if (hidden) return null
  return <>{children}</>
}
