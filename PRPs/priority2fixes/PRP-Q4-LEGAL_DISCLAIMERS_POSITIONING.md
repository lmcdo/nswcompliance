# PRP-Q4: Legal Disclaimers and Positioning

## OBJECTIVE
Strengthen legal positioning by adding clear disclaimers, removing "authoritative" claims, and positioning system as "regulation reference tool" to reduce liability exposure.

## SUCCESS CRITERIA
- [ ] Remove all "authoritative" language from APIs and frontend
- [ ] Add comprehensive legal disclaimers to all user-facing interfaces
- [ ] Implement data currency timestamps
- [ ] Add professional consultation requirements
- [ ] Create liability limitation framework
- [ ] Update all documentation with correct positioning

## TECHNICAL SPECIFICATION

### Phase Q4A: Disclaimer Framework
```typescript
interface LegalDisclaimer {
    disclaimer_type: 'general' | 'data_currency' | 'professional_advice' | 'liability';
    content: string;
    severity: 'info' | 'warning' | 'critical';
    required_display: boolean;
    last_updated: Date;
}

const LEGAL_DISCLAIMERS: LegalDisclaimer[] = [
    {
        disclaimer_type: 'general',
        content: 'This tool provides regulation reference only. It does not constitute professional planning advice or replace the need for qualified consultation.',
        severity: 'warning',
        required_display: true,
        last_updated: new Date()
    },
    {
        disclaimer_type: 'professional_advice',
        content: 'Professional planning advice from a qualified consultant is required for all development applications.',
        severity: 'critical',
        required_display: true,
        last_updated: new Date()
    }
];
```

### Phase Q4B: Data Currency Framework
```python
class DataCurrencyTracker:
    def get_data_freshness_info(self) -> Dict:
        """Get data currency information"""

        conn = sqlite3.connect('nsw_planning.db')
        cursor = conn.cursor()

        # Check document ages
        cursor.execute("""
        SELECT
            MIN(extraction_timestamp) as oldest_data,
            MAX(extraction_timestamp) as newest_data,
            COUNT(*) as total_documents
        FROM documents
        """)

        freshness = cursor.fetchone()

        return {
            'data_as_of': datetime.fromtimestamp(freshness[1]).isoformat(),
            'oldest_data_date': datetime.fromtimestamp(freshness[0]).isoformat(),
            'total_documents': freshness[2],
            'currency_warning': self.assess_data_currency(freshness[1])
        }

    def assess_data_currency(self, latest_timestamp: float) -> str:
        """Assess if data currency warning needed"""

        days_old = (time.time() - latest_timestamp) / 86400

        if days_old > 365:
            return "DATA OVER 1 YEAR OLD - VERIFY CURRENT REGULATIONS"
        elif days_old > 180:
            return "Data over 6 months old - recommend verification"
        elif days_old > 90:
            return "Data over 3 months old - check for recent amendments"
        else:
            return "Data reasonably current"
```

### Phase Q4C: Liability Limitation
```typescript
interface LiabilityFramework {
    system_limitations: string[];
    user_responsibilities: string[];
    recommended_professional_verification: string[];
    council_authority_acknowledgment: string;
}

const LIABILITY_FRAMEWORK: LiabilityFramework = {
    system_limitations: [
        "Text-based regulation retrieval only",
        "No spatial analysis or site-specific assessment",
        "Limited to Inner West Council area only",
        "Does not account for recent amendments or site-specific conditions"
    ],
    user_responsibilities: [
        "Verify all information with current regulations",
        "Consult qualified planning professional",
        "Check for recent amendments and site-specific overlays",
        "Confirm with relevant council before proceeding"
    ],
    recommended_professional_verification: [
        "All development applications",
        "Complex or commercial development",
        "Heritage or environmentally sensitive sites",
        "Any development requiring detailed assessment"
    ],
    council_authority_acknowledgment: "Only Council has authority to make binding development determinations"
};
```

## IMPLEMENTATION STEPS

