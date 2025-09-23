#!/usr/bin/env python3
"""
AutoSchema + RAG-Anything Multimodal Integration
Combines AutoSchema KG with RAG-Anything image and context extraction
"""

import json
import os
import sqlite3
from typing import Dict, List, Optional, Tuple
from pathlib import Path

class MultimodalKnowledgeGraph:
 def __init__(self):
 self.db_path = "nsw_planning.db"
 self.raganything_output = "output"
 self.autoschema_path = "autoschema_database_output"
 
 # Load multimodal relationships
 self.multimodal_data = self._load_multimodal_relationships()
 
 # Load AutoSchema data
 self.autoschema_nodes = self._load_autoschema_nodes()
 self.autoschema_edges = self._load_autoschema_edges()
 
 # Build image-clause index
 self.image_clause_index = self._build_image_clause_index()
 
 def _load_multimodal_relationships(self) -> Dict:
 """Load RAG-Anything multimodal relationships"""
 multimodal_path = "multimodal_relationships_complete.json"
 
 if os.path.exists(multimodal_path):
 with open(multimodal_path, 'r', encoding='utf-8') as f:
 return json.load(f)
 return {"documents": {}}
 
 def _load_autoschema_nodes(self) -> Dict:
 """Load AutoSchema knowledge graph nodes"""
 nodes = {}
 nodes_path = os.path.join(self.autoschema_path, "nodes.json")
 
 if os.path.exists(nodes_path):
 with open(nodes_path, 'r', encoding='utf-8') as f:
 data = json.load(f)
 for node in data:
 nodes[node['id']] = node
 return nodes
 
 def _load_autoschema_edges(self) -> List:
 """Load AutoSchema knowledge graph edges"""
 edges_path = os.path.join(self.autoschema_path, "edges.json")
 
 if os.path.exists(edges_path):
 with open(edges_path, 'r', encoding='utf-8') as f:
 return json.load(f)
 return []
 
 def _build_image_clause_index(self) -> Dict:
 """Build index mapping images to their surrounding clause context"""
 index = {}
 
 for doc_name, doc_data in self.multimodal_data.get("documents", {}).items():
 if "content_sequence" not in doc_data:
 continue
 
 sequence = doc_data["content_sequence"]
 
 # Track current clause context
 current_clause = None
 current_section = None
 
 for i, item in enumerate(sequence):
 # Update clause/section context
 if item["type"] == "text":
 text = item.get("text", "").lower()
 
 # Check for clause markers
 if "clause" in text or "section" in text:
 import re
 
 # Extract clause number
 clause_match = re.search(r'clause\s+(\d+(?:\.\d+)*)', text, re.IGNORECASE)
 if clause_match:
 current_clause = clause_match.group(1)
 
 section_match = re.search(r'section\s+(\d+(?:\.\d+)*)', text, re.IGNORECASE)
 if section_match:
 current_section = section_match.group(1)
 
 # Index images with their clause context
 elif item["type"] == "image":
 img_path = item.get("img_path", "")
 if img_path:
 # Get surrounding text context
 context_before = self._get_text_context(sequence, i, -3, 0)
 context_after = self._get_text_context(sequence, i, 1, 4)
 
 index[img_path] = {
 "document": doc_name,
 "page": item.get("page_idx", 0),
 "clause": current_clause,
 "section": current_section,
 "context_before": context_before,
 "context_after": context_after,
 "full_path": os.path.join(self.raganything_output, doc_name, "auto", img_path)
 }
 
 return index
 
 def _get_text_context(self, sequence: List, current_idx: int, start_offset: int, end_offset: int) -> str:
 """Get text context around a specific position in the sequence"""
 context_parts = []
 
 for offset in range(start_offset, end_offset):
 idx = current_idx + offset
 if 0 <= idx < len(sequence):
 item = sequence[idx]
 if item["type"] == "text" and item.get("text"):
 context_parts.append(item["text"].strip())
 
 return " ".join(context_parts)
 
 def find_images_for_clause(self, clause_number: str) -> List[Dict]:
 """Find all images related to a specific clause"""
 results = []
 
 # Normalize clause number
 clause_num = clause_number.replace("Clause", "").replace("clause", "").strip()
 
 for img_path, img_data in self.image_clause_index.items():
 # Check direct clause match
 if img_data.get("clause") == clause_num:
 results.append({
 "image": img_path,
 "match_type": "direct_clause",
 **img_data
 })
 # Check context mentions
 elif clause_num in img_data.get("context_before", "") or clause_num in img_data.get("context_after", ""):
 results.append({
 "image": img_path,
 "match_type": "context_mention",
 **img_data
 })
 
 return results
 
 def find_clauses_with_images(self) -> Dict[str, List]:
 """Find all clauses that have associated images"""
 clauses_with_images = {}
 
 for img_path, img_data in self.image_clause_index.items():
 clause = img_data.get("clause")
 if clause:
 if clause not in clauses_with_images:
 clauses_with_images[clause] = []
 clauses_with_images[clause].append({
 "image": img_path,
 "document": img_data["document"],
 "page": img_data["page"]
 })
 
 return clauses_with_images
 
 def get_multimodal_clause_info(self, clause_ref: str) -> Dict:
 """Get comprehensive clause information including text, images, and relationships"""
 
 result = {
 "clause": clause_ref,
 "text_content": None,
 "images": [],
 "relationships": [],
 "autoschema_entities": []
 }
 
 # Find images
 result["images"] = self.find_images_for_clause(clause_ref)
 
 # Find AutoSchema entities
 clause_lower = clause_ref.lower()
 for node_id, node_data in self.autoschema_nodes.items():
 if clause_lower in node_id.lower() or clause_lower in str(node_data).lower():
 result["autoschema_entities"].append(node_data)
 
 # Find relationships
 for edge in self.autoschema_edges:
 if clause_lower in str(edge).lower():
 result["relationships"].append(edge)
 
 # Get text content from database
 conn = sqlite3.connect(self.db_path)
 cursor = conn.cursor()
 
 # Search for clause in extracted text
 cursor.execute("""
 SELECT pdf_name, full_text 
 FROM documents 
 WHERE full_text LIKE ? 
 LIMIT 5
 """, (f'%{clause_ref}%',))
 
 text_results = cursor.fetchall()
 if text_results:
 result["text_content"] = [
 {"document": pdf_name, "excerpt": self._extract_clause_excerpt(full_text, clause_ref)}
 for pdf_name, full_text in text_results
 ]
 
 conn.close()
 
 return result
 
 def _extract_clause_excerpt(self, full_text: str, clause_ref: str, context_chars: int = 500) -> str:
 """Extract text excerpt around a clause reference"""
 import re
 
 # Find clause position
 pattern = re.compile(re.escape(clause_ref), re.IGNORECASE)
 match = pattern.search(full_text)
 
 if match:
 start = max(0, match.start() - context_chars)
 end = min(len(full_text), match.end() + context_chars)
 excerpt = full_text[start:end]
 
 # Clean up excerpt
 if start > 0:
 excerpt = "..." + excerpt
 if end < len(full_text):
 excerpt = excerpt + "..."
 
 return excerpt.strip()
 
 return ""
 
 def search_multimodal(self, query: str) -> Dict:
 """Search across text, images, and knowledge graph"""
 results = {
 "images": [],
 "clauses": [],
 "entities": [],
 "relationships": []
 }
 
 query_lower = query.lower()
 
 # Search images by context
 for img_path, img_data in self.image_clause_index.items():
 if (query_lower in img_data.get("context_before", "").lower() or 
 query_lower in img_data.get("context_after", "").lower()):
 results["images"].append({
 "image": img_path,
 **img_data
 })
 
 # Search AutoSchema entities
 for node_id, node_data in self.autoschema_nodes.items():
 if query_lower in str(node_data).lower():
 results["entities"].append(node_data)
 
 # Search relationships
 for edge in self.autoschema_edges:
 if query_lower in str(edge).lower():
 results["relationships"].append(edge)
 
 # Limit results
 for key in results:
 results[key] = results[key][:10]
 
 return results
 
 def get_statistics(self) -> Dict:
 """Get statistics about the multimodal knowledge graph"""
 
 # Count images by document
 images_by_doc = {}
 for img_data in self.image_clause_index.values():
 doc = img_data["document"]
 images_by_doc[doc] = images_by_doc.get(doc, 0) + 1
 
 # Count clauses with images
 clauses_with_images = len(self.find_clauses_with_images())
 
 return {
 "total_images": len(self.image_clause_index),
 "total_documents": len(self.multimodal_data.get("documents", {})),
 "total_autoschema_nodes": len(self.autoschema_nodes),
 "total_autoschema_edges": len(self.autoschema_edges),
 "clauses_with_images": clauses_with_images,
 "images_by_document": images_by_doc
 }


