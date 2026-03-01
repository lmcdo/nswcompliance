# Professional User Feedback System Design

## Executive Summary

**Target Users**: Council Certifiers, Town Planners, Developers
**Goal**: Capture data accuracy and workflow insights effortlessly
**Strategy**: Context-aware feedback capture at natural decision points

---

## 🎯 User Persona Analysis

### **Council Certifiers**
- **Workflow**: Verify compliance against specific DCP requirements
- **Pain Points**: Inaccurate setback calculations, missing precinct requirements
- **Focus Areas**: Technical accuracy, regulatory compliance
- **Usage Pattern**: Quick property lookups, detailed compliance analysis

### **Town Planners**
- **Workflow**: Assess development feasibility, identify constraints
- **Pain Points**: Incorrect zoning information, missing heritage items
- **Focus Areas**: Planning policy accuracy, development constraints
- **Usage Pattern**: Comprehensive property analysis, constraint identification

### **Developers**
- **Workflow**: Due diligence, feasibility assessment
- **Pain Points**: Wrong property boundaries, incorrect FSR calculations
- **Focus Areas**: Development potential, constraint identification
- **Usage Pattern**: Multiple property assessments, comparative analysis

---

## 🔍 Key Data Quality Issues to Capture

### **1. Address Resolution Errors**
- **NSW Planning API returns wrong address**
- **Geocoding accuracy issues**
- **Suburb/mapping inconsistencies**
- **Property boundary discrepancies**

### **2. Regulatory Data Gaps**
- **Missing DCP general requirements**
- **Incorrect precinct assignments**
- **Outdated planning controls**
- **Missing heritage or flood information**

### **3. Calculation Inaccuracies**
- **Incorrect setback calculations**
- **Wrong FSR or height limits**
- **Missing minimum lot sizes**
- **Inaccurate constraint boundaries**

---

## 💡 Feedback Capture Strategy

### **Principle: "Notice and Report"**
- **Capture feedback** at the moment professionals notice issues
- **Minimal disruption** to their workflow
- **Context-aware prompts** based on usage patterns
- **Quick, one-click feedback** with optional detailed input

---

## 🎨 UI Feedback System Design

### **1. Smart Feedback Buttons**
```typescript
// Context-aware feedback trigger
interface FeedbackTrigger {
  type: 'address_issue' | 'missing_data' | 'incorrect_calculation';
  context: {
    propertyAddress: string;
    section: string;
    currentValue: any;
    expectedValue?: any;
  };
  position: 'floating' | 'inline' | 'sidebar';
}
```

### **2. Implementation Pattern**
```typescript
// components/feedback/SmartFeedbackTrigger.tsx
export function SmartFeedbackTrigger({
  context,
  type,
  onFeedback
}: FeedbackTriggerProps) {
  const [isVisible, setIsVisible] = useState(false);

  // Show based on user interaction patterns
  useEffect(() => {
    const timer = setTimeout(() => {
      if (userInteractedWithSection(context.section)) {
        setIsVisible(true);
      }
    }, 3000); // Show after 3 seconds of interaction

    return () => clearTimeout(timer);
  }, [context]);

  if (!isVisible) return null;

  return (
    <div className="fixed bottom-4 right-4 bg-white rounded-lg shadow-lg p-4 max-w-sm z-50">
      <div className="flex items-center gap-2 mb-2">
        <AlertCircle className="h-4 w-4 text-orange-500" />
        <span className="text-sm font-medium">Notice something incorrect?</span>
      </div>

      <div className="text-xs text-gray-600 mb-3">
        {getFeedbackPrompt(type, context)}
      </div>

      <div className="flex gap-2">
        <button
          onClick={() => handleFeedback('incorrect_data', context)}
          className="px-3 py-1 bg-red-100 text-red-700 rounded text-xs hover:bg-red-200"
        >
          Data seems wrong
        </button>
        <button
          onClick={() => handleFeedback('missing_data', context)}
          className="px-3 py-1 bg-yellow-100 text-yellow-700 rounded text-xs hover:bg-yellow-200"
        >
          Missing information
        </button>
        <button
          onClick={() => setIsVisible(false)}
          className="px-3 py-1 bg-gray-100 text-gray-700 rounded text-xs hover:bg-gray-200"
        >
          All good
        </button>
      </div>
    </div>
  );
}
```

