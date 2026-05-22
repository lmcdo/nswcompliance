import pytest
pytestmark = pytest.mark.stale

"""
Integration tests for the complete processing pipeline
"""

import os
import json
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.models import FormerCouncilArea, InnerWestSetbacks
from src.processing.simple_pdf_processor import SimplePDFProcessor
from src.processing.schema_extractor import SchemaExtractor
from src.utils.document_finder import DocumentFinder


class TestIntegrationPipeline:
    """Integration tests for the complete processing pipeline"""

    @pytest.fixture
    def temp_environment(self):
        """Create temporary environment with test documents and output directory"""
        temp_dir = tempfile.mkdtemp()
        
        # Create docs directory structure
        docs_path = os.path.join(temp_dir, "docs", "dcps", "INNERWEST")
        os.makedirs(docs_path, exist_ok=True)
        os.makedirs(os.path.join(docs_path, "leichhardt"), exist_ok=True)
        os.makedirs(os.path.join(docs_path, "Marrickville"), exist_ok=True)
        
        # Create output directory
        output_path = os.path.join(temp_dir, "public", "regulatory-data")
        os.makedirs(output_path, exist_ok=True)
        
        # Create test PDF files
        test_files = [
            os.path.join(docs_path, "Ashfield Chapter F.pdf"),
            os.path.join(docs_path, "leichhardt", "Leichhardt Part C.pdf"),
            os.path.join(docs_path, "Marrickville", "Marrickville DCP.pdf"),
        ]
        
        for file_path in test_files:
            Path(file_path).touch()
        
        yield {
            'temp_dir': temp_dir,
            'docs_path': docs_path,
            'output_path': output_path
        }
        
        shutil.rmtree(temp_dir)

    def test_document_discovery_integration(self, temp_environment):
        """Test document discovery works with real directory structure"""
        docs_path = temp_environment['docs_path']
        finder = DocumentFinder(docs_path)
        
        all_docs = finder.get_all_documents()
        
        assert isinstance(all_docs, dict)
        assert len(all_docs) == 3
        
        # Should find documents for each area
        for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
            assert area in all_docs
            assert isinstance(all_docs[area], list)

    @patch('src.processing.simple_pdf_processor.pymupdf')
    def test_pdf_processing_integration(self, mock_pymupdf, temp_environment):
        """Test PDF processing with mocked PyMuPDF"""
        # Mock PDF content with regulatory text
        mock_doc = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = """
        Building Development Controls
        Rear setback requirements specify minimum 3m distance from boundary.
        Maximum height within rear setback area is 6m for residential development.
        Side boundary setback minimum 1.5m with height limit 4m.
        Front setback minimum 6m from street alignment for all buildings.
        """
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.close = MagicMock()
        mock_pymupdf.open.return_value = mock_doc
        
        processor = SimplePDFProcessor()
        test_file = os.path.join(temp_environment['docs_path'], "Ashfield Chapter F.pdf")
        
        # Extract text
        text = processor.extract_text_from_pdf(test_file)
        assert isinstance(text, str)
        assert len(text) > 0
        assert "setback" in text.lower()
        
        # Chunk text
        chunks = processor.chunk_regulatory_text(text)
        assert isinstance(chunks, list)
        assert len(chunks) > 0

    def test_schema_extraction_integration(self):
        """Test schema extraction with realistic regulatory text"""
        extractor = SchemaExtractor()
        
        # Realistic regulatory text chunks
        test_chunks = [
            "Building within 6m of the rear boundary must not exceed maximum height of 4m metres",
            "Side boundary setback minimum 1.5m with maximum building height 6m",
            "Front setback minimum 6m from street boundary for all residential development"
        ]
        
        result = extractor.extract_setback_rules(test_chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        assert isinstance(result, dict)
        assert 'rear' in result
        assert 'side' in result
        assert 'front' in result
        
        # Should extract at least some rules
        extracted_rules = [rule for rule in result.values() if rule is not None]
        assert len(extracted_rules) > 0

    def test_confidence_calculation_integration(self):
        """Test confidence calculation in realistic scenarios"""
        extractor = SchemaExtractor()
        
        # High confidence scenario - all rules present
        complete_chunks = [
            "Rear setback minimum 3m with height limit 8m",
            "Side boundary setback 1.5m minimum with 6m maximum height",
            "Front setback 6m minimum from street boundary"
        ]
        
        complete_rules = extractor.extract_setback_rules(
            complete_chunks, FormerCouncilArea.LEICHHARDT, "complete.pdf"
        )
        complete_confidence = extractor.calculate_confidence(complete_rules)
        
        # Partial scenario - only some rules present
        partial_chunks = [
            "Rear setback minimum 4m from boundary",
            "General development guidelines apply"
        ]
        
        partial_rules = extractor.extract_setback_rules(
            partial_chunks, FormerCouncilArea.LEICHHARDT, "partial.pdf"
        )
        partial_confidence = extractor.calculate_confidence(partial_rules)
        
        # Complete should have higher confidence than partial
        assert complete_confidence >= partial_confidence
        assert 0.0 <= partial_confidence <= 1.0
        assert 0.0 <= complete_confidence <= 1.0

    def test_output_json_structure(self, temp_environment):
        """Test that output JSON has correct structure"""
        from src.models import ProcessedCouncilArea, SetbackRules, SetbackRule
        
        # Create test data structure
        test_setbacks = SetbackRules(
            rear=SetbackRule(distance=3.0, height_limit=6.0, source="Test DCP", source_file="test.pdf"),
            side=SetbackRule(height_limit=4.0, source="Test DCP", source_file="test.pdf"),
            front=SetbackRule(min_distance=6.0, source="Test DCP", source_file="test.pdf")
        )
        
        test_area = ProcessedCouncilArea(
            name=FormerCouncilArea.ASHFIELD,
            dcp_version="Ashfield DCP 2016",
            processed_files=["test.pdf"],
            setbacks=test_setbacks,
            extraction_confidence=1.0
        )
        
        test_output = InnerWestSetbacks(
            areas={"Ashfield": test_area},
            processing_metadata={
                "total_areas_processed": 1,
                "processing_timestamp": "2024-01-01T12:00:00",
                "avg_confidence": 1.0,
                "total_files_processed": 1,
                "successful_extractions": 1
            }
        )
        
        # Test API format
        api_data = test_output.to_api_format()
        
        assert isinstance(api_data, dict)
        assert "lga" in api_data
        assert "areas" in api_data
        assert api_data["lga"] == "INNER WEST COUNCIL"
        
        # Test area structure
        assert "Ashfield" in api_data["areas"]
        ashfield_data = api_data["areas"]["Ashfield"]
        assert "setbacks" in ashfield_data
        
        # Test setback structure
        setbacks = ashfield_data["setbacks"]
        assert "rear" in setbacks
        assert "side" in setbacks
        assert "front" in setbacks

    @patch('src.processing.simple_pdf_processor.pymupdf')
    def test_error_handling_integration(self, mock_pymupdf, temp_environment):
        """Test error handling in integrated pipeline"""
        # Mock PDF processing failure
        mock_pymupdf.open.side_effect = Exception("PDF processing failed")
        
        processor = SimplePDFProcessor()
        extractor = SchemaExtractor()
        finder = DocumentFinder(temp_environment['docs_path'])
        
        # Should handle PDF processing errors gracefully
        test_file = os.path.join(temp_environment['docs_path'], "Ashfield Chapter F.pdf")
        text = processor.extract_text_from_pdf(test_file)
        
        # Should return empty string on error
        assert text == ""
        
        # Schema extraction should handle empty chunks
        chunks = processor.chunk_regulatory_text(text)
        result = extractor.extract_setback_rules(chunks, FormerCouncilArea.ASHFIELD, "test.pdf")
        
        # Should return structure with None values
        assert all(rule is None for rule in result.values())

    def test_file_path_handling(self, temp_environment):
        """Test correct handling of file paths across different platforms"""
        docs_path = temp_environment['docs_path']
        finder = DocumentFinder(docs_path)
        
        # Get documents for each area
        for area in [FormerCouncilArea.ASHFIELD, FormerCouncilArea.LEICHHARDT, FormerCouncilArea.MARRICKVILLE]:
            docs = finder.get_setback_documents(area)
            
            for doc_path in docs:
                # All paths should be absolute and exist
                assert os.path.isabs(doc_path)
                assert os.path.exists(doc_path)
                assert doc_path.endswith('.pdf')

    def test_empty_directory_integration(self):
        """Test integration behavior with empty directories"""
        # Create finder pointing to non-existent directory
        finder = DocumentFinder("/nonexistent/path/")
        processor = SimplePDFProcessor()
        extractor = SchemaExtractor()
        
        # Should handle missing directories gracefully
        all_docs = finder.get_all_documents()
        assert isinstance(all_docs, dict)
        
        for area_docs in all_docs.values():
            assert isinstance(area_docs, list)
            assert len(area_docs) == 0

    def test_processing_statistics_tracking(self):
        """Test that processing statistics are properly tracked"""
        # This would be tested in the actual main processing script
        # Here we test the components that contribute to statistics
        
        extractor = SchemaExtractor()
        
        # Simulate successful and failed extractions
        successful_chunks = ["Rear setback minimum 3m with height limit 6m"]
        failed_chunks = ["Administrative text without regulatory content"]
        
        successful_result = extractor.extract_setback_rules(
            successful_chunks, FormerCouncilArea.ASHFIELD, "success.pdf"
        )
        failed_result = extractor.extract_setback_rules(
            failed_chunks, FormerCouncilArea.ASHFIELD, "failed.pdf"
        )
        
        # Successful extraction should have rules
        successful_count = sum(1 for rule in successful_result.values() if rule is not None)
        assert successful_count > 0
        
        # Failed extraction should have no rules
        failed_count = sum(1 for rule in failed_result.values() if rule is not None)
        assert failed_count == 0