# Problem Resolution Procedures (PRPs) - WSL2 LightRAG Implementation
## NSW Property Compliance Engine: Complete Semantic Processing

### Executive Summary
This PRP series establishes the definitive path to implement **LightRAG + AutoSchemaKG + RagAnything** on **WSL2 Ubuntu** for real regulatory text processing. **No alternatives, no backsliding, no Windows native attempts**. Each PRP is a sequential gate that must be completed before proceeding.

### ** MANDATORY EXECUTION PROTOCOL**

** Before Starting Each Phase:**
1. **Read the phase objectives** - Understand what you're building
2. ⏰ **Set a timer** for the estimated duration 
3. **Confirm success criteria** are understood
4. **Update PRP_STATUS.md** to mark phase as "in_progress"

** After Each Phase:**
1. **Run the validation tests** - MUST pass to continue
2. **Update PRP_STATUS.md** with progress and actual time taken
3. **Document any issues encountered** in PRP_STATUS.md
4. ⏱ **Note actual time taken vs estimated** for future planning

** If Problems Occur:**
1. **STOP** - do NOT continue to next phase
2. **Document the exact error** in PRP_STATUS.md
3. **Focus on resolving current phase only** - no shortcuts
4. **Re-run validation tests** after fixes before proceeding

** VIOLATION OF PROTOCOL = RESTART FROM CURRENT PHASE**

---

## **PRP-001: WSL2 Foundation Setup**
**Objective**: Establish bulletproof WSL2 Ubuntu environment with all dependencies
**Duration**: 2-3 hours
**Success Criteria**: All packages installed, no errors, test scripts pass

### Phase 1A: WSL2 Installation & Configuration (45 min)
** PHASE PROTOCOL:** Read objectives → Set timer → Update status → Execute → Validate → Document

```powershell
# Windows PowerShell as Administrator
wsl --install -d Ubuntu-22.04
wsl --set-default-version 2
wsl --set-default Ubuntu-22.04
```

** Success Criteria**: WSL2 Ubuntu launches successfully, `wsl --list --verbose` shows Ubuntu-22.04 as default

### Phase 1B: Ubuntu Environment Setup (60 min)
** PHASE PROTOCOL:** Read objectives → Set timer → Update status → Execute → Validate → Document

```bash
# Inside WSL2 Ubuntu
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip
sudo apt install -y nodejs npm git curl wget
sudo apt install -y build-essential libpq-dev
sudo apt install -y libreoffice-headless # For RagAnything
```

** Success Criteria**: All packages install without errors, `python3.11 --version` returns Python 3.11.x

### Phase 1C: Python Environment Setup (30 min)
** PHASE PROTOCOL:** Read objectives → Set timer → Update status → Execute → Validate → Document

```bash
python3.11 -m venv /home/$USER/compliance_rag_env
source /home/$USER/compliance_rag_env/bin/activate
echo 'source /home/$USER/compliance_rag_env/bin/activate' >> ~/.bashrc
```

** Success Criteria**: Virtual environment activates, `which python` shows venv path, new terminal auto-activates

### Phase 1D: Core Package Installation (45 min)
** PHASE PROTOCOL:** Read objectives → Set timer → Update status → Execute → Validate → Document
**Note**: Based on existing installations found in project, use these corrected packages:
```bash
pip install --upgrade pip setuptools wheel

# Install LightRAG (confirmed working version)
pip install lightrag-hku

# Install RagAnything (confirmed version 1.2.7 working)
pip install raganything

# Install AutoSchemaKG from PyPI (atlas-rag package)
pip install atlas-rag

# Install LangExtract (confirmed version 1.0.8 working) 
pip install langextract
```

### Validation Tests
```bash
# Test 1: LightRAG import (use correct import)
python -c "from lightrag import LightRAG; print(' LightRAG OK')"

# Test 2: RagAnything import (use correct import)
python -c "from raganything import RAGAnything; print(' RagAnything OK')"

# Test 3: AutoSchemaKG import (use atlas-rag package)
python -c "from atlas_rag.kg_construction.triple_extraction import KnowledgeGraphExtractor; print(' AutoSchemaKG OK')"

# Test 4: LangExtract import
python -c "import langextract as lx; print(' LangExtract OK')"
```

**Gate**: All four validation tests must pass before PRP-002

---

