#!/usr/bin/env python3
"""
FastAPI server to bridge the frontend to the Ultimate NSW Processor
Connects Windows frontend to WSL2 Ultimate Processor (RagAnything + LightRAG)
"""

import asyncio
import json
import os
import sys
import subprocess
from typing import Dict, List, Optional, Union
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# Request/Response Models
class QueryRequest(BaseModel):
    address: str = Field(..., description="Property address to query")
    query_type: str = Field(..., description="Type of planning query")
    context: Optional[str] = Field(None, description="Additional context")

class PlanningRule(BaseModel):
    title: str
    text: str
    type: str
    source: Optional[str] = None
    confidence: Optional[float] = None
    citation_text: Optional[str] = None  # Full unsullied regulatory text
    citation_clause: Optional[str] = None  # Specific clause reference
    
    class Config:
        # Ensure optional fields are included in response
        json_encoders = {type(None): lambda x: None}

class QueryResponse(BaseModel):
    success: bool
    results: List[PlanningRule]
    address: str
    query_type: str
    processing_time: Optional[float] = None
    error: Optional[str] = None
    
    class Config:
        # Include all fields even if None
        fields = {'exclude_none': False}

# FastAPI App
app = FastAPI(
    title="NSW Planning Compliance Engine API",
    description="API bridge to Ultimate NSW Processor (RagAnything + LightRAG)",
    version="1.0.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global processor instance
ultimate_processor = None

async def initialize_ultimate_processor():
    """Initialize connection to the Ultimate NSW Processor running in WSL2"""
    global ultimate_processor
    
    try:
        # Try to connect to WSL2 Ultimate NSW Processor
        # The processor should be accessible via subprocess calls to WSL2
        print("INFO: Attempting to connect to Ultimate NSW Processor in WSL2...")
        
        # Test WSL2 connection and virtual environment
        result = subprocess.run([
            "wsl", "--", "bash", "-c", 
            "source /home/lawre/compliance_rag_env/bin/activate && python -c 'import lightrag; import raganything; print(\"SUCCESS: Packages available\")'"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("SUCCESS: Ultimate NSW Processor packages available in WSL2")
            print(f"Output: {result.stdout.strip()}")
            ultimate_processor = "WSL2_CONNECTION"  # Flag that WSL2 is available
            return True
        else:
            print(f"ERROR: WSL2 connection failed: {result.stderr}")
            print("WARNING: Ultimate NSW Processor not found, using mock responses")
            return False
            
    except Exception as e:
        print(f"ERROR: Failed to connect to WSL2 Ultimate NSW Processor: {e}")
        print("WARNING: Using mock responses")
        return False

async def query_ultimate_processor(address: str, query_type: str, context: Optional[str] = None) -> List[PlanningRule]:
    """Query the Ultimate NSW Processor running in WSL2"""
    print(f"DEBUG ENTRY: query_ultimate_processor called with address={address}, query_type={query_type}")
    global ultimate_processor
    
    if ultimate_processor != "WSL2_CONNECTION":
        # NEVER use mock data - return error instead
        print("ERROR: WSL2 Ultimate Processor not connected")
        return [PlanningRule(
            title="CONNECTION ERROR",
            text="Cannot connect to Ultimate NSW Processor in WSL2. The real regulatory processing system is not available.",
            type="error",
            source="System Error",
            confidence=0.0,
            citation_text="No connection to WSL2 Ultimate NSW Processor. No regulatory data available.",
            citation_clause="System Error"
        )]
    
    try:
        # Build query based on type
        if query_type == "height":
            query = f"What are the building height limits for {address}?"
        elif query_type == "fsr":
            query = f"What is the Floor Space Ratio (FSR) for {address}?"
        elif query_type == "setback":
            query = f"What are the boundary setback requirements for {address}?"
        elif query_type == "general":
            query = f"What are the general planning rules for {address}?"
        elif query_type == "all":
            query = f"What are all the planning controls (height, FSR, setbacks) for {address}?"
        else:
            query = f"What planning rules apply to {address}?"
            
        if context:
            query += f" Context: {context}"
            
        print(f"INFO: Querying WSL2 Ultimate NSW Processor: {query}")
        
        # Execute query in WSL2 environment
        # Use existing query_lep_lightrag_fixed.py script
        query_script_path = "/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/scripts/query_lep_lightrag_fixed.py"
        
        # Use the working_nsw_query.py script which is self-contained and tested
        query_command = f'''
import sys
import json
import asyncio

# Add current directory to path  
sys.path.insert(0, "scripts")

try:
    from working_nsw_query import query_nsw_lightrag_async
    
    # Execute the query
    result = asyncio.run(query_nsw_lightrag_async("{query}"))
    
    if result and len(result.strip()) > 0:
        response = {{
            "success": True,
            "query": "{query}",
            "query_type": "{query_type}",
            "address": "{address}",
            "results": [
                {{
                    "title": "NSW Planning Requirement",
                    "text": result,
                    "type": "{query_type}",
                    "source": "Inner West Local Environmental Plan 2022 (Ultimate NSW Processor)",
                    "confidence": 0.95,
                    "citation_text": result,
                    "citation_clause": "Ultimate NSW Processor - LightRAG Knowledge Base"
                }}
            ]
        }}
    else:
        response = {{
            "success": False,
            "error": "No results found in NSW knowledge base",
            "query": "{query}"
        }}
    
    print(json.dumps(response))
    
except Exception as e:
    import traceback
    error_response = {{
        "success": False,
        "error": f"Ultimate NSW Processor query failed: {{str(e)}}",
        "query": "{query}",
        "exception_type": type(e).__name__,
        "traceback": traceback.format_exc()
    }}
    print(json.dumps(error_response))
'''
        
        # Use the real knowledge base query script that reads actual content
        result = subprocess.run([
            "wsl", "--", "bash", "-c", 
            f"cd /home/lawre/compliance-engine && python3 scripts/query_real_nsw_kb.py '{query.replace(chr(39), chr(92)+chr(39))}' './production_nsw_processor'"
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            try:
                response_data = json.loads(result.stdout.strip())
                if response_data.get("success") and response_data.get("result"):
                    # Handle direct_nsw_query.py response format  
                    regulatory_text = response_data.get("result", "")
                    if regulatory_text and len(regulatory_text.strip()) > 0:
                        return [PlanningRule(
                            title="NSW Planning Requirement",
                            text=regulatory_text,
                            type=query_type,
                            source="Inner West Local Environmental Plan 2022 (Ultimate NSW Processor)",
                            confidence=0.95,
                            citation_text=regulatory_text,
                            citation_clause="Direct knowledge base access - NSW LEP 2022"
                        )]
                else:
                    print(f"ERROR: WSL2 processor returned error: {response_data.get('error')}")
            except json.JSONDecodeError as e:
                print(f"ERROR: Failed to parse WSL2 response: {e}")
                print(f"Raw output: {result.stdout}")
        else:
            print(f"ERROR: WSL2 execution failed: {result.stderr}")
            
        # NEVER use mock data - return error instead
        print("ERROR: WSL2 query failed, no regulatory data available")
        return [PlanningRule(
            title="QUERY FAILED",
            text=f"WSL2 Ultimate NSW Processor query failed. Cannot retrieve regulatory data for {address}.",
            type="error", 
            source="System Error",
            confidence=0.0,
            citation_text="WSL2 Ultimate NSW Processor query execution failed. No regulatory data available.",
            citation_clause="Query Error"
        )]
        
    except Exception as e:
        print(f"ERROR: Exception during WSL2 query: {e}")
        return [PlanningRule(
            title="SYSTEM ERROR",
            text=f"System error occurred while querying Ultimate NSW Processor: {str(e)}",
            type="error",
            source="System Error", 
            confidence=0.0,
            citation_text=f"Exception during WSL2 query: {str(e)}. No regulatory data available.",
            citation_clause="Exception Error"
        )]

# NO MOCK DATA EVER - REMOVED COMPLETELY

# API Endpoints
@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML"""
    from pathlib import Path
    from fastapi.responses import HTMLResponse
    
    html_file = Path("index.html")
    if html_file.exists():
        content = html_file.read_text(encoding='utf-8')
        return HTMLResponse(content=content)
    else:
        return {"error": "index.html not found", "cwd": str(Path.cwd())}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "processor_available": ultimate_processor is not None,
        "message": "NSW Planning Compliance Engine API is running"
    }

@app.post("/query")
async def query_planning_rules(request: QueryRequest):
    """Query NSW planning rules for a property"""
    
    try:
        import time
        start_time = time.time()
        
        # Validate inputs
        if not request.address.strip():
            raise HTTPException(status_code=400, detail="Address is required")
            
        # Query the Ultimate NSW Processor
        results = await query_ultimate_processor(
            request.address,
            request.query_type, 
            request.context
        )
        
        # Debug print
        print(f"Query for {request.address}, type: {request.query_type}")
        print(f"Returning {len(results)} results")
        if results and len(results) > 0:
            print(f"First result has citation_text: {'citation_text' in results[0].__dict__}")
        
        processing_time = time.time() - start_time
        
        # Convert results to dict to preserve all fields including None values
        results_dict = [r.dict(exclude_none=False) for r in results]
        
        return {
            "success": True,
            "results": results_dict,
            "address": request.address,
            "query_type": request.query_type,
            "processing_time": processing_time,
            "error": None
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Query processing failed: {str(e)}"
        )

@app.get("/test/{address}")
async def test_address(address: str):
    """Quick test endpoint for a specific address"""
    request = QueryRequest(
        address=address,
        query_type="all",
        context="test query"
    )
    return await query_planning_rules(request)

# Startup event
@app.on_event("startup")
async def startup_event():
    """Initialize the Ultimate NSW Processor on startup"""
    print("STARTING: NSW Planning Compliance Engine API...")
    await initialize_ultimate_processor()
    print("SUCCESS: API server ready on http://localhost:8003")
    print("FRONTEND: Available at http://localhost:8003")

if __name__ == "__main__":
    import uvicorn
    
    print("NSW Planning Compliance Engine")
    print("Bridging frontend to Ultimate NSW Processor")
    print("Starting server on http://localhost:8003")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=3000,
        reload=True,
        log_level="info"
    )# Force reload
