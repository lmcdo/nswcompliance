"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ChevronDown, ChevronRight, MapPin, Calendar, FileText, Zap, TreePine, Building, Shield, ExternalLink } from "lucide-react"

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

interface PropertyDetailsComprehensiveProps {
 propertyData: PropertyData;
}

export function PropertyDetailsComprehensive({ propertyData }: PropertyDetailsComprehensiveProps) {
 const [expandedLayers, setExpandedLayers] = useState<Set<string>>(new Set())

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

 // Handle legislationUrl and other URL fields
 if ((key === 'legislationUrl' || key.toLowerCase().includes('url')) && typeof value === 'string' && value.startsWith('http')) {
 return (
 <a
 href={value}
 target="_blank"
 rel="noopener noreferrer"
 className="text-blue-600 hover:text-blue-700 underline inline-flex items-center gap-1"
 >
 View Legislation
 <ExternalLink className="h-3 w-3" />
 </a>
 )
 }

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

 if (!propertyData || !propertyData.planningLayers || propertyData.planningLayers.length === 0) {
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

         // Determine color scheme based on layer type
         const isSEPP = layerName === 'Special Provisions'

         // Color scheme: SEPP=Orange, LEP=Blue, N/A=Gray
         const colors = isPresent
           ? (isSEPP
             ? { bg: 'bg-orange-50', border: 'border-orange-200', text: 'text-orange-800', circleBg: 'bg-orange-100', circleText: 'text-orange-700', circleBorder: 'border-orange-300', circleActiveBg: 'bg-orange-600' }
             : { bg: 'bg-blue-50', border: 'border-blue-200', text: 'text-blue-800', circleBg: 'bg-blue-100', circleText: 'text-blue-700', circleBorder: 'border-blue-300', circleActiveBg: 'bg-blue-600' })
           : { bg: 'bg-gray-50', border: 'border-gray-200', text: 'text-gray-500', circleBg: '', circleText: '', circleBorder: '', circleActiveBg: '' }

         return (
           <div key={layerName} className={`border rounded-lg ${colors.bg} ${colors.border}`}>
             <Button
               variant="ghost"
               className="!flex w-full justify-between h-auto p-3 font-normal whitespace-normal text-left"
               onClick={() => layer && toggleLayer(layer.id)}
               disabled={!isPresent}
             >
               <div className="flex items-start justify-between gap-2 w-full">
                 <span className={`font-medium text-xs leading-tight flex-1 break-words ${colors.text}`}>{layerName}</span>
                 {isPresent ? (
                   <div className={`flex items-center justify-center h-6 w-6 rounded-full text-xs font-semibold flex-shrink-0 ${expandedLayers.has(layer.id) ? `${colors.circleActiveBg} text-white` : `${colors.circleBg} ${colors.circleText} border ${colors.circleBorder}`}`}>
                     {layer.results.length}
                   </div>
                 ) : (
                   <span className="text-xs text-gray-500 flex-shrink-0">N/A</span>
                 )}
               </div>
             </Button>

             {layer && expandedLayers.has(layer.id) && (
               <div className="border-t bg-gray-50 p-3 space-y-3">
                 {layer.results.map((result, idx) => (
                   <div key={idx} className="bg-white rounded-lg p-3 shadow-sm">
                     {/* Important fields prominently displayed */}
                     <div className="flex flex-wrap gap-1.5 mb-2">
                       {getImportantFields(result).map(({ key, value }) => (
                         <Badge key={key} variant="default" className="text-xs font-semibold px-2 py-0.5">
                           {key}: {value}
                         </Badge>
                       ))}
                     </div>

                     {/* All other metadata - simple list format */}
                     <div className="space-y-1.5 text-xs">
                       {getSecondaryFields(result).map(([key, value]) => (
                         <div key={key} className="leading-relaxed">
                           <span className="text-gray-500 font-medium">{key}:</span>{' '}
                           <span className="text-gray-900 font-semibold">
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