### **3. Context-Aware Prompts**
```typescript
// Smart prompts based on context
function getFeedbackPrompt(type: string, context: any): string {
  switch (type) {
    case 'address_issue':
      return `Is "${context.propertyAddress}" the correct address for this property?`;

    case 'missing_data':
      return `Are there missing ${context.section} requirements for this property?`;

    case 'incorrect_calculation':
      return `Do the ${context.section} calculations look correct?`;

    default:
      return 'Notice anything that needs attention?';
  }
}
```

---

## 📍 Strategic Feedback Capture Points

### **1. Property Address Resolution**
```typescript
// Trigger when address search completes
useEffect(() => {
  if (propertyData && nswPlanningResponse) {
    // Check for address mismatches
    const addressMismatch = detectAddressMismatch(
      userInput,
      nswPlanningResponse.address
    );

    if (addressMismatch.confidence < 0.8) {
      showFeedbackTrigger({
        type: 'address_issue',
        context: {
          propertyAddress: nswPlanningResponse.address,
          userInput,
          confidence: addressMismatch.confidence
        }
      });
    }
  }
}, [propertyData, nswPlanningResponse]);
```

### **2. Compliance Results Display**
```typescript
// Trigger when compliance results are shown
export function ComplianceResults({ results, propertyAddress }) {
  const [feedbackShown, setFeedbackShown] = useState(false);

  useEffect(() => {
    // Show feedback after user reviews results
    const timer = setTimeout(() => {
      if (!feedbackShown && results.length > 0) {
        setFeedbackShown(true);
      }
    }, 5000); // Give user time to review

    return () => clearTimeout(timer);
  }, [results, feedbackShown]);

  return (
    <div>
      {/* Compliance results */}
      <ComplianceDashboard results={results} />

      {/* Feedback prompt */}
      {feedbackShown && (
        <SmartFeedbackTrigger
          type="data_quality"
          context={{
            propertyAddress,
            section: 'compliance_results',
            resultCount: results.length
          }}
        />
      )}
    </div>
  );
}
```

### **3. Specific Requirement Sections**
```typescript
// Inline feedback for each requirement
export function RequirementCard({ requirement, propertyAddress }) {
  const [showFeedback, setShowFeedback] = useState(false);

  return (
    <Card className="mb-4">
      <CardContent>
        <div className="flex justify-between items-start">
          <div className="flex-1">
            <h4 className="font-medium">{requirement.title}</h4>
            <p className="text-sm text-gray-600">{requirement.text}</p>
          </div>

          {/* Subtle feedback trigger */}
          <button
            onClick={() => setShowFeedback(!showFeedback)}
            className="ml-2 p-1 text-gray-400 hover:text-gray-600"
            title="Report issue with this requirement"
          >
            <Flag className="h-4 w-4" />
          </button>
        </div>

        {/* Inline feedback form */}
        {showFeedback && (
          <RequirementFeedback
            requirement={requirement}
            propertyAddress={propertyAddress}
            onSubmit={() => setShowFeedback(false)}
          />
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 📊 Feedback Collection Architecture

### **1. Feedback API Endpoint**
```typescript
// app/api/feedback/submit/route.ts
export async function POST(request: Request) {
  const feedback = await request.json();

  // Validate feedback data
  const validatedFeedback = feedbackSchema.parse(feedback);

  // Store in database
  await db.query(`
    INSERT INTO user_feedback (
      user_type, property_address, feedback_type,
      section, issue_description, context_data,
      created_at
    ) VALUES ($1, $2, $3, $4, $5, $6, NOW())
  `, [
    validatedFeedback.userType,
    validatedFeedback.propertyAddress,
    validatedFeedback.type,
    validatedFeedback.section,
    validatedFeedback.description,
    JSON.stringify(validatedFeedback.context)
  ]);

  // Send notification to development team
  await sendSlackNotification(validatedFeedback);

  return Response.json({ success: true });
}
```

### **2. Feedback Database Schema**
```sql
CREATE TABLE user_feedback (
  id SERIAL PRIMARY KEY,
  user_type VARCHAR(50) NOT NULL, -- 'certifier', 'planner', 'developer'
  property_address TEXT NOT NULL,
  feedback_type VARCHAR(50) NOT NULL, -- 'address_issue', 'missing_data', 'incorrect_calculation'
  section VARCHAR(100), -- 'dcp_general', 'precinct_requirements', 'setbacks', etc.
  issue_description TEXT,
  context_data JSONB, -- Additional context for debugging
  user_agent TEXT,
  ip_address INET,
  created_at TIMESTAMP DEFAULT NOW(),
  resolved BOOLEAN DEFAULT FALSE,
  resolution_notes TEXT
);

