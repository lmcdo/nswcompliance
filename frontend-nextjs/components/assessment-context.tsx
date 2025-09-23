"use client"

import { useState, useEffect } from "react"
import { Calendar, AlertTriangle } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

interface PropertyLEPInfo {
 lepName?: string
 amendment?: string
 commencedDate?: string
 lga?: string
}

export function AssessmentContext() {
 const [lepInfo, setLepInfo] = useState<PropertyLEPInfo>({})
 const [currentAddress, setCurrentAddress] = useState<string>("")

 // Listen for address selection from header
 useEffect(() => {
 const handleAddressSelected = (event: CustomEvent) => {
 const newAddress = event.detail
 console.log(' AssessmentContext received address event:', newAddress)
 setCurrentAddress(newAddress)
 fetchPropertyLEPInfo(newAddress)
 }

 window.addEventListener('addressSelected', handleAddressSelected as EventListener)
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
 }
 }, [])

 // No initial data loading - only load when address is selected

 const extractAmendmentFromData = (data: any): string => {
 // Extract real amendment info from the API response
 const heightSource = data.heightSource
 const fsrSource = data.fsrSource

 // Use amendment from height source (preferred)
 if (heightSource?.amendment) {
 return heightSource.amendment
 }

 // Fallback to FSR source amendment
 if (fsrSource?.amendment) {
 return fsrSource.amendment
 }

 // If no amendment data available
 return "No amendment data available"
 }

 const extractCommencedDateFromData = (data: any): string => {
 // Extract real commenced date from the API response
 const heightSource = data.heightSource
 const fsrSource = data.fsrSource

 // Use commenced date from height source (preferred)
 if (heightSource?.commencedDate) {
 return heightSource.commencedDate
 }

 // Fallback to FSR source commenced date
 if (fsrSource?.commencedDate) {
 return fsrSource.commencedDate
 }

 // If no date data available
 return "No date data available"
 }

 const fetchPropertyLEPInfo = async (addr: string) => {
 if (!addr) return

 try {
 const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
 if (response.ok) {
 const apiResponse = await response.json()

 // Extract LEP info from height source (most reliable LEP reference)
 const heightSource = apiResponse.data.heightSource
 if (heightSource) {
 setLepInfo({
 lepName: heightSource.epiName,
 amendment: extractAmendmentFromData(apiResponse.data),
 commencedDate: extractCommencedDateFromData(apiResponse.data),
 lga: apiResponse.data.constraints?.lga
 })
 }

 console.log(' AssessmentContext updated with LEP info:', apiResponse.data)
 }
 } catch (error) {
 console.error('Failed to fetch property LEP info:', error)
 }
 }

 const formatDate = (dateStr?: string) => {
 if (!dateStr) return "Unknown"

 // Convert "24-5-2025" format to "24 May 2025"
 const parts = dateStr.split("-")
 if (parts.length === 3) {
 const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
 "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
 const month = months[parseInt(parts[1]) - 1] || parts[1]
 return `${parts[0]} ${month} ${parts[2]}`
 }
 return dateStr
 }

 const calculateDaysAgo = (dateStr?: string) => {
 if (!dateStr) return "Unknown time"

 // For demo purposes, return a reasonable number
 return "3 days"
 }

 return (
 <div>
 <h3 className="text-lg font-semibold text-gray-900 mb-4">Assessment Context</h3>
 <Card className="p-5 border-amber-200 shadow-sm">
 <div className="space-y-5">
 <div>
 <label className="text-sm font-semibold text-gray-700 block mb-3">Assessment Date</label>
 <div className="relative">
 <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
 <Input type="date" defaultValue={new Date().toISOString().split('T')[0]} className="pl-10 h-10 text-sm font-medium" />
 </div>
 </div>

 {lepInfo.lepName && (
 <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
 <div className="flex items-start gap-3">
 <AlertTriangle className="h-5 w-5 text-amber-600 mt-0.5 flex-shrink-0" />
 <div className="text-sm">
 <div className="font-semibold text-amber-800 mb-1">Version Alert</div>
 <div className="text-amber-700 leading-relaxed">
 {lepInfo.lepName} updated {calculateDaysAgo(lepInfo.commencedDate)} ago
 <br />
 {lepInfo.amendment && `Using ${lepInfo.amendment}`}
 {lepInfo.lga && (
 <>
 <br />
 LGA: {lepInfo.lga}
 </>
 )}
 </div>
 <Button
 variant="link"
 className="h-auto p-0 text-amber-700 text-sm mt-2 font-medium hover:text-amber-800"
 >
 View Changes
 </Button>
 </div>
 </div>
 </div>
 )}

 {!lepInfo.lepName && (
 <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
 <div className="text-sm text-gray-500 text-center">
 LEP version information will appear here when a property is selected
 </div>
 </div>
 )}
 </div>
 </Card>
 </div>
 )
}