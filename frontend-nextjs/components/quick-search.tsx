"use client"

import { useState, useEffect } from "react"
import { Search } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface PropertyProvisions {
 zone?: string
 maxHeight?: number
 maxFsr?: number
 lga?: string
 heightSource?: {
 clause?: string
 epiName?: string
 }
 fsrSource?: {
 clause?: string
 epiName?: string
 }
}

export function QuickSearch() {
 const [propertyProvisions, setPropertyProvisions] = useState<PropertyProvisions>({})
 const [currentAddress, setCurrentAddress] = useState<string>("")

 // Listen for address selection from header
 useEffect(() => {
 const handleAddressSelected = (event: CustomEvent) => {
 const newAddress = event.detail
 console.log(' QuickSearch received address event:', newAddress)
 setCurrentAddress(newAddress)
 fetchPropertyProvisions(newAddress)
 }

 window.addEventListener('addressSelected', handleAddressSelected as EventListener)
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
 }
 }, [])

 // No initial data loading - only load when address is selected

 const fetchPropertyProvisions = async (addr: string) => {
 if (!addr) return

 try {
 const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
 if (response.ok) {
 const apiResponse = await response.json()
 const data = apiResponse.data

 setPropertyProvisions({
 zone: data.constraints?.zone,
 maxHeight: data.constraints?.maxHeight,
 maxFsr: data.constraints?.maxFsr,
 lga: data.constraints?.lga,
 heightSource: data.heightSource,
 fsrSource: data.fsrSource
 })

 console.log(' QuickSearch updated with provisions:', data)
 }
 } catch (error) {
 console.error('Failed to fetch property provisions:', error)
 }
 }

 const getPropertySpecificSuggestions = () => {
 const suggestions = []

 if (propertyProvisions.zone) {
 suggestions.push(`${propertyProvisions.zone} zone requirements`)
 }

 if (propertyProvisions.maxHeight) {
 suggestions.push(`Height limit ${propertyProvisions.maxHeight}m`)
 }

 if (propertyProvisions.maxFsr) {
 suggestions.push(`FSR limit ${propertyProvisions.maxFsr}:1 sq m`)
 }

 // Only add default suggestions if we have property data
 if (suggestions.length === 0 && propertyProvisions.zone) {
 suggestions.push("Setback requirements", "Minimum lot size", "Heritage provisions")
 }

 return suggestions
 }

 const getPropertySpecificResults = () => {
 const results = []

 // Height provision
 if (propertyProvisions.heightSource?.clause) {
 results.push({
 title: `LEP ${propertyProvisions.heightSource.clause} - Building Height`,
 type: "LEP",
 description: `Max height: ${propertyProvisions.maxHeight}m`
 })
 }

 // FSR provision
 if (propertyProvisions.fsrSource?.clause) {
 results.push({
 title: `LEP ${propertyProvisions.fsrSource.clause} - Floor Space Ratio`,
 type: "LEP",
 description: `Max FSR: ${propertyProvisions.maxFsr}:1 sq m`
 })
 }

 // Add zone provision
 if (propertyProvisions.zone) {
 results.push({
 title: `LEP Zone ${propertyProvisions.zone} - Land Use`,
 type: "LEP",
 description: `Zoning: ${propertyProvisions.zone} zone`
 })
 }

 // Don't show default results - only show when we have property data
 return results
 }

 const suggestions = getPropertySpecificSuggestions()
 const results = getPropertySpecificResults()

 return (
 <div>
 <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Search</h3>
 <Card className="p-5 shadow-sm">
 <div className="space-y-5">
 <div>
 <label className="text-sm font-semibold text-gray-700 block mb-3">Search Provisions</label>
 <div className="relative">
 <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
 <Input placeholder="Search..." className="pl-10 h-10 text-sm focus:ring-2 focus:ring-blue-500" />
 </div>
 </div>

 {suggestions.length > 0 && (
 <div>
 <div className="text-sm font-medium text-gray-600 mb-3">Recent/Suggested:</div>
 <ul className="space-y-2">
 {suggestions.map((suggestion, index) => (
 <li
 key={index}
 className="text-sm text-blue-600 hover:text-blue-800 cursor-pointer hover:bg-blue-50 p-2 rounded transition-colors"
 >
 • {suggestion}
 </li>
 ))}
 </ul>
 </div>
 )}

 {results.length > 0 && (
 <div>
 <div className="text-sm font-medium text-gray-600 mb-3">Property Provisions</div>
 <div className="max-h-48 overflow-y-auto space-y-3">
 {results.map((result, index) => (
 <div
 key={index}
 className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors"
 >
 <div className="text-sm font-semibold text-gray-900 mb-1">{result.title}</div>
 {result.description && (
 <div className="text-xs text-gray-600 mb-3">{result.description}</div>
 )}
 <div className="flex gap-2">
 <Button
 size="sm"
 className="bg-blue-600 hover:bg-blue-700 text-white text-xs font-medium px-3"
 >
 Apply
 </Button>
 <Button
 size="sm"
 variant="outline"
 className="border-gray-300 text-gray-700 hover:bg-gray-50 text-xs font-medium px-3"
 >
 View Full
 </Button>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}

 {suggestions.length === 0 && results.length === 0 && (
 <div className="text-center py-8">
 <div className="text-sm text-gray-500">
 Select a property above to see relevant planning provisions and suggestions
 </div>
 </div>
 )}
 </div>
 </Card>
 </div>
 )
}