CREATE INDEX idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX idx_feedback_section ON user_feedback(section);
CREATE INDEX idx_feedback_created ON user_feedback(created_at);
CREATE INDEX idx_feedback_property ON user_feedback(property_address);
```

### **3. Real-time Feedback Processing**
```typescript
// lib/feedback/processor.ts
export class FeedbackProcessor {
  async processFeedback(feedback: FeedbackData) {
    // Categorize and prioritize feedback
    const priority = this.calculatePriority(feedback);

    // Check for similar feedback
    const similarIssues = await this.findSimilarIssues(feedback);

    // Create development task if needed
    if (priority === 'high' || similarIssues.length >= 3) {
      await this.createDevelopmentTask(feedback, similarIssues);
    }

    // Update analytics
    await this.updateFeedbackAnalytics(feedback);
  }

  private calculatePriority(feedback: FeedbackData): 'high' | 'medium' | 'low' {
    // High priority: Address issues, missing critical data
    if (feedback.type === 'address_issue') return 'high';
    if (feedback.section === 'setbacks' || feedback.section === 'fsr') return 'high';

    // Medium priority: Missing requirements, calculation issues
    if (feedback.type === 'missing_data') return 'medium';
    if (feedback.type === 'incorrect_calculation') return 'medium';

    return 'low';
  }
}
```

---

## 📈 Analytics Dashboard for Development Team

### **1. Feedback Overview**
```typescript
// app/admin/feedback/page.tsx
export default function FeedbackDashboard() {
  const [feedback, setFeedback] = useState<FeedbackData[]>([]);
  const [analytics, setAnalytics] = useState<FeedbackAnalytics>();

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold mb-6">Professional User Feedback</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <MetricCard
          title="Total Feedback"
          value={analytics?.totalFeedback}
          change={analytics?.weeklyChange}
        />
        <MetricCard
          title="Address Issues"
          value={analytics?.addressIssues}
          change={analytics?.addressIssuesChange}
        />
        <MetricCard
          title="Data Gaps"
          value={analytics?.missingData}
          change={analytics?.missingDataChange}
        />
        <MetricCard
          title="Resolved Issues"
          value={analytics?.resolvedIssues}
          change={analytics?.resolvedChange}
        />
      </div>

      {/* Feedback by Type */}
      <div className="grid grid-cols-2 gap-6 mb-6">
        <FeedbackChart
          title="Feedback by Type"
          data={analytics?.byType}
        />
        <FeedbackChart
          title="Feedback by Section"
          data={analytics?.bySection}
        />
      </div>

      {/* Recent Feedback */}
      <FeedbackTable feedback={feedback} />
    </div>
  );
}
```

### **2. Prioritized Issue Tracking**
```typescript
// Components/feedback/IssueTracker.tsx
export function IssueTracker() {
  const [issues, setIssues] = useState<PrioritizedIssue[]>([]);

  return (
    <div className="space-y-4">
      {issues.map(issue => (
        <div key={issue.id} className="border rounded-lg p-4">
          <div className="flex justify-between items-start mb-2">
            <div>
              <h3 className="font-medium">{issue.title}</h3>
              <p className="text-sm text-gray-600">{issue.description}</p>
            </div>
            <span className={`px-2 py-1 rounded text-xs ${
              issue.priority === 'high' ? 'bg-red-100 text-red-700' :
              issue.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
              'bg-gray-100 text-gray-700'
            }`}>
              {issue.priority}
            </span>
          </div>

          <div className="flex gap-2 text-xs text-gray-500">
            <span>Reported by: {issue.userType}</span>
            <span>•</span>
            <span>{issue.reportCount} reports</span>
            <span>•</span>
            <span>{issue.timeAgo}</span>
          </div>
        </div>
      ))}
    </div>
  );
}
```

---

## 🎯 Implementation Priority

### **Phase 1: Core Feedback Collection (Week 1)**
1. **Smart feedback triggers** for address resolution
2. **Inline feedback buttons** for requirement cards
3. **Basic feedback API** with database storage
4. **Simple admin dashboard** for viewing feedback

### **Phase 2: Enhanced Analytics (Week 2)**
1. **Feedback categorization** and prioritization
2. **Trend analysis** and pattern detection
3. **Automated issue grouping** and deduplication
4. **Real-time notifications** for critical issues

### **Phase 3: Professional Optimization (Week 3)**
1. **User-specific feedback patterns**
2. **Workflow-optimized prompts**
3. **Advanced analytics** for professional insights
4. **Integration with development workflow**

---

## 📋 Success Metrics

### **User Engagement**
- **Feedback submission rate**: Target 15-20% of professional users
- **Completion rate**: Target 80% of initiated feedback submissions
- **User satisfaction**: Track through optional satisfaction surveys

### **Data Quality Improvement**
- **Issue resolution time**: Target < 48 hours for critical issues
- **Data accuracy improvement**: Measure through re-submission rates
- **Pattern identification**: Identify and fix systemic data issues

### **Professional Value**
- **Professional retention rate**: Track ongoing engagement
- **Referral rate**: Measure professional user recommendations
- **Case study collection**: Document successful corrections

---

## 🔧 Technical Implementation Checklist

### **Frontend Components**
- [ ] Smart feedback trigger component
- [ ] Inline feedback buttons
- [ ] Feedback form with validation
- [ ] Context-aware prompt system
- [ ] User preference management

### **Backend Infrastructure**
- [ ] Feedback API endpoints
- [ ] Database schema and indexes
- [ ] Feedback processing service
- [ ] Analytics aggregation
- [ ] Notification system

### **Admin Dashboard**
- [ ] Feedback overview and metrics
- [ ] Issue prioritization and tracking
- [ ] Trend analysis and reporting
- [ ] Bulk issue management
- [ ] Export functionality

---

## 🎨 Design Principles

### **Non-Obtrusive Design**
- **Passive prompts** that don't interrupt workflow
- **Contextual timing** based on user interaction patterns
- **Optional participation** with gentle reminders
- **Professional interface** matching the application's aesthetic

### **Effortless Participation**
- **One-click feedback** for common issues
- **Smart defaults** based on context
- **Progressive disclosure** for additional details
- **Mobile-optimized** for field use

### **Immediate Value**
- **Acknowledgment** of feedback submission
- **Transparency** about issue resolution
- **Follow-up** on reported issues
- **Professional recognition** for valuable contributions

---

*Last Updated: November 2025*
*Designed for Professional User Feedback Collection*