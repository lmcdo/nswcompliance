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

 return (
 <Card className="shadow-sm">
 <CardHeader>
 <CardTitle className="text-lg font-semibold flex items-center gap-2">
 <FileText className="h-5 w-5" />
 NSW Planning Layers ({propertyData.planningLayers.length})
 </CardTitle>
 </CardHeader>
 <CardContent className="space-y-3">
 {propertyData.planningLayers.map((layer) => (
 <div key={layer.id} className="border rounded-lg">
 <Button
 variant="ghost"
 className="w-full justify-between h-auto p-3 font-normal"
 onClick={() => toggleLayer(layer.id)}
 >
 <div className="flex items-center gap-2">
 {getLayerIcon(layer.layerName)}
 <span className="font-medium text-xs">{layer.layerName}</span>
 <Badge variant="outline" className="text-xs">
 {layer.results.length} item{layer.results.length !== 1 ? 's' : ''}
 </Badge>
 </div>
 {expandedLayers.has(layer.id) ?
 <ChevronDown className="h-4 w-4" /> :
 <ChevronRight className="h-4 w-4" />
 }
 </Button>

 {expandedLayers.has(layer.id) && (
 <div className="border-t p-3 space-y-3">
 {layer.results.map((result, idx) => (
 <div key={idx} className="bg-gray-50 rounded p-3">
 {/* Important fields prominently displayed */}
 <div className="flex flex-wrap gap-2 mb-2">
 {getImportantFields(result).map(({ key, value }) => (
 <Badge key={key} variant="default" className="text-xs">
 {key}: {value}
 </Badge>
 ))}
 </div>

 {/* Title if available and not redundant with important fields */}
 {result.title && result.title !== 'Canopy %' && (
 <div className="font-medium text-sm mb-2">{result.title}</div>
 )}

 {/* All other metadata in compact grid */}
 <div className="grid grid-cols-2 gap-1 text-xs">
 {getSecondaryFields(result).map(([key, value]) => (
 <div key={key} className="flex justify-between">
 <span className="text-gray-600 font-medium">{key}:</span>
 <span className="text-gray-900">{formatValue(key, value)}</span>
 </div>
 ))}
 </div>
 </div>
 ))}
 </div>
 )}
 </div>
 ))}
 </CardContent>
 </Card>
 )
}