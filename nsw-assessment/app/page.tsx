"use client"

import { useState } from "react"
import { Header } from "@/components/header"
import { PropertyPanel } from "@/components/property-panel"
import { AssessmentPanel } from "@/components/assessment-panel"

export default function AssessmentInterface() {
 const [selectedProperty, setSelectedProperty] = useState("30 Illawarra Road")
 const [developmentType, setDevelopmentType] = useState("Dual Occupancy")

 return (
 <div className="min-h-screen bg-white">
 <Header />
 <main className="flex flex-col md:flex-row h-[calc(100vh-80px)] pt-[80px]">
 <PropertyPanel />
 <AssessmentPanel developmentType={developmentType} />
 </main>
 </div>
 )
}
