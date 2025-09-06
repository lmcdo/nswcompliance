#!/usr/bin/env python3
"""
Simple startup script for the NSW Planning Compliance Engine
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    print("NSW Planning Compliance Engine Startup")
    print("=" * 50)
    
    # Check if we're in the right directory
    current_dir = Path.cwd()
    if not (current_dir / "frontend" / "index.html").exists():
        print("ERROR: Please run this script from the compliance-engine directory")
        return
    
    # Check if FastAPI and uvicorn are installed
    try:
        import fastapi
        import uvicorn
        print("SUCCESS: FastAPI and uvicorn are available")
    except ImportError:
        print("ERROR: FastAPI or uvicorn not installed")
        print("HINT: Install with: pip install fastapi uvicorn")
        return
    
    # Start the server
    print("STARTING: NSW Planning Compliance Engine...")
    print("FRONTEND: http://localhost:8000")
    print("API DOCS: http://localhost:8000/docs")
    print("HEALTH: http://localhost:8000/health")
    print("")
    print("Press Ctrl+C to stop the server")
    print("=" * 50)
    
    try:
        # Change to frontend directory
        os.chdir("frontend")
        
        # Start uvicorn
        subprocess.run([
            sys.executable, "-m", "uvicorn",
            "server:app",
            "--host", "0.0.0.0", 
            "--port", "8000",
            "--reload"
        ])
    except KeyboardInterrupt:
        print("\nSERVER STOPPED by user")
    except Exception as e:
        print(f"ERROR starting server: {e}")

if __name__ == "__main__":
    main()