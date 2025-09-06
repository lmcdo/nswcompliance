#!/usr/bin/env python
"""
Complete missing PDF extractions using MinerU directly
Processes only files that haven't been extracted yet
"""

import os
import subprocess
import json
from pathlib import Path
from datetime import datetime
import time

class CompleteMissingExtractions:
    def __init__(self):
        self.output_dir = Path("output")
        self.docs_dir = Path("docs/dcps/INNERWEST")
        self.progress_file = Path("validated_outputs/extraction_progress.json")
        self.completed = self.load_progress()
        
    def load_progress(self):
        """Load existing progress tracking"""
        if self.progress_file.exists():
            with open(self.progress_file, 'r') as f:
                return json.load(f)
        return {"completed": [], "failed": [], "stats": {}}
    
    def save_progress(self):
        """Save progress after each file"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.completed, f, indent=2)
    
    def update_progress_log(self, pdf_path, current_count, total_count):
        """Update progress log file in output directory"""
        log_path = self.output_dir / "extraction_progress_log.txt"
        
        # Get actual counts
        actual_dirs = len([d for d in self.output_dir.iterdir() if d.is_dir()])
        actual_md_files = len(list(self.output_dir.rglob("*.md")))
        
        # Get latest completed files from progress
        latest_completed = self.completed.get("completed", [])[-5:]
        
        log_content = f"""EXTRACTION PROGRESS LOG
========================
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

LATEST COMPLETED FILE:
----------------------
✅ {pdf_path.name}
   Output: output/{pdf_path.stem}/auto/
   MD File: {pdf_path.stem}.md

RECENT COMPLETIONS:
-------------------
{chr(10).join(f"{i+1}. {Path(f).name}" for i, f in enumerate(reversed(latest_completed[-5:])))}

ACTUAL FILE COUNT VERIFICATION:
-------------------------------
✅ Total MD files found: {actual_md_files} files
✅ Progress tracking: {len(self.completed.get("completed", []))} completed files
✅ Current batch: {current_count}/{total_count}

FAILED FILES:
-------------
{chr(10).join(f"- {Path(f).name}" for f in set(self.completed.get("failed", [])))}

NEXT FILES IN QUEUE:
--------------------
Continuing with remaining documents...
"""
        
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
    
    def get_all_pdfs(self):
        """Get all PDFs from all three councils"""
        pdfs = {
            "Ashfield": list(Path(self.docs_dir / "Ashfield").glob("*.pdf")),
            "Leichhardt": list(Path(self.docs_dir / "leichhardt").glob("*.pdf")) + 
                          list(Path(self.docs_dir / "leichhardt").glob("*.PDF")),
            "Marrickville": list(Path(self.docs_dir / "Marrickville").glob("*.pdf"))
        }
        return pdfs
    
    def check_if_processed(self, pdf_path):
        """Check if a PDF has already been processed"""
        pdf_name = pdf_path.stem
        
        # Check all directories in output folder (handle special chars)
        for output_dir in self.output_dir.iterdir():
            if output_dir.is_dir():
                # Normalize names for comparison (remove special chars)
                normalized_output = output_dir.name.replace("–", "-").replace("  ", " ").strip()
                normalized_pdf = pdf_name.replace("–", "-").replace("  ", " ").strip()
                
                if normalized_output.lower() == normalized_pdf.lower():
                    # Found matching directory, check if it has content
                    auto_dir = output_dir / "auto"
                    if auto_dir.exists():
                        md_files = list(auto_dir.glob("*.md"))
                        json_files = list(auto_dir.glob("*_content_list.json"))
                        # Check if we have substantial content (MD file > 500 bytes OR JSON content file exists)
                        if (md_files and md_files[0].stat().st_size > 500) or json_files:
                            return True
        
        # Also check completed list
        return str(pdf_path) in self.completed.get("completed", [])
    
    def extract_with_mineru(self, pdf_path):
        """Use MinerU directly to extract PDF content"""
        pdf_name = pdf_path.stem
        print(f"  Extracting with MinerU: {pdf_name}")
        
        # 🚨 CRITICAL: MUST USE WSL2 - Windows MinerU has antlr4 dependency conflicts!
        wsl_pdf_path = str(pdf_path).replace("\\", "/").replace("C:/", "/mnt/c/")
        wsl_output_path = "/mnt/c/Users/lawre/Downloads/solvyra/projects/compliance\ engine/compliance-engine/output"
        
        cmd = [
            "wsl", "--", "bash", "-c",
            f"source /home/lawre/compliance_rag_env/bin/activate && mineru -p '{wsl_pdf_path}' -o {wsl_output_path} -m auto"
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes per file
                encoding='utf-8',
                errors='ignore'
            )
            
            if result.returncode == 0:
                # MANDATORY: Verify actual output was created (PRP requirement)
                pdf_name = pdf_path.stem
                output_dir = self.output_dir / pdf_name
                auto_dir = output_dir / "auto"
                
                if not output_dir.exists():
                    print(f"    [FAIL] No output directory created despite exit code 0")
                    return False
                    
                if not auto_dir.exists():
                    print(f"    [FAIL] No auto subdirectory created")
                    return False
                
                # Check for substantial content
                md_files = list(auto_dir.glob("*.md"))
                json_files = list(auto_dir.glob("*_content_list.json"))
                
                if not md_files and not json_files:
                    print(f"    [FAIL] No MD or JSON content files created")
                    return False
                
                # Verify MD file has substantial content (PRP requirement: > 500 bytes)
                if md_files:
                    md_size = md_files[0].stat().st_size
                    if md_size < 500 and not json_files:
                        print(f"    [FAIL] MD file too small ({md_size} bytes) and no JSON files")
                        return False
                
                # MANDATORY VERIFICATION OUTPUT
                print(f"    [OK] Successfully extracted and verified")
                print(f"        Output dir: {output_dir}")
                print(f"        MD size: {md_files[0].stat().st_size if md_files else 0} bytes")
                print(f"        JSON files: {len(json_files)}")
                return True
            else:
                print(f"    [FAIL] MinerU error: {result.stderr[:200] if result.stderr else 'Unknown error'}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"    [FAIL] Timeout after 2 minutes")
            return False
        except Exception as e:
            print(f"    [FAIL] Error: {str(e)}")
            return False
    
    def process_missing_files(self):
        """Process only files that haven't been extracted yet"""
        print("=" * 70)
        print("COMPLETE MISSING EXTRACTIONS")
        print("=" * 70)
        
        all_pdfs = self.get_all_pdfs()
        
        # Calculate what needs processing
        stats = {
            "Ashfield": {"total": len(all_pdfs["Ashfield"]), "processed": 0, "needed": 0},
            "Leichhardt": {"total": len(all_pdfs["Leichhardt"]), "processed": 0, "needed": 0},
            "Marrickville": {"total": len(all_pdfs["Marrickville"]), "processed": 0, "needed": 0}
        }
        
        to_process = []
        
        for council, pdfs in all_pdfs.items():
            for pdf in pdfs:
                if self.check_if_processed(pdf):
                    stats[council]["processed"] += 1
                else:
                    stats[council]["needed"] += 1
                    to_process.append((council, pdf))
        
        # Show status
        print("\nCurrent Status:")
        for council, stat in stats.items():
            print(f"  {council}: {stat['processed']}/{stat['total']} completed, {stat['needed']} needed")
        
        total_needed = sum(s["needed"] for s in stats.values())
        
        if total_needed == 0:
            print("\n✓ All files already processed!")
            return True
        
        print(f"\nTotal files to process: {total_needed}")
        estimated_time = total_needed * 30  # 30 seconds per file average
        print(f"Estimated time: {estimated_time//60} minutes")
        
        # Process missing files
        print("\n" + "=" * 40)
        print("PROCESSING MISSING FILES")
        print("=" * 40)
        
        start_time = time.time()
        processed_count = 0
        failed_files = []
        
        for i, (council, pdf_path) in enumerate(to_process, 1):
            print(f"\n[{i}/{total_needed}] {council}: {pdf_path.name}")
            
            success = self.extract_with_mineru(pdf_path)
            
            if success:
                self.completed["completed"].append(str(pdf_path))
                processed_count += 1
            else:
                self.completed["failed"].append(str(pdf_path))
                failed_files.append(str(pdf_path))
            
            # Save progress after each file
            self.save_progress()
            
            # UPDATE PROGRESS LOG FILE AFTER EACH COMPLETION
            if success:
                self.update_progress_log(pdf_path, i, total_needed)
            
            # MANDATORY VERIFICATION REPORT every 5 files
            if i % 5 == 0:
                elapsed = time.time() - start_time
                rate = i / elapsed
                remaining = (total_needed - i) / rate if rate > 0 else 0
                
                # ACTUAL OUTPUT VERIFICATION
                actual_dirs = len([d for d in self.output_dir.iterdir() if d.is_dir()])
                actual_md_files = len(list(self.output_dir.rglob("*.md")))
                
                print(f"\n--- VERIFIED PROGRESS: {i}/{total_needed} files")
                print(f"    ACTUAL output dirs: {actual_dirs}")
                print(f"    ACTUAL MD files: {actual_md_files}")
                print(f"    Time elapsed: {elapsed//60:.0f} minutes")
                print(f"    Est. remaining: {remaining//60:.0f} minutes")
        
        # MANDATORY FINAL VERIFICATION
        elapsed_total = time.time() - start_time
        
        # ACTUAL OUTPUT COUNTS
        final_dirs = len([d for d in self.output_dir.iterdir() if d.is_dir()])
        final_md_files = len(list(self.output_dir.rglob("*.md")))
        final_json_files = len(list(self.output_dir.rglob("*_content_list.json")))
        
        print("\n" + "=" * 70)
        print("MANDATORY VERIFICATION REPORT")
        print("=" * 70)
        print(f"CLAIMED processed: {processed_count}/{total_needed} files")
        print(f"ACTUAL output dirs: {final_dirs}")
        print(f"ACTUAL MD files: {final_md_files}")
        print(f"ACTUAL JSON files: {final_json_files}")
        print(f"Failed: {len(failed_files)} files")
        print(f"Total time: {elapsed_total//60:.0f} minutes")
        
        # TRUTH CHECK
        discrepancy = processed_count - final_dirs
        if discrepancy > 0:
            print(f"🚨 VERIFICATION FAILED: {discrepancy} files claimed but directories missing!")
        else:
            print(f"✅ VERIFICATION PASSED: Claims match actual outputs")
        
        if failed_files:
            print("\nFailed files:")
            for f in failed_files[:10]:  # Show first 10
                print(f"  - {f}")
        
        # Update stats
        self.completed["stats"] = {
            "last_run": datetime.now().isoformat(),
            "processed": processed_count,
            "failed": len(failed_files),
            "total_time_seconds": elapsed_total
        }
        self.save_progress()
        
        # Create completion marker if all done
        if processed_count == total_needed:
            marker_path = Path("prp_checkpoints/A2_COMPLETE_all_extractions.marker")
            with open(marker_path, 'w') as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ")
                f.write(f"All Inner West DCPs extracted: ")
                f.write(f"Ashfield {stats['Ashfield']['total']}, ")
                f.write(f"Leichhardt {stats['Leichhardt']['total']}, ")
                f.write(f"Marrickville {stats['Marrickville']['total']}")
            print(f"\n✓ Completion marker created: {marker_path}")
        
        return processed_count > 0

if __name__ == "__main__":
    extractor = CompleteMissingExtractions()
    success = extractor.process_missing_files()
    
    if success:
        print("\n✓ Extraction process completed successfully")
    else:
        print("\n✗ Extraction process failed or no files to process")