## **PRP-002: Database Infrastructure Setup**
**Objective**: Install and configure PostgreSQL + Neo4j for production workloads
**Duration**: 1-2 hours
**Success Criteria**: Both databases running, test connections successful

### Phase 2A: PostgreSQL Installation (30 min)
```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create compliance database
sudo -u postgres createuser -s compliance_user
sudo -u postgres createdb nsw_planning_compliance -O compliance_user
sudo -u postgres psql -c "ALTER USER compliance_user PASSWORD 'ComplexPassword123!';"
```

### Phase 2B: Neo4j Installation (45 min)
```bash
# Install Java 11 (Neo4j requirement)
sudo apt install -y openjdk-11-jdk

# Add Neo4j repository
curl -fsSL https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable 4.4' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update

# Install Neo4j
sudo apt install -y neo4j=1:4.4.30
sudo systemctl enable neo4j
sudo systemctl start neo4j

# Set initial password
sudo neo4j-admin set-initial-password ComplexPassword123!
```

### Phase 2C: Connection Testing (15 min)
```python
# Test PostgreSQL
import psycopg2
conn = psycopg2.connect(
 host="localhost",
 database="nsw_planning_compliance", 
 user="compliance_user",
 password="ComplexPassword123!"
)
print(" PostgreSQL connection OK")

# Test Neo4j
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "ComplexPassword123!"))
print(" Neo4j connection OK")
```

**Gate**: Both database connections must succeed before PRP-003

---

## **PRP-003: Document Processing Pipeline**
**Objective**: Process NSW DCP/LEP/SEPP documents into semantic knowledge graph
**Duration**: 4-6 hours
**Success Criteria**: All documents processed, knowledge graph populated

### Phase 3A: Document Collection & Validation (60 min)
```bash
# Create document structure
mkdir -p /home/$USER/nsw_planning_docs/{dcps,leps,sepps}

# Verify existing document paths
ls -la "C:/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/docs/"

# Copy documents to WSL2 (via /mnt/c/ path)
cp -r /mnt/c/Users/lawre/Downloads/solvyra/projects/compliance\ engine/compliance-engine/docs/* /home/$USER/nsw_planning_docs/
```

### Phase 3B: RagAnything Document Processing (120 min)
```python
from raganything import DocumentProcessor

processor = DocumentProcessor()

# Process all NSW planning documents
def process_planning_documents():
 doc_types = {
 'dcps': '/home/user/nsw_planning_docs/dcps',
 'leps': '/home/user/nsw_planning_docs/leps', 
 'sepps': '/home/user/nsw_planning_docs/sepps'
 }
 
 processed_docs = {}
 for doc_type, path in doc_types.items():
 processed_docs[doc_type] = processor.process_directory(
 path,
 output_format='structured_text',
 extract_tables=True,
 extract_images=True
 )
 
 return processed_docs
```

### Phase 3C: AutoSchemaKG Knowledge Graph Construction (180 min)
```python
from autoschemakg import AutoSchemaKG

# Initialize AutoSchemaKG for NSW planning
schema_kg = AutoSchemaKG(
 llm_config={
 "provider": "openai",
 "model": "gpt-4-turbo",
 "api_key": "your-api-key",
 "temperature": 0.1
 },
 extraction_config={
 "entity_types": ["legal_provision", "development_standard", "zone", "setback_rule"],
 "relationship_types": ["applies_to", "permits", "prohibits", "requires", "refers_to"],
 "conceptualization_level": "high"
 }
)

# Process documents and build knowledge graph
triples, schema = schema_kg.process_documents(processed_docs)
```

### Phase 3D: LightRAG Integration (120 min)
```python
from lightrag import LightRAG

lightrag = LightRAG(
 working_dir="./lightrag_nsw_planning",
 llm_model_func=openai_llm_func,
 embedding_func=openai_embedding_func
)

# Index all processed documents
for doc_content in all_processed_docs:
 await lightrag.ainsert(doc_content)
```

### Validation Tests
```python
# Test 1: Knowledge graph populated
assert len(triples) > 1000, "Knowledge graph too small"

# Test 2: LightRAG queries work
result = await lightrag.aquery("What are the front setback requirements for dwelling houses?")
assert len(result) > 100, "Query results too short"

# Test 3: Schema extraction successful
assert "setback_rule" in schema.entity_types, "Missing setback rules in schema"
```

**Gate**: All validation tests pass, knowledge graph contains >1000 triples

