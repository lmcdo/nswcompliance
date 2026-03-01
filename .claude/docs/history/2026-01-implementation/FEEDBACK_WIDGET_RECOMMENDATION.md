# Professional Feedback Widget - Recommendation for Compliance Engine

## Executive Summary

For professional users (certifiers, town planners), I recommend **a custom-built, context-aware feedback widget** rather than generic solutions. This ensures:
- ✅ Captures **structured, actionable feedback** specific to planning compliance
- ✅ **Non-intrusive** expandable/collapsible design
- ✅ **Context retention** (what page, address, provision they're looking at)
- ✅ **Professional tone** matching certifier/planner expectations
- ✅ **Categorized feedback** (data accuracy, UI/UX, missing features, bugs)

---

## Recommended Solution: Custom Feedback Panel

### Why Custom vs. Off-the-Shelf?

| Aspect | Generic Widget (Hotjar, UserSnap) | Custom Widget |
|--------|-----------------------------------|---------------|
| Context awareness | ❌ Generic "page feedback" | ✅ Knows property address, provision, DCP section |
| Professional tone | ❌ Consumer-focused | ✅ Tailored to certifiers/planners |
| Structured data | ⚠️ Free-form text only | ✅ Categorized + structured |
| Integration | ⚠️ 3rd party dependency | ✅ Native to your app |
| Cost | 💰 $80-300/month | ✅ Free (build once) |
| Data ownership | ⚠️ Stored externally | ✅ Your database |

---

## Design Specification

### Visual Design

**Collapsed State** (default):
```
┌─────────────────────────────────────┐
│                                     │
│    [Main Application Content]       │
│                                     │
│                                     │
└─────────────────────────────────────┘
                                    ┌──┐
                                    │💬│ ← Floating button
                                    │  │   (bottom-right)
                                    └──┘
```

**Expanded State**:
```
┌─────────────────────────────────────┐
│                                     │
│    [Main Application Content]       │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ 📝 Share Your Feedback    [×]│  │
│  ├──────────────────────────────┤  │
│  │ As a professional user,      │  │
│  │ your insights help improve   │  │
│  │ this tool for certifiers.    │  │
│  │                              │  │
│  │ Feedback Type:               │  │
│  │ ○ Data Accuracy Issue        │  │
│  │ ○ Missing Information        │  │
│  │ ○ Feature Request            │  │
│  │ ○ UI/UX Improvement          │  │
│  │ ○ Bug Report                 │  │
│  │ ○ General Comment            │  │
│  │                              │  │
│  │ Your Feedback:               │  │
│  │ ┌──────────────────────────┐ │  │
│  │ │                          │ │  │
│  │ │ [Text area]              │ │  │
│  │ │                          │ │  │
│  │ └──────────────────────────┘ │  │
│  │                              │  │
│  │ [Optional] Email:            │  │
│  │ [____________________]       │  │
│  │                              │  │
│  │        [Submit Feedback]     │  │
│  └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

### Professional Tone

**Copy should be formal, not casual:**

❌ "Hey! Got feedback? We'd love to hear from you! 😊"
✅ "Share Your Professional Feedback"

❌ "Tell us what you think!"
✅ "As a professional user, your insights help us improve compliance accuracy."

---

## Implementation Plan

### Tech Stack (React + Next.js)

**Component Structure:**
```
frontend-nextjs/
├── components/
│   └── feedback/
│       ├── FeedbackWidget.tsx          # Main widget component
│       ├── FeedbackButton.tsx          # Floating button
│       ├── FeedbackPanel.tsx           # Expandable panel
│       └── FeedbackConfirmation.tsx    # Success message
├── app/
│   └── api/
│       └── feedback/
│           └── route.ts                # POST /api/feedback endpoint
└── lib/
    └── types/
        └── feedback.ts                 # TypeScript types
```

### Features

#### 1. Context Awareness ⭐ KEY FEATURE

Automatically captures:
```typescript
{
  // User context
  userEmail: "optional@example.com",
  timestamp: "2025-11-08T21:30:00Z",

  // Page context
  page: "/assessment",
  url: "http://localhost:3000/assessment?address=180%20Addison",

  // Property context (if on assessment page)
  propertyAddress: "180 Addison Road, Marrickville NSW 2204",
  propertyCoordinates: [-33.9089, 151.1537],
  zoningData: "R3 Medium Density Residential",

  // Provision context (if viewing a specific provision)
  provisionId: 12345,
  provisionTitle: "Building Height - Maximum 12m",
  provisionSource: "Marrickville DCP 2011, Part 4.2.3",

  // User feedback
  feedbackType: "Data Accuracy Issue",
  feedbackText: "The setback shown is incorrect for R3 zones...",

  // Technical context
  browserInfo: "Chrome 120.0.0 on Windows 11",
  screenResolution: "1920x1080"
}
```

This context is **gold** for understanding feedback without back-and-forth.

#### 2. Structured Feedback Types

Professional users think in categories:

**Data Accuracy Issue**
- "The FSR shown is incorrect"
- "Missing DCP provision for my zone"
- "Setback calculation doesn't match DCP"

**Missing Information**
- "Need heritage overlay data"
- "Missing parking requirements"
- "No information on minimum lot size"

**Feature Request**
- "Add ability to export report as PDF"
- "Need comparison view for multiple properties"
- "Add calculator for site coverage"

**UI/UX Improvement**
- "Hard to find the setback requirements"
- "Text is too small on mobile"
- "Confusing navigation between DCP sections"

**Bug Report**
- "Page crashes when I select R4 zone"
- "Search doesn't work for street numbers"
- "Map doesn't load"

**General Comment**
- "Great tool, saving me hours!"
- "Would like to see more councils added"

#### 3. Smart Defaults

Pre-fill what you can:
```typescript
// Example: User is viewing setback requirement
<FeedbackWidget
  suggestedType="Data Accuracy Issue"
  contextHint="Regarding: Front setback 6m for R3 zone"
/>
```

#### 4. Non-Intrusive Design

**Behavior:**
- ✅ Collapsed by default (floating button bottom-right)
- ✅ Smooth slide-in animation (300ms)
- ✅ Dismissible with X button or ESC key
- ✅ Doesn't cover critical UI elements
- ✅ Persists across page navigation (stays collapsed)
- ✅ "Sticky" - follows scroll on long pages

**Accessibility:**
- ✅ Keyboard navigable (Tab, Enter, ESC)
- ✅ Screen reader friendly (ARIA labels)
- ✅ High contrast mode support
- ✅ Large touch targets (44px minimum)

---

## Component Code (React + TypeScript)

### 1. Feedback Widget Component

**`frontend-nextjs/components/feedback/FeedbackWidget.tsx`**

```typescript
'use client';

import { useState } from 'react';
import { MessageCircle, X, Send } from 'lucide-react';
import { usePathname } from 'next/navigation';

interface FeedbackWidgetProps {
  propertyAddress?: string;
  provisionContext?: {
    id: number;
    title: string;
    source: string;
  };
}

type FeedbackType =
  | 'data_accuracy'
  | 'missing_info'
  | 'feature_request'
  | 'ui_ux'
  | 'bug_report'
  | 'general';

export default function FeedbackWidget({
  propertyAddress,
  provisionContext
}: FeedbackWidgetProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [feedbackType, setFeedbackType] = useState<FeedbackType>('general');
  const [feedbackText, setFeedbackText] = useState('');
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const pathname = usePathname();

  const feedbackTypes = [
    { value: 'data_accuracy', label: 'Data Accuracy Issue', icon: '🎯' },
    { value: 'missing_info', label: 'Missing Information', icon: '📋' },
    { value: 'feature_request', label: 'Feature Request', icon: '💡' },
    { value: 'ui_ux', label: 'UI/UX Improvement', icon: '🎨' },
    { value: 'bug_report', label: 'Bug Report', icon: '🐛' },
    { value: 'general', label: 'General Comment', icon: '💬' },
  ];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      const response = await fetch('/api/feedback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          feedbackType,
          feedbackText,
          email: email || null,
          context: {
            page: pathname,
            url: window.location.href,
            propertyAddress,
            provisionContext,
            timestamp: new Date().toISOString(),
            browserInfo: navigator.userAgent,
            screenResolution: `${window.screen.width}x${window.screen.height}`,
          },
        }),
      });

      if (response.ok) {
        setSubmitted(true);
        setTimeout(() => {
          setIsOpen(false);
          setSubmitted(false);
          setFeedbackText('');
          setEmail('');
          setFeedbackType('general');
        }, 3000);
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 flex items-center gap-2 bg-blue-600 text-white px-4 py-3 rounded-full shadow-lg hover:bg-blue-700 transition-all hover:scale-105"
        aria-label="Open feedback panel"
      >
        <MessageCircle size={20} />
        <span className="font-medium">Feedback</span>
      </button>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-96 bg-white rounded-lg shadow-2xl border border-gray-200 animate-slide-in">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          <MessageCircle size={20} className="text-blue-600" />
          <h3 className="font-semibold text-gray-900">Share Your Feedback</h3>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-400 hover:text-gray-600 transition-colors"
          aria-label="Close feedback panel"
        >
          <X size={20} />
        </button>
      </div>

      {/* Content */}
      <div className="p-4">
        {submitted ? (
          <div className="py-8 text-center">
            <div className="text-green-600 text-5xl mb-3">✓</div>
            <h4 className="font-semibold text-gray-900 mb-2">Thank You!</h4>
            <p className="text-sm text-gray-600">
              Your feedback helps improve compliance accuracy for all professionals.
            </p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Context Display (if available) */}
            {(propertyAddress || provisionContext) && (
              <div className="bg-blue-50 border border-blue-200 rounded-md p-3 text-xs">
                <p className="font-medium text-blue-900 mb-1">Context:</p>
                {propertyAddress && (
                  <p className="text-blue-700">📍 {propertyAddress}</p>
                )}
                {provisionContext && (
                  <p className="text-blue-700 mt-1">
                    📋 {provisionContext.title}
                  </p>
                )}
              </div>
            )}

            {/* Intro Text */}
            <p className="text-sm text-gray-600">
              As a professional user, your insights help us improve this tool for certifiers and planners.
            </p>

            {/* Feedback Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Feedback Type
              </label>
              <div className="space-y-2">
                {feedbackTypes.map((type) => (
                  <label
                    key={type.value}
                    className="flex items-center gap-2 p-2 rounded border border-gray-200 hover:bg-gray-50 cursor-pointer transition-colors"
                  >
                    <input
                      type="radio"
                      name="feedbackType"
                      value={type.value}
                      checked={feedbackType === type.value}
                      onChange={(e) => setFeedbackType(e.target.value as FeedbackType)}
                      className="text-blue-600 focus:ring-blue-500"
                    />
                    <span className="text-lg">{type.icon}</span>
                    <span className="text-sm text-gray-700">{type.label}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Feedback Text */}
            <div>
              <label
                htmlFor="feedbackText"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Your Feedback
              </label>
              <textarea
                id="feedbackText"
                value={feedbackText}
                onChange={(e) => setFeedbackText(e.target.value)}
                placeholder="Please describe your feedback in detail..."
                required
                rows={4}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
            </div>

            {/* Optional Email */}
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-2"
              >
                Email (optional - for follow-up)
              </label>
              <input
                type="email"
                id="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="your.email@example.com"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 text-sm"
              />
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting || !feedbackText.trim()}
              className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-medium"
            >
              {isSubmitting ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Submitting...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Submit Feedback
                </>
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
```

### 2. API Endpoint

**`frontend-nextjs/app/api/feedback/route.ts`**

```typescript
import { NextRequest, NextResponse } from 'next/server';
import { Pool } from 'pg';

// Database connection
const pool = new Pool({
  host: process.env.DB_HOST || 'localhost',
  database: process.env.DB_NAME || 'nsw_planning',
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'postgres',
  port: parseInt(process.env.DB_PORT || '5432'),
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const {
      feedbackType,
      feedbackText,
      email,
      context,
    } = body;

    // Validate required fields
    if (!feedbackType || !feedbackText) {
      return NextResponse.json(
        { error: 'Missing required fields' },
        { status: 400 }
      );
    }

    // Insert feedback into database
    const query = `
      INSERT INTO user_feedback (
        feedback_type,
        feedback_text,
        email,
        page,
        url,
        property_address,
        provision_id,
        provision_title,
        provision_source,
        browser_info,
        screen_resolution,
        context_data,
        created_at
      ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
      RETURNING id;
    `;

    const values = [
      feedbackType,
      feedbackText,
      email || null,
      context.page || null,
      context.url || null,
      context.propertyAddress || null,
      context.provisionContext?.id || null,
      context.provisionContext?.title || null,
      context.provisionContext?.source || null,
      context.browserInfo || null,
      context.screenResolution || null,
      JSON.stringify(context),
    ];

    const result = await pool.query(query, values);

    return NextResponse.json(
      {
        success: true,
        feedbackId: result.rows[0].id,
        message: 'Feedback submitted successfully'
      },
      { status: 201 }
    );
  } catch (error) {
    console.error('Error saving feedback:', error);
    return NextResponse.json(
      { error: 'Failed to save feedback' },
      { status: 500 }
    );
  }
}
```

### 3. Database Schema

**`create_feedback_table.sql`**

```sql
CREATE TABLE IF NOT EXISTS user_feedback (
  id SERIAL PRIMARY KEY,

  -- Feedback content
  feedback_type VARCHAR(50) NOT NULL CHECK (
    feedback_type IN (
      'data_accuracy',
      'missing_info',
      'feature_request',
      'ui_ux',
      'bug_report',
      'general'
    )
  ),
  feedback_text TEXT NOT NULL,
  email VARCHAR(255),

  -- Page context
  page VARCHAR(500),
  url TEXT,

  -- Property context
  property_address TEXT,

  -- Provision context
  provision_id INTEGER,
  provision_title TEXT,
  provision_source TEXT,

  -- Technical context
  browser_info TEXT,
  screen_resolution VARCHAR(50),

  -- Full context JSON
  context_data JSONB,

  -- Status tracking
  status VARCHAR(20) DEFAULT 'new' CHECK (
    status IN ('new', 'reviewed', 'in_progress', 'resolved', 'archived')
  ),
  internal_notes TEXT,
  assigned_to VARCHAR(255),

  -- Timestamps
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW(),
  resolved_at TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_feedback_type ON user_feedback(feedback_type);
CREATE INDEX idx_feedback_status ON user_feedback(status);
CREATE INDEX idx_feedback_created ON user_feedback(created_at DESC);
CREATE INDEX idx_feedback_property ON user_feedback(property_address);

-- Full-text search on feedback
CREATE INDEX idx_feedback_text_search ON user_feedback USING gin(to_tsvector('english', feedback_text));

COMMENT ON TABLE user_feedback IS 'Stores user feedback from professional users (certifiers, planners)';
COMMENT ON COLUMN user_feedback.context_data IS 'Full JSON context for debugging and analysis';
```

### 4. CSS Animation

**`frontend-nextjs/app/globals.css`** (add this)

```css
@keyframes slide-in {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
```

---

## Integration with Assessment Page

**`frontend-nextjs/app/assessment/page.tsx`** (add widget)

```typescript
import FeedbackWidget from '@/components/feedback/FeedbackWidget';

export default function AssessmentPage() {
  // ... existing code ...

  const [selectedProperty, setSelectedProperty] = useState<Property | null>(null);
  const [activeProvision, setActiveProvision] = useState<Provision | null>(null);

  return (
    <div>
      {/* ... existing assessment UI ... */}

      {/* Feedback Widget - always visible */}
      <FeedbackWidget
        propertyAddress={selectedProperty?.address}
        provisionContext={activeProvision ? {
          id: activeProvision.id,
          title: activeProvision.title,
          source: activeProvision.source,
        } : undefined}
      />
    </div>
  );
}
```

---

## Admin Dashboard for Reviewing Feedback

**`frontend-nextjs/app/admin/feedback/page.tsx`**

```typescript
'use client';

import { useEffect, useState } from 'react';

interface Feedback {
  id: number;
  feedback_type: string;
  feedback_text: string;
  email: string | null;
  property_address: string | null;
  provision_title: string | null;
  status: string;
  created_at: string;
}

export default function FeedbackAdminPage() {
  const [feedback, setFeedback] = useState<Feedback[]>([]);
  const [filter, setFilter] = useState<string>('all');

  useEffect(() => {
    fetchFeedback();
  }, [filter]);

  const fetchFeedback = async () => {
    const params = filter !== 'all' ? `?type=${filter}` : '';
    const response = await fetch(`/api/admin/feedback${params}`);
    const data = await response.json();
    setFeedback(data);
  };

  const feedbackTypeLabels: Record<string, string> = {
    data_accuracy: 'Data Accuracy',
    missing_info: 'Missing Info',
    feature_request: 'Feature Request',
    ui_ux: 'UI/UX',
    bug_report: 'Bug Report',
    general: 'General',
  };

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">User Feedback Dashboard</h1>

      {/* Filters */}
      <div className="mb-6 flex gap-2">
        <button
          onClick={() => setFilter('all')}
          className={`px-4 py-2 rounded ${filter === 'all' ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
        >
          All
        </button>
        {Object.entries(feedbackTypeLabels).map(([value, label]) => (
          <button
            key={value}
            onClick={() => setFilter(value)}
            className={`px-4 py-2 rounded ${filter === value ? 'bg-blue-600 text-white' : 'bg-gray-200'}`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Feedback List */}
      <div className="space-y-4">
        {feedback.map((item) => (
          <div key={item.id} className="bg-white border rounded-lg p-4 shadow-sm">
            <div className="flex items-start justify-between mb-2">
              <div>
                <span className="inline-block px-3 py-1 bg-blue-100 text-blue-800 text-xs font-medium rounded-full">
                  {feedbackTypeLabels[item.feedback_type]}
                </span>
                {item.property_address && (
                  <span className="ml-2 text-sm text-gray-600">
                    📍 {item.property_address}
                  </span>
                )}
              </div>
              <span className="text-xs text-gray-500">
                {new Date(item.created_at).toLocaleDateString()}
              </span>
            </div>

            {item.provision_title && (
              <p className="text-sm text-gray-600 mb-2">
                <strong>Regarding:</strong> {item.provision_title}
              </p>
            )}

            <p className="text-gray-800 mb-3">{item.feedback_text}</p>

            {item.email && (
              <p className="text-sm text-gray-600">
                <strong>Contact:</strong> {item.email}
              </p>
            )}

            <div className="mt-3 pt-3 border-t flex gap-2">
              <select className="text-sm border rounded px-2 py-1">
                <option value="new">New</option>
                <option value="reviewed">Reviewed</option>
                <option value="in_progress">In Progress</option>
                <option value="resolved">Resolved</option>
              </select>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

---

## Alternative: Third-Party Solutions (If You Prefer)

### Option 1: Canny (Best for Feature Requests)
**URL**: https://canny.io
**Cost**: $50-400/month
**Pros**:
- ✅ Voting system (users upvote features)
- ✅ Public roadmap
- ✅ Changelog integration
**Cons**:
- ❌ Not context-aware
- ❌ Consumer-focused UI
- ❌ Expensive for beta

### Option 2: Hotjar (Best for General Feedback)
**URL**: https://www.hotjar.com
**Cost**: $32-80/month
**Pros**:
- ✅ Heatmaps + session recording
- ✅ Easy setup
**Cons**:
- ❌ Not professional-focused
- ❌ Generic feedback forms
- ❌ No structured categorization

### Option 3: UserVoice (Professional Focused)
**URL**: https://www.uservoice.com
**Cost**: Contact sales ($$$$)
**Pros**:
- ✅ B2B focused
- ✅ Feedback management
**Cons**:
- ❌ Very expensive
- ❌ Overkill for beta testing

---

## Recommendation Summary

### ✅ Build the Custom Widget

**Why:**
1. **Context awareness** - Automatically captures property, provision, DCP context
2. **Professional tone** - Matches certifier/planner expectations
3. **Structured data** - Categorized feedback you can action
4. **Free** - No monthly fees
5. **Full control** - Your database, your analytics
6. **Lightweight** - 1 component, 1 API route

**Implementation Time**: 4-6 hours

**Cost**: $0/month (vs. $50-300/month for 3rd party)

**ROI**: Priceless insights into how professionals use your tool

---

## Next Steps

1. ✅ **Create database table** - Run `create_feedback_table.sql`
2. ✅ **Build widget component** - Copy code above
3. ✅ **Create API endpoint** - Set up POST /api/feedback
4. ✅ **Integrate into assessment page** - Add `<FeedbackWidget />`
5. ✅ **Test with stakeholders** - Get early feedback on the feedback widget!
6. ✅ **Build admin dashboard** - Review and action feedback

**Want me to implement this now?**
