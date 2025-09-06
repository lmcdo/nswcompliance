# UPDATED PRP SEQUENCE - LARGE FILE SPLITTING FIRST
**Date**: 2025-08-27  
**Status**: IMMEDIATE IMPLEMENTATION REQUIRED  
**Priority**: CRITICAL WORKFLOW IMPROVEMENT

---

## 🚨 **IDENTIFIED ISSUES**

1. **API Rate Limits Hit Too Early**: Gemini API quota exceeded after only 24/98 chunks
2. **Incomplete A3.5 Processing**: 5/10 documents still need processing (74 chunks remaining)
3. **Large File Splitting Should Be Standard**: Currently done ad-hoc, should be systematic
4. **All Marrickville Files Need Same Treatment**: 85+ files will hit same issues

---

## 🎯 **CORRECTED PRP SEQUENCE**

### **NEW STANDARD SEQUENCE:**
```
✅ PRP-A1: Package Installation Verification
✅ PRP-A2: PDF Content Extraction (54 documents)  
🆕 PRP-A2.5: SPLIT ALL LARGE FILES (Standard Step)
⚠️  PRP-A3: Small Files Source Grounding (LangExtract)
🔄 PRP-A3.5: Large Files Source Grounding (LangExtract on chunks)
🆕 PRP-A2-EXT: Process Missing Marrickville DCPs → Split if needed
⏳ PRP-A4: Knowledge Graph Construction (complete dataset)
⏳ PRP-A5-A7: Pipeline completion
```

### **PRP-A2.5: UNIVERSAL LARGE FILE SPLITTER**
**Duration**: 5-10 minutes  
**Objective**: Split ALL large files (>50KB) into manageable chunks BEFORE any API processing

**Implementation:**
1. **Analyze ALL documents** (existing + future Marrickville)
2. **Split large files** into 40KB chunks with 2KB overlap
3. **Create unified chunk database** for all subsequent processing
4. **No API calls** - pure file processing step

---

## ⚡ **IMPROVED API RATE LIMITING STRATEGY**

### **Current Problem:**
- **Gemini Free Tier**: 10 requests/minute (too restrictive)
- **No intelligent backoff** when limits hit
- **No quota monitoring** during processing

### **SOLUTION: ADAPTIVE RATE LIMITING**
```python
class AdaptiveRateLimiter:
    def __init__(self):
        self.requests_per_minute = 10  # Start conservative
        self.success_count = 0
        self.failure_count = 0
        
    def wait_if_needed(self):
        if self.requests_per_minute >= 10:
            wait_time = 60 / self.requests_per_minute
            time.sleep(wait_time)
    
    def handle_success(self):
        self.success_count += 1
        # Gradually increase rate if successful
        if self.success_count % 20 == 0:
            self.requests_per_minute = min(15, self.requests_per_minute + 1)
    
    def handle_rate_limit(self, retry_delay):
        self.failure_count += 1
        # Reduce rate and wait
        self.requests_per_minute = max(5, self.requests_per_minute - 2)
        time.sleep(retry_delay + 5)  # Extra buffer
    
    def get_current_rate(self):
        return f"{self.requests_per_minute} req/min"
```

---

## 📋 **IMMEDIATE ACTION PLAN**

### **Step 1: Complete A3.5 Processing (Today)**
- **Fix API rate limiting** in existing processor
- **Process remaining 5 documents** (74 chunks)
- **Use conservative 5 req/min rate** with exponential backoff

### **Step 2: Create PRP-A2.5 Universal Splitter (Next Session)**
- **Split ALL large files** from all sources
- **Create standardized chunk format**
- **No API dependencies** - pure file processing

### **Step 3: Update All Subsequent PRPs**
- **A3/A3.5**: Process pre-split chunks only
- **A2-EXT**: Split Marrickville files first, then process chunks
- **Standard workflow**: Split → Extract → Ground → Graph

---

## 🔧 **IMMEDIATE FIXES NEEDED**

### **Fix 1: Complete A3.5 with Better Rate Limiting**
```python
# process_remaining_a3_5_chunks.py
def process_with_adaptive_limiting():
    limiter = AdaptiveRateLimiter()
    
    for chunk in remaining_chunks:
        limiter.wait_if_needed()
        
        try:
            result = process_chunk(chunk)
            limiter.handle_success()
        except RateLimitError as e:
            retry_delay = extract_retry_delay(e)
            limiter.handle_rate_limit(retry_delay)
            # Retry with new rate
            result = process_chunk(chunk)
```

### **Fix 2: Universal Large File Splitter**
```python
# prp_a2_5_universal_file_splitter.py
def split_all_large_files():
    """Split ALL large files from ALL sources before any API processing"""
    
    # Find large files from:
    # 1. Existing A2 dataset (54 docs)
    # 2. Marrickville DCPs (85 files)
    # 3. Any other sources
    
    all_large_files = identify_all_large_files_comprehensive()
    
    for file_info in all_large_files:
        if file_info['size_kb'] > 50:
            chunks = split_document_intelligent(file_info)
            store_chunks_for_processing(file_info, chunks)
    
    # Create unified chunk database
    create_unified_chunk_manifest()
```

---

## 🚀 **NEXT ACTIONS**

### **Immediate (Current Session)**
1. **Create adaptive rate limiter**
2. **Process remaining 5 A3.5 documents** with 5 req/min rate
3. **Complete A3.5 with all 10 documents**

### **Next Session Priority**
```bash
"Execute PRP-A2.5: Universal Large File Splitter - Split ALL large files before API processing"
```

### **Future Sessions**
- **PRP-A2-EXT**: Process Marrickville DCPs (pre-split)
- **Updated A3/A3.5**: Process chunks with reliable rate limiting
- **PRP-A4+**: Use complete, properly processed dataset

---

This approach makes large file splitting a **standard first step** and prevents API quota issues through **intelligent rate limiting and pre-splitting**.