### Step 1: Remove "Authoritative" Language (20 minutes)
```python
def remove_authoritative_language():
    """Remove authoritative claims from all interfaces"""

    # Files to update with language changes
    language_updates = [
        {
            'file': 'frontend-nextjs/app/api/authoritative/compliance-check/route.ts',
            'changes': [
                ('authoritative', 'reference'),
                ('Authoritative Compliance', 'Compliance Reference'),
                ('definitive assessment', 'guidance based on available data'),
                ('conclusive determination', 'preliminary assessment')
            ]
        },
        {
            'file': 'frontend-nextjs/components/compliance/AuthoritativeComplianceDisplay.tsx',
            'changes': [
                ('Authoritative', 'Reference'),
                ('definitive', 'indicative'),
                ('conclusive', 'preliminary')
            ]
        },
        {
            'file': 'services/enhanced_compliance_api.py',
            'changes': [
                ('authoritative guidance', 'regulation reference'),
                ('definitive compliance', 'compliance guidance')
            ]
        }
    ]

    for update in language_updates:
        apply_language_changes(update['file'], update['changes'])

    return len(language_updates)
```

### Step 2: Add Comprehensive Disclaimers (25 minutes)
```typescript
// Enhanced API responses with disclaimers
interface EnhancedComplianceResponse {
    // Existing response data
    zone: string;
    development_permissions?: DevelopmentPermissions;
    feasibility_check?: FeasibilityCheck;

    // NEW: Legal disclaimers and positioning
    legal_disclaimers: LegalDisclaimer[];
    data_currency: DataCurrencyInfo;
    system_limitations: string[];
    professional_advice_required: boolean;
}

// Disclaimer component for frontend
const LegalDisclaimerBanner: React.FC = () => {
    return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4 mb-6">
            <div className="flex items-start">
                <div className="flex-shrink-0">
                    <ExclamationTriangleIcon className="h-5 w-5 text-yellow-400" />
                </div>
                <div className="ml-3">
                    <h3 className="text-sm font-medium text-yellow-800">
                        Important: Regulation Reference Only
                    </h3>
                    <div className="mt-2 text-sm text-yellow-700">
                        <ul className="list-disc pl-5 space-y-1">
                            <li>This tool provides regulation reference only - not professional planning advice</li>
                            <li>Professional consultation required for all development applications</li>
                            <li>Verify all information with current regulations and Council</li>
                            <li>Data currency: {dataCurrency} - check for recent amendments</li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    );
};
```

### Step 3: Implement Data Currency Tracking (20 minutes)
```python
def implement_data_currency():
    """Add data currency tracking to all responses"""

    # Create data_currency table
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS data_currency (
        id INTEGER PRIMARY KEY,
        source_type TEXT NOT NULL,  -- 'sepp', 'lep', 'dcp'
        document_name TEXT,
        last_updated DATE,
        extraction_date DATE,
        currency_status TEXT,  -- 'current', 'aging', 'outdated'
        verification_required BOOLEAN DEFAULT FALSE
    )
    """)

    # Populate with current document dates
    cursor.execute("""
    INSERT OR REPLACE INTO data_currency
    (source_type, document_name, extraction_date, currency_status)
    SELECT
        CASE
            WHEN LOWER(pdf_name) LIKE '%sepp%' THEN 'sepp'
            WHEN LOWER(pdf_name) LIKE '%lep%' THEN 'lep'
            WHEN LOWER(pdf_name) LIKE '%dcp%' THEN 'dcp'
            ELSE 'other'
        END as source_type,
        pdf_name,
        DATE(extraction_timestamp, 'unixepoch'),
        CASE
            WHEN (julianday('now') - julianday(DATE(extraction_timestamp, 'unixepoch'))) > 365
            THEN 'outdated'
            WHEN (julianday('now') - julianday(DATE(extraction_timestamp, 'unixepoch'))) > 180
            THEN 'aging'
            ELSE 'current'
        END as currency_status
    FROM documents
    """)

    conn.commit()
    conn.close()

    return True
```

