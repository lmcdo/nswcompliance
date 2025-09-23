"""
Create SQLite Database for Complete NSW Planning Documents
Store all 139 extracted planning documents in structured database.
"""

from db_config import get_connection # Unified PostgreSQL connection
import json
import os
from pathlib import Path
import time
try:
 import PyPDF2
except ImportError:
 PyPDF2 = None
try:
 import fitz # PyMuPDF
except ImportError:
 fitz = None

def extract_pdf_text(pdf_path):
 """Extract text from PDF using available libraries."""
 try:
 if fitz: # Try PyMuPDF first (better)
 doc = fitz.open(pdf_path)
 text = ""
 for page in doc:
 text += page.get_text()
 doc.close()
 return text
 elif PyPDF2: # Fallback to PyPDF2
 with open(pdf_path, 'rb') as file:
 reader = PyPDF2.PdfReader(file)
 text = ""
 for page in reader.pages:
 text += page.extract_text()
 return text
 except Exception as e:
 print(f"Error extracting PDF {pdf_path}: {e}")
 return ""
 return ""

def create_planning_database():
 """Create SQLite database schema for NSW planning documents."""
 
 get_connection()
 
 # Remove existing database to start fresh
 if os.path.exists(db_path):
 os.remove(db_path)
 print(f"Removed existing database: {db_path}")
 
 conn = get_connection()
 cursor = conn.cursor()
 
 # Create documents table
 cursor.execute('''
 CREATE TABLE documents (
 id TEXT PRIMARY KEY,
 pdf_name TEXT NOT NULL,
 document_type TEXT NOT NULL,
 document_area TEXT,
 pdf_path TEXT NOT NULL,
 char_count INTEGER,
 word_count INTEGER,
 total_regulatory_refs INTEGER,
 extraction_timestamp REAL,
 full_text TEXT NOT NULL
 )
 ''')
 
 # Create regulatory references table
 cursor.execute('''
 CREATE TABLE regulatory_refs (
 id SERIAL PRIMARY KEY SERIAL,
 document_id TEXT NOT NULL,
 ref_type TEXT NOT NULL,
 ref_number TEXT NOT NULL,
 ref_context TEXT,
 FOREIGN KEY (document_id) REFERENCES documents (id)
 )
 ''')
 
 # Create indexes for fast queries
 cursor.execute('CREATE INDEX idx_doc_type ON documents(document_type)')
 cursor.execute('CREATE INDEX idx_doc_area ON documents(document_area)')
 cursor.execute('CREATE INDEX idx_ref_type ON regulatory_refs(ref_type)')
 cursor.execute('CREATE INDEX idx_ref_number ON regulatory_refs(ref_number)')
 cursor.execute('CREATE INDEX idx_full_text ON documents(full_text)')
 
 conn.commit()
 print(f"Database schema created: {db_path}")
 return conn

