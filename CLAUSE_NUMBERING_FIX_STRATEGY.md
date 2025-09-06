# Clause Numbering Fix Strategy - Best Practices

**Issue ID:** CNFS-001  
**Priority:** High  
**Created:** 2025-08-30  
**Status:** Analysis Complete - Implementation Needed

## 🚨 Problem Statement

The extracted regulatory data contains **systematic clause numbering errors** that affect requirement connections:

### **Identified Issues:**

1. **PDF Page Number Contamination**
   - `"4.2.4.2 Building heights . 5"` ← `. 5` is page number
   - `"4.2.4.3 Building setbacks.. 5"` ← `.. 5` is page number  
   - `"4.2.4.1 Floor space ratio and site coverage . /4"` ← `. /4` is page number

2. **Invalid Clause Structure**
   - `4.2.4.2` and `4.2.4.3` don't exist as separate clauses
   - Should be subsections of `4.2.4` (e.g., `4.2.4(a)`, `4.2.4(b)`)

3. **Inconsistent Clause References**
   - Mixed numbering schemes across different extractions
   - Some clauses missing, others duplicated with variations

## 🛠️ Best Practice Fix Strategy

### **Phase 1: Data Audit & Validation**

1. **Source Verification**
   ```bash
   # Extract text from original PDF to verify correct clause structure
   ./venv_linux/Scripts/python.exe -c "
   import fitz  # PyMuPDF
   doc = fitz.open('docs/dcps/INNERWEST/Marrickville/Marrickville DCP 2011 - 4 2 Multi Dwelling Housing and RFBs - with IWLEP 2022 amendments.pdf')
   for page in doc:
       print(f'=== PAGE {page.number + 1} ===')
       print(page.get_text())
   "
   ```

2. **Clause Pattern Analysis**
   ```python
   # Identify all clause numbering patterns in processed data
   patterns = {
       'standard': r'^\d+\.\d+\.\d+$',           # 4.2.4
       'invalid_sub': r'^\d+\.\d+\.\d+\.\d+$',   # 4.2.4.2 (INVALID)
       'page_contaminated': r'\.+ \d+$',         # ". 5", ".. 5"
       'slash_contaminated': r'\.+ /\d+$'        # ". /4"
   }
   ```

### **Phase 2: Cleanup Implementation**

1. **Regex-Based Page Number Removal**
   ```python
   def clean_clause_title(raw_title: str) -> str:
       """Remove PDF page number artifacts from clause titles"""
       
       # Remove page number patterns
       cleaned = re.sub(r'\.+\s*/?\d+$', '', raw_title)
       
       # Remove trailing dots and spaces
       cleaned = re.sub(r'[\.\s]+$', '', cleaned)
       
       # Standardize spacing
       cleaned = re.sub(r'\s+', ' ', cleaned).strip()
       
       return cleaned
   ```

2. **Clause Number Standardization**
   ```python
   def standardize_clause_number(clause_num: str) -> str:
       """Convert invalid clause numbers to valid DCP structure"""
       
       # Fix invalid sub-clause numbering
       if re.match(r'^\d+\.\d+\.\d+\.\d+$', clause_num):
           # Convert 4.2.4.2 -> 4.2.4(b), 4.2.4.3 -> 4.2.4(c)
           parts = clause_num.split('.')
           base_clause = '.'.join(parts[:3])  # 4.2.4
           sub_num = int(parts[3])
           sub_letter = chr(ord('a') + sub_num - 1)  # 1->a, 2->b, 3->c
           return f"{base_clause}({sub_letter})"
       
       return clause_num
   ```

### **Phase 3: Data Reprocessing**

1. **Clean All Processed Data Files**
   ```bash
   # Process all autoschemakg JSON files
   for file in autoschemakg_data_ollama_final/*.json; do
       python clause_cleanup_processor.py "$file"
   done
   
   # Process CSV triple files  
   for file in autoschemakg_output/triples_csv/*.csv; do
       python csv_clause_cleanup.py "$file"
   done
   ```

2. **Update Knowledge Graph Relations**
   ```python
   # Update LightRAG knowledge graph with corrected clauses
   def update_lightrag_clauses():
       rag = LightRAG(working_dir="./rag_storage")
       
       # Query and update all clause references
       corrected_clauses = load_corrected_clause_mapping()
       
       for old_clause, new_clause in corrected_clauses.items():
           rag.update_clause_references(old_clause, new_clause)
   ```

### **Phase 4: Validation & Testing**

1. **Automated Validation**
   ```python
   def validate_clause_corrections():
       """Ensure all clause numbers follow DCP standards"""
       
       valid_patterns = [
           r'^\d+\.\d+$',        # 4.2
           r'^\d+\.\d+\.\d+$',   # 4.2.4
           r'^\d+\.\d+\.\d+\([a-z]\)$'  # 4.2.4(a)
       ]
       
       # Check all clause references match valid patterns
       return validation_results
   ```

2. **Requirement Connection Testing**
   ```python
   def test_corrected_requirements():
       """Test that requirement connections work with corrected clauses"""
       
       # Test the specific case from user report
       test_cases = [
           "4.2.4 Building heights",  # Corrected from 4.2.4.2
           "4.2.4 Building setbacks", # Corrected from 4.2.4.3  
           "4.2.4 Floor space ratio"  # Corrected from 4.2.4.1
       ]
       
       for clause in test_cases:
           connections = get_requirement_connections(clause)
           assert len(connections) > 0, f"No connections found for {clause}"
   ```

## 📊 Implementation Priority

### **High Priority (Week 1)**
- [x] Identify all contaminated clause patterns
- [ ] Implement regex cleanup functions
- [ ] Process autoschemakg JSON files
- [ ] Update universal regulatory engine queries

### **Medium Priority (Week 2)**  
- [ ] Reprocess CSV triple files
- [ ] Update LightRAG knowledge graph
- [ ] Test requirement connections

### **Low Priority (Week 3)**
- [ ] Historical data cleanup
- [ ] Documentation updates
- [ ] Performance optimization

## 🎯 Expected Outcomes

### **Before Fix:**
```
CLAUSE 4.2.4.2 - HEIGHT LIMIT: 4.2.4.2 Building heights . 5
CLAUSE 4.2.4.3 - SETBACK: 4.2.4.3 Building setbacks.. 5
```

### **After Fix:**
```
CLAUSE 4.2.4(a) - HEIGHT LIMIT: Building heights
CLAUSE 4.2.4(b) - SETBACK: Building setbacks
```

### **Benefits:**
- ✅ Accurate clause references matching DCP structure
- ✅ Clean requirement connection displays
- ✅ Consistent regulatory data across all systems
- ✅ Improved council confidence in system accuracy

## 🚨 Risk Mitigation

1. **Backup Strategy**: Create full backup before processing
2. **Rollback Plan**: Keep original data files for restoration
3. **Validation Testing**: Comprehensive testing before deployment
4. **Gradual Rollout**: Process one document type at a time

---

**Next Action:** Implement Phase 1 - Source Verification  
**Timeline:** 3 weeks to completion  
**Review Date:** Weekly validation checkpoints  
**Success Criteria:** All clause numbers follow valid DCP structure