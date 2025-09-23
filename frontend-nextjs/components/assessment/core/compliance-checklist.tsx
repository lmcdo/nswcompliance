"use client"

import { useState } from "react"
import { CheckCircle2, Circle, AlertTriangle, FileText, MessageSquare, ChevronDown, ChevronUp } from "lucide-react"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"

interface ChecklistItem {
 id: string
 title: string
 clause: string
 status: "compliant" | "non-compliant" | "pending"
 details: string
 completed: boolean
 requiresVariation?: boolean
}

export function ComplianceChecklist() {
 const [expandedItems, setExpandedItems] = useState<string[]>(["1", "2"])

 const checklistItems: ChecklistItem[] = [
 {
 id: "1",
 title: "Permissibility",
 clause: "LEP Clause 2.3",
 status: "compliant",
 details: "Dual occupancy is permitted with consent in Zone R2",
 completed: true,
 },
 {
 id: "2",
 title: "Minimum Lot Size",
 clause: "LEP Cl 4.1",
 status: "non-compliant",
 details: "Lot is 208m², minimum 400m² required for dual occupancy",
 completed: false,
 requiresVariation: true,
 },
 {
 id: "3",
 title: "Height Limit",
 clause: "LEP Clause 4.3",
 status: "pending",
 details: "Maximum: 9.5m",
 completed: false,
 },
 {
 id: "4",
 title: "Floor Space Ratio",
 clause: "LEP Clause 4.4",
 status: "compliant",
 details: "Proposed: 0.45:1, Maximum: 0.6:1",
 completed: true,
 },
 {
 id: "5",
 title: "Building Setbacks",
 clause: "DCP Section 3.1",
 status: "non-compliant",
 details: "Front setback: 3m provided, 4m required",
 completed: false,
 },
 {
 id: "6",
 title: "Landscaping",
 clause: "DCP Section 4.2",
 status: "pending",
 details: "Minimum 25% of site area required",
 completed: false,
 },
 {
 id: "7",
 title: "Parking Requirements",
 clause: "DCP Section 5.1",
 status: "pending",
 details: "2 spaces required per dwelling",
 completed: false,
 },
 ]

 const completedItems = checklistItems.filter((item) => item.completed).length
 const totalItems = checklistItems.length
 const progressPercentage = Math.round((completedItems / totalItems) * 100)

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

 return (
 <Card className="shadow-sm">
 <div className="bg-gray-50 px-4 md:px-6 py-4 border-b">
 <div className="flex items-center gap-3 mb-3">
 <FileText className="h-5 w-5 text-gray-600" />
 <h3 className="text-base md:text-lg font-semibold text-gray-900">Compliance Checklist for Dual Occupancy</h3>
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
 </div>

 <div className="max-h-96 overflow-y-auto">
 {checklistItems.map((item, index) => {
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
 <h4 className="font-semibold text-gray-900 text-sm">
 {item.title} ({item.clause})
 </h4>
 {isExpanded ? (
 <ChevronUp className="h-4 w-4 text-gray-400" />
 ) : (
 <ChevronDown className="h-4 w-4 text-gray-400" />
 )}
 </div>

 <div className="flex items-center gap-2 mt-2">
 <span className="text-sm text-gray-600">Status:</span>
 {getStatusBadge(item.status)}
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
 Enter Actual Height
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
 })}
 </div>
 </Card>
 )
}
