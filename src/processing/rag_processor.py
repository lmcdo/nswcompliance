"""
RAG-Anything based PDF processor for regulatory documents
Extracts text from Inner West Council DCPs while preserving regulatory structure
"""

import os
import re
from typing import List, Dict, Optional
from raganything import RAGAnything, RAGAnythingConfig
from ..models import FormerCouncilArea

class RAGProcessor:
    """PDF processor using RAG-Anything for regulatory document extraction"""
    
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """Initialize RAG processor with configuration"""
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        self.config = RAGAnythingConfig(
            enable_table_processing=True,  # Handle tables in PDFs
            enable_image_processing=True,  # Handle images/diagrams
            max_context_tokens=2000,  # Reasonable context size
            context_mode='page'  # Process by page
        )
        self.rag = RAGAnything(config=self.config)
        
        # Regulatory keywords to identify relevant text chunks
        self.setback_keywords = [
            "setback", "metres", "meters", "height", "distance", "boundary", 
            "rear", "side", "front", "minimum", "maximum", "building",
            "development", "zone", "residential", "commercial"
        ]
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using RAG-Anything
        
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
            # Use RAG-Anything to parse document
            parsed_data = self.rag.parse_document(pdf_path)
            
            # Extract text from parsed data - RAG-Anything structures vary
            text = ""
            if hasattr(parsed_data, 'text_content'):
                text = parsed_data.text_content
            elif hasattr(parsed_data, 'content'):
                text = parsed_data.content
            elif isinstance(parsed_data, dict):
                # Try common text field names
                for field in ['text', 'content', 'body', 'extracted_text']:
                    if field in parsed_data:
                        text = parsed_data[field]
                        break
                if not text:
                    # If no text field found, convert whole dict to string
                    text = str(parsed_data)
            elif isinstance(parsed_data, str):
                text = parsed_data
            else:
                # Fallback - convert to string
                text = str(parsed_data)
            
            if not text or len(text.strip()) < 100:
                raise ValueError(f"Insufficient text extracted from {pdf_path}: got {len(text) if text else 0} characters")
            
            return text
            
        except Exception as e:
            # Log error but continue processing - some PDFs may be problematic
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
        # RAG-Anything doesn't have a direct chunk_text method
        # Use simple chunking approach for regulatory text
        return self._simple_chunk_text(text, self.chunk_size)
    
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
    
    def _clean_chunk_text(self, chunk: str) -> str:
        """Clean up chunk text for processing"""
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', chunk.strip())
        
        # Remove page headers/footers patterns
        cleaned = re.sub(r'Page\s+\d+.*?(?=\n|$)', '', cleaned, flags=re.IGNORECASE)
        
        # Remove table formatting artifacts  
        cleaned = re.sub(r'[|┌┐└┘├┤┬┴┼─│]+', ' ', cleaned)
        
        return cleaned.strip()
    
    def _simple_chunk_text(self, text: str, max_chunk_size: int = 500) -> List[str]:
        """Fallback chunking method"""
        words = text.split()
        chunks = []
        current_chunk = []
        
        for word in words:
            current_chunk.append(word)
            if len(' '.join(current_chunk)) > max_chunk_size:
                chunk_text = ' '.join(current_chunk)
                if self._is_regulatory_chunk(chunk_text):
                    chunks.append(self._clean_chunk_text(chunk_text))
                current_chunk = []
        
        # Add remaining words
        if current_chunk:
            chunk_text = ' '.join(current_chunk)
            if self._is_regulatory_chunk(chunk_text):
                chunks.append(self._clean_chunk_text(chunk_text))
        
        return chunks