def load_extraction_data():
 """Load extraction data from MinerU output format."""
 
 # Check for MinerU extraction output
 output_dir = "output"
 if os.path.exists(output_dir):
 print(f"Loading from MinerU output directory: {output_dir}")
 documents = {}
 
 # Scan all subdirectories for .md files
 for root, dirs, files in os.walk(output_dir):
 for file in files:
 if file.endswith(".md"):
 md_file_path = os.path.join(root, file)
 
 try:
 # Read the full markdown text
 with open(md_file_path, 'r', encoding='utf-8') as f:
 full_text = f.read()
 
 # Extract document info from filename
 pdf_name = file.replace(".md", ".pdf")
 
 # Determine document type from filename
 doc_type = "DCP" # Default
 # Note: "IWLEP amendments" means DCP with LEP amendments, not an actual LEP
 if ("LEP" in pdf_name or "Environmental Plan" in pdf_name) and "IWLEP" not in pdf_name:
 doc_type = "LEP"
 elif "SEPP" in pdf_name or "State Environmental" in pdf_name:
 doc_type = "SEPP"
 elif "Policy" in pdf_name:
 doc_type = "POLICY"
 
 # Extract area from filename
 doc_area = None
 if "Marrickville" in pdf_name:
 doc_area = "Marrickville"
 elif "Leichhardt" in pdf_name:
 doc_area = "Leichhardt"
 elif "Ashfield" in pdf_name:
 doc_area = "Ashfield"
 elif "Inner West" in pdf_name:
 doc_area = "Inner West"
 
 # Convert to expected format
 doc_result = {
 "pdf_name": pdf_name,
 "document_type": doc_type,
 "document_area": doc_area,
 "pdf_path": md_file_path,
 "extraction_timestamp": time.time(),
 "char_count": len(full_text),
 "word_count": len(full_text.split()),
 "full_text": full_text,
 "total_regulatory_refs": full_text.count("# C") + full_text.count("## C") + full_text.count("###"), # Count clause markers
 "extraction_success": True
 }
 
 documents[pdf_name] = doc_result
 
 except Exception as e:
 print(f"Error loading {md_file_path}: {e}")
 
 print(f"Loaded MinerU extraction data: {len(documents)} documents")
 
 # Also load PDFs directly from docs folder for SEPPs and LEPs
 docs_folders = [
 ("docs/sepps", "SEPP"),
 ("docs/lep", "LEP")
 ]
 
 for folder_path, doc_type in docs_folders:
 if os.path.exists(folder_path):
 print(f"Loading {doc_type} PDFs from: {folder_path}")
 
 for filename in os.listdir(folder_path):
 if filename.endswith(".pdf"):
 pdf_path = os.path.join(folder_path, filename)
 
 try:
 # Extract text directly from PDF
 full_text = extract_pdf_text(pdf_path)
 
 if full_text and len(full_text) > 1000: # Only include substantial PDFs
 
 # Extract area from filename
 doc_area = None
 if "Inner West" in filename:
 doc_area = "Inner West"
 elif "NSW" in filename:
 doc_area = "NSW"
 
 # Convert to expected format
 doc_result = {
 "pdf_name": filename,
 "document_type": doc_type,
 "document_area": doc_area,
 "pdf_path": pdf_path,
 "extraction_timestamp": time.time(),
 "char_count": len(full_text),
 "word_count": len(full_text.split()),
 "full_text": full_text,
 "total_regulatory_refs": full_text.count("Clause") + full_text.count("clause"),
 "extraction_success": True
 }
 
 documents[filename] = doc_result
 print(f" Loaded {filename}: {len(full_text):,} chars")
 else:
 print(f" Skipped {filename}: insufficient text")
 
 except Exception as e:
 print(f"Error loading {filename}: {e}")
 
 print(f"Total documents after adding PDFs: {len(documents)}")
 return {"individual_results": documents}
 
 # Fallback to AutoSchema data files
 autoschema_dir = "autoschema_database_output/input_texts"
 if os.path.exists(autoschema_dir):
 print(f"Loading from AutoSchema directory: {autoschema_dir}")
 documents = {}
 
 # Load all JSON files in the AutoSchema directory
 for json_file in os.listdir(autoschema_dir):
 if json_file.endswith(".json"):
 file_path = os.path.join(autoschema_dir, json_file)
 try:
 with open(file_path, 'r', encoding='utf-8') as f:
 doc_data = json.load(f)
 
 # Extract document info from metadata
 doc_title = doc_data.get("metadata", {}).get("title", "Unknown Document")
 doc_text = doc_data.get("text", "")
 doc_type = doc_data.get("metadata", {}).get("doc_type", "UNKNOWN")
 
 # Convert to expected format
 doc_result = {
 "pdf_name": doc_title,
 "document_type": doc_type,
 "document_area": None,
 "pdf_path": f"docs/{doc_title}",
 "extraction_timestamp": time.time(),
 "char_count": len(doc_text),
 "word_count": len(doc_text.split()),
 "full_text": doc_text,
 "total_regulatory_refs": doc_data.get("metadata", {}).get("num_clauses", 0),
 "extraction_success": True
 }
 
 documents[doc_title] = doc_result
 
 except Exception as e:
 print(f"Error loading {json_file}: {e}")
 
 print(f"Loaded AutoSchema data: {len(documents)} documents")
 return {"individual_results": documents}
 
 # Check for real-time verified output directory
 if os.path.exists("langextract_verified_output"):
 print("Loading from verified output directory...")
 documents = {}
 
 for json_file in os.listdir("langextract_verified_output"):
 if json_file.endswith("_verified.json"):
 file_path = os.path.join("langextract_verified_output", json_file)
 try:
 with open(file_path, 'r', encoding='utf-8') as f:
 file_data = json.load(f)
 # Convert to expected format
 doc_result = {
 "pdf_name": json_file.replace("_verified.json", ".pdf"),
 "extraction_timestamp": time.time(),
 "char_count": len(str(file_data)),
 "word_count": len(str(file_data).split()),
 "full_text": str(file_data),
 "provisions": file_data if isinstance(file_data, list) else [],
 "total_regulatory_refs": len(file_data) if isinstance(file_data, list) else 0,
 "extraction_success": True
 }
 documents[json_file.replace("_verified.json", ".pdf")] = doc_result
 except Exception as e:
 print(f"Error loading {json_file}: {e}")
 
 print(f"Loaded verified data: {len(documents)} documents")
 return {"individual_results": documents}
 
 # Fallback to old format
 summary_file = "extracted_texts_complete/NSW_PLANNING_COMPLETE_EXTRACTION.json"
 if os.path.exists(summary_file):
 with open(summary_file, 'r', encoding='utf-8') as f:
 data = json.load(f)
 print(f"Loaded extraction data: {len(data['individual_results'])} documents")
 return data
 
 raise Exception("No extraction data found")

