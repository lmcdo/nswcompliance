"use client"

import { useState, useEffect } from "react"
import { CheckCircle, AlertTriangle, XCircle } from "lucide-react"
import { Card } from "@/components/ui/card"

interface PropertyConstraints {
 maxHeight?: number
 maxFsr?: number
 zone?: string
 lga?: string
}

export function ComplianceStatus() {
 const [propertyConstraints, setPropertyConstraints] = useState<PropertyConstraints>({})
 const [currentAddress, setCurrentAddress] = useState<string>("")
 const [developmentType, setDevelopmentType] = useState<string>("dual_occupancy")

 // Listen for address selection from header
 useEffect(() => {
 const handleAddressSelected = (event: CustomEvent) => {
 const newAddress = event.detail
 console.log(' ComplianceStatus received address event:', newAddress)
 setCurrentAddress(newAddress)
 fetchPropertyConstraints(newAddress)
 }

 window.addEventListener('addressSelected', handleAddressSelected as EventListener)
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
 }
 }, [])

 // Listen for development type changes
 useEffect(() => {
 const handleDevelopmentTypeChanged = (event: CustomEvent) => {
 const { developmentType: newType } = event.detail
 console.log(' ComplianceStatus received development type change:', newType)
 setDevelopmentType(newType)
 }

 window.addEventListener('developmentTypeChanged', handleDevelopmentTypeChanged as EventListener)
 return () => {
 window.removeEventListener('developmentTypeChanged', handleDevelopmentTypeChanged as EventListener)
 }
 }, [])

 // No initial data loading - only load when address is selected

 const fetchPropertyConstraints = async (addr: string) => {
 if (!addr) return

 try {
 const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
 if (response.ok) {
 const apiResponse = await response.json()
 const constraints = apiResponse.data.constraints
 setPropertyConstraints(constraints)
 console.log(' ComplianceStatus updated with constraints:', constraints)
 }
 } catch (error) {
 console.error('Failed to fetch property constraints:', error)
 }
 }

 // Get development type display name
 const getDevelopmentDisplayName = (type: string) => {
 const displayNames: Record<string, string> = {
 'dwelling_house': 'Single dwelling house',
 'dual_occupancy': 'Dual occupancy',
 'multi_dwelling_housing': 'Multi dwelling housing',
 'residential_flat_building': 'Residential flat building',
 'boarding_house': 'Boarding house',
 'shop_top_housing': 'Shop top housing',
 'seniors_housing': 'Seniors housing',
 'secondary_dwelling': 'Secondary dwelling',
 'group_home': 'Group home',
 'commercial_premises': 'Commercial development',
 'industrial': 'Industrial development',
 'subdivision': 'Subdivision'
 }
 return displayNames[type] || type.replace(/_/g, ' ')
 }

 // Generate dynamic status items based on property constraints
 const getStatusItems = () => {
 const items = []

 // Zone permissibility check
 if (propertyConstraints.zone) {
 const developmentDisplayName = getDevelopmentDisplayName(developmentType)
 items.push({
 icon: CheckCircle,
 title: "Permissible",
 description: `${developmentDisplayName} permitted in ${propertyConstraints.zone}`,
 status: "success",
 })
 }

 // Height limit check
 if (propertyConstraints.maxHeight) {
 items.push({
 icon: AlertTriangle,
 title: "Height Limit",
 description: `${propertyConstraints.maxHeight}m maximum\nCheck plans`,
 status: "warning",
 })
 }

 // FSR check
 if (propertyConstraints.maxFsr) {
 items.push({
 icon: CheckCircle,
 title: "FSR",
 description: `Max: ${propertyConstraints.maxFsr}:1 sq m\nCheck proposal`,
 status: "success",
 })
 }

 // Only add setback info if we have property data
 if (propertyConstraints.zone) {
 items.push({
 icon: XCircle,
 title: "Setback",
 description: "Front: TBD\nRequired: TBD\nNeeds assessment",
 status: "error",
 })
 }

 return items
 }

 const statusItems = getStatusItems()

 const getStatusStyles = (status: string) => {
 switch (status) {
 case "success":
 return "bg-green-50 border-green-200 text-green-800"
 case "warning":
 return "bg-amber-50 border-amber-200 text-amber-800"
 case "error":
 return "bg-red-50 border-red-200 text-red-800"
 default:
 return "bg-gray-50 border-gray-200 text-gray-800"
 }
 }

 const getIconColor = (status: string) => {
 switch (status) {
 case "success":
 return "text-green-600"
 case "warning":
 return "text-amber-600"
 case "error":
 return "text-red-600"
 default:
 return "text-gray-600"
 }
 }

 return (
 <Card className="p-6 border-l-4 border-l-blue-600 shadow-sm">
 <h3 className="font-semibold text-gray-900 mb-5 text-lg">Quick Compliance Status</h3>
 {statusItems.length > 0 ? (
 <div className="grid grid-cols-2 gap-4">
 {statusItems.map((item, index) => {
 const Icon = item.icon
 return (
 <div key={index} className={`p-4 rounded-lg border-2 ${getStatusStyles(item.status)}`}>
 <div className="flex items-start gap-3">
 <Icon className={`h-5 w-5 mt-0.5 flex-shrink-0 ${getIconColor(item.status)}`} />
 <div>
 <div className="font-semibold text-sm mb-1">{item.title}</div>
 <div className="text-xs leading-relaxed whitespace-pre-line">{item.description}</div>
 </div>
 </div>
 </div>
 )
 })}
 </div>
 ) : (
 <div className="text-center py-8">
 <div className="text-sm text-gray-500">
 Compliance status will appear here when a property is selected
 </div>
 </div>
 )}
 </Card>
 )
}