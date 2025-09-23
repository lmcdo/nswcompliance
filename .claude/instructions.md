# Claude Instructions - Compliance Engine Project

## CRITICAL: Read These Files First

### 1. **PRP_STATUS.md** - ALWAYS CHECK FIRST
- Contains current implementation status
- Lists ACTIVE vs OBSOLETE PRPs
- Shows which code patterns to avoid
- Tracks progress through PRPs

### 2. **Active PRP Document**
- Currently: `PRP_WSL2_LIGHTRAG_IMPLEMENTATION.md`
- Follow this document ONLY
- Do not reference obsolete PRPs

---

## Project Context

This is a NSW property compliance engine that needs to extract and display REAL regulatory text from planning documents (LEP, DCP, SEPP).

### Current Problem
- Windows native LightRAG implementation has failed (async issues)
- Regex extraction cannot handle legal document complexity
- Need semantic understanding for context-specific rules

### Current Solution
- WSL2 Ubuntu with LightRAG + AutoSchemaKG + RagAnything
- Full semantic processing (no regex)
- API bridge between Windows frontend and WSL2 backend

---

## Implementation Rules

### ALWAYS DO
 Check PRP_STATUS.md first
 Use WSL2 for all Python RAG processing
 Implement semantic extraction only
 Require source attribution for all text
 Follow the ACTIVE PRP document

### NEVER DO
 Use Windows native Python for LightRAG
 Implement regex-based extraction
 Hardcode compliance rule values
 Add "enrichment" or "enhancement" layers
 Create fallback placeholder text
 Reference obsolete PRPs or code

---

## Key Technical Decisions

1. **WSL2 Only**: All Python RAG processing must run in WSL2 Ubuntu
2. **Semantic Only**: No regex patterns for extracting regulatory text
3. **Source Grounding**: Every piece of regulatory text must trace to source
4. **No Backsliding**: If current approach fails, fix it - don't try alternatives
5. **Real Text Only**: Display actual regulatory text or nothing

---

## Current Status (as of 2025-08-26)

- **Active PRP**: PRP_WSL2_LIGHTRAG_IMPLEMENTATION.md
- **Current Phase**: PRP-001 (WSL2 Foundation Setup) - NOT STARTED
- **Progress**: 0/7 PRPs completed
- **Next Action**: Begin PRP-001 WSL2 setup

---

## Common Pitfalls to Avoid

1. **Don't try to fix Windows LightRAG** - It has fundamental async issues
2. **Don't use regex for DCP extraction** - Documents have context-specific rules
3. **Don't hardcode setback values** - Must come from semantic processing
4. **Don't create "enrichment" methods** - Use direct text only
5. **Don't implement fallback text** - Show real text or nothing

---

## File Organization

```
compliance-engine/
├── PRP_STATUS.md # CHECK THIS FIRST
├── PRP_WSL2_LIGHTRAG_IMPLEMENTATION.md # ACTIVE - Current implementation guide
├── PRP_REGULATORY_TEXT_EXTRACTION.md # OBSOLETE - DO NOT USE
├── .claude/
│ └── instructions.md # This file
├── scripts/
│ ├── direct_dcp_access.py # OBSOLETE - Windows approach
│ ├── direct_lep_access.py # OBSOLETE - Windows approach
│ └── process_*_lightrag.py # OBSOLETE - Windows approach
└── lib/
 ├── regulatory-text-retriever.ts # Needs updating for WSL2 API
 └── enhanced-compliance-engine.ts # Needs updating for WSL2 API
```

---

## Questions to Ask Before Implementing

1. Is this approach listed as ACTIVE in PRP_STATUS.md?
2. Does this follow the WSL2 semantic processing path?
3. Is this extracting real text from source documents?
4. Does every claim have source attribution?
5. Am I avoiding all OBSOLETE patterns listed?

If any answer is NO, stop and reconsider the approach.