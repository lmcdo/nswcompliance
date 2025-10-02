"use client"

import { redirect } from 'next/navigation'
import { useEffect } from 'react'

export default function HomePage() {
  useEffect(() => {
    // Redirect to the 2-column assessment page
    window.location.href = '/assessment'
  }, [])

  return (
    <div className="flex min-h-screen items-center justify-center">
      <div className="text-center">
        <h1 className="text-2xl font-bold mb-4">NSW Compliance Engine</h1>
        <p className="text-gray-600">Redirecting to the new dashboard...</p>
      </div>
    </div>
  )
}