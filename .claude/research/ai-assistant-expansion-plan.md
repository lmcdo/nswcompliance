# AI Assistant Expansion Plan

## Executive Summary

The AI assistant's optimal role is **procedural guidance and definitions** - NOT provision lookup (which tabs do better). This document outlines the content expansion needed to make the AI uniquely valuable.

## Current State

| Content Type | Count | Coverage |
|--------------|-------|----------|
| Q&A Pairs | 18 | 30% |
| Checklists | 61 items / 4 types | 50% |
| Definitions | 465 terms | 80% |

## Architecture Decision

**AI Assistant Scope:**
- Procedural guidance (CDC vs DA, process, timelines)
- Definitions (planning terms)
- Checklists (document requirements)
- Getting started guides (user journeys)

**Tabs Scope:**
- DCP provisions (175+ by topic)
- SEPP requirements (structured)
- LEP controls (height, FSR, permissibility)

**Rationale:** No concordance problems, clear differentiation, unique value.

---

## Content Expansion Targets

### Q&A Pairs: +50 (Total: 68)

#### 1. Pre-Application Phase (+10)
| ID | Question | Category | Priority |
|----|----------|----------|----------|
| Q19 | Do I need a pre-lodgement meeting? | pre-application | High |
| Q20 | How do I book a pre-DA meeting with Inner West Council? | pre-application | High |
| Q21 | What should I bring to a pre-lodgement meeting? | pre-application | Medium |
| Q22 | Can I get informal advice from council before applying? | pre-application | Medium |
| Q23 | What's the difference between a Planning Proposal and DA? | pre-application | Low |
| Q24 | Do I need to notify my neighbours before applying? | pre-application | High |
| Q25 | What's the role of a town planner vs architect? | professional | High |
| Q26 | How much does a DA typically cost (fees + professionals)? | cost | High |
| Q27 | Can I do my own DA drawings? | professional | Medium |
| Q28 | What's a Section 10.7 Planning Certificate? | pre-application | High |

#### 2. During Assessment (+8)
| ID | Question | Category | Priority |
|----|----------|----------|----------|
| Q29 | What happens after I submit my DA? | process | High |
| Q30 | How will I know if council needs more information? | process | High |
| Q31 | Can neighbours object to my DA? | notification | High |
| Q32 | What if someone objects to my development? | notification | High |
| Q33 | How long can council take to assess my DA? | timeline | High |
| Q34 | Can I check the status of my application online? | process | Medium |
| Q35 | What's a 'deemed refusal'? | process | Medium |
| Q36 | Can I withdraw my DA and get a refund? | process | Low |

#### 3. Variations & Non-Compliance (+12)
| ID | Question | Category | Priority |
|----|----------|----------|----------|
| Q37 | What is a Clause 4.6 variation? | variation | High |
| Q38 | Can I exceed the height limit? | variation | High |
| Q39 | What makes a variation request more likely to succeed? | variation | High |
| Q40 | What's the difference between variation and non-compliance? | variation | Medium |
| Q41 | Can I vary setback requirements? | variation | High |
| Q42 | What happens if I build something different from approval? | compliance | High |
| Q43 | How do I regularise unauthorised work? | compliance | High |
| Q44 | What's a Section 4.55 modification? | modification | High |
| Q45 | Can I modify my approval after construction starts? | modification | High |
| Q46 | What's the difference between 4.55(1), (1A), and (2)? | modification | Medium |
| Q47 | What are 'development standards' vs 'controls'? | terminology | Medium |
| Q48 | What happens if council refuses my DA? | appeals | High |

#### 4. Post-Approval & Construction (+10)
| ID | Question | Category | Priority |
|----|----------|----------|----------|
| Q49 | What's a Principal Certifier and do I need one? | construction | High |
| Q50 | What inspections are required during construction? | construction | High |
| Q51 | What's a Critical Stage Inspection? | construction | High |
| Q52 | How do I choose a private certifier vs council? | professional | High |
| Q53 | What's a Compliance Certificate vs Occupation Certificate? | construction | High |
| Q54 | How long is my DA approval valid? | approval | High |
| Q55 | Can I extend my DA approval if it's about to lapse? | approval | High |
| Q56 | What records do I need to keep during construction? | construction | Medium |
| Q57 | What's the final inspection process? | construction | High |
| Q58 | Can I move in before getting an Occupation Certificate? | construction | High |

