"use client"

import { useState, useEffect } from "react"
import { Header } from "@/components/header"
import { PropertyPanel } from "@/components/property-panel"
import { DevelopmentSelector } from "@/components/development-selector"
import { DevelopmentSelectorEnhanced } from "@/components/development-selector-enhanced"
import { ComplianceStatus } from "@/components/compliance-status"
import { ComplianceChecklist } from "@/components/compliance-checklist"
import { useFeatureFlags } from "@/components/providers/FeatureFlagProvider"

export default function AssessmentInterface() {
 const { flags } = useFeatureFlags()
 const [selectedProperty, setSelectedProperty] = useState<string | null>(null)
 const [propertyData, setPropertyData] = useState<any>(null)
 const [developmentType, setDevelopmentType] = useState("dual_occupancy")
 const [zoneCode, setZoneCode] = useState<string>("")

 // Listen for address selection to update property data
 useEffect(() => {
 const handleAddressSelected = async (event: CustomEvent) => {
 const address = event.detail
 console.log('Main page received address:', address)
 setSelectedProperty(address)

 // Fetch property data
 try {
 const response = await fetch(`/api/property?address=${encodeURIComponent(address)}`)
 if (response.ok) {
 const apiResponse = await response.json()
 const data = apiResponse.data
 setPropertyData(data)
 setZoneCode(data.constraints?.zone || '')
 console.log('Property data loaded:', data)
 }
 } catch (error) {
 console.error('Failed to fetch property data:', error)
 }
 }

 window.addEventListener('addressSelected', handleAddressSelected as EventListener)
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
 }
 }, [])

 const handleDevelopmentTypeChange = (type: string) => {
 console.log('🎯 Main page: Development type changing from', developmentType, 'to', type)
 setDevelopmentType(type)
 }

 return (
 <>
 <Header />
 {/* Simple two-column layout */}
 <div style={{
 display: 'flex',
 height: 'calc(100vh - 80px)',
 marginTop: '80px'
 }}>
 {/* Left column - 50% width */}
 <div style={{ width: '50%', minWidth: '400px' }}>
   <PropertyPanel />
 </div>

 {/* Right column with flex column layout */}
 <div style={{
 flex: 1,
 backgroundColor: '#f9fafb',
 display: 'flex',
 flexDirection: 'column'
 }}>
 {/* Scrollable content area */}
 <div style={{
 flex: 1,
 overflowY: 'auto',
 padding: '32px'
 }}>
 <div style={{ display: 'flex', flexDirection: 'column', gap: '32px' }}>
 {flags.newDevelopmentSelector ? (
 <DevelopmentSelectorEnhanced
 value={developmentType}
 onChange={handleDevelopmentTypeChange}
 zoneCode={zoneCode}
 />
 ) : (
 <DevelopmentSelector />
 )}
 <ComplianceStatus />
 <ComplianceChecklist
 propertyData={propertyData}
 developmentType={developmentType}
 propertyId={selectedProperty}
 zoneCode={zoneCode}
 onComplianceUpdate={(status) => {
 console.log('Compliance status updated:', status)
 }}
 />
 </div>
 </div>

 {/* Buttons fixed at bottom */}
 <div style={{
 height: '80px',
 backgroundColor: 'white',
 borderTop: '1px solid #e5e7eb',
 padding: '0 24px',
 display: 'flex',
 alignItems: 'center',
 justifyContent: 'space-between'
 }}>
 <button style={{
 padding: '8px 24px',
 background: 'linear-gradient(to bottom, #047857, #065f46)',
 color: 'white',
 border: 'none',
 borderRadius: '6px',
 fontWeight: '500',
 cursor: 'pointer'
 }}>
 Save Draft
 </button>
 <div style={{ display: 'flex', gap: '12px' }}>
 <button style={{
 padding: '8px 24px',
 background: 'linear-gradient(to bottom, #059669, #047857)',
 color: 'white',
 border: 'none',
 borderRadius: '6px',
 fontWeight: '500',
 cursor: 'pointer'
 }}>
 Generate Report
 </button>
 <button style={{
 padding: '8px 24px',
 background: 'linear-gradient(to bottom, #047857, #065f46)',
 color: 'white',
 border: 'none',
 borderRadius: '6px',
 fontWeight: '500',
 cursor: 'pointer'
 }}>
 Submit Assessment
 </button>
 </div>
 </div>
 </div>
 </div>
 </>
 )
}