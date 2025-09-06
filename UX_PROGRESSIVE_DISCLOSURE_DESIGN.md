# UX PROGRESSIVE DISCLOSURE DESIGN
## NSW Planning Compliance Engine - Enhanced Assessment Flow

### DESIGN PROBLEM
**User Journey**: Address entered → Property data displayed → **ONE BUTTON** → Complex regulatory data
**Challenge**: Present database-driven setbacks, connected requirements, visual content, and page citations while maintaining ease of use and maximum utility.

---

## RECOMMENDED UX FLOW: "SMART LAYERS" PATTERN

### **INITIAL STATE: Single Action Button**
```
┌─────────────────────────────────────────────┐
│  🏠 123 Smith St, Marrickville              │
│  📍 R2 Zone • Inner West LGA • 8.5m Height │
│                                             │
│  ┌─────────────────────────────────────────┐ │
│  │  🔍 GET COMPLETE ASSESSMENT             │ │
│  │  Enhanced setbacks + requirements       │ │
│  └─────────────────────────────────────────┘ │
└─────────────────────────────────────────────┘
```

### **LAYER 1: IMMEDIATE VALUE (3 seconds to load)**
**Design Philosophy**: Give instant, actionable answers first

```
┌─────────────────────────────────────────────────────────────────────┐
│  ✅ ASSESSMENT COMPLETE                                             │
│                                                                     │
│  📐 SETBACKS (HIGH CONFIDENCE)          🔗 NEXT STEPS              │
│  ┌─────────────────────────┐            ┌─────────────────────────┐ │
│  │ Front: 6.0m             │            │ Height: Check 8.5m limit│ │
│  │ Side:  1.4m             │            │ FSR: Verify 0.6:1 ratio │ │
│  │ Rear:  6.0m             │            │ Parking: Review needs   │ │
│  └─────────────────────────┘            └─────────────────────────┘ │
│                                                                     │
│  💡 3 VISUAL GUIDES FOUND               📋 12 CONNECTED RULES       │
│     └─── Show Examples ───┘                └── Show Details ──┘     │
└─────────────────────────────────────────────────────────────────────┘
```

**Key UX Decisions**:
- **Immediate satisfaction**: Core setback values shown instantly
- **Progressive hints**: Visual guides and connected rules counts visible but not overwhelming
- **Action-oriented**: "Next Steps" focuses on what user needs to do
- **Confidence indicators**: Users see data quality immediately

### **LAYER 2: CONTEXTUAL EXPANSION (Click-to-reveal)**

#### **Option A: Smart Tabs (Horizontal Organization)**
```
┌─────────────────────────────────────────────────────────────────────┐
│ [ SETBACKS ] [ VISUALS ] [ CONNECTED RULES ] [ CITATIONS ] [ ALL ]  │
│                                                                     │
│ 📐 SETBACK DETAILS                                                  │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ Front Setback: 6.0m                                             │ │
│ │ ├─ Source: Marrickville DCP 2011, Section 4.2                  │ │
│ │ ├─ Confidence: HIGH (87%)                                       │ │
│ │ ├─ Applies to: Dwelling houses, R2 zones                       │ │
│ │ └─ 📊 See setback diagram →                                     │ │
│ │                                                                 │ │
│ │ Side Setback: 1.4m                                             │ │
│ │ ├─ Source: Inner West LEP 2022, Clause 5.1.2                  │ │
│ │ ├─ Confidence: HIGH (91%)                                       │ │
│ │ └─ Note: Minimum for buildings up to 8.5m height              │ │
│ └─────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

#### **Option B: Accordion Cards (Vertical Flow)**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 📐 SETBACK CALCULATIONS                                    [EXPANDED]│
│ ├─ Front: 6.0m (HIGH confidence) • Marrickville DCP 4.2            │
│ ├─ Side: 1.4m (HIGH confidence) • Inner West LEP 5.1.2             │
│ └─ Rear: 6.0m (MEDIUM confidence) • General R2 requirements        │
│                                                                     │
│ 🔗 CONNECTED REQUIREMENTS                                    [CLICK] │
│ └─ 12 related rules found • Height, FSR, parking connections        │
│                                                                     │
│ 💡 VISUAL GUIDANCE                                           [CLICK] │ 
│ └─ 3 diagrams available • Setback examples, site planning          │
│                                                                     │
│ 📋 PAGE CITATIONS                                            [CLICK] │
│ └─ 8 precise references • Council-quality page numbers             │
└─────────────────────────────────────────────────────────────────────┘
```

### **LAYER 3: DEEP DIVE MODES**

