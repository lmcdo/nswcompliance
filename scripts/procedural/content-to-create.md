# Procedural Content To Create

This file tracks the Q&As, checklists, and guides to be created and imported into the database.

## Implementation Order

1. **High-priority Q&As** (20 items) - Most frequently asked
2. **Getting Started Guides** (5 guides) - User journey entry points
3. **Remaining Q&As** (30 items) - Complete coverage
4. **New Checklists** (8 checklists) - Actionable outputs

---

## Phase 1: High-Priority Q&As (Week 1)

These address the most common user confusion points.

### Format for JSON Import

Each Q&A needs this structure for `pathway_guidance.json`:

```json
{
  "question_pattern": "Should I use CDC or DA?",
  "question_normalized": "cdc da pathway choice",
  "question_category": "pathway",
  "answer_summary": "Short answer (1-2 sentences)",
  "answer_detailed": "Full explanation (2-4 paragraphs)",
  "answer_conditions": ["Condition 1", "Condition 2"],
  "source_document": "NSW Planning Portal",
  "source_url": "https://...",
  "source_section": "Section reference",
  "last_verified": "2026-01-20",
  "follow_up_questions": ["Related Q1?", "Related Q2?"],
  "applies_to_cdc": true,
  "applies_to_da": true,
  "applies_to_dev_types": ["dwelling_house", "secondary_dwelling"],
  "extraction_confidence": 1.0,
  "manual_verified": true
}
```

---

### Q&As To Write (Priority Order)

#### Batch 1: Pre-Application (Critical)

**Q19: Do I need a pre-lodgement meeting?**
- Category: pre-application
- Source: Inner West Council website
- Key points:
  - Recommended for complex DAs
  - Required for some major developments
  - Costs ~$500-1500
  - Can save months of back-and-forth

**Q28: What's a Section 10.7 Planning Certificate?**
- Category: pre-application
- Source: EP&A Act
- Key points:
  - Shows zoning and planning controls
  - Required for most applications
  - Ordered from council (~$75)
  - Valid for limited time

**Q26: How much does a DA typically cost?**
- Category: cost
- Source: Council fee schedule + industry data
- Key points:
  - Council fees: $500-5000 depending on value
  - Architect: $5,000-30,000
  - Engineer: $2,000-10,000
  - Other consultants: varies
  - Total typical range: $15,000-50,000 for residential

**Q25: What's the role of a town planner vs architect?**
- Category: professional
- Source: Industry knowledge
- Key points:
  - Architect: designs the building
  - Town planner: navigates planning controls, writes SEE
  - When you need both vs just one
  - Cost implications

#### Batch 2: During Assessment (High Anxiety)

**Q29: What happens after I submit my DA?**
- Category: process
- Source: Council DA process guide
- Key points:
  - Lodgement and fee payment
  - Completeness check (5 business days)
  - Referrals (internal + external)
  - Neighbour notification (14-28 days)
  - Assessment and determination
  - Timeline: typically 40-90 days

**Q31: Can neighbours object to my DA?**
- Category: notification
- Source: EP&A Regulation
- Key points:
  - Notification requirements by development type
  - Objection period (usually 14 days)
  - How objections are considered
  - They don't have veto power

**Q33: How long can council take to assess my DA?**
- Category: timeline
- Source: EP&A Act
- Key points:
  - No statutory deadline (unlike CDC)
  - Typical: 40-90 days
  - Complex: 6-12 months
  - Deemed refusal after 40 days (not automatic)
  - Stop-the-clock for RFIs

#### Batch 3: Variations (Most Misunderstood)

**Q37: What is a Clause 4.6 variation?**
- Category: variation
- Source: Standard Instrument LEP
- Key points:
  - Allows exceeding development standards
  - Requires written justification
  - Must demonstrate compliance unreasonable/unnecessary
  - Must demonstrate sufficient environmental planning grounds
  - Common for height, FSR, setbacks

**Q38: Can I exceed the height limit?**
- Category: variation
- Source: LEP Clause 4.6
- Key points:
  - Yes, via Clause 4.6 variation
  - Need strong justification
  - Minor exceedances more likely approved
  - Heritage areas more difficult
  - Precedent matters

**Q44: What's a Section 4.55 modification?**
- Category: modification
- Source: EP&A Act s4.55
- Key points:
  - Changes to existing approval
  - Three types: (1) minor error, (1A) minimal impact, (2) other
  - Faster than new DA
  - Can't be "substantially different"

#### Batch 4: Post-Approval (Critical Gap)

**Q49: What's a Principal Certifier?**
- Category: construction
- Source: EP&A Act
- Key points:
  - Mandatory for all construction
  - Can be council or private
  - Appointed before construction starts
  - Issues Construction Certificate
  - Conducts inspections
  - Issues Occupation Certificate

