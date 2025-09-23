import { CheckCircle, AlertTriangle, XCircle } from "lucide-react"
import { Card } from "@/components/ui/card"

export function ComplianceStatus() {
 const statusItems = [
 {
 icon: CheckCircle,
 title: "Permissible",
 description: "Dual occupancy permitted in R2",
 status: "success",
 },
 {
 icon: AlertTriangle,
 title: "Height Limit",
 description: "9.5m maximum\nCheck plans",
 status: "warning",
 },
 {
 icon: XCircle,
 title: "Setback",
 description: "Front: 3m\nRequired: 4m\nNon-compliant",
 status: "error",
 },
 {
 icon: CheckCircle,
 title: "FSR",
 description: "0.45:1 sq m\nMax: 0.6:1 sq m\nCompliant",
 status: "success",
 },
 ]

 const getStatusStyles = (status: string) => {
 switch (status) {
 case "success":
 // Updated success status to use gradient background
 return "bg-gradient-to-b from-emerald-100 to-emerald-50 border-emerald-200 text-emerald-800"
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
 return "text-emerald-600"
 case "warning":
 return "text-amber-600"
 case "error":
 return "text-red-600"
 default:
 return "text-gray-600"
 }
 }

 return (
 <Card className="p-6 border-l-4 border-l-emerald-700 shadow-sm">
 <h3 className="font-semibold text-gray-900 mb-5 text-lg">Quick Compliance Status</h3>
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
 </Card>
 )
}
