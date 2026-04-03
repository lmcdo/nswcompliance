"""
Tests for DocumentFinder utility class
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.document_finder import DocumentFinder
from src.models import FormerCouncilArea


class TestDocumentFinder:
    """Test suite for DocumentFinder class"""

    @pytest.fixture
    def temp_docs_dir(self):
        """Create temporary directory structure for testing.

        DocumentFinder takes a base_path (e.g. "docs") and internally builds
        legacy_base = base_path/dcps/INNERWEST, so we create files there and
        yield the root, not the innerwest dir.
        """
        temp_dir = tempfile.mkdtemp()
        innerwest = os.path.join(temp_dir, "dcps", "INNERWEST")

        # Create directory structure — all files at flat root since
        # _find_pdfs_in_directory uses os.listdir (no recursion).
        os.makedirs(innerwest, exist_ok=True)

        # Create test PDF files
        test_files = [
            # Ashfield files
            os.path.join(innerwest, "Ashfield DCP Chapter F.pdf"),
            os.path.join(innerwest, "Chapter E2 Haberfield.pdf"),

            # Leichhardt files
            os.path.join(innerwest, "Leichhardt Part C Section 1.pdf"),
            os.path.join(innerwest, "Leichhardt Part C Place Section 2.pdf"),

            # Marrickville files
            os.path.join(innerwest, "Marrickville DCP Contents.pdf"),
        ]

        for file_path in test_files:
            Path(file_path).touch()

        yield temp_dir

        # Cleanup
        shutil.rmtree(temp_dir)

    def test_init_default_path(self):
        """Test DocumentFinder initialization with default path"""
        finder = DocumentFinder()
        assert finder.base_path == "docs"
        assert len(finder.council_paths) == 3

    def test_init_custom_path(self):
        """Test DocumentFinder initialization with custom path"""
        custom_path = "/custom/path/"
        finder = DocumentFinder(custom_path)
        assert finder.base_path == custom_path

    def test_get_all_documents(self, temp_docs_dir):
        """Test getting all documents organized by council area"""
        finder = DocumentFinder(temp_docs_dir)
        documents = finder.get_all_documents()
        
        assert isinstance(documents, dict)
        assert len(documents) == 3
        assert FormerCouncilArea.ASHFIELD in documents
        assert FormerCouncilArea.LEICHHARDT in documents
        assert FormerCouncilArea.MARRICKVILLE in documents
        
        # Check Ashfield documents
        ashfield_docs = documents[FormerCouncilArea.ASHFIELD]
        assert len(ashfield_docs) == 2
        assert any("Ashfield DCP Chapter F.pdf" in doc for doc in ashfield_docs)
        
        # Check Leichhardt documents
        leichhardt_docs = documents[FormerCouncilArea.LEICHHARDT]
        assert len(leichhardt_docs) >= 1
        assert any("Leichhardt Part C Section 1.pdf" in doc for doc in leichhardt_docs)

    def test_get_setback_documents_ashfield(self, temp_docs_dir):
        """Test getting setback documents for Ashfield"""
        finder = DocumentFinder(temp_docs_dir)
        docs = finder.get_setback_documents(FormerCouncilArea.ASHFIELD)
        
        assert isinstance(docs, list)
        assert len(docs) > 0
        # Should prioritize Chapter F document
        assert any("Chapter F" in os.path.basename(doc) for doc in docs)

    def test_get_setback_documents_leichhardt(self, temp_docs_dir):
        """Test getting setback documents for Leichhardt"""
        finder = DocumentFinder(temp_docs_dir)
        docs = finder.get_setback_documents(FormerCouncilArea.LEICHHARDT)
        
        assert isinstance(docs, list)
        assert len(docs) > 0
        # Should prioritize Part C documents
        assert any("Part C" in os.path.basename(doc) for doc in docs)

    def test_get_setback_documents_marrickville(self, temp_docs_dir):
        """Test getting setback documents for Marrickville"""
        finder = DocumentFinder(temp_docs_dir)
        docs = finder.get_setback_documents(FormerCouncilArea.MARRICKVILLE)
        
        assert isinstance(docs, list)
        assert len(docs) > 0

    def test_get_setback_documents_nonexistent_area(self, temp_docs_dir):
        """Test behavior with nonexistent base directory"""
        # Remove the entire INNERWEST directory to simulate missing data
        marrickville_path = os.path.join(temp_docs_dir, "dcps", "INNERWEST")
        shutil.rmtree(marrickville_path)
        
        finder = DocumentFinder(temp_docs_dir)
        docs = finder.get_setback_documents(FormerCouncilArea.MARRICKVILLE)
        
        assert isinstance(docs, list)
        assert len(docs) == 0

    def test_is_relevant_for_area(self, temp_docs_dir):
        """Test file relevance filtering for council areas"""
        finder = DocumentFinder(temp_docs_dir)
        
        # Test Ashfield files
        assert finder._is_relevant_for_area("Ashfield DCP.pdf", FormerCouncilArea.ASHFIELD)
        assert finder._is_relevant_for_area("Chapter F.pdf", FormerCouncilArea.ASHFIELD)  # Generic file for Ashfield
        assert not finder._is_relevant_for_area("Leichhardt DCP.pdf", FormerCouncilArea.ASHFIELD)
        
        # Test Leichhardt files
        assert finder._is_relevant_for_area("Leichhardt Part C.pdf", FormerCouncilArea.LEICHHARDT)
        assert not finder._is_relevant_for_area("Ashfield DCP.pdf", FormerCouncilArea.LEICHHARDT)

    def test_get_dcp_year(self, temp_docs_dir):
        """Test getting DCP year for council areas"""
        finder = DocumentFinder(temp_docs_dir)
        
        assert finder.get_dcp_year(FormerCouncilArea.ASHFIELD) == "2016"
        assert finder.get_dcp_year(FormerCouncilArea.LEICHHARDT) == "2013"
        assert finder.get_dcp_year(FormerCouncilArea.MARRICKVILLE) == "2011"

    def test_empty_directory_handling(self):
        """Test handling of empty or nonexistent directories"""
        finder = DocumentFinder("/nonexistent/path/")
        documents = finder.get_all_documents()
        
        assert isinstance(documents, dict)
        # Should return empty lists for all areas
        for area_docs in documents.values():
            assert isinstance(area_docs, list)
            assert len(area_docs) == 0

    def test_non_pdf_files_ignored(self, temp_docs_dir):
        """Test that non-PDF files are ignored"""
        # Create non-PDF file
        non_pdf_path = os.path.join(temp_docs_dir, "text_file.txt")
        Path(non_pdf_path).touch()
        
        finder = DocumentFinder(temp_docs_dir)
        docs = finder.get_setback_documents(FormerCouncilArea.ASHFIELD)
        
        # Should only contain PDF files
        for doc_path in docs:
            assert doc_path.lower().endswith('.pdf')