**Q54: How long is my DA approval valid?**
- Category: approval
- Source: EP&A Act
- Key points:
  - Physical commencement: 5 years from determination
  - Lapsing provisions
  - What counts as "commencement"
  - Extension options (s4.56)

**Q58: Can I move in before getting an OC?**
- Category: construction
- Source: EP&A Act
- Key points:
  - NO - it's illegal
  - Fines up to $1.1 million
  - Insurance implications
  - Safety reasons
  - Interim OC option for staged occupation

#### Batch 5: Mistakes (Prevention)

**Q59: What are the most common reasons DAs get rejected?**
- Category: mistakes
- Source: Industry knowledge + council feedback
- Key points:
  - Non-compliance with height/FSR (no variation)
  - Inadequate heritage response
  - Privacy/overshadowing impacts
  - Insufficient parking
  - Poor design quality
  - Incomplete documentation

**Q60: What causes delays in DA assessment?**
- Category: mistakes
- Source: Council process knowledge
- Key points:
  - Incomplete applications
  - Missing reports (heritage, traffic, etc.)
  - Neighbour objections requiring response
  - Referral delays (RMS, Sydney Water)
  - Design amendments during assessment

**Q62: What's the difference between exempt, complying, and DA?**
- Category: pathway
- Source: Codes SEPP
- Key points:
  - Exempt: No approval needed (tiny works)
  - Complying (CDC): Fast-track, must meet all standards
  - DA: Full assessment, can vary standards
  - Decision tree for which applies

---

## Phase 2: Getting Started Guides (Week 2)

### What's Involved

Each guide is a **structured JSON document** with:

1. **Metadata**
   - Title
   - Target user
   - Estimated timeline
   - Typical cost range

2. **Eligibility Check**
   - Zone requirements
   - Lot size requirements
   - Constraint considerations

3. **Steps** (7 each)
   - Step number
   - Step title
   - Description
   - Key decisions
   - Documents/outputs
   - Typical duration
   - Common mistakes

4. **Related Q&As**
   - Links to relevant Q&A IDs

5. **Related Checklists**
   - Links to relevant checklist IDs

### Guide Structure Example

```json
{
  "guide_id": "G1",
  "title": "I Want to Build a Granny Flat",
  "slug": "build-granny-flat",
  "target_user": "Homeowner with existing dwelling",
  "typical_timeline": "3-6 months",
  "typical_cost_range": "$80,000-150,000 (construction) + $5,000-15,000 (approvals)",

  "eligibility": {
    "zones": ["R1", "R2", "R3", "R4"],
    "min_lot_size": 450,
    "requires_principal_dwelling": true,
    "max_size": "60m² or 25% of principal dwelling",
    "constraints_to_check": ["heritage", "flood", "bushfire"]
  },

  "steps": [
    {
      "step": 1,
      "title": "Check Eligibility",
      "description": "Verify your property can have a secondary dwelling",
      "key_decisions": [
        "Is your lot at least 450m²?",
        "Is secondary dwelling permitted in your zone?",
        "Do you have any constraints (heritage, flood)?"
      ],
      "outputs": ["Eligibility confirmed or issues identified"],
      "duration": "1 day (using this app)",
      "common_mistakes": ["Assuming all R2 lots can have granny flats (need 450m²)"]
    },
    {
      "step": 2,
      "title": "Understand the Limits",
      "description": "Know what you can build",
      "key_decisions": [
        "Attached vs detached?",
        "What size (max 60m²)?",
        "Where on the lot?"
      ],
      "outputs": ["Basic brief for designer"],
      "duration": "1-2 days",
      "common_mistakes": ["Planning for 65m² then having to redesign"]
    },
    {
      "step": 3,
      "title": "Choose Your Pathway",
      "description": "CDC (fast) vs DA (flexible)",
      "key_decisions": [
        "Does design meet all CDC standards?",
        "Any variations needed?",
        "Heritage or other constraints?"
      ],
      "outputs": ["Pathway decision"],
      "duration": "Part of design process",
      "common_mistakes": ["Assuming CDC is always available"]
    },
    {
      "step": 4,
      "title": "Engage Professionals",
      "description": "Get the right team",
      "key_decisions": [
        "Designer/draftsperson vs architect?",
        "Private certifier vs council?",
        "Need structural engineer?"
      ],
      "outputs": ["Signed contracts with professionals"],
      "duration": "1-2 weeks to find and engage",
      "common_mistakes": ["Not getting structural engineer early enough"]
    },
    {
      "step": 5,
      "title": "Prepare Application",
      "description": "Compile all required documents",
      "key_decisions": [
        "All drawings complete?",
        "BASIX certificate obtained?",
        "Site survey current?"
      ],
      "outputs": ["Complete application package"],
      "duration": "4-8 weeks (design + documentation)",
      "common_mistakes": ["Missing Section 10.7 certificate"]
    },
    {
      "step": 6,
      "title": "Submit and Wait",
      "description": "Lodge application and respond to queries",
      "key_decisions": [
        "Respond to RFI promptly?",
        "Amend design if needed?"
      ],
      "outputs": ["Approval (CDC or DA consent)"],
      "duration": "CDC: 10-20 days, DA: 40-90 days",
      "common_mistakes": ["Slow RFI response extending timeline"]
    },
    {
      "step": 7,
      "title": "Build and Certify",
      "description": "Construction and final approval",
      "key_decisions": [
        "Principal Certifier appointed?",
        "All inspections booked?",
        "Ready for final inspection?"
      ],
      "outputs": ["Occupation Certificate"],
      "duration": "3-6 months (construction)",
      "common_mistakes": ["Moving family in before OC"]
    }
  ],

  "related_qa_ids": ["Q1", "Q2", "Q3", "Q13", "Q49", "Q58"],
  "related_checklist_ids": ["CL3"]
}
```