---

## **PRP-004: Python API Server Implementation**
**Objective**: FastAPI server exposing semantic compliance queries
**Duration**: 2-3 hours 
**Success Criteria**: API running, test queries return real regulatory text

### Phase 4A: FastAPI Server Structure (60 min)
```python
# /home/user/compliance_api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio

app = FastAPI(title="NSW Planning Compliance API")

class ComplianceQuery(BaseModel):
 question: str
 area: str = None # Ashfield, Leichhardt, Marrickville
 development_type: str = "dwelling_house"
 rule_type: str = None # height, fsr, front_setback, side_setback, rear_setback

@app.post("/compliance/query")
async def query_compliance(query: ComplianceQuery):
 # Route to appropriate processor based on rule type
 if query.rule_type in ["height", "fsr"]:
 result = await query_lep(query.question, query.rule_type)
 elif query.rule_type in ["front_setback", "side_setback", "rear_setback"]:
 result = await query_dcp(query.question, query.area, query.rule_type)
 else:
 result = await query_general(query.question)
 
 return {
 "answer": result.text,
 "confidence": result.confidence,
 "source_documents": result.sources,
 "exact_citation": result.citation
 }
```

### Phase 4B: Semantic Query Processors (90 min)
```python
async def query_lep(question: str, rule_type: str):
 """Query LEP using LightRAG for height/FSR rules"""
 result = await lightrag.aquery(
 f"Extract the exact clause text for {rule_type} requirements from Inner West LEP 2022",
 param=QueryParam(mode="hybrid", only_need_context=False)
 )
 
 # Extract exact citation using AutoSchemaKG
 citation = schema_kg.extract_citation(result, rule_type)
 
 return ComplianceResult(
 text=result,
 confidence=calculate_confidence(result),
 sources=extract_sources(result),
 citation=citation
 )

async def query_dcp(question: str, area: str, rule_type: str):
 """Query DCP using knowledge graph traversal"""
 # Use Neo4j to find related rules
 cypher_query = f"""
 MATCH (rule:SetbackRule)-[:APPLIES_TO]->(area:Area {{name: '{area}'}})
 WHERE rule.type = '{rule_type}'
 RETURN rule.exact_text, rule.source_clause, rule.confidence
 """
 
 graph_result = neo4j_driver.run(cypher_query)
 
 if graph_result:
 return ComplianceResult(
 text=graph_result['rule.exact_text'],
 confidence=graph_result['rule.confidence'],
 citation=graph_result['rule.source_clause']
 )
 else:
 # Fallback to LightRAG
 return await lightrag.aquery(f"{area} DCP {rule_type} setback requirements")
```

### Phase 4C: Server Deployment (30 min)
```bash
# Install uvicorn
pip install uvicorn[standard]

# Start API server
cd /home/$USER/compliance_api
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Test server
curl http://localhost:8000/docs # Should show FastAPI docs
```

### Validation Tests
```bash
# Test 1: Height query
curl -X POST "http://localhost:8000/compliance/query" \
 -H "Content-Type: application/json" \
 -d '{"question":"height requirements","rule_type":"height"}'

# Test 2: Setback query 
curl -X POST "http://localhost:8000/compliance/query" \
 -H "Content-Type: application/json" \
 -d '{"question":"front setback","area":"Marrickville","rule_type":"front_setback"}'
```

**Gate**: Both test queries return real regulatory text (not "not available")

---

## **PRP-005: TypeScript Integration Bridge**
**Objective**: Connect Windows TypeScript app to WSL2 Python API
**Duration**: 1-2 hours
**Success Criteria**: Frontend shows real regulatory text from WSL2 backend

