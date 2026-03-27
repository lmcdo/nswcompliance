import { PropertyCard } from "@/components/property-card"
import { AssessmentContext } from "@/components/assessment-context"
import { QuickSearch } from "@/components/quick-search"

export function PropertyPanel(props: Record<string, any> = {}) {
 return (
 <div className="w-full md:w-[380px] lg:w-[320px] xl:w-[380px] bg-white border-r border-gray-100 p-6 overflow-y-auto">
 <div className="space-y-8">
 <div>
 <h2 className="text-xl font-semibold text-gray-900 mb-6">Property Information</h2>
 <PropertyCard />
 </div>
 <AssessmentContext />
 <QuickSearch />
 </div>
 </div>
 )
}
