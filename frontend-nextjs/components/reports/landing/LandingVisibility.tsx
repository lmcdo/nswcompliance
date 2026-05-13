"use client"

import { useState, useEffect } from "react"

export function LandingVisibility({ children }: { children: React.ReactNode }) {
  const [hidden, setHidden] = useState(false)

  useEffect(() => {
    const hide = () => setHidden(true)
    const show = () => setHidden(false)
    window.addEventListener("landing-search", hide)
    window.addEventListener("landing-reset", show)
    return () => {
      window.removeEventListener("landing-search", hide)
      window.removeEventListener("landing-reset", show)
    }
  }, [])

  if (hidden) return null
  return <>{children}</>
}