### Phase 5A: TypeScript Service Update (45 min)
```typescript
// Update Windows: lib/regulatory-text-retriever.ts
export class RegulatoryTextRetriever {
 private apiBaseUrl = 'http://localhost:8000';

 async getHeightRegulatoryText(): Promise<RegulatoryTextMatch | null> {
 const response = await fetch(`${this.apiBaseUrl}/compliance/query`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 question: 'height requirements for buildings',
 rule_type: 'height'
 })
 });

 const result = await response.json();
 
 return {
 text: result.exact_citation,
 source: result.source_documents[0],
 confidence: result.confidence,
 chunk_id: 'wsl2_lightrag_height'
 };
 }

 async getSetbackRegulatoryText(ruleType: string, formerCouncilArea: string): Promise<RegulatoryTextMatch | null> {
 const response = await fetch(`${this.apiBaseUrl}/compliance/query`, {
 method: 'POST', 
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify({
 question: `${ruleType} setback requirements`,
 area: formerCouncilArea,
 rule_type: `${ruleType}_setback`
 })
 });

 const result = await response.json();
 
 return {
 text: result.exact_citation,
 source: `${formerCouncilArea} DCP - ${result.source_documents[0]}`,
 confidence: result.confidence,
 chunk_id: `wsl2_lightrag_${ruleType}_${formerCouncilArea.toLowerCase()}`
 };
 }
}
```

### Phase 5B: Error Handling & Fallbacks (30 min)
```typescript
// Add robust error handling for WSL2 connection issues
private async queryWSL2API(endpoint: string, payload: any): Promise<any> {
 try {
 const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
 method: 'POST',
 headers: { 'Content-Type': 'application/json' },
 body: JSON.stringify(payload),
 timeout: 10000 // 10 second timeout
 });

 if (!response.ok) {
 throw new Error(`WSL2 API error: ${response.status}`);
 }

 return await response.json();
 } catch (error) {
 console.error('WSL2 API connection failed:', error);
 
 // Fallback to old direct access method
 console.warn('Falling back to direct storage access');
 return this.fallbackDirectAccess(payload);
 }
}
```

### Phase 5C: Integration Testing (15 min)
```bash
# Start both servers
# WSL2: uvicorn main:app --host 0.0.0.0 --port 8000
# Windows: npm run dev -- --port 3000

# Test integration via browser
# Navigate to: http://localhost:3000/property/enhanced
```

### Validation Tests
1. **Frontend Query Test**: Property page shows real regulatory text from WSL2
2. **Performance Test**: Queries respond within 5 seconds
3. **Fallback Test**: Windows app still works if WSL2 is down

**Gate**: Real regulatory text displayed in frontend, sourced from WSL2 semantic processing

---

## **PRP-006: Anti-Hallucination Validation**
**Objective**: Ensure all regulatory text is grounded in actual documents
**Duration**: 2-3 hours
**Success Criteria**: 100% source attribution, confidence >80% for all responses

### Phase 6A: Source Attribution Validation (90 min)
```python
class SourceAttributionValidator:
 def validate_response(self, query_result):
 """Ensure every claim is backed by source document"""
 
 claims = self.extract_claims(query_result.answer)
 attributions = []
 
 for claim in claims:
 # Find exact source location
 source_match = self.find_in_source_docs(claim, query_result.source_documents)
 
 attributions.append({
 "claim": claim,
 "source_found": source_match is not None,
 "exact_location": source_match.location if source_match else None,
 "confidence": source_match.confidence if source_match else 0.0
 })
 
 # Fail if any claim lacks proper attribution
 unattributed_claims = [a for a in attributions if not a["source_found"]]
 
 if unattributed_claims:
 raise HallucinationError(f"Unattributed claims detected: {unattributed_claims}")
 
 return attributions
```

### Phase 6B: Confidence Thresholds (60 min)
```python
# Set strict confidence thresholds
CONFIDENCE_THRESHOLDS = {
 "height": 0.85, # LEP rules are clearer
 "fsr": 0.85, # LEP rules are clearer 
 "front_setback": 0.80, # DCP rules more complex
 "side_setback": 0.80,
 "rear_setback": 0.80
}

def validate_confidence(query_result, rule_type):
 required_confidence = CONFIDENCE_THRESHOLDS.get(rule_type, 0.75)
 
 if query_result.confidence < required_confidence:
 return {
 "approved": False,
 "reason": f"Confidence {query_result.confidence} below threshold {required_confidence}",
 "recommendation": "Manual review required"
 }
 
 return {"approved": True}
```

### Phase 6C: Automated Testing Pipeline (30 min)
```python
# Test known regulatory requirements
TEST_CASES = [
 {
 "query": "height requirements Inner West LEP",
 "expected_contains": ["Height of Buildings Map", "Clause 4.3"],
 "rule_type": "height"
 },
 {
 "query": "front setback Marrickville dwelling house", 
 "expected_contains": ["front boundary", "metres"],
 "area": "Marrickville",
 "rule_type": "front_setback"
 }
]

async def run_validation_tests():
 for test_case in TEST_CASES:
 result = await compliance_api.query(test_case["query"])
 
 # Check expected content present
 for expected in test_case["expected_contains"]:
 assert expected in result.answer, f"Missing expected content: {expected}"
 
 # Check confidence threshold
 validation = validate_confidence(result, test_case["rule_type"])
 assert validation["approved"], f"Confidence validation failed: {validation['reason']}"
 
 print(f" Test passed: {test_case['query']}")
```

