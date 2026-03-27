"use client"

import { useState, useEffect } from "react"
import { CheckCircle2, Circle, AlertTriangle, FileText, MessageSquare, ChevronDown, ChevronUp, Clock, Shield } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { useFeatureFlags } from "@/components/providers/FeatureFlagProvider"

interface ChecklistItem {
 id: string
 title: string
 clause: string
 status: "compliant" | "non-compliant" | "pending"
 details: string
 completed: boolean
 requiresVariation?: boolean
 tierLevel?: number
 confidenceLevel?: number
 documentType?: string
 numericValue?: number
 unit?: string
}

interface ComplianceChecklistProps {
 propertyData?: any;
 developmentType?: string;
 zoneCode?: string;
 propertyId?: string | null;
 onComplianceUpdate?: (status: any) => void;
}

export function ComplianceChecklist({
 propertyData,
 developmentType,
 zoneCode,
 propertyId,
 onComplianceUpdate
}: ComplianceChecklistProps) {
 const { flags } = useFeatureFlags()
 const [expandedItems, setExpandedItems] = useState<string[]>(["1", "2"])
 const [checklistItems, setChecklistItems] = useState<ChecklistItem[]>([])
 const [loading, setLoading] = useState(false)
 const [error, setError] = useState<string | null>(null)

 // No more static fallback data - only show real compliance data

 // Fetch dynamic compliance data when new functionality is enabled
 const fetchDynamicCompliance = async () => {
 console.log('🔍 ComplianceChecklist fetchDynamicCompliance called with:', {
 propertyId,
 zoneCode,
 developmentType,
 flagEnabled: flags.newComplianceChecklist
 })

 if (!flags.newComplianceChecklist || !propertyId || !zoneCode || !developmentType) {
 setChecklistItems([]) // Don't show fake data when no address selected
 return
 }

 setLoading(true)
 setError(null)

 try {
 // Try enhanced compliance endpoint first
 const response = await fetch('/api/compliance/enhanced', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify({
 propertyId: propertyData?.propId || propertyId,
 zone: zoneCode,
 developmentType: developmentType,
 })
 })

 console.log('📡 Sending compliance request with development type:', developmentType)

 if (!response.ok) {
 // Fallback to authoritative endpoint
 const fallbackResponse = await fetch('/api/authoritative/compliance-check', {
 method: 'POST',
 headers: {
 'Content-Type': 'application/json',
 },
 body: JSON.stringify({
 zone_code: zoneCode,
 property_id: propertyId,
 development_type: developmentType,
 })
 })

 if (fallbackResponse.ok) {
 const data = await fallbackResponse.json()
 setChecklistItems(data.items || [])
 onComplianceUpdate?.(data)
 } else {
 throw new Error('Both compliance endpoints failed')
 }
 return
 }

 const data = await response.json()

 console.log('✅ Received compliance data for', developmentType, ':', {
 success: data.success,
 totalProvisions: data.data ? [
 ...(data.data.tier_1_provisions || []),
 ...(data.data.tier_2_provisions || []),
 ...(data.data.tier_3_provisions || []),
 ...(data.data.tier_4_provisions || []),
 ...(data.data.tier_5_provisions || [])
 ].length : 0,
 feasibilityStatus: data.data?.feasibility_check?.permission_status
 })

 // Transform API response to checklist format
 const dynamicItems = transformApiToChecklistItems(data.data || data)
 setChecklistItems(dynamicItems || [])
 onComplianceUpdate?.(data)

 } catch (err) {
 console.error('Failed to fetch dynamic compliance data:', err)
 setError(err instanceof Error ? err.message : 'Unknown error')
 // Fallback to empty array on error
 setChecklistItems([])
 } finally {
 setLoading(false)
 }
 }

 // Transform authoritative API response to checklist format
 const transformApiToChecklistItems = (apiData: any): ChecklistItem[] => {
 const items: ChecklistItem[] = []

 // Process each tier of provisions
 const allProvisions = [
 ...(apiData.tier_1_provisions || []),
 ...(apiData.tier_2_provisions || []),
 ...(apiData.tier_3_provisions || []),
 ...(apiData.tier_4_provisions || []),
 ...(apiData.tier_5_provisions || [])
 ]

 allProvisions.forEach((provision, index) => {
 const status = getComplianceStatus(provision)
 const requiresVariation = provision.tier_level >= 4 || status === 'non-compliant'

 items.push({
 id: `provision-${index + 1}`,
 title: getProvisionTitle(provision),
 clause: provision.clause_reference || 'Unknown',
 status: status,
 details: getProvisionDetails(provision),
 completed: status === 'compliant',
 requiresVariation,
 tierLevel: provision.tier_level,
 confidenceLevel: provision.confidence_level,
 documentType: provision.document_type,
 numericValue: provision.numeric_value,
 unit: provision.unit
 })
 })

 // Return empty array if no compliance data available
 if (items.length === 0) {
 return []
 }

 return items
 }

 const getComplianceStatus = (provision: any): "compliant" | "non-compliant" | "pending" => {
 // Tier 1 provisions with numeric values are likely enforceable
 if (provision.tier_level === 1 && provision.numeric_value) {
 return 'compliant'
 }

 // Higher tier provisions need assessment
 if (provision.tier_level >= 4) {
 return 'pending'
 }

 // Default based on confidence
 if (provision.confidence_level && provision.confidence_level > 0.8) {
 return 'compliant'
 }

 return 'pending'
 }

 const getProvisionTitle = (provision: any): string => {
 if (provision.measurement_context === 'height') return 'Height Limit'
 if (provision.measurement_context === 'fsr') return 'Floor Space Ratio'
 if (provision.measurement_context === 'setback') return 'Building Setbacks'
 if (provision.provision_type === 'land_use') return 'Permissibility'

 // Extract title from provision text or use document type
 const text = provision.provision_text || ''
 if (text.includes('lot size')) return 'Minimum Lot Size'
 if (text.includes('parking')) return 'Parking Requirements'
 if (text.includes('landscap')) return 'Landscaping'

 return provision.document_type === 'LEP' ? 'LEP Requirement' : 'DCP Requirement'
 }

 const getProvisionDetails = (provision: any): string => {
 let details = provision.provision_text || 'No details available'

 if (provision.numeric_value && provision.unit) {
 const formattedValue = provision.measurement_context === 'fsr'
 ? `${provision.numeric_value}:1 sq m`
 : `${provision.numeric_value}${provision.unit}`
 details = `${formattedValue}\n${details}`
 }

 return details.length > 150 ? details.substring(0, 150) + '...' : details
 }

 useEffect(() => {
 fetchDynamicCompliance()
 }, [propertyId, zoneCode, developmentType, flags.newComplianceChecklist])

 // Show empty state when no property selected or no checklist items
 if ((!propertyData && !flags.newComplianceChecklist) || checklistItems.length === 0) {
 return (
 <Card className="shadow-sm">
 <div className="p-6 text-center text-gray-500">
 <FileText className="h-8 w-8 mx-auto mb-2 text-gray-400" />
 <p>Select a property address and development type to see compliance requirements</p>
 </div>
 </Card>
 );
 }

 const completedItems = checklistItems.filter((item) => item.completed).length
 const totalItems = checklistItems.length
 const progressPercentage = totalItems > 0 ? Math.round((completedItems / totalItems) * 100) : 0

 const toggleExpanded = (itemId: string) => {
 setExpandedItems((prev) => (prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]))
 }

 const getStatusIcon = (item: ChecklistItem) => {
 if (item.completed) {
 return <CheckCircle2 className="h-4 w-4 text-green-600" />
 }
 return <Circle className="h-4 w-4 text-gray-400" />
 }

 const getStatusBadge = (status: ChecklistItem["status"]) => {
 switch (status) {
 case "compliant":
 return (
 <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gradient-to-b from-emerald-200 to-emerald-100 text-emerald-800">
 Compliant
 </span>
 )
 case "non-compliant":
 return (
 <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
 Non-compliant
 </span>
 )
 case "pending":
 return (
 <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
 Pending verification
 </span>
 )
 default:
 return null
 }
 }

 const getTierIcon = (tierLevel?: number) => {
 if (!tierLevel) return null

 switch (tierLevel) {
 case 1:
 return <Shield className="h-3 w-3 text-green-600" />
 case 2:
 return <FileText className="h-3 w-3 text-blue-600" />
 case 3:
 return <AlertTriangle className="h-3 w-3 text-orange-600" />
 default:
 return <Clock className="h-3 w-3 text-gray-600" />
 }
 }

 return (
 <Card className="shadow-sm">
 <div className="bg-gray-50 px-4 md:px-6 py-4 border-b">
 <div className="flex items-center gap-3 mb-3">
 <FileText className="h-5 w-5 text-gray-600" />
 <h3 className="text-base md:text-lg font-semibold text-gray-900">
 Compliance Checklist for {developmentType?.replace('_', ' ') || 'Development'}
 </h3>
 {flags.newComplianceChecklist && (
 <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded">Dynamic</span>
 )}
 </div>
 <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
 <span className="text-sm text-gray-600">
 Progress: {completedItems}/{totalItems} complete
 </span>
 <div className="flex-1 max-w-xs">
 <Progress value={progressPercentage} className="h-2" />
 </div>
 <span className="text-sm font-medium text-gray-900">{progressPercentage}%</span>
 </div>
 {error && (
 <div className="mt-2 text-xs text-red-600">
 Error loading dynamic data: {error}. Showing fallback data.
 </div>
 )}
 </div>

 <div className="max-h-96 overflow-y-auto">
 {loading ? (
 <div className="p-6 text-center">
 <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"></div>
 <p className="text-sm text-gray-500 mt-2">Loading compliance requirements...</p>
 </div>
 ) : (
 checklistItems.map((item, index) => {
 const isExpanded = expandedItems.includes(item.id)
 return (
 <div
 key={item.id}
 className={`border-b border-gray-200 transition-colors ${
 item.completed ? "bg-green-50/30" : ""
 } ${isExpanded ? "bg-blue-50/30" : "hover:bg-gray-50"}`}
 >
 <div className="p-4 md:p-6 cursor-pointer" onClick={() => toggleExpanded(item.id)}>
 <div className="flex items-start gap-4">
 <div className="mt-1">{getStatusIcon(item)}</div>

 <div className="flex-1">
 <div className="flex items-center justify-between">
 <div className="flex items-center gap-2">
 <h4 className="font-semibold text-gray-900 text-sm">
 {item.title} ({item.clause})
 </h4>
 {getTierIcon(item.tierLevel)}
 </div>
 {isExpanded ? (
 <ChevronUp className="h-4 w-4 text-gray-400" />
 ) : (
 <ChevronDown className="h-4 w-4 text-gray-400" />
 )}
 </div>

 <div className="flex items-center gap-2 mt-2">
 <span className="text-sm text-gray-600">Status:</span>
 {getStatusBadge(item.status)}
 {item.confidenceLevel && (
 <span className="text-xs text-gray-500">
 {Math.round(item.confidenceLevel * 100)}% confidence
 </span>
 )}
 </div>
 </div>
 </div>
 </div>

 {isExpanded && (
 <div className="px-4 md:px-6 pb-4 md:pb-6 ml-8">
 <div className="space-y-4">
 <div className="text-sm text-gray-700 leading-relaxed">
 <span className="font-medium">Details:</span> {item.details}
 </div>

 {item.tierLevel && (
 <div className="text-xs text-gray-500">
 <span className="font-medium">Authority Level:</span> Tier {item.tierLevel}
 {item.documentType && ` (${item.documentType})`}
 </div>
 )}

 {item.requiresVariation && (
 <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
 <div className="flex items-start gap-2">
 <AlertTriangle className="h-4 w-4 text-amber-600 mt-0.5 flex-shrink-0" />
 <div>
 <div className="text-sm font-medium text-amber-800">Variation may be required</div>
 <Button
 size="sm"
 className="mt-2 bg-gradient-to-b from-amber-700 to-amber-600 hover:from-amber-800 hover:to-amber-700 text-white text-xs"
 >
 Request Cl 4.6 Variation
 </Button>
 </div>
 </div>
 </div>
 )}

 {item.status === "pending" && (
 <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
 <Button
 size="sm"
 className="bg-gradient-to-b from-blue-700 to-blue-600 hover:from-blue-800 hover:to-blue-700 text-white text-xs"
 >
 Verify Compliance
 </Button>
 </div>
 )}

 <div className="flex flex-wrap gap-2 pt-2">
 <Button
 variant="outline"
 size="sm"
 className="text-xs bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white border-0"
 >
 <FileText className="h-3 w-3 mr-1" />
 View Full Provision
 </Button>
 <Button
 variant="outline"
 size="sm"
 className="text-xs bg-gradient-to-b from-emerald-800 to-emerald-600 hover:from-emerald-900 hover:to-emerald-700 text-white border-0"
 >
 <MessageSquare className="h-3 w-3 mr-1" />
 Add Note
 </Button>
 </div>
 </div>
 </div>
 )}
 </div>
 )
 })
 )}
 </div>
 </Card>
 )
}
