import { PropertyCard } from "@/components/property-card"
import { AssessmentContext } from "@/components/assessment-context"
import { QuickSearch } from "@/components/quick-search"
import { PropertyDetailsComprehensive } from "@/components/property-details-comprehensive"

export function PropertyPanel() {
 return (
 <div className="w-full bg-gray-50 border-r border-gray-200 overflow-y-auto h-full">
 <div className="p-6 space-y-6">
 <div>
 <h2 className="text-xl font-semibold text-gray-900 mb-4">Property Information</h2>
 <PropertyCard />
 </div>
 <AssessmentContext />
 <PropertyDetailsComprehensive />
 <QuickSearch />
 </div>
 </div>
 )
}
