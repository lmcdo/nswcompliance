import sqlite3

def check_langextract_status():
 conn = sqlite3.connect('nsw_planning.db')
 cur = conn.cursor()
 
 # Check table structure
 cols = cur.execute('PRAGMA table_info(documents)').fetchall()
 print('Document table columns:')
 for col in cols:
 print(f' {col[1]} ({col[2]})')
 
 # Count total documents
 total = cur.execute('SELECT COUNT(*) FROM documents').fetchone()[0]
 print(f'\nTotal documents: {total}')
 
 # Check if langextract processing column exists
 col_names = [col[1] for col in cols]
 if 'langextract_processed' in col_names:
 processed = cur.execute('SELECT COUNT(*) FROM documents WHERE langextract_processed = 1').fetchone()[0]
 print(f'LangExtract processed: {processed}')
 print(f'Processing rate: {processed/total*100:.1f}%' if total > 0 else 'No documents')
 else:
 print('No langextract_processed column found')
 
 # Show sample document data
 print('\nSample documents:')
 samples = cur.execute('SELECT * FROM documents LIMIT 3').fetchall()
 for sample in samples:
 print(f' {sample}')
 
 conn.close()

if __name__ == "__main__":
 check_langextract_status()