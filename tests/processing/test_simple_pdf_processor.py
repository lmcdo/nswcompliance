"""
Tests for SimplePDFProcessor class
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.processing.simple_pdf_processor import SimplePDFProcessor


class TestSimplePDFProcessor:
    """Test suite for SimplePDFProcessor class"""

    @pytest.fixture
    def processor(self):
        """Create processor instance for testing"""
        return SimplePDFProcessor(chunk_size=100, chunk_overlap=20)

    def test_init_default_params(self):
        """Test processor initialization with default parameters"""
        processor = SimplePDFProcessor()
        assert processor.chunk_size == 500
        assert processor.chunk_overlap == 50
        assert len(processor.setback_keywords) > 0

    def test_init_custom_params(self):
        """Test processor initialization with custom parameters"""
        processor = SimplePDFProcessor(chunk_size=200, chunk_overlap=30)
        assert processor.chunk_size == 200
        assert processor.chunk_overlap == 30

    def test_extract_text_from_pdf_nonexistent_file(self, processor):
        """Test error handling for nonexistent PDF file"""
        with pytest.raises(FileNotFoundError):
            processor.extract_text_from_pdf("/nonexistent/file.pdf")

    @patch('src.processing.simple_pdf_processor.pymupdf')
    def test_extract_text_from_pdf_success(self, mock_pymupdf, processor):
        """Test successful text extraction from PDF"""
        # Mock PDF document and pages
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Sample regulatory text with 6m setback requirements for building development"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.close = MagicMock()
        
        mock_pymupdf.open.return_value = mock_doc
        
        # Mock file existence
        with patch('os.path.exists', return_value=True):
            result = processor.extract_text_from_pdf("test.pdf")
            
            assert isinstance(result, str)
            assert len(result) > 0
            assert "regulatory" in result.lower()

    @patch('src.processing.simple_pdf_processor.pymupdf')
    def test_extract_text_from_pdf_insufficient_text(self, mock_pymupdf, processor):
        """Test handling of PDFs with insufficient text"""
        # Mock PDF with very little text
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Short"
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.close = MagicMock()
        
        mock_pymupdf.open.return_value = mock_doc
        
        with patch('os.path.exists', return_value=True):
            result = processor.extract_text_from_pdf("test.pdf")
            # Should return empty string on insufficient text
            assert result == ""

    @patch('src.processing.simple_pdf_processor.pymupdf')
    def test_extract_text_from_pdf_exception_handling(self, mock_pymupdf, processor):
        """Test exception handling during PDF processing"""
        mock_pymupdf.open.side_effect = Exception("PDF processing error")
        
        with patch('os.path.exists', return_value=True):
            result = processor.extract_text_from_pdf("test.pdf")
            assert result == ""

    def test_clean_page_text(self, processor):
        """Test page text cleaning functionality"""
        dirty_text = "  Sample   text  with   excessive    whitespace  Page 123 footer  "
        cleaned = processor._clean_page_text(dirty_text)
        
        # Check that excessive whitespace is normalized to single spaces
        assert "   " not in cleaned  # No triple spaces
        assert "Sample text with excessive whitespace" in cleaned
        assert "Page 123" not in cleaned

    def test_is_regulatory_chunk(self, processor):
        """Test regulatory chunk identification"""
        # Valid regulatory chunk
        regulatory_text = "Building setback requirements specify minimum 3m distance from rear boundary with 6m height limit for residential development"
        assert processor._is_regulatory_chunk(regulatory_text)
        
        # Non-regulatory chunk (no keywords)
        non_regulatory_text = "This document contains general information about the council's administrative procedures"
        assert not processor._is_regulatory_chunk(non_regulatory_text)
        
        # Too short chunk
        short_text = "3m setback"
        assert not processor._is_regulatory_chunk(short_text)
        
        # No measurements
        no_measurements = "Building setback requirements specify minimum distance from boundary for residential development"
        assert not processor._is_regulatory_chunk(no_measurements)

    def test_chunk_regulatory_text(self, processor):
        """Test text chunking for regulatory content"""
        sample_text = """
        Building setback requirements specify minimum 3m distance from rear boundary. 
        The height limit is 6m for residential development in this zone.
        Administrative procedures for application processing are outlined below.
        Side setback must be 1.5m minimum from boundary with 4m height restriction.
        """
        
        chunks = processor.chunk_regulatory_text(sample_text)
        
        assert isinstance(chunks, list)
        assert len(chunks) > 0
        # Should contain regulatory chunks only
        for chunk in chunks:
            assert processor._is_regulatory_chunk(chunk)

    def test_simple_chunk_text_with_overlap(self, processor):
        """Test simple chunking method with overlap"""
        # Create text longer than chunk size
        words = ["building", "setback", "3m", "minimum"] * 50  # 200 words
        test_text = " ".join(words)
        
        chunks = processor._simple_chunk_text(test_text, max_chunk_size=50)
        
        assert isinstance(chunks, list)
        if len(chunks) > 1:
            # Check that chunks overlap (share some words)
            first_chunk_words = chunks[0].split()
            second_chunk_words = chunks[1].split()
            shared_words = set(first_chunk_words) & set(second_chunk_words)
            assert len(shared_words) > 0

    def test_simple_chunk_text_empty_input(self, processor):
        """Test chunking with empty input"""
        chunks = processor._simple_chunk_text("", max_chunk_size=100)
        assert chunks == []

    def test_simple_chunk_text_filters_non_regulatory(self, processor):
        """Test that chunking filters out non-regulatory content"""
        mixed_text = """
        This is administrative text about council procedures and meetings.
        Building setback requirements specify minimum 3m distance from rear boundary.
        More administrative content without regulatory keywords or measurements.
        Side setback must be 1.5m minimum from boundary with height restriction.
        """
        
        chunks = processor._simple_chunk_text(mixed_text, max_chunk_size=100)
        
        # Should only contain regulatory chunks
        for chunk in chunks:
            assert processor._is_regulatory_chunk(chunk)
            # Should contain regulatory keywords and measurements
            assert any(keyword in chunk.lower() for keyword in processor.setback_keywords)
            assert any(char.isdigit() for char in chunk)

    def test_setback_keywords_completeness(self, processor):
        """Test that setback keywords include essential terms"""
        essential_keywords = [
            "setback", "metres", "height", "distance", "boundary",
            "rear", "side", "front", "minimum", "building", "development"
        ]
        
        for keyword in essential_keywords:
            assert keyword in processor.setback_keywords

    def test_table_formatting_removal(self, processor):
        """Test removal of table formatting artifacts"""
        table_text = "│Building│Height│Distance│ ┌─────┐ Data content ├──┤ more content"
        cleaned = processor._clean_page_text(table_text)
        
        # Should remove table characters
        table_chars = ['│', '┌', '┐', '└', '┘', '├', '┤', '┬', '┴', '┼', '─']
        for char in table_chars:
            assert char not in cleaned