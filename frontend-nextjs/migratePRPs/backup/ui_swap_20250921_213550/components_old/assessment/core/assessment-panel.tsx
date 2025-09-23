import { DevelopmentSelector } from "@/components/development-selector"
import { ComplianceStatus } from "@/components/compliance-status"
import { ComplianceChecklist } from "@/components/compliance-checklist"
import { ActionBar } from "@/components/action-bar"

interface AssessmentPanelProps {
  developmentType: string
}

export function AssessmentPanel({ developmentType }: AssessmentPanelProps) {
  return (
    <div className="flex-1 bg-gray-50 flex flex-col">
      <div className="flex-1 p-8 overflow-y-auto">
        <div className="space-y-8">
          <DevelopmentSelector />
          <ComplianceStatus />
          <ComplianceChecklist />
        </div>
      </div>
      <ActionBar />
    </div>
  )
}