def populate_database():
 """Populate database with extracted planning documents (excluding maps)."""
 
 print("CREATING NSW PLANNING DATABASE")
 print("="*50)
 
 # Create database
 conn = create_planning_database()
 cursor = conn.cursor()
 
 # Load extraction data
 extraction_data = load_extraction_data()
 
 documents_inserted = 0
 refs_inserted = 0
 maps_excluded = 0
 
 print(f"\nFiltering and inserting documents...")
 
 for doc_key, doc_data in extraction_data['individual_results'].items():
 
 # Skip map files (they contain street names, not regulatory content)
 pdf_name = doc_data.get('pdf_name', '')
 if any(map_type in pdf_name.lower() for map_type in ['map', 'cover', 'contents']):
 maps_excluded += 1
 print(f" EXCLUDED MAP: {pdf_name}")
 continue
 
 if not doc_data.get('extraction_success', False):
 continue
 
 # Generate document ID
 doc_id = doc_key.replace('.pdf', '').replace(' ', '_').replace('-', '_')
 
 # Insert document
 cursor.execute('''
 INSERT INTO documents (
 id, pdf_name, document_type, document_area, pdf_path,
 char_count, word_count, total_regulatory_refs, 
 extraction_timestamp, full_text
 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 ''', (
 doc_id,
 doc_data['pdf_name'],
 doc_data['document_type'],
 doc_data.get('document_area'),
 doc_data['pdf_path'],
 doc_data['char_count'],
 doc_data['word_count'],
 doc_data['total_regulatory_refs'],
 doc_data['extraction_timestamp'],
 doc_data['full_text']
 ))
 
 documents_inserted += 1
 
 # Insert regulatory references
 for ref_type in ['clauses', 'sections', 'subsections', 'schedules', 'parts']:
 refs = doc_data.get(ref_type, [])
 for ref_num in refs:
 cursor.execute('''
 INSERT INTO regulatory_refs (document_id, ref_type, ref_number)
 VALUES (?, ?, ?)
 ''', (doc_id, ref_type, ref_num))
 refs_inserted += 1
 
 # Progress update
 if documents_inserted % 20 == 0:
 print(f" Inserted {documents_inserted} documents...")
 
 conn.commit()
 
 # Verify database contents
 cursor.execute('SELECT COUNT(*) FROM documents')
 doc_count = cursor.fetchone()[0]
 
 cursor.execute('SELECT COUNT(*) FROM regulatory_refs')
 ref_count = cursor.fetchone()[0]
 
 cursor.execute('SELECT document_type, COUNT(*) FROM documents GROUP BY document_type')
 type_breakdown = cursor.fetchall()
 
 print(f"\nDATABASE POPULATED SUCCESSFULLY:")
 print(f" Documents: {doc_count}")
 print(f" Maps/covers excluded: {maps_excluded}")
 print(f" Regulatory references: {ref_count}")
 print(f"\nDocument breakdown:")
 for doc_type, count in type_breakdown:
 print(f" {doc_type}: {count} documents")
 
 conn.close()
 
 return {
 'database_path': 'nsw_planning.db',
 'documents_count': doc_count,
 'references_count': ref_count,
 'success': True
 }

def test_database_queries():
 """Test basic queries on the populated database."""
 
 print(f"\nTESTING DATABASE QUERIES:")
 print("="*30)
 
 conn = get_connection()
 cursor = conn.cursor()
 
 # Test queries
 queries = [
 ("Total documents", "SELECT COUNT(*) FROM documents"),
 ("DCP documents", "SELECT COUNT(*) FROM documents WHERE document_type = 'DCP'"),
 ("LEP documents", "SELECT COUNT(*) FROM documents WHERE document_type = 'LEP'"),
 ("SEPP documents", "SELECT COUNT(*) FROM documents WHERE document_type = 'SEPP'"),
 ("Documents with clauses", "SELECT COUNT(DISTINCT document_id) FROM regulatory_refs WHERE ref_type = 'clauses'"),
 ("Total clause references", "SELECT COUNT(*) FROM regulatory_refs WHERE ref_type = 'clauses'"),
 ("Heritage documents", "SELECT COUNT(*) FROM documents WHERE pdf_name LIKE '%Heritage%'")
 ]
 
 for query_name, sql in queries:
 cursor.execute(sql)
 result = cursor.fetchone()[0]
 print(f" {query_name}: {result}")
 
 conn.close()
 print(f"\nDatabase queries working correctly!")

if __name__ == "__main__":
 try:
 result = populate_database()
 if result['success']:
 test_database_queries()
 print(f"\nSQLite database ready: {result['database_path']}")
 else:
 print(f"Database creation failed")
 except Exception as e:
 print(f"ERROR: {e}")