#### **Visual Content Disclosure Pattern**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 💡 VISUAL GUIDANCE (3 items)                                       │
│                                                                     │
│ 🎯 PRIORITY 1: CRITICAL FOR YOUR PROPERTY                          │
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ [DIAGRAM]              R2 Zone Setback Requirements             │ │
│ │                        Page 47, Marrickville DCP                │ │
│ │ Shows exact measurements for dwelling houses                     │ │
│ └─────────────────────────────────────────────────────────────────┘ │
│                                                                     │
│ ⭐ PRIORITY 2: HELPFUL CONTEXT                                      │
│ ├─ Site Planning Examples (Page 52)                  [SHOW IMAGE]  │
│ ├─ Height Transition Diagram (Page 61)               [SHOW IMAGE]  │
│                                                                     │
│ 📚 PRIORITY 3: COMPREHENSIVE REFERENCE                             │
│ ├─ FSR Calculation Table (Page 15)                   [SHOW ON DEMAND] │
│ ├─ Parking Requirements Chart (Page 89)              [SHOW ON DEMAND] │
│ └─ └── 8 more references available ──────────────── [EXPAND ALL]   │
└─────────────────────────────────────────────────────────────────────┘
```

#### **Connected Requirements Flow Pattern**
```
┌─────────────────────────────────────────────────────────────────────┐
│ 🔗 CONNECTED REQUIREMENTS                                           │
│                                                                     │
│ 🚨 SAME-SECTION CONNECTIONS (Act on these first)                    │
│ ├─ Height Limit: 8.5m maximum (DCP 4.2) • VERIFY WITH ARCHITECT   │
│ ├─ Site Coverage: 50% max (DCP 4.2) • CALCULATE YOUR FOOTPRINT     │
│ └─ Landscaping: 25% min (DCP 4.2) • PLAN GARDEN AREAS             │
│                                                                     │
│ 🔄 CROSS-REFERENCE CONNECTIONS                        [EXPAND MORE] │ │
│ ├─ Parking: 1 space per dwelling (DCP 7.2)                         │
│ └─ Waste: Collection point requirements (DCP 8.1)                  │
│                                                                     │
│ 🏘️ ZONE COHERENCE CONNECTIONS                         [EXPAND MORE] │
│ ├─ Street setback consistency with neighborhood                     │
│ └─ Building materials compatible with R2 character                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## DESIGN PRINCIPLES FOR MAXIMUM UTILITY

### **1. PROGRESSIVE INFORMATION ARCHITECTURE**
```
UTILITY PYRAMID:
                     ┌─────────────────┐
                     │ COMPREHENSIVE   │ ← Professional users, complex cases
                     │ (All data)      │ 
                ┌────┴─────────────────┴────┐
                │    CONTEXTUAL DETAIL      │ ← Informed users, specific questions  
                │  (Connected requirements) │
           ┌────┴───────────────────────────┴────┐
           │         ACTIONABLE ANSWERS          │ ← All users, immediate needs
           │        (Core setback values)        │
           └─────────────────────────────────────┘
```

### **2. SMART DEFAULT BEHAVIORS**
- **Auto-expand critical items**: Setback diagrams auto-show for low-confidence results
- **Context-aware prioritization**: Different priorities for renovation vs new build
- **Confidence-driven disclosure**: More detail automatically shown for uncertain results
- **Time-sensitive highlighting**: Deadlines, application periods get priority treatment

### **3. PROFESSIONAL USER SHORTCUTS**
```
┌─────────────────────────────────────────────┐
│ 👤 USER TYPE DETECTED: PROFESSIONAL        │
│                                             │
│ ⚡ QUICK ACTIONS:                           │
│ ├─ Download complete report (PDF)          │
│ ├─ Export citations (Council format)       │
│ ├─ View all visuals (Gallery mode)         │
│ └─ Check compliance matrix (Advanced)      │
└─────────────────────────────────────────────┘
```

### **4. INFORMATION SCENT & WAYFINDING**
- **Breadcrumb trails**: "Setbacks > Front Setback > DCP Source > Visual Examples"
- **Information previews**: Hover states show content summaries
- **Progress indicators**: "3 of 12 connected requirements reviewed"
- **Related content suggestions**: "Users who viewed setbacks also checked FSR limits"

---

## IMPLEMENTATION PRIORITIES

### **PHASE 1: CORE EXPERIENCE (Week 1)**
1. Single assessment button with immediate setback results
2. Basic progressive disclosure with accordion cards
3. Visual content integration (Priority 1 items only)

### **PHASE 2: SMART BEHAVIORS (Week 2)** 
1. Confidence-driven auto-expansion
2. Connected requirements with action-oriented language
3. Professional user shortcuts

### **PHASE 3: ADVANCED UX (Week 3)**
1. Smart tabs with contextual organization
2. Full visual content gallery with priorities
3. Advanced filtering and export capabilities

---

## SUCCESS METRICS

### **EASE OF USE INDICATORS**
- **Time to first value**: < 3 seconds for core setback display
- **Click efficiency**: 80% of users get answers within 2 clicks
- **Cognitive load**: Information hierarchy tested with 5-second rule

### **MAXIMUM UTILITY INDICATORS**
- **Data exploitation**: 60%+ of visual content accessed by professionals
- **Connected discovery**: Average 4+ connected requirements explored per session
- **Citation usage**: 40%+ download/reference page citations

### **USER SATISFACTION INDICATORS**
- **Task completion**: 90%+ complete their primary assessment goal
- **Return usage**: 70%+ return for additional properties
- **Professional adoption**: 80%+ of professional users use advanced features

This progressive disclosure design gives immediate value while providing clear, organized pathways to comprehensive detail - perfect for both homeowners needing quick answers and professionals requiring complete regulatory analysis.