**Gate**: All validation tests pass, no hallucination detected

---

## **PRP-007: Production Deployment & Monitoring**
**Objective**: Production-ready deployment with monitoring and maintenance
**Duration**: 1-2 hours
**Success Criteria**: System runs reliably, monitoring in place

### Phase 7A: Service Management (45 min)
```bash
# Create systemd service for API server
sudo tee /etc/systemd/system/compliance-api.service << EOF
[Unit]
Description=NSW Compliance API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/home/$USER/compliance_api
Environment=PATH=/home/$USER/compliance_rag_env/bin
ExecStart=/home/$USER/compliance_rag_env/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable compliance-api
sudo systemctl start compliance-api
```

### Phase 7B: Health Monitoring (30 min)
```python
# Add health check endpoint
@app.get("/health")
async def health_check():
 health_status = {
 "api_status": "healthy",
 "lightrag_status": await test_lightrag_connection(),
 "neo4j_status": await test_neo4j_connection(),
 "postgresql_status": await test_postgresql_connection()
 }
 
 overall_healthy = all(status == "healthy" for status in health_status.values())
 
 if not overall_healthy:
 raise HTTPException(status_code=503, detail=health_status)
 
 return health_status
```

### Phase 7C: Performance Optimization (15 min)
```python
# Add caching for frequently queried rules
from functools import lru_cache

@lru_cache(maxsize=100)
async def cached_compliance_query(question: str, rule_type: str, area: str = None):
 return await process_compliance_query(question, rule_type, area)
```

**Gate**: System running as service, health checks passing

---

## **Success Criteria Summary**

### **Technical Validation**
- [ ] WSL2 Ubuntu environment fully configured
- [ ] All packages (LightRAG, AutoSchemaKG, RagAnything) working
- [ ] PostgreSQL + Neo4j databases operational
- [ ] NSW planning documents processed into knowledge graph
- [ ] Python API server responding to queries
- [ ] TypeScript integration returning real regulatory text
- [ ] All regulatory text properly attributed to source documents
- [ ] Confidence scores >80% for all rule types

### **Functional Validation**
- [ ] Height requirements return exact LEP clause text
- [ ] FSR requirements return exact LEP clause text 
- [ ] Setback requirements return exact DCP clause text for all areas
- [ ] Frontend displays real regulatory citations (no "not available")
- [ ] Query responses within 5 seconds
- [ ] System handles 100+ concurrent queries

### **Quality Validation** 
- [ ] Zero hallucinated regulatory content
- [ ] 100% source attribution for all claims
- [ ] No regex-based processing (full semantic understanding)
- [ ] Professional-grade legal citations
- [ ] Handles complex conditional clauses and exceptions

---

## **Critical Success Factors**

1. **No Backsliding**: If any PRP fails, must resolve before proceeding to next PRP
2. **No Alternative Approaches**: WSL2 only, no Windows native attempts
3. **Semantic-Only Processing**: No regex extraction, full LightRAG/AutoSchemaKG pipeline
4. **Source Grounding**: Every regulatory claim must trace to exact document location
5. **Production Quality**: System must handle real user queries reliably

This PRP structure ensures systematic implementation without misunderstandings or divergence from the semantic processing approach.

---

## **Implementation Timeline**

### **Week 1: Foundation**
- Day 1: PRP-001 WSL2 Foundation Setup
- Day 2: PRP-002 Database Infrastructure 
- Day 3-4: PRP-003 Document Processing (Phase A-B)
- Day 5: PRP-003 Document Processing (Phase C-D)

### **Week 2: Integration** 
- Day 1: PRP-004 Python API Server
- Day 2: PRP-005 TypeScript Integration
- Day 3: PRP-006 Anti-Hallucination Validation
- Day 4: PRP-007 Production Deployment
- Day 5: End-to-end testing and optimization

**Total Implementation Time**: 13-21 hours across 2 weeks