#!/usr/bin/env python3
"""
Script to update setback data for the frontend
This can be run periodically or when DCPs are updated
"""

import os
import sys
import subprocess
import json
from datetime import datetime

def main():
    """Update setback data by running the processing pipeline"""
    print("NSW Development Compliance MVP - Data Update")
    print("=" * 50)
    
    # Check if we're in the correct directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    os.chdir(project_root)
    print(f"Working directory: {project_root}")
    
    # Check if virtual environment exists
    venv_python = os.path.join(project_root, "venv_linux", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        print("Virtual environment not found. Please set up venv_linux first.")
        return False
    
    # Check if docs directory exists
    docs_dir = os.path.join(project_root, "docs", "dcps", "INNERWEST")
    if not os.path.exists(docs_dir):
        print(f"Documents directory not found: {docs_dir}")
        print("Please ensure DCP documents are in the correct location.")
        return False
    
    # Check if output directory exists, create if not
    output_dir = os.path.join(project_root, "public", "regulatory-data")
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output directory: {output_dir}")
    
    try:
        print("\nRunning processing pipeline...")
        
        # Run the main processing script
        result = subprocess.run([
            venv_python,
            os.path.join("scripts", "process_inner_west_dcps.py")
        ], capture_output=True, text=True, cwd=project_root)
        
        if result.returncode == 0:
            print("Processing completed successfully!")
            print("\nProcessing output:")
            print(result.stdout)
            
            # Verify output files exist
            api_file = os.path.join(output_dir, "inner-west-setbacks.json")
            detailed_file = os.path.join(output_dir, "inner-west-setbacks-detailed.json")
            
            if os.path.exists(api_file) and os.path.exists(detailed_file):
                print(f"\nOutput files created:")
                print(f"   API data: {api_file}")
                print(f"   Detailed data: {detailed_file}")
                
                # Show summary stats
                with open(detailed_file, 'r') as f:
                    data = json.load(f)
                    metadata = data.get('processing_metadata', {})
                    areas_count = metadata.get('total_areas_processed', 0)
                    files_count = metadata.get('total_files_processed', 0)
                    confidence = metadata.get('avg_confidence', 0)
                    
                    print(f"\nSummary:")
                    print(f"   Council areas processed: {areas_count}")
                    print(f"   PDF files processed: {files_count}")
                    print(f"   Average confidence: {confidence:.2f}")
                
                return True
            else:
                print("Output files were not created properly")
                return False
        else:
            print("Processing failed!")
            print(f"Error output: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error running processing pipeline: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)