#!/usr/bin/env python3
"""
Simple WSL2 Query Wrapper for NSW Planning Compliance Engine
This script is called from Windows and executes queries in WSL2
"""
import sys
import subprocess
import json
import tempfile
import os

def main():
    if len(sys.argv) < 2:
        print(json.dumps({"success": False, "error": "No query provided"}))
        return
    
    query = sys.argv[1]
    
    try:
        # Execute query directly in WSL2 using the symlink path
        escaped_query = query.replace("'", "\\'")
        wsl_command = f"cd /home/lawre/compliance-engine && python3 -c \"import sys; sys.path.insert(0, 'scripts'); from working_nsw_query import query_nsw_lightrag_async; import asyncio; import json; result = asyncio.run(query_nsw_lightrag_async('{escaped_query}')) or 'No results'; print(json.dumps({{'success': True, 'result': result}}))\"" 
        
        cmd = ["wsl", "--", "bash", "-c", wsl_command]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            # Parse the output and return it
            try:
                data = json.loads(result.stdout.strip())
                print(json.dumps(data))
            except json.JSONDecodeError:
                print(json.dumps({
                    "success": False, 
                    "error": "Failed to parse WSL2 response",
                    "raw_output": result.stdout[:200]
                }))
        else:
            print(json.dumps({
                "success": False, 
                "error": f"WSL2 execution failed: {result.stderr[:200]}"
            }))
            
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))

if __name__ == "__main__":
    main()