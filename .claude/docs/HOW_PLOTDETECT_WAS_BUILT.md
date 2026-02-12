# How Verify Was Built: Engineering Trust in Planning Compliance

## The Problem We Set Out to Solve

Property development compliance in NSW involves navigating three tiers of planning controls: State Environmental Planning Policies (SEPPs), Local Environmental Plans (LEPs), and Development Control Plans (DCPs). A single property might be subject to hundreds of provisions across dozens of documents, each with different applicability rules based on zoning, land use, lot characteristics, and geographic location.

Traditional approaches either overwhelm users with every possible requirement or, worse, use AI to "summarize" regulations—creating liability when summaries miss critical controls. We chose a different path: build a system where every compliance claim traces directly to its regulatory source.

## Core Architectural Principle: The Provision IS the Requirement

Verify's fundamental design decision was to treat regulatory provisions as first-class data objects, not as text to be interpreted. When users see a planning requirement, they see the exact clause text as published in the official instrument. This isn't a summary or interpretation—it's the authoritative source.

This principle drove every subsequent technical decision:

- **No AI interpretation of what provisions "mean"**
- **Direct PDF links to source documents with exact page numbers**
- **Verbatim provision text maintained through all processing stages**
- **Traceability from every displayed requirement back to its gazette source**

## The Data Pipeline: From PDFs to Addressable Requirements

### Source Document Processing

We built document-specific extractors for each regulatory instrument. The Inner West LEP alone required parsing 100+ pages of structured legal text, with special handling for:

- Part 6 site-specific provisions that apply only to particular Lot/DP combinations
- Heritage schedules with thousands of individually listed properties
- Key sites with bespoke height and FSR controls

Each extractor preserves the provision's structural metadata: clause number, parent section, applicable zones, and the exact PDF page where the text appears.

### The 4-Layer Filtering Model

Not every provision applies to every property. Verify implements a cascading filter:

1. **Generic Layer**: Provisions applying council-wide (e.g., tree preservation, parking rates)
2. **Use-Specific Layer**: Controls triggered by development type (e.g., boarding house provisions only shown for boarding house applications)
3. **Condition Layer**: Requirements contingent on development characteristics (e.g., height controls only relevant when proposing buildings above existing)
4. **Precinct Layer**: Location-specific controls (e.g., Marrickville Town Centre provisions)

This filtering reduces noise dramatically. A residential alteration in Stanmore doesn't need to see industrial setback requirements or heritage provisions for buildings in Balmain.

### Address-Driven PDF Extraction

Early versions extracted every page from every planning PDF. This was wasteful and slow. We refined the approach to be address-driven: only extract and cache PDF page images for provisions that could actually apply to queryable addresses.

For example, LEP Part 6 contains site-specific provisions for particular properties. Rather than extract all 50+ Part 6 pages, we mapped each clause to its applicable Lot/DP identifiers:

```
Clause 6.17 → Lot 1, DP 963000 → Page 75
Clause 6.14 → Lots at 145-155 Parramatta Rd → Page 73
```

When a user queries an address, the system checks if any Part 6 clauses apply to that Lot/DP. Only then does it retrieve the relevant PDF page image.

## The Actionable Classifier: Separating Signal from Noise

Raw regulatory documents contain more than just requirements. They include:

- Objectives and aims (important context, not checkable requirements)
- Definitions (necessary for interpretation, not actionable themselves)
- Procedural text (how to lodge applications, not development controls)
- Notes and examples (clarifying commentary)

We developed a classifier to distinguish actionable controls from non-actionable text. The classifier examines:

- Linguistic markers ("must", "shall", "is required to" vs "aims to", "seeks to")
- Clause structure (numbered requirements vs explanatory paragraphs)
- Section context (controls sections vs interpretation sections)

After iterative refinement, the classifier achieved a 0.0% false negative rate on our test corpus—no genuine requirements are incorrectly filtered out. We prioritized eliminating false negatives over false positives; showing an extra provision is far less harmful than missing a real requirement.

## Council-Specific Adaptations

Inner West Council's three predecessor DCPs each use different organizational structures:

**Marrickville DCP 2011**: Heavily precinct-based. 102 distinct precincts with location-specific controls. Generic provisions are minimal.

**Leichhardt DCP 2013**: 77% generic provisions applying council-wide. Uses "C-markers" (C1, C2, C3...) for discrete controls within sections.

**Ashfield DCP 2007**: PC/DS format separating Performance Criteria from Design Solutions, requiring both to be displayed together.

Verify's data model accommodates all three structures through a unified `regulatory_provisions` schema with council-specific metadata fields.

## Processing Economics: The Tiered Approach

Enriching 47,000+ provisions with AI classification would be prohibitively expensive if done naively. We implemented a three-tier processing pipeline:

1. **Regex Layer**: Fast pattern matching handles ~70% of provisions (clear objectives, obvious definitions)
2. **Batch LLM Layer**: Groups similar provisions for efficient batch classification
3. **Selective Deep Enrichment**: Expensive per-provision analysis only for ambiguous cases

This reduced API costs by 97% compared to uniform deep processing, while maintaining classification accuracy.

## What Verify Deliberately Does NOT Do

Equally important as what the system does is what it refuses to do:

- **No merit assessment**: The system shows requirements; it doesn't judge whether a development is "good"
- **No council decision prediction**: Consent authority discretion cannot be algorithmically predicted
- **No approximate data**: If we don't have verified coordinates or boundaries, we don't show fake ones
- **No hallucinated sources**: Every PDF link is verified to exist before display

## Verification and Audit Trail

Every provision displayed includes:

- Source document identifier (e.g., "Inner West LEP 2022")
- Clause/section reference (e.g., "Clause 4.3(2A)")
- PDF page number for direct verification
- Processing metadata (extraction date, classification confidence)

Users—and their lawyers—can verify any requirement against the gazetted source document.

## The Result

Verify transforms the compliance checking process from "read 2,000 pages and hope you didn't miss anything" to "here are the 47 provisions that actually apply to your property, with links to verify each one."

The system doesn't replace professional judgment. It eliminates the mechanical drudgery of document trawling, letting planners and developers focus on design responses rather than regulatory archaeology.

Every claim the application makes is traceable. Every provision links to its source. The system acknowledges what it doesn't know rather than guessing. That's how we built trust into planning compliance.

---

*Verify processes planning instruments for Inner West Council, covering the former Marrickville, Leichhardt, and Ashfield local government areas—three DCPs, three LEPs, and applicable SEPPs.*
