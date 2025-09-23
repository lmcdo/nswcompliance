#!/usr/bin/env python3
"""
Clause Image API - Serves clause-image relationships via HTTP
"""

from flask import Flask, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
import json
from pathlib import Path
from autoschema_multimodal_integration import MultimodalKnowledgeGraph

app = Flask(__name__)
CORS(app)

# Initialize the multimodal knowledge graph
mkg = MultimodalKnowledgeGraph()

@app.route('/')
def home():
 """Serve the HTML viewer"""
 return send_file('test_clause_images.html')

@app.route('/api/clause-images/<clause_number>')
def get_clause_images(clause_number):
 """Get all images for a specific clause"""
 
 # Find images for the clause
 images = mkg.find_images_for_clause(clause_number)
 
 # Convert paths to be web-accessible
 for img in images:
 # Create correct web path for serving
 img['web_path'] = f"/images/{img['document']}/auto/{img['image']}"
 # Keep the full system path for backend
 img['full_path'] = f"output/{img['document']}/auto/{img['image']}"
 
 return jsonify({
 'clause': clause_number,
 'count': len(images),
 'images': images[:50] # Limit to 50 images for performance
 })

@app.route('/api/multimodal/search/<query>')
def search_multimodal(query):
 """Search across all multimodal data"""
 results = mkg.search_multimodal(query)
 return jsonify(results)

@app.route('/api/multimodal/stats')
def get_stats():
 """Get statistics about the multimodal knowledge graph"""
 stats = mkg.get_statistics()
 return jsonify(stats)

@app.route('/api/multimodal/clauses-with-images')
def get_clauses_with_images():
 """Get list of all clauses that have images"""
 clauses = mkg.find_clauses_with_images()
 
 # Convert to list format for easier consumption
 clause_list = []
 for clause, images in clauses.items():
 clause_list.append({
 'clause': clause,
 'image_count': len(images),
 'sample_images': images[:3] # Just first 3 as samples
 })
 
 # Sort by image count
 clause_list.sort(key=lambda x: x['image_count'], reverse=True)
 
 return jsonify(clause_list)

@app.route('/api/multimodal/data')
def get_multimodal_data():
 """Get complete multimodal data structure"""
 
 # Get statistics
 stats = mkg.get_statistics()
 
 # Get top clauses with images
 clauses = mkg.find_clauses_with_images()
 top_clauses = {}
 for clause, images in list(clauses.items())[:20]:
 top_clauses[clause] = {
 'count': len(images),
 'images': images[:5]
 }
 
 return jsonify({
 'statistics': stats,
 'top_clauses': top_clauses
 })

@app.route('/images/<path:filepath>')
def serve_image(filepath):
 """Serve images from the output directory"""
 
 # Construct the full path
 image_path = Path('output') / filepath
 
 if image_path.exists():
 return send_file(str(image_path), mimetype='image/jpeg')
 else:
 # Return a placeholder image or 404
 return "Image not found", 404

@app.route('/api/clause/<clause_number>/full')
def get_full_clause_info(clause_number):
 """Get comprehensive multimodal information for a clause"""
 
 info = mkg.get_multimodal_clause_info(clause_number)
 
 # Add web paths for images
 for img in info['images']:
 img['web_path'] = f"/images/{img['document']}/auto/{img['image']}"
 
 return jsonify(info)

if __name__ == '__main__':
 print("=" * 60)
 print("CLAUSE IMAGE VIEWER API")
 print("=" * 60)
 print("\nStarting server...")
 print("\nOpen in browser: http://localhost:8000")
 print("\nAPI Endpoints:")
 print(" - http://localhost:8000/ (HTML Viewer)")
 print(" - http://localhost:8000/api/clause-images/4.2")
 print(" - http://localhost:8000/api/multimodal/stats")
 print(" - http://localhost:8000/api/clauses-with-images")
 print("\nPress Ctrl+C to stop\n")
 
 app.run(host='0.0.0.0', port=8000, debug=True)