def main():
 """Test the multimodal integration"""
 
 print("MULTIMODAL KNOWLEDGE GRAPH INTEGRATION")
 print("=" * 50)
 
 # Initialize
 mkg = MultimodalKnowledgeGraph()
 
 # Get statistics
 stats = mkg.get_statistics()
 print(f"\nStatistics:")
 print(f" Total images indexed: {stats['total_images']}")
 print(f" Total documents: {stats['total_documents']}")
 print(f" AutoSchema nodes: {stats['total_autoschema_nodes']}")
 print(f" AutoSchema edges: {stats['total_autoschema_edges']}")
 print(f" Clauses with images: {stats['clauses_with_images']}")
 
 # Test clause search
 print(f"\nTesting clause image search...")
 test_clauses = ["4.2", "2.1", "3.5"]
 
 for clause in test_clauses:
 images = mkg.find_images_for_clause(clause)
 if images:
 print(f"\nClause {clause}: {len(images)} images found")
 for img in images[:2]:
 print(f" - {img['image']} (page {img['page']})")
 
 # Test multimodal search
 print(f"\nTesting multimodal search for 'setback'...")
 results = mkg.search_multimodal("setback")
 
 print(f" Images: {len(results['images'])}")
 print(f" Entities: {len(results['entities'])}")
 print(f" Relationships: {len(results['relationships'])}")
 
 # Show clauses with images
 print(f"\nClauses with associated images:")
 clauses_with_imgs = mkg.find_clauses_with_images()
 for clause, images in list(clauses_with_imgs.items())[:5]:
 print(f" Clause {clause}: {len(images)} images")
 
 print("\nMultimodal integration complete!")
 print("Use mkg.get_multimodal_clause_info(clause) to get full clause details")


if __name__ == "__main__":
 main()