### Step 4: Update API Responses with Disclaimers (30 minutes)
```python
def enhance_api_with_disclaimers():
    """Add disclaimers to all API responses"""

    def add_legal_framework_to_response(response: Dict) -> Dict:
        """Add legal disclaimers to any API response"""

        # Get data currency info
        data_currency = DataCurrencyTracker().get_data_freshness_info()

        response['legal_disclaimers'] = [
            {
                'type': 'general',
                'message': 'REGULATION REFERENCE TOOL ONLY - Not professional planning advice',
                'severity': 'critical'
            },
            {
                'type': 'professional_advice',
                'message': 'Professional planning consultation required for all development applications',
                'severity': 'warning'
            },
            {
                'type': 'council_authority',
                'message': 'Only Council has authority to make binding development determinations',
                'severity': 'info'
            }
        ]

        response['data_currency'] = {
            'data_as_of': data_currency['data_as_of'],
            'currency_warning': data_currency['currency_warning'],
            'verification_required': True
        }

        response['system_limitations'] = [
            "Text-based regulation retrieval only",
            "No spatial analysis or site-specific assessment",
            "Limited to Inner West Council area",
            "Does not account for site-specific conditions or recent amendments"
        ]

        response['professional_verification_required'] = True

        return response

    # Update enhanced compliance API
    update_file(
        'services/enhanced_compliance_api.py',
        'response = json.loads(result.stdout.strip())',
        'response = add_legal_framework_to_response(json.loads(result.stdout.strip()))'
    )

    return True
```

### Step 5: Update Frontend with Clear Positioning (25 minutes)
```typescript
// Updated component with clear positioning
const ComplianceReferenceDisplay: React.FC = () => {
    const [acceptedDisclaimer, setAcceptedDisclaimer] = useState(false);

    if (!acceptedDisclaimer) {
        return (
            <DisclaimerAcceptanceModal
                onAccept={() => setAcceptedDisclaimer(true)}
            />
        );
    }

    return (
        <div className="space-y-6">
            <LegalDisclaimerBanner />

            <div className="bg-blue-50 border border-blue-200 rounded-md p-4">
                <h3 className="text-lg font-medium text-blue-900">
                    NSW Planning Regulation Reference
                </h3>
                <p className="text-sm text-blue-700 mt-1">
                    Text-based regulation search for Inner West Council area.
                    Professional planning advice required for all development applications.
                </p>
            </div>

            {/* Rest of compliance display */}
            <ComplianceResults />

            <ProfessionalAdviceReminder />
        </div>
    );
};

const ProfessionalAdviceReminder: React.FC = () => (
    <div className="bg-gray-50 border border-gray-200 rounded-md p-4 mt-6">
        <h4 className="font-medium text-gray-900">Next Steps</h4>
        <ul className="text-sm text-gray-600 mt-2 space-y-1">
            <li>• Consult a qualified planning professional</li>
            <li>• Verify information with current regulations</li>
            <li>• Check for recent amendments with Inner West Council</li>
            <li>• Consider site-specific conditions and constraints</li>
        </ul>
    </div>
);
```

## VERIFICATION CHECKLIST

### Language Updates
- [ ] All "authoritative" references removed
- [ ] "Compliance check" changed to "compliance reference"
- [ ] "Definitive" and "conclusive" language removed
- [ ] System positioned as "regulation reference tool"

### Disclaimer Implementation
- [ ] Legal disclaimers on all user interfaces
- [ ] Data currency warnings implemented
- [ ] Professional advice requirements clear
- [ ] Council authority acknowledgment present

### API Enhancement
- [ ] All API responses include disclaimers
- [ ] Data currency information provided
- [ ] System limitations documented
- [ ] Professional verification requirements stated

### Frontend Updates
- [ ] Disclaimer acceptance modal
- [ ] Clear system positioning
- [ ] Professional advice reminders
- [ ] Visual warning indicators

## DELIVERABLES

1. **legal_framework.ts** - Comprehensive disclaimer framework
2. **data_currency_tracker.py** - Data freshness monitoring
3. **updated_api_responses** - Enhanced with disclaimers
4. **disclaimer_components.tsx** - Frontend disclaimer components
5. **legal_positioning_report.md** - Documentation of changes

## ESTIMATED TIME
**2 hours total**
- Language updates: 20 minutes
- Disclaimer implementation: 25 minutes
- Data currency tracking: 20 minutes
- API enhancements: 30 minutes
- Frontend updates: 25 minutes

## COMPLETION CRITERIA
✅ All "authoritative" language removed
✅ Comprehensive disclaimers on all interfaces
✅ Data currency tracking implemented
✅ Professional advice requirements clear
✅ System positioned as reference tool only