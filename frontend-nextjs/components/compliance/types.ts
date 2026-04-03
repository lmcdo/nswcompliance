export interface ComplianceItem {
 id: string;
 title: string;
 description: string;
 status: 'pending' | 'compliant' | 'non-compliant' | 'not-applicable';
 tier: 'tier1' | 'tier2' | 'tier3';
 authority: string;
 confidence: number;
 evidence?: string[];
 requirements?: string[];
}

export interface ComplianceCheck {
 id: string;
 provision: string;
 requirement: string;
 status: 'compliant' | 'non-compliant' | 'conditional' | 'not-applicable' | 'pending';
 severity: 'critical' | 'major' | 'minor' | 'informational';
 result?: any;
 evidence?: Evidence[];
 recommendations?: string[];
 lastChecked: Date;
 autoCheckEnabled: boolean;
}

export interface Evidence {
 id: string;
 type: 'document' | 'calculation' | 'measurement' | 'photo' | 'drawing' | 'certificate';
 title: string;
 description?: string;
 fileUrl?: string;
 metadata: Record<string, any>;
 uploadedAt: Date;
 uploadedBy: string;
 verified: boolean;
}

export interface ComplianceStatusState {
 overallStatus: 'pass' | 'fail' | 'conditional' | 'incomplete' | 'not-started';
 checks: ComplianceCheck[];
 progress: {
 completed: number;
 total: number;
 percentage: number;
 };
 criticalIssues: ComplianceCheck[];
 warnings: ComplianceCheck[];
 lastUpdated: Date;
 autoRefreshEnabled: boolean;
}

export interface ComplianceStatusProps {
 propertyId: string;
 developmentType: any;
 assessmentId?: string;
 showDetails?: boolean;
 autoRefresh?: boolean;
 onStatusChange?: (status: ComplianceStatusState) => void;
 variant?: 'full' | 'summary' | 'minimal';
 groupBy?: 'category' | 'severity' | 'status' | 'provision';
}

export interface ComplianceUpdate {
 type: 'status_change' | 'check_complete' | 'error';
 checkId?: string;
 status?: ComplianceCheck['status'];
 message?: string;
 timestamp: Date;
}
