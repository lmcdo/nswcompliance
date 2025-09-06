"""
Simple PDF processor using PyMuPDF for reliable text extraction
This is a fallback implementation that focuses on getting working text extraction
"""

import os
import re
import pymupdf  # PyMuPDF
from typing import List, Dict, Optional
from ..models import FormerCouncilArea

class SimplePDFProcessor:
    """Simple PDF processor using PyMuPDF for regulatory document extraction"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize processor with chunking parameters"""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Regulatory keywords to identify relevant text chunks
        self.setback_keywords = [
            "setback", "metres", "meters", "height", "distance", "boundary", 
            "rear", "side", "front", "minimum", "maximum", "building",
            "development", "zone", "residential", "commercial"
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using PyMuPDF
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
            
        Raises:
            FileNotFoundError: If PDF file doesn't exist
            ValueError: If insufficient text extracted
        """
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")
        
        try:
            # Open PDF with PyMuPDF
            doc = pymupdf.open(pdf_path)
            
            # Extract text from all pages
            text_parts = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text()
                
                # Clean up page text
                if page_text.strip():
                    cleaned_text = self._clean_page_text(page_text)
                    if cleaned_text:
                        text_parts.append(cleaned_text)
            
            doc.close()
            
            # Combine all pages
            full_text = '\n\n'.join(text_parts)
            
            if not full_text or len(full_text.strip()) < 50:
                raise ValueError(f"Insufficient text extracted from {pdf_path}: got {len(full_text) if full_text else 0} characters")
            
            return full_text
            
        except Exception as e:
            print(f"Warning: Failed to extract text from {pdf_path}: {e}")
            return ""
    
    def chunk_regulatory_text(self, text: str) -> List[str]:
        """
        Chunk text while preserving regulatory structure
        
        Args:
            text: Full text content from PDF
            
        Returns:
            List of text chunks filtered for regulatory content
        """
        return self._simple_chunk_text(text, self.chunk_size)
    
    def _clean_page_text(self, page_text: str) -> str:
        """Clean up text from a single page"""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', page_text.strip())
        
        # Remove page headers/footers patterns
        cleaned = re.sub(r'Page\s+\d+.*?(?=\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove table formatting artifacts  
        cleaned = re.sub(r'[|┌┐└┘├┤┬┴┼─│]+', ' ', cleaned)
        
        # Remove excessive punctuation
        cleaned = re.sub(r'\.{3,}', '...', cleaned)
        
        return cleaned.strip()
    
    def _is_regulatory_chunk(self, chunk: str) -> bool:
        """Check if chunk contains regulatory content"""
        chunk_lower = chunk.lower()
        
        # Must contain at least one setback keyword
        has_keyword = any(keyword in chunk_lower for keyword in self.setback_keywords)
        
        # Must be substantial enough
        has_substance = len(chunk.strip()) > 50
        
        # Should contain some numeric information (distances, heights, etc.)
        has_numbers = bool(re.search(r'\d+(?:\.\d+)?\s*(?:m|metre|meter)', chunk_lower))
        
        return has_keyword and has_substance and has_numbers
    
    def _simple_chunk_text(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Simple chunking method with overlap"""
        words = text.split()
        chunks = []
        
        i = 0
        while i < len(words):
            # Calculate chunk end
            chunk_end = min(i + max_chunk_size, len(words))
            current_chunk_words = words[i:chunk_end]
            chunk_text = ' '.join(current_chunk_words)
            
            # Only include chunks with regulatory content
            if self._is_regulatory_chunk(chunk_text):
                chunks.append(chunk_text)
            
            # Move forward with overlap
            overlap_words = max_chunk_size // 4  # 25% overlap
            i = max(i + max_chunk_size - overlap_words, i + 1)
        
        return chunks