import { NextApiRequest, NextApiResponse } from 'next';
import { ComplianceStatusState, ComplianceCheck } from '@/components/compliance/types';

// Mock compliance checks data
const generateMockChecks = (): ComplianceCheck[] => [
 {
 id: '1',
 provision: '4.6.1',
 requirement: 'Building height must not exceed 24m',
 status: 'compliant',
 severity: 'critical',
 evidence: [],
 recommendations: [],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
 {
 id: '2',
 provision: '4.6.2',
 requirement: 'Floor space ratio must not exceed 1.2:1',
 status: 'pending',
 severity: 'major',
 evidence: [],
 recommendations: ['Submit architectural plans for review'],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
 {
 id: '3',
 provision: '4.6.3',
 requirement: 'Minimum 3m front setback required',
 status: 'non-compliant',
 severity: 'major',
 evidence: [],
 recommendations: ['Adjust building placement to meet setback requirements'],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
 {
 id: '4',
 provision: '4.6.4',
 requirement: 'Minimum 20 parking spaces required',
 status: 'conditional',
 severity: 'minor',
 evidence: [],
 recommendations: ['Provide parking calculation based on development mix'],
 lastChecked: new Date(),
 autoCheckEnabled: true,
 },
];

function calculateComplianceStatus(checks: ComplianceCheck[]): ComplianceStatusState {
 const total = checks.length;
 const completed = checks.filter(check =>
 check.status !== 'pending' && check.status !== 'not-applicable'
 ).length;

 const criticalIssues = checks.filter(check =>
 check.severity === 'critical' && check.status === 'non-compliant'
 );

 const warnings = checks.filter(check =>
 check.status === 'conditional' ||
 (check.severity === 'major' && check.status === 'non-compliant')
 );

 const nonCompliantChecks = checks.filter(check => check.status === 'non-compliant');

 let overallStatus: ComplianceStatusState['overallStatus'];
 if (criticalIssues.length > 0) {
 overallStatus = 'fail';
 } else if (warnings.length > 0 || nonCompliantChecks.length > 0) {
 overallStatus = 'conditional';
 } else if (completed < total) {
 overallStatus = 'incomplete';
 } else {
 overallStatus = 'pass';
 }

 return {
 overallStatus,
 checks,
 progress: {
 completed,
 total,
 percentage: total > 0 ? Math.round((completed / total) * 100) : 0,
 },
 criticalIssues,
 warnings,
 lastUpdated: new Date(),
 autoRefreshEnabled: false,
 };
}

export default async function handler(
 req: NextApiRequest,
 res: NextApiResponse
) {
 try {
 if (req.method === 'POST') {
 // Initialize compliance status
 const { propertyId, developmentType } = req.body;

 if (!propertyId || !developmentType) {
 return res.status(400).json({ error: 'Property ID and development type required' });
 }

 const checks = generateMockChecks();
 const status = calculateComplianceStatus(checks);

 return res.status(200).json(status);
 }

 if (req.method === 'GET') {
 // Get current compliance status
 const checks = generateMockChecks();
 const status = calculateComplianceStatus(checks);

 return res.status(200).json(status);
 }

 res.status(405).json({ error: 'Method not allowed' });
 } catch (error) {
 console.error('Compliance status API error:', error);
 res.status(500).json({ error: 'Failed to process compliance status' });
 }
}
