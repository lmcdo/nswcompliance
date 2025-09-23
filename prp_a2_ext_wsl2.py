#!/usr/bin/env python
"""
PRP-A2-EXT: Process 85 Marrickville DCP files using WSL2 environment as per PRP specification
The PRP clearly states to use WSL2 Ubuntu Environment - that's why mineru isn't working in Windows
"""

import subprocess
import json
import os
import asyncio
from pathlib import Path
from datetime import datetime

def run_in_wsl2():
 """Execute RagAnything processing in WSL2 as per PRP specification"""
 print("PRP-A2-EXT: USING WSL2 UBUNTU ENVIRONMENT (AS PER PRP SPEC)")
 print("=" * 70)
 print("Following PRP specification exactly - using WSL2 environment")
 print()
 
 # Create WSL2 Python script
 wsl_script = '''
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from raganything import RAGAnything
from raganything.config import RAGAnythingConfig

async def process_marrickville_wsl2():
 print("Processing in WSL2 Ubuntu environment...")
 
 # Initialize RagAnything (should work properly in WSL2)
 config = RAGAnythingConfig()
 rag = RAGAnything(config=config)
 
 # Convert Windows paths to WSL paths
 marrickville_dir = "/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/docs/dcps/INNERWEST/Marrickville"
 pdf_files = []
 
 import glob
 pdf_files = glob.glob(f"{marrickville_dir}/*.pdf")
 pdf_files.sort()
 
 print(f"Found {len(pdf_files)} Marrickville PDF files in WSL2")
 
 all_extracted_content = {}
 processed_count = 0
 
 for pdf_path in pdf_files[:5]: # Test with 5 files first
 filename = os.path.basename(pdf_path)
 print(f"Processing [{processed_count+1}/5]: {filename}")
 
 try:
 # Process with RagAnything
 extracted_content = await rag.parse_document(pdf_path)
 
 # Convert back to Windows path format for storage
 win_path = pdf_path.replace("/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/", "").replace("/", "\\\\")
 
 file_key = win_path.replace("\\\\", "_").replace(".pdf", "")
 all_extracted_content[file_key] = {
 "source_path": win_path,
 "content": extracted_content,
 "processed_timestamp": datetime.now().isoformat()
 }
 
 processed_count += 1
 print(f"SUCCESS: Completed {processed_count}/5 files")
 
 except Exception as e:
 print(f"FAILED: {filename} - {str(e)}")
 break
 
 # Save results
 output_file = "/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance engine/compliance-engine/validated_outputs/A2_EXT_wsl2_test.json"
 with open(output_file, "w", encoding="utf-8") as f:
 json.dump(all_extracted_content, f, indent=2, ensure_ascii=False)
 
 print(f"WSL2 Results: {processed_count}/5 files processed")
 print(f"Output: {output_file}")
 
 return processed_count > 0

if __name__ == "__main__":
 success = asyncio.run(process_marrickville_wsl2())
 if success:
 print("WSL2 processing successful!")
 else:
 print("WSL2 processing failed")
'''
 
 # Write WSL script to temp file
 with open("temp_wsl_script.py", "w") as f:
 f.write(wsl_script)
 
 # Execute in WSL2 as per PRP specification
 cmd = [
 "wsl", "--", "bash", "-c",
 "source /home/lawre/compliance_rag_env/bin/activate && python3 /mnt/c/Users/lawre/Downloads/solvyra/projects/compliance\\ engine/compliance-engine/temp_wsl_script.py"
 ]
 
 print("Executing in WSL2 Ubuntu environment...")
 result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
 
 print("WSL2 STDOUT:")
 print(result.stdout)
 
 if result.stderr:
 print("WSL2 STDERR:")
 print(result.stderr)
 
 # Clean up
 os.remove("temp_wsl_script.py")
 
 return result.returncode == 0

if __name__ == "__main__":
 success = run_in_wsl2()
 if success:
 print("\nPRP-A2-EXT: WSL2 processing completed successfully")
 else:
 print("\nPRP-A2-EXT: WSL2 processing failed")