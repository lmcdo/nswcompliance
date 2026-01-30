# PlotDetect: Executive Summary for Certifier Managers

**Version 2.1** | January 2026

**The Problem:** Certifiers assessing a property in Inner West face 47,818 provisions scattered across SEPPs, LEPs, and three merged DCPs. Hours are spent just identifying what applies before compliance assessment begins. Manual cross-referencing between NSW Planning Portal data and PDF documents is error-prone and inefficient.

**The Solution:** PlotDetect automates provision discovery using a two-stage, three-tab workflow modeled on legal research platforms like LexisNexis.

**Workflow Overview:**

Address entry ("100 Illawarra Road, Marrickville") triggers automatic NSW Planning Portal API query, returning zone (R2), heritage overlays (HCA C35), flood/bushfire status, and legislated height/FSR limits. This data populates the left column with clickable legislation URLs.

Three tabs organize provisions by regulatory hierarchy:

**SEPP Tab** (purple - State Environmental Planning Policies): Shows SEPP Housing 2021 requirements, eligibility checks, Apartment Design Guide (ADG) building separation and solar access tables, Transit Oriented Development controls if applicable, and CDC compliance calculators. These state-level policies override local controls where inconsistent.

**LEP Tab** (amber - Local Environmental Plan): Displays zone objectives, permitted/prohibited uses, local FSR and height provisions, and heritage conservation requirements extracted from the Planning Portal's legislated values. Links directly to gazetted legislation.

**DCP Tab** (green - Development Control Plan): Council-level design provisions organized via table of contents structure (Parts 2, 4, 8, 9 for Marrickville; Sections 1-3 for Leichhardt; Parts A-F for Ashfield). This is where the 4-layer applicability model filters 5,500 DCP provisions to 400-700 relevant ones: Layer 1 (generic - always apply), Layer 2 (zone-specific for R2), Layer 3 (heritage if HCA C35 applies), Layer 4 (precinct-specific for location).

**Two-Stage Data Processing:**

Stage 1 filters document structure—table of contents pages, legislative boilerplate, PDF artifacts—with 99.96% precision (only 5 potential false negatives in 11,176 filtered provisions). This mirrors how LexisNexis hides navigation elements while preserving all law.

Stage 2 prioritizes the remaining 10,316 actionable provisions using tags: "Critical" for mandatory numeric controls (height limits, FSR, parking rates), "Important" for design standards, "Guideline" for objectives. Provisions remain visible regardless of tag; nothing is hidden based on priority categorization.

The system organizes provisions by topic (parking, setbacks, solar access, heritage) for efficient navigation. Certifiers review all applicable provisions—same thoroughness, better workflow. Professional responsibility and liability remain with the certifier. The system provides intelligent organization, not compliance decisions.

**Supporting documentation:** METHODOLOGY.md provides full technical rationale and validation results.
