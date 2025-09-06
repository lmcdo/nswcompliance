# AutoSchemaKG Knowledge Graph Construction - Client Guide

## Overview
AutoSchemaKG is a 5-step pipeline that transforms regulatory documents into structured knowledge graphs. It extracts entities, relationships, and concepts to create queryable knowledge representations.

---

## Step 1: Triple Extraction (`run_extraction()`)

### What It Does
Analyzes regulatory text and extracts structured relationships between entities.

### Input
- Raw regulatory text from documents (e.g., "Development applications must comply with height limits")

### Process
1. **Entity-Relation Extraction**: Identifies specific entities and their relationships
   - Example: `{"Head": "development applications", "Relation": "must comply with", "Tail": "height limits"}`

2. **Event-Entity Extraction**: Identifies events and participating entities
   - Example: `{"Event": "Development applications must be assessed", "Entity": ["applications", "assessment", "council"]}`

3. **Event-Relation Extraction**: Identifies temporal/causal relationships between events
   - Example: `{"Head": "application submitted", "Relation": "before", "Tail": "assessment begins"}`

### Output
- JSON files containing structured relationship triplets
- Typical output: 1,725+ regulatory provisions from 217 NSW planning documents

---

## Step 2: CSV Conversion (`convert_json_to_csv()`)

### What It Does
Converts JSON relationship data into CSV format and creates temporary knowledge graph.

### Process
1. **Relationship Processing**: Converts JSON triplets into CSV rows
2. **Node Creation**: Creates unique identifiers for all entities, events, and relations
3. **Graph Construction**: Builds temporary NetworkX graph for relationship mapping
4. **Missing Concept Identification**: Identifies nodes that need concept definitions

### Output Files
- `triple_nodes_*.csv` - All unique entities/events/relations
- `triple_edges_*.csv` - All relationships between nodes  
- `missing_concepts_*.csv` - Nodes requiring semantic concept mapping
- `*_without_concept.pkl` - Temporary graph for Step 3 context

---

## Step 3: Concept Generation (`generate_concept_csv_temp()`)

### What It Does
Creates semantic abstractions for regulatory terms to improve searchability and connections.

### AI-Powered Semantic Mapping Process

#### For Events (Regulatory Actions):
**Prompt Template:**
```
EVENT: Development applications must be assessed
Your answer: assessment, evaluation, review, regulation, approval
```

#### For Entities (Regulatory Terms):
**Prompt Template:**
```  
ENTITY: residential development
CONTEXT: controlled by height limits, regulated by zoning
Your answer: housing, construction, zoning, development, planning
```

#### For Relations (Regulatory Connections):
**Prompt Template:**
```
RELATION: controlled by
Your answer: regulation, governance, restriction, management, oversight
```

### Context Enrichment
- **For entities**: AutoSchemaKG adds context from knowledge graph neighbors
- Example: "residential development" gets context like "controlled by height limits, applies to zoning"

### Real NSW Planning Examples Generated:
- `"heritage conservation" → "preservation, conservation, protection, restoration, heritage"`
- `"building setbacks" → "setbacks, heritage, zoning, development, accessibility"`  
- `"environmental protection" → "conservation, regulation, compliance, sustainability, responsibility"`

### Output
- `concept_shard_0.csv` containing 4,888+ semantic concept mappings
- Format: `original_term, "concept1, concept2, concept3", type`

---

## Step 4: Concept CSV Creation (`create_concept_csv()`)

### What It Does
Merges concept definitions with original relationship data to create enriched knowledge graph structure.

### Process
1. **Concept Merging**: Combines concept definitions from Step 3 with original triplets
2. **Node Enrichment**: Adds semantic concepts as additional node properties
3. **CSV Restructuring**: Creates final CSV files with both original and conceptualized data

### Output Files
- `concept_nodes_*.csv` - Nodes with semantic concept mappings
- `concept_edges_*.csv` - Edges connecting conceptualized nodes
- `triple_edges_*_with_concept.csv` - Original relationships enriched with concepts

---

## Step 5: GraphML Conversion (`convert_to_graphml()`)

### What It Does
Converts CSV knowledge graph data into GraphML format for visualization and advanced querying.

### Process
1. **Graph Assembly**: Combines all nodes (entities, concepts, text) and edges into unified graph
2. **Format Conversion**: Converts to GraphML standard format
3. **Metadata Preservation**: Maintains all relationship types and concept mappings
4. **Visualization Preparation**: Structure enables network visualization tools

### Output
- `nsw_planning_docs_graph.graphml` - Complete knowledge graph in GraphML format
- Compatible with tools like: Gephi, Cytoscape, NetworkX, Neo4j

---

## Key Benefits of AutoSchemaKG Process

### 1. **Enhanced Searchability**
- Query "conservation" finds all heritage-related provisions across documents
- Search by concept rather than exact terminology

### 2. **Relationship Discovery**
- Automatically identifies connections between related regulatory requirements
- Maps dependencies and cross-references between planning provisions

### 3. **Semantic Understanding**
- Converts legal jargon into accessible concepts
- Example: "Floor Space Ratio" → "density, development, regulation, control"

### 4. **Knowledge Graph Navigation**
- Visual exploration of regulatory relationships
- Path finding between related requirements

### 5. **Compliance Analysis**
- Identify all requirements affecting a specific development type
- Trace regulatory pathways and dependencies

---

## Technical Architecture

### Processing Scale
- **Documents**: 217 NSW planning documents processed
- **Relationships**: 1,725+ regulatory provisions extracted
- **Concepts**: 4,888+ unique semantic mappings generated
- **Processing Time**: ~4 hours for complete pipeline

### AI Integration
- **Local Model**: Ollama Llama 3.1-8B for cost-effective processing
- **No API Costs**: Fully local processing, no external API dependencies
- **Quality Control**: Consistent semantic concept generation

### Output Integration
- **GraphML**: Industry-standard knowledge graph format
- **CSV Files**: Structured data for analysis and integration
- **Visualization Ready**: Compatible with major graph visualization tools

---

## Use Cases

### 1. **Regulatory Compliance**
- Find all requirements for specific development types
- Identify conflicting or overlapping regulations

### 2. **Planning Analysis**
- Understand regulatory relationships across multiple councils
- Compare planning approaches between jurisdictions

### 3. **Development Guidance**
- Navigate complex regulatory requirements
- Identify all applicable provisions for a development proposal

### 4. **Policy Research**
- Analyze regulatory patterns and relationships
- Support evidence-based policy development

---

## Next Steps: Integration with RAG Systems

The AutoSchemaKG knowledge graph serves as input for:
- **RAG-Anything**: Document processing and indexing
- **LangExtract**: Source citation and grounding
- **LightRAG**: Conversational query interface

This creates a complete pipeline from raw regulatory documents to intelligent, queryable compliance systems.