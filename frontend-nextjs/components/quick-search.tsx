"use client"

import { useState, useEffect } from "react"
import { Search, FileText, X, Loader2 } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"

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
 const [selectedClause, setSelectedClause] = useState<any>(null)
 const [isClauseDialogOpen, setIsClauseDialogOpen] = useState(false)
 const [isLoadingClause, setIsLoadingClause] = useState(false)
 const [isLoadingProperty, setIsLoadingProperty] = useState(false)

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

 setIsLoadingProperty(true)
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
 } finally {
 setIsLoadingProperty(false)
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
 description: `Max height: ${propertyProvisions.maxHeight}m`,
 clauseNumber: propertyProvisions.heightSource.clause,
 documentName: propertyProvisions.heightSource.epiName || "Inner West Local Environmental Plan 2022"
 })
 }

 // FSR provision
 if (propertyProvisions.fsrSource?.clause) {
 results.push({
 title: `LEP ${propertyProvisions.fsrSource.clause} - Floor Space Ratio`,
 type: "LEP",
 description: `Max FSR: ${propertyProvisions.maxFsr}:1 sq m`,
 clauseNumber: propertyProvisions.fsrSource.clause,
 documentName: propertyProvisions.fsrSource.epiName || "Inner West Local Environmental Plan 2022"
 })
 }

 // Add zone provision
 if (propertyProvisions.zone) {
 results.push({
 title: `LEP Zone ${propertyProvisions.zone} - Land Use`,
 type: "LEP",
 description: `Zoning: ${propertyProvisions.zone} zone`,
 clauseNumber: `Zone ${propertyProvisions.zone}`,
 documentName: "Inner West Local Environmental Plan 2022"
 })
 }

 // Don't show default results - only show when we have property data
 return results
 }

 // Handler for View Full button
 const handleViewFullClause = async (result: any) => {
 setIsLoadingClause(true)
 setIsClauseDialogOpen(true)

 try {
 // Map clause types to known database IDs
 const clauseIdMap: Record<string, number> = {
 'Clause 4.3': 17479, // Height of Buildings - policy intent
 'Clause 4.4': 17473, // Floor Space Ratio - development standards
 'Clause 4.4 2C & 2D': 17473 // FSR clause - same as 4.4
 }

 // Extract clause number from title
 const clauseMatch = result.title.match(/Clause ([0-9\.]+[A-Z]*)/)
 const clauseKey = clauseMatch ? `Clause ${clauseMatch[1]}` : result.clauseNumber
 const clauseId = clauseIdMap[clauseKey] || clauseIdMap[result.clauseNumber]

 if (clauseId) {
 // Use the clause API with known ID
 const response = await fetch(`/api/clause/${clauseId}`)
 if (response.ok) {
 const data = await response.json()
 if (data.success && data.clause) {
 setSelectedClause({
 title: result.title,
 clauseNumber: data.clause.clause_reference,
 documentName: data.clause.document_name,
 content: data.clause.full_text,
 documentType: data.clause.document_type,
 description: result.description,
 authorityLevel: data.clause.authority_level,
 legalContext: data.clause.legal_context
 })
 return
 }
 }
 }

 // If no clause ID mapping or API call failed, show error
 setSelectedClause({
 title: result.title,
 clauseNumber: result.clauseNumber,
 documentName: result.documentName,
 content: "Database content not available. Please refer to the official Inner West Local Environmental Plan 2022.",
 documentType: result.type,
 description: result.description
 })

 } catch (error) {
 console.error('Failed to load clause:', error)
 setSelectedClause({
 title: result.title,
 clauseNumber: result.clauseNumber,
 documentName: result.documentName,
 content: "Error loading clause content from database. Please refer to the official legislation.",
 documentType: result.type,
 description: result.description
 })
 } finally {
 setIsLoadingClause(false)
 }
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

 {isLoadingProperty && (
 <div className="flex flex-col items-center justify-center py-8 space-y-3">
 <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
 <div className="text-sm text-gray-600 font-medium">Searching NSW Planning Portal...</div>
 <div className="text-xs text-gray-500">Finding property data and planning constraints</div>
 </div>
 )}

 {!isLoadingProperty && suggestions.length > 0 && (
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

 {!isLoadingProperty && results.length > 0 && (
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
 onClick={() => handleViewFullClause(result)}
 >
 View Full
 </Button>
 </div>
 </div>
 ))}
 </div>
 </div>
 )}

 </div>
 </Card>

 {/* Clause Display Dialog */}
 <Dialog open={isClauseDialogOpen} onOpenChange={setIsClauseDialogOpen}>
 <DialogContent className="max-w-2xl max-h-[80vh] w-full overflow-hidden">
 <DialogHeader>
 <DialogTitle className="flex items-center justify-between">
 <span>{selectedClause?.title}</span>
 <Badge variant="outline" className="ml-2">
 {selectedClause?.documentType}
 </Badge>
 </DialogTitle>
 <DialogDescription>
 Inner West Local Environmental Plan 2022
 </DialogDescription>
 </DialogHeader>
 <ScrollArea className="h-[50vh] mt-4">
 {isLoadingClause ? (
 <div className="flex items-center justify-center h-32">
 <div className="text-gray-500">Loading clause content...</div>
 </div>
 ) : (
 <div className="space-y-4 pr-2">
 <div className="bg-blue-50 p-3 rounded-lg">
 <p className="text-sm font-medium text-blue-900">
 {selectedClause?.description}
 </p>
 </div>
 <div className="bg-gray-50 p-4 rounded-lg">
 <h4 className="font-semibold text-gray-900 mb-2">
 {selectedClause?.clauseNumber} - Full Clause Text
 </h4>
 <div className="text-xs leading-tight text-gray-800 whitespace-pre-wrap">
 {selectedClause?.content}
 </div>
 </div>
 {selectedClause?.legalContext && (
 <div className="bg-amber-50 p-3 rounded-lg border border-amber-200">
 <p className="text-sm text-amber-800">
 <strong>Legal Context:</strong> {selectedClause.legalContext}
 </p>
 </div>
 )}
 </div>
 )}
 </ScrollArea>
 <div className="mt-4 flex justify-end">
 <Button
 variant="outline"
 onClick={() => setIsClauseDialogOpen(false)}
 >
 Close
 </Button>
 </div>
 </DialogContent>
 </Dialog>
 </div>
 )
}