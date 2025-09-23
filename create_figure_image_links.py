#!/usr/bin/env python3
"""
Figure-Image Linking System
===========================
Creates connections between LangExtract provisions mentioning figures
and their corresponding RAG-Anything extracted images.

For frontend display when querying "Figure (1.1a)" provisions.
"""

import json
import re
import os
from pathlib import Path
from typing import Dict, List, Tuple

class FigureImageLinker:
 def __init__(self):
 self.langextract_file = "langextract_realtime_verified_provisions.json"
 self.raganything_output = Path("output")
 self.figure_image_links = {}
 
 def create_figure_image_links(self):
 """Create links between figure references and actual images"""
 
 print("CREATING FIGURE-IMAGE LINKS")
 print("=" * 50)
 
 # Load LangExtract provisions
 if not Path(self.langextract_file).exists():
 print(f"LangExtract file not found: {self.langextract_file}")
 return
 
 with open(self.langextract_file, 'r', encoding='utf-8') as f:
 langextract_data = json.load(f)
 
 provisions = langextract_data.get('verified_provisions', [])
 print(f"Processing {len(provisions)} verified provisions...")
 
 figure_provisions = []
 
 # Find provisions that reference figures
 for prov in provisions:
 text = prov.get('regulatory_text', '') + ' ' + prov.get('applies_to', '')
 
 # Look for figure references
 figure_matches = re.findall(r'[Ff]igure\s*\(?(\d+\.\d+[a-z]?)\)?', text)
 
 if figure_matches:
 for fig_ref in figure_matches:
 figure_provisions.append({
 'provision': prov,
 'figure_ref': fig_ref,
 'document': prov.get('document_source', '')
 })
 print(f"Found Figure {fig_ref} in {prov.get('document_source', '')}")
 
 print(f"\nFound {len(figure_provisions)} provisions with figure references")
 
 # Link each figure reference to images
 linked_count = 0
 for fig_prov in figure_provisions:
 
 doc_name = fig_prov['document'].replace('.pdf', '')
 figure_ref = fig_prov['figure_ref']
 
 # Find corresponding RAG-Anything content
 content_file = self.raganything_output / doc_name / "auto" / f"{doc_name}_content_list.json"
 
 if content_file.exists():
 linked_images = self.find_figure_images(content_file, figure_ref)
 
 if linked_images:
 key = f"{doc_name}::Figure_{figure_ref}"
 self.figure_image_links[key] = {
 'provision': fig_prov['provision'],
 'figure_reference': figure_ref,
 'document': doc_name,
 'linked_images': linked_images,
 'image_paths': [img['full_path'] for img in linked_images]
 }
 linked_count += 1
 print(f" Linked Figure {figure_ref} to {len(linked_images)} images")
 else:
 print(f" No images found for Figure {figure_ref} in {doc_name}")
 
 print(f"\nSuccessfully linked {linked_count} figure references to images")
 
 # Save links
 links_file = "figure_image_links.json"
 with open(links_file, 'w', encoding='utf-8') as f:
 json.dump({
 'metadata': {
 'total_figure_provisions': len(figure_provisions),
 'successfully_linked': linked_count,
 'created_at': '2025-09-01T08:30:00'
 },
 'links': self.figure_image_links
 }, f, indent=2, ensure_ascii=False)
 
 print(f"\nFigure-image links saved to: {links_file}")
 return self.figure_image_links
 
 def find_figure_images(self, content_file: Path, figure_ref: str) -> List[Dict]:
 """Find images related to a specific figure reference"""
 
 try:
 with open(content_file, 'r', encoding='utf-8') as f:
 content_sequence = json.load(f)
 except Exception as e:
 print(f"Error reading {content_file}: {e}")
 return []
 
 linked_images = []
 
 # Search for figure reference in content sequence
 for i, item in enumerate(content_sequence):
 if item.get('type') == 'text':
 text = item.get('text', '').lower()
 
 # Check if this text mentions the figure
 figure_patterns = [
 f'figure ({figure_ref}',
 f'figure {figure_ref}',
 f'figure({figure_ref})',
 f'({figure_ref})'
 ]
 
 if any(pattern in text for pattern in figure_patterns):
 # Look for nearby images (within 5 items before/after)
 search_range = range(max(0, i-5), min(len(content_sequence), i+6))
 
 for j in search_range:
 if content_sequence[j].get('type') == 'image':
 img_path = content_sequence[j].get('img_path', '')
 if img_path:
 # Create full path for web serving
 doc_name = content_file.parent.parent.name
 full_path = f"output/{doc_name}/auto/{img_path}"
 
 linked_images.append({
 'img_path': img_path,
 'full_path': full_path,
 'page_idx': content_sequence[j].get('page_idx', 0),
 'proximity_to_figure': abs(i - j),
 'content_index': j
 })
 
 # Sort by proximity to figure reference
 linked_images.sort(key=lambda x: x['proximity_to_figure'])
 
 return linked_images[:3] # Return top 3 closest images
 
 def demonstrate_usage(self):
 """Show how the figure-image links work"""
 
 if not self.figure_image_links:
 print("No figure-image links created yet")
 return
 
 print("\nDEMONSTRATION: Frontend Query Example")
 print("=" * 50)
 
 # Find a good example
 for key, link_data in list(self.figure_image_links.items())[:3]:
 
 provision = link_data['provision']
 figure_ref = link_data['figure_reference']
 images = link_data['linked_images']
 
 print(f"\n QUERY RESULT FOR: 'Figure {figure_ref}'")
 print("-" * 30)
 print(f" Regulatory Requirement:")
 print(f" Clause: {provision.get('clause_reference', 'N/A')}")
 print(f" Text: {provision.get('regulatory_text', '')[:100]}...")
 print(f" Document: {provision.get('document_source', '')}")
 
 print(f"\n Related Figures:")
 for i, img in enumerate(images):
 print(f" [{i+1}] {img['full_path']}")
 print(f" Page: {img['page_idx']}")
 print(f" Proximity: {img['proximity_to_figure']} items from figure reference")
 
 print(f"\n Frontend Display:")
 print(f" - Show regulatory text")
 print(f" - Display {len(images)} related diagram(s)")
 print(f" - User can see both rule and visual context")

def main():
 """Create figure-image links"""
 
 linker = FigureImageLinker()
 
 # Create the links
 links = linker.create_figure_image_links()
 
 # Demonstrate usage
 if links:
 linker.demonstrate_usage()
 
 print(f"\n INTEGRATION COMPLETE")
 print(f"Frontend can now display:")
 print(f" - LangExtract provisions (rules)")
 print(f" - RAG-Anything images (visual context)")
 print(f" - Automatic figure-image connections")
 else:
 print("\n No figure-image links created")

if __name__ == "__main__":
 main()