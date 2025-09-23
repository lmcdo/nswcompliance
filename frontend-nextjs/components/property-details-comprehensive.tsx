"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, MapPin, Calendar, FileText, Zap, TreePine, Building, Shield } from "lucide-react"

interface PlanningLayer {
 id: string;
 layerName: string;
 results: any[];
}

interface PropertyData {
 planningLayers?: PlanningLayer[];
 constraints?: any;
 fsrSource?: any;
 heightSource?: any;
 environmental?: any;
 heritage?: any;
}

export function PropertyDetailsComprehensive() {
 const [propertyData, setPropertyData] = useState<PropertyData>({})
 const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set())
 const [currentAddress, setCurrentAddress] = useState<string>("")

 // Listen for address selection from header
 useEffect(() => {
 const handleAddressSelected = (event: CustomEvent) => {
 const newAddress = event.detail
 console.log(' PropertyDetailsComprehensive received address event:', newAddress)
 setCurrentAddress(newAddress)
 fetchComprehensivePropertyData(newAddress)
 }

 window.addEventListener('addressSelected', handleAddressSelected as EventListener)
 return () => {
 window.removeEventListener('addressSelected', handleAddressSelected as EventListener)
 }
 }, [])

 // No initial data loading - only load when address is selected

 const fetchComprehensivePropertyData = async (addr: string) => {
 if (!addr) return

 try {
 const response = await fetch(`/api/property?address=${encodeURIComponent(addr)}`)
 if (response.ok) {
 const apiResponse = await response.json()
 setPropertyData(apiResponse.data)
 console.log(' PropertyDetailsComprehensive updated with data:', apiResponse.data)
 }
 } catch (error) {
 console.error('Failed to fetch comprehensive property data:', error)
 }
 }

 const toggleLayer = (layerId: string) => {
 const newExpanded = new Set(expandedLayers)
 if (newExpanded.has(layerId)) {
 newExpanded.delete(layerId)
 } else {
 newExpanded.add(layerId)
 }
 setExpandedLayers(newExpanded)
 }

 const getLayerIcon = (layerName: string) => {
 switch (layerName) {
 case 'Land Zoning Map': return <Building className="h-4 w-4" />
 case 'Height of Buildings Map': return <Building className="h-4 w-4" />
 case 'Floor Space Ratio Map': return <Building className="h-4 w-4" />
 case 'Heritage Map': return <Shield className="h-4 w-4" />
 case 'Special Provisions': return <Zap className="h-4 w-4" />
 case 'Regional Plan Boundary': return <MapPin className="h-4 w-4" />
 case 'Greater Sydney Tree Canopy Cover 2019':
 case 'Greater Sydney Tree Canopy Cover 2022': return <TreePine className="h-4 w-4" />
 default: return <FileText className="h-4 w-4" />
 }
 }

 const formatValue = (key: string, value: any) => {
 if (value === null || value === undefined) return 'N/A'

 // Handle Regional Plan Website links
 if (key === 'Regional Plan Website' && typeof value === 'string' && value.includes('&lt;a href=')) {
 const decoded = value.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
 const linkMatch = decoded.match(/<a href="([^"]+)">([^<]+)<\/a>/)
 if (linkMatch) {
 const [, url, text] = linkMatch
 return (
 <a
 href={url}
 target="_blank"
 rel="noopener noreferrer"
 className="text-blue-600 hover:text-blue-800 underline font-medium"
 >
 {text}
 </a>
 )
 }
 }

 if (typeof value === 'string' && value.includes('&lt;')) {
 return value.replace(/&lt;/g, '<').replace(/&gt;/g, '>')
 }
 return String(value)
 }

 const getImportantFields = (result: any) => {
 const important = []

 // Key regulatory fields
 if (result['Zone']) important.push({ key: 'Zone', value: result['Zone'] })
 if (result['Maximum Building Height']) important.push({ key: 'Height', value: `${result['Maximum Building Height']}${result['Units'] || ''}` })
 if (result['Floor Space Ratio']) important.push({ key: 'FSR', value: `${result['Floor Space Ratio']}:1 sq m` })
 if (result['Land Use']) important.push({ key: 'Use', value: result['Land Use'] })
 if (result['Legislative Clause']) important.push({ key: 'Clause', value: result['Legislative Clause'] })

 // Environmental/Special
 if (result['Class']) important.push({ key: 'Class', value: result['Class'] })
 if (result['Canopy %']) important.push({ key: 'Canopy', value: `${result['Canopy %']}%` })
 if (result['Type']) important.push({ key: 'Type', value: result['Type'] })

 return important
 }

 const getSecondaryFields = (result: any) => {
 const exclude = ['Zone', 'Maximum Building Height', 'Floor Space Ratio', 'Land Use', 'Legislative Clause', 'Class', 'Canopy %', 'Type', 'title']
 return Object.entries(result).filter(([key, value]) => !exclude.includes(key) && value !== null && value !== undefined && value !== '')
 }

 if (!propertyData.planningLayers || propertyData.planningLayers.length === 0) {
 return (
 <Card className="shadow-sm">
 <CardHeader>
 <CardTitle className="text-lg font-semibold flex items-center gap-2">
 <FileText className="h-5 w-5" />
 Planning Layers Details
 </CardTitle>
 </CardHeader>
 <CardContent>
 <div className="text-sm text-gray-500">Loading comprehensive planning data...</div>
 </CardContent>
 </Card>
 )
 }

 // Define all expected NSW Planning Layers
 const expectedLayers = [
   'Heritage Map',
   'Floor Space Ratio Map',
   'Height of Buildings Map',
   'Acid Sulfate Soils Map',
   'Local Aboriginal Land Council',
   'Special Provisions',
   'Land Application Map',
   'Regional Plan Boundary',
   'Land Zoning Map',
   'Greater Sydney Tree Canopy Cover 2019',
   'Greater Sydney Tree Canopy Cover 2022',
   'Terrestrial Biodiversity Map'
 ]

 // Create map of actual layers
 const layerMap = new Map()
 propertyData.planningLayers?.forEach(layer => {
   layerMap.set(layer.layerName, layer)
 })

 return (
 <Card className="shadow-sm">
 <CardHeader>
 <CardTitle className="text-lg font-semibold flex items-center gap-2">
 <FileText className="h-5 w-5" />
 NSW Planning Layers ({expectedLayers.length})
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 {expectedLayers.map((layerName) => {
   const layer = layerMap.get(layerName)
   const isPresent = !!layer
   return (
   <div key={layerName} className={`border rounded-lg ${isPresent ? 'bg-green-50 border-green-200' : 'bg-orange-50 border-orange-200'}`}>
   <Button
   variant="ghost"
   className="w-full justify-between h-auto p-3 font-normal"
   onClick={() => layer && toggleLayer(layer.id)}
   disabled={!isPresent}
   >
   <div className="flex items-center gap-2">
   {getLayerIcon(layerName)}
   <span className={`font-medium text-xs ${isPresent ? 'text-green-800' : 'text-orange-600'}`}>{layerName}</span>
   <Badge variant="outline" className={`text-xs ${isPresent ? 'border-green-300 text-green-700' : 'border-orange-300 text-orange-600'}`}>
   {isPresent ? `${layer.results.length} item${layer.results.length !== 1 ? 's' : ''}` : 'Does not apply'}
   </Badge>
   </div>
   {isPresent && (expandedLayers.has(layer.id) ?
   <ChevronDown className="h-4 w-4" /> :
   <ChevronRight className="h-4 w-4" />
   )}
   </Button>

 {layer && expandedLayers.has(layer.id) && (
 <div className="border-t p-4 space-y-4">
 {layer.results.map((result, idx) => (
 <div key={idx} className="bg-white border rounded-lg p-4 shadow-sm">
 {/* Important fields prominently displayed */}
 <div className="flex flex-wrap gap-2 mb-3">
 {getImportantFields(result).map(({ key, value }) => (
 <Badge key={key} variant="default" className="text-xs font-medium">
 {key}: {value}
 </Badge>
 ))}
 </div>

 {/* Title if available and not redundant with important fields */}
 {result.title && result.title !== 'Canopy %' && (
 <h4 className="font-semibold text-base mb-3 text-gray-900">{result.title}</h4>
 )}

 {/* All other metadata in clean vertical layout */}
 <div className="space-y-2">
 {getSecondaryFields(result).map(([key, value]) => (
 <div key={key} className="flex flex-col sm:flex-row sm:justify-between border-b border-gray-100 pb-1">
 <span className="text-gray-600 font-medium text-sm">{key}:</span>
 <span className="text-gray-900 text-sm sm:text-right max-w-xs break-words">
 {typeof formatValue(key, value) === 'object' ? formatValue(key, value) : formatValue(key, value)}
 </span>
 </div>
 ))}
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 )
 })}
 </CardContent>
 </Card>
 )
}