#### 5. Common Mistakes & Red Flags (+10)
| ID | Question | Category | Priority |
|----|----------|----------|----------|
| Q59 | What are the most common reasons DAs get rejected? | mistakes | High |
| Q60 | What causes delays in DA assessment? | mistakes | High |
| Q61 | What documents are most often missing from applications? | mistakes | High |
| Q62 | What's the difference between exempt, complying, and DA? | pathway | High |
| Q63 | When does 'exempt development' not apply? | pathway | High |
| Q64 | What triggers the need for additional reports? | requirements | High |
| Q65 | What are red flags that council looks for? | assessment | Medium |
| Q66 | How do I know if my site has contamination issues? | constraints | High |
| Q67 | What's the most expensive mistake people make? | mistakes | Medium |
| Q68 | What should I check before buying a property to develop? | due-diligence | Medium |

---

### Checklists: +8 (Total: 12)

#### Development Type Specific
| ID | Checklist Name | Items | Dev Type |
|----|----------------|-------|----------|
| CL5 | Two-Storey Addition CDC | 18 | addition |
| CL6 | Swimming Pool CDC | 12 | pool |
| CL7 | Garage/Carport CDC | 10 | garage |
| CL8 | Deck/Pergola CDC | 8 | deck |
| CL9 | Commercial Fit-out DA | 15 | commercial |

#### Constraint-Triggered
| ID | Checklist Name | Items | Trigger |
|----|----------------|-------|---------|
| CL10 | Heritage Item DA Additional Requirements | 12 | heritage |
| CL11 | Flood Zone DA Additional Requirements | 10 | flood |
| CL12 | Bushfire Prone Land Additional Requirements | 12 | bushfire |

---

### Getting Started Guides: 5

| ID | Guide Title | Target User | Steps |
|----|-------------|-------------|-------|
| G1 | I Want to Build a Granny Flat | Homeowner | 7 |
| G2 | I Want to Add a Second Storey | Homeowner | 7 |
| G3 | I Want to Build a Duplex | Investor | 7 |
| G4 | I Want to Knock Down and Rebuild | Developer | 7 |
| G5 | I Want to Subdivide My Property | Investor | 7 |

---

## Fine-Tuning Opportunities (Future)

Only consider after content expansion complete.

### Opportunity 1: Property-Context-Aware Guidance
- Training data: 500 examples of (property_context, question, tailored_answer)
- Value: Personalized responses using zone, lot size, constraints

### Opportunity 2: Provision Summarisation
- Training data: 300 examples of (provisions_list, property_context, summary)
- Value: Synthesize 25 provisions into key points
- Safeguard: Must cite provision IDs

### Opportunity 3: Conversational Process Navigation
- Training data: 200 multi-turn conversations
- Value: Guide users through step-by-step

### Opportunity 4: Error Prevention & Warnings
- Training data: 400 examples with property-specific warnings
- Value: Proactive alerts about heritage, flood, etc.

---

## Implementation Roadmap

| Phase | Action | Effort | Impact |
|-------|--------|--------|--------|
| 1 | Add 50 Q&A pairs | 2 weeks | High |
| 2 | Add 8 checklists | 1 week | High |
| 3 | Create 5 Getting Started guides | 1 week | High |
| 4 | Polish definitions | 3 days | Medium |
| 5 | Log production questions | Ongoing | Data collection |
| 6 | Evaluate fine-tuning need | Month 2 | Decision point |

---

## Data Sources for Content

- NSW Planning Portal guides
- Inner West Council DA Guide
- Codes SEPP (State Environmental Planning Policy - Exempt and Complying Development)
- EPA Legislation website
- Council fee schedules
- Private certifier industry guides

---

## Success Metrics

1. **Coverage**: % of user questions that get a relevant answer
2. **Satisfaction**: User ratings on AI responses
3. **Redirect rate**: % of questions redirected to tabs (should decrease)
4. **Completion rate**: Users who complete checklist items

---

*Created: 2026-01-20*
*Status: Planning*
