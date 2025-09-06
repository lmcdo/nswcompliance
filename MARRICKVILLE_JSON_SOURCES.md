# COMPREHENSIVE MARRICKVILLE JSON SOURCES WITH SETBACK DATA

## VERIFIED FILES WITH ACTUAL SETBACK MEASUREMENTS

### AutoSchemaKG Data Files (Contains 900mm, 1.5m, 2.5m setbacks)
```
./autoschemakg_data_ollama_final/nsw_planning_docs_006.json
./autoschemakg_data_ollama_final/nsw_planning_docs_014.json  
./autoschemakg_data_ollama_final/nsw_planning_docs_018.json
./autoschemakg_data_ollama_final/nsw_planning_docs_019.json
./autoschemakg_data_ollama_final/nsw_planning_docs_027.json
./autoschemakg_data_ollama_final/nsw_planning_docs_030.json
./autoschemakg_data_ollama_final/nsw_planning_docs_032.json
./autoschemakg_data_ollama_final/nsw_planning_docs_044.json
```

### LangExtract Verified Output Files
```
./langextract_verified_output/Marrickville DCP 2011 - 10.0 Definitions_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 2 5 Equity of Access and Mobility_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 2 6 Acoustic and Visual Privacy_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 5 0 Commercial and Mixed Use Development - with IWLEP 2022 amendments_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 8.0 Heritage - Part2 (pages 63-124)_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 8.0 Heritage - Part4 (pages 187-248)_verified.json
./langextract_verified_output/Marrickville DCP 2011 - 9 27 Barwon Park South_verified.json
```

### Structured Output Files  
```
./output/Marrickville DCP 2011 - 4.1 Low Density Residential Development/auto/Marrickville DCP 2011 - 4.1 Low Density Residential Development_model.json
./output/Marrickville DCP 2011 - 4 2 Multi Dwelling Housing and RFBs - with IWLEP 2022 amendments/auto/Marrickville DCP 2011 - 4 2 Multi Dwelling Housing and RFBs - with IWLEP 2022 amendments_model.json
./output/Marrickville DCP 2011 - 4 3 Boarding Houses/auto/Marrickville DCP 2011 - 4 3 Boarding Houses_model.json
```

### RAG Storage Files
```
./rag_storage/vdb_relationships.json
./rag_storage/vdb_entities.json  
./rag_storage/vdb_chunks.json
./rag_fixed_storage/vdb_relationships.json
./rag_fixed_storage/vdb_entities.json
./rag_fixed_storage/vdb_chunks.json
```

### Validated Output Files
```
./validated_outputs/A2_ALL_DCP_complete_extracted_content.json
./validated_outputs/A2_EXT_marrickville_raganything_format.json
./validated_outputs/A2_EXT_marrickville_complete.json
./validated_outputs/large_files_split.json
```

## MISSING FROM CURRENT EXTRACTION

**Current Status**: Only importing from 2 sources:
- `public/regulatory-data/inner-west-compliance-rules.json` (6 rules for Ashfield & Leichhardt only)
- `compliance_result.json` (no additional rules extracted)

**Required**: Extract from ALL AutoSchemaKG files above which contain the actual Marrickville setback measurements (900mm, 1.5m, 2.5m)