### Guides To Create

| ID | Title | Key Decisions |
|----|-------|---------------|
| G1 | Build a Granny Flat | CDC vs DA, attached vs detached |
| G2 | Add a Second Storey | Height compliance, heritage, structural |
| G3 | Build a Duplex | Zone permissibility, subdivision, Strata vs Torrens |
| G4 | Knock Down and Rebuild | Demolition, combined vs staged, character |
| G5 | Subdivide My Property | Min lot sizes, access, battle-axe |

---

## Phase 3: Remaining Q&As (Week 3)

Complete the remaining 30 Q&As following the same format.

---

## Phase 4: New Checklists (Week 4)

### Checklist Structure

```json
{
  "checklist_name": "Two-Storey Addition CDC",
  "pathway": "CDC",
  "development_type": "addition",
  "items": [
    {
      "item_order": 1,
      "item_name": "Site Survey",
      "item_description": "Survey plan showing existing dwelling, boundaries, levels",
      "item_required": true,
      "item_conditions": null,
      "source_document": "Codes SEPP",
      "source_url": "..."
    }
  ]
}
```

### Checklists To Create

| ID | Name | Items | Notes |
|----|------|-------|-------|
| CL5 | Two-Storey Addition CDC | 18 | Most common renovation |
| CL6 | Swimming Pool CDC | 12 | Fencing requirements critical |
| CL7 | Garage/Carport CDC | 10 | Setback variations common |
| CL8 | Deck/Pergola CDC | 8 | Exempt vs CDC boundary |
| CL9 | Commercial Fit-out DA | 15 | Different requirement set |
| CL10 | Heritage Item DA Extras | 12 | Additional to standard DA |
| CL11 | Flood Zone DA Extras | 10 | FPL, flood study requirements |
| CL12 | Bushfire Prone Land Extras | 12 | BAL assessment, APZ |

---

## Data Sources

### Primary Sources (Authoritative)
- NSW Planning Portal: https://www.planningportal.nsw.gov.au/
- NSW Legislation: https://legislation.nsw.gov.au/
- Inner West Council: https://www.innerwest.nsw.gov.au/develop/development-applications
- Codes SEPP: https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572

### Secondary Sources (Guidance)
- NSW Planning Portal "How to" guides
- Inner West Council DA Guide PDF
- Private certifier industry guides
- Planning Institute Australia resources

---

## Import Process

1. Write content in JSON format matching schema
2. Add to `scripts/procedural/extracted/` directory
3. Run `python scripts/procedural/import_procedural.py`
4. Verify via `/api/procedural` endpoint
5. Test in AI assistant

---

## Status Tracking

| Content | Status | Assigned | Due |
|---------|--------|----------|-----|
| Q19-Q28 (Batch 1) | Not started | - | - |
| Q29-Q36 (Batch 2) | Not started | - | - |
| Q37-Q48 (Batch 3) | Not started | - | - |
| Q49-Q58 (Batch 4) | Not started | - | - |
| Q59-Q68 (Batch 5) | Not started | - | - |
| G1: Granny Flat | Not started | - | - |
| G2: Second Storey | Not started | - | - |
| G3: Duplex | Not started | - | - |
| G4: Knock Down Rebuild | Not started | - | - |
| G5: Subdivide | Not started | - | - |
| CL5-CL12 | Not started | - | - |

---

*Created: 2026-01-20*
