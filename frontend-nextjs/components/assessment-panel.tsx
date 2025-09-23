"use client"

import { useState } from "react"
import { DevelopmentSelector } from "@/components/development-selector"
import { ComplianceStatus } from "@/components/compliance-status"
import { ComplianceChecklist } from "@/components/compliance-checklist"

interface AssessmentPanelProps {
 developmentType: string
 propertyData?: any
}

export function AssessmentPanel({ developmentType, propertyData }: AssessmentPanelProps) {
 const [isAssessing, setIsAssessing] = useState(false)
 const [complianceResults, setComplianceResults] = useState([])

 const runComplianceCheck = async () => {
 setIsAssessing(true)
 try {
 const response = await fetch("/api/compliance/live-check", {
 method: "POST",
 headers: { "Content-Type": "application/json" },
 body: JSON.stringify({ developmentType })
 })
 if (response.ok) {
 const data = await response.json()
 setComplianceResults(data.checks || [])
 }
 } catch (error) {
 console.error("Compliance check failed:", error)
 }
 setIsAssessing(false)
 }

 return (
 <section className="flex-1 bg-gray-50 relative flex flex-col h-full overflow-hidden">
 {/* Scrollable content area */}
 <div className="flex-1 overflow-y-auto">
 <div className="p-8 space-y-8">
 <DevelopmentSelector />
 <ComplianceStatus />
 <ComplianceChecklist propertyData={propertyData} />
 </div>
 </div>

 {/* Fixed action bar at bottom */}
 <div className="border-t border-gray-200 bg-white px-4 md:px-6 h-16 md:h-20 flex items-center justify-between flex-shrink-0">
 <button className="px-4 md:px-6 py-2 bg-gradient-to-b from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white font-medium text-sm md:text-base rounded-md shadow-lg">
 Save Draft
 </button>
 <div className="flex gap-2 md:gap-3">
 <button className="px-4 md:px-6 py-2 bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 text-white font-medium text-sm md:text-base rounded-md shadow-lg">
 Generate Report
 </button>
 <button className="px-4 md:px-6 py-2 bg-gradient-to-b from-emerald-700 to-emerald-800 hover:from-emerald-800 hover:to-emerald-900 text-white font-medium text-sm md:text-base rounded-md shadow-lg">
 Submit Assessment
 </button>
 </div>
 </div>
 </section>
 )
}