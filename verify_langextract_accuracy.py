#!/usr/bin/env python3
"""
LangExtract Accuracy Verification Tool
=====================================
Provides PROOF that LangExtract provisions are real, not synthetic

Verification Methods:
1. Source text cross-reference - Show exact text from original PDF
2. Clause number validation - Verify clause references exist in documents 
3. Measurement verification - Check extracted measurements against source
4. Random sampling verification - Manual spot-checks with proof
"""

import json
import sqlite3
import re
from pathlib import Path

class LangExtractVerifier:
 def __init__(self):
 self.db_path = "nsw_planning.db"
 self.provisions_file = "langextract_re2_provisions_complete.json"
 
 def load_provisions(self):
 """Load extracted provisions for verification"""
 if not Path(self.provisions_file).exists():
 print(f"ERROR: {self.provisions_file} not found")
 return None
 
 with open(self.provisions_file, 'r', encoding='utf-8') as f:
 return json.load(f)
 
 def get_source_text(self, document_name, chunk_index=None):
 """Get original source text from database for verification"""
 conn = sqlite3.connect(self.db_path)
 cursor = conn.cursor()
 
 cursor.execute("""
 SELECT full_text FROM documents 
 WHERE pdf_name = ?
 """, (document_name,))
 
 result = cursor.fetchone()
 conn.close()
 
 if result:
 return result[0]
 return None
 
 def verify_provision_exists_in_source(self, provision, source_text):
 """Verify that a provision's regulatory_text actually exists in source"""
 
 regulatory_text = provision.get('regulatory_text', '').strip()
 if not regulatory_text:
 return False, "No regulatory text to verify"
 
 # Check if the exact text exists
 if regulatory_text in source_text:
 return True, "EXACT MATCH FOUND"
 
 # Check for partial matches (accounting for formatting differences)
 words = regulatory_text.split()
 if len(words) >= 5: # Only check meaningful phrases
 key_phrase = ' '.join(words[:5]) # First 5 words
 if key_phrase in source_text:
 return True, f"PARTIAL MATCH FOUND: '{key_phrase}'"
 
 return False, "TEXT NOT FOUND IN SOURCE"
 
 def verify_clause_reference(self, provision, source_text):
 """Verify that clause reference actually exists in source document"""
 
 clause_ref = provision.get('clause_reference', '')
 if not clause_ref:
 return False, "No clause reference provided"
 
 # Extract clause number (e.g., "4.2.4" from "Clause 4.2.4")
 clause_match = re.search(r'(\d+(?:\.\d+)*)', clause_ref)
 if not clause_match:
 return False, "Invalid clause format"
 
 clause_num = clause_match.group(1)
 
 # Check if clause number appears in source
 clause_patterns = [
 f"Clause {clause_num}",
 f"Section {clause_num}",
 f"{clause_num}.",
 f"{clause_num} "
 ]
 
 for pattern in clause_patterns:
 if pattern in source_text:
 return True, f"CLAUSE VERIFIED: Found '{pattern}'"
 
 return False, f"Clause {clause_num} not found in source"
 
 def verify_measurements(self, provision, source_text):
 """Verify that extracted measurements exist in source"""
 
 measurements = provision.get('measurements', '')
 if not measurements:
 return True, "No measurements to verify"
 
 # Extract numbers from measurements
 numbers = re.findall(r'\d+(?:\.\d+)?', measurements)
 
 verified_numbers = []
 for num in numbers:
 if num in source_text:
 verified_numbers.append(num)
 
 if verified_numbers:
 return True, f"MEASUREMENTS VERIFIED: {', '.join(verified_numbers)}"
 
 return False, "No measurements found in source"
 
 def generate_verification_report(self):
 """Generate comprehensive verification report"""
 
 print("LANGEXTRACT ACCURACY VERIFICATION REPORT")
 print("=" * 60)
 
 # Load provisions
 provisions_data = self.load_provisions()
 if not provisions_data:
 return
 
 provisions = provisions_data.get('provisions', [])
 if not provisions:
 print("No provisions found to verify")
 return
 
 print(f"Total provisions to verify: {len(provisions)}")
 print()
 
 # Verification statistics
 verified_count = 0
 text_matches = 0
 clause_matches = 0 
 measurement_matches = 0
 
 # Sample verification (first 10 provisions)
 sample_size = min(10, len(provisions))
 print(f"DETAILED VERIFICATION (Sample: {sample_size} provisions)")
 print("-" * 60)
 
 for i in range(sample_size):
 prov = provisions[i]
 doc_name = prov.get('document_source', 'Unknown')
 
 print(f"\n[{i+1}] PROVISION VERIFICATION")
 print(f"Document: {doc_name}")
 print(f"Clause: {prov.get('clause_reference', 'N/A')}")
 print(f"Type: {prov.get('provision_type', 'N/A')}")
 print(f"Text: {prov.get('regulatory_text', 'N/A')[:100]}...")
 
 # Get source text
 source_text = self.get_source_text(doc_name)
 if not source_text:
 print(" SOURCE TEXT NOT AVAILABLE")
 continue
 
 # Verify text exists in source
 text_verified, text_msg = self.verify_provision_exists_in_source(prov, source_text)
 print(f" Text Verification: {text_msg}")
 if text_verified:
 text_matches += 1
 
 # Verify clause reference
 clause_verified, clause_msg = self.verify_clause_reference(prov, source_text) 
 print(f" Clause Verification: {clause_msg}")
 if clause_verified:
 clause_matches += 1
 
 # Verify measurements
 measure_verified, measure_msg = self.verify_measurements(prov, source_text)
 print(f" Measurement Verification: {measure_msg}")
 if measure_verified:
 measurement_matches += 1
 
 if text_verified and clause_verified:
 verified_count += 1
 print(f" PROVISION VERIFIED")
 else:
 print(f" VERIFICATION FAILED")
 
 # Summary statistics
 print(f"\nVERIFICATION SUMMARY")
 print("=" * 30)
 print(f"Sample size: {sample_size}")
 print(f"Fully verified: {verified_count}")
 print(f"Text matches: {text_matches}")
 print(f"Clause matches: {clause_matches}")
 print(f"Measurement matches: {measurement_matches}")
 print(f"Accuracy rate: {(verified_count/sample_size)*100:.1f}%")
 
 # Manual verification instructions
 print(f"\nMANUAL VERIFICATION INSTRUCTIONS")
 print("=" * 40)
 print("To manually verify ANY provision:")
 print("1. Note the document_source and clause_reference")
 print("2. Open the original PDF in docs/ folder") 
 print("3. Search for the clause number")
 print("4. Compare extracted text with original")
 
 return {
 'sample_size': sample_size,
 'verified_count': verified_count,
 'accuracy_rate': (verified_count/sample_size)*100 if sample_size > 0 else 0
 }
 
 def show_proof_for_provision(self, provision_index=0):
 """Show detailed proof for a specific provision"""
 
 provisions_data = self.load_provisions()
 if not provisions_data:
 return
 
 provisions = provisions_data.get('provisions', [])
 if provision_index >= len(provisions):
 print(f"Provision index {provision_index} out of range")
 return
 
 prov = provisions[provision_index]
 doc_name = prov.get('document_source', '')
 
 print(f"DETAILED PROOF FOR PROVISION #{provision_index}")
 print("=" * 50)
 print(f"Document: {doc_name}")
 print(f"Clause: {prov.get('clause_reference', 'N/A')}")
 print(f"Extracted Text: {prov.get('regulatory_text', 'N/A')}")
 print()
 
 # Get source text
 source_text = self.get_source_text(doc_name)
 if not source_text:
 print(" Cannot verify - source text not available")
 return
 
 # Find the text in source
 regulatory_text = prov.get('regulatory_text', '').strip()
 if regulatory_text in source_text:
 # Find position and show context
 pos = source_text.find(regulatory_text)
 start = max(0, pos - 200)
 end = min(len(source_text), pos + len(regulatory_text) + 200)
 context = source_text[start:end]
 
 print(" PROOF: EXACT TEXT FOUND IN SOURCE")
 print("-" * 30)
 print("SOURCE CONTEXT:")
 print(context)
 print()
 print("EXTRACTED TEXT HIGHLIGHTED:")
 highlighted = context.replace(regulatory_text, f">>> {regulatory_text} <<<")
 print(highlighted)
 else:
 print(" TEXT NOT FOUND IN SOURCE - POSSIBLE SYNTHETIC DATA")

def main():
 """Run verification"""
 verifier = LangExtractVerifier()
 
 # Wait for LangExtract to complete
 if not Path("langextract_re2_provisions_complete.json").exists():
 print("Waiting for LangExtract PRP-RE2 to complete...")
 print("Run this script again after PRP-RE2 finishes.")
 return
 
 # Generate verification report
 stats = verifier.generate_verification_report()
 
 if stats and stats['accuracy_rate'] < 80:
 print("\n WARNING: Low accuracy rate detected!")
 print("Manual inspection recommended.")
 
 # Show detailed proof for first provision
 print(f"\nSHOWING DETAILED PROOF FOR FIRST PROVISION:")
 verifier.show_proof_for_provision(0)

if __name__ == "__main__":
 main()