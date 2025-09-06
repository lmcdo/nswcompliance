"""
Enhanced document discovery utility using regulatory hierarchy
Routes document processing based on LGA, zone, and development type
"""

import os
import glob
from typing import List, Dict, Optional, Tuple
from ..models import FormerCouncilArea

# LGA to directory mapping
LGA_DIRECTORY_MAP = {
    "Inner West": "INNERWEST",
    "Sydney": "SYDNEY", 
    "Randwick": "RANDWICK",
    "Waverley": "WAVERLEY",
    "Woollahra": "WOOLLAHRA",
    "Canada Bay": "CANADABAY"
}

# Former council mapping for amalgamated councils
FORMER_COUNCIL_MAPPING = {
    "Inner West": {
        "Ashfield": "Ashfield",
        "Haberfield": "Ashfield",
        "Summer Hill": "Ashfield",
        "Leichhardt": "Leichhardt", 
        "Annandale": "Leichhardt",
        "Balmain": "Leichhardt",
        "Rozelle": "Leichhardt",
        "Marrickville": "Marrickville",
        "Newtown": "Marrickville",
        "Enmore": "Marrickville"
    }
}

class DocumentFinder:
    """Enhanced document finder using regulatory hierarchy and case-specific routing"""
    
    def __init__(self, base_path: str = "docs"):
        """
        Initialize document finder with docs base path
        
        Args:
            base_path: Base directory containing all regulatory documents (docs/)
        """
        self.base_path = base_path
        
        # Legacy paths for backward compatibility
        self.legacy_base = os.path.join(base_path, "dcps", "INNERWEST")
        self.council_paths = {
            FormerCouncilArea.ASHFIELD: self.legacy_base,
            FormerCouncilArea.LEICHHARDT: self.legacy_base,
            FormerCouncilArea.MARRICKVILLE: self.legacy_base
        }
    
    def get_all_documents(self) -> Dict[FormerCouncilArea, List[str]]:
        """
        Get all PDF documents organized by council area
        
        Returns:
            Dictionary mapping council areas to lists of PDF file paths
        """
        documents = {}
        
        for area, path in self.council_paths.items():
            documents[area] = self._find_pdfs_in_directory(path, area)
        
        return documents
    
    def get_documents_for_property(
        self, 
        lga: str, 
        zone: str, 
        development_type: str,
        suburb: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Get all applicable documents for a property using case-specific routing
        
        Args:
            lga: Local Government Area (e.g., "Inner West")
            zone: Zoning classification (e.g., "R2")
            development_type: Type of development (e.g., "residential_low")
            suburb: Suburb for former council determination
            
        Returns:
            Dict with document types and file paths: {"SEPP": [...], "LEP": [...], "DCP": [...]}
        """
        documents = {
            "SEPP": [],
            "LEP": [],
            "DCP": []
        }
        
        # Get LGA directory
        lga_dir = LGA_DIRECTORY_MAP.get(lga)
        if not lga_dir:
            print(f"Warning: No directory mapping for LGA: {lga}")
            return documents
        
        # Find SEPP documents (state-wide)
        sepp_docs = self._find_sepp_documents(zone, development_type)
        documents["SEPP"].extend(sepp_docs)
        
        # Find LEP documents (LGA-specific)
        lep_docs = self._find_lep_documents(lga, lga_dir)
        documents["LEP"].extend(lep_docs)
        
        # Find DCP documents (LGA and area-specific)
        former_council = self._determine_former_council(lga, suburb) if suburb else None
        dcp_docs = self._find_dcp_documents(lga, lga_dir, zone, former_council)
        documents["DCP"].extend(dcp_docs)
        
        return documents
    
    def get_setback_documents(self, area: FormerCouncilArea) -> List[str]:
        """
        Legacy method: Get documents likely to contain setback rules
        Enhanced with better targeting of relevant sections
        """
        all_docs = self._find_pdfs_in_directory(self.council_paths[area], area)
        
        # Enhanced filtering with regulatory knowledge
        setback_docs = []
        
        for doc_path in all_docs:
            filename = os.path.basename(doc_path).lower()
            
            if area == FormerCouncilArea.ASHFIELD:
                # Target specific chapters known to contain setback rules
                if any(pattern in filename for pattern in [
                    "chapter e2",    # Haberfield specific controls
                    "chapter f",     # Development categories
                    "haberfield"     # Neighborhood-specific
                ]):
                    setback_docs.append(doc_path)
                    
            elif area == FormerCouncilArea.LEICHHARDT:
                # Target residential control sections
                if any(pattern in filename for pattern in [
                    "part g",        # Residential controls
                    "section 1-12",  # Main residential sections
                    "section 1",     # General residential
                    "section 2"      # Place-specific
                ]):
                    setback_docs.append(doc_path)
                    
            elif area == FormerCouncilArea.MARRICKVILLE:
                # All Marrickville documents (limited set)
                if "marrickville" in filename:
                    setback_docs.append(doc_path)
        
        return setback_docs if setback_docs else all_docs[:2]
    
    def _find_pdfs_in_directory(self, directory: str, area: FormerCouncilArea) -> List[str]:
        """
        Find all PDF files in a directory
        
        Args:
            directory: Directory to search
            area: Council area for filtering
            
        Returns:
            List of PDF file paths
        """
        pdf_files = []
        
        if not os.path.exists(directory):
            print(f"Warning: Directory not found: {directory}")
            return []
        
        try:
            for filename in os.listdir(directory):
                if filename.lower().endswith('.pdf'):
                    full_path = os.path.join(directory, filename)
                    
                    # Additional filtering by area if files are mixed
                    if self._is_relevant_for_area(filename, area):
                        pdf_files.append(full_path)
            
            # Sort files for consistent processing order
            pdf_files.sort()
            
        except Exception as e:
            print(f"Error scanning directory {directory}: {e}")
        
        return pdf_files
    
    def _is_relevant_for_area(self, filename: str, area: FormerCouncilArea) -> bool:
        """
        Check if a filename is relevant for the specified area
        
        Args:
            filename: Name of the file
            area: Council area
            
        Returns:
            True if file is relevant for the area
        """
        filename_lower = filename.lower()
        area_name = area.value.lower()
        
        # Direct area name match
        if area_name in filename_lower:
            return True
        
        # For Ashfield files in root directory - check they're not Leichhardt/Marrickville
        if area == FormerCouncilArea.ASHFIELD:
            return "leichhardt" not in filename_lower and "marrickville" not in filename_lower
        
        # For other areas, filename should contain area name
        return area_name in filename_lower
    
    def _find_sepp_documents(self, zone: str, development_type: str) -> List[str]:
        """Find applicable SEPP documents"""
        sepp_dir = os.path.join(self.base_path, "sepps")
        sepp_docs = []
        
        if os.path.exists(sepp_dir):
            for filename in os.listdir(sepp_dir):
                if filename.endswith('.pdf'):
                    # Route based on development type and zone
                    filename_lower = filename.lower()
                    if 'residential' in development_type:
                        if any(term in filename_lower for term in ['housing', 'residential', 'planning']):
                            sepp_docs.append(os.path.join(sepp_dir, filename))
        
        return sepp_docs
    
    def _find_lep_documents(self, lga: str, lga_dir: str) -> List[str]:
        """Find LEP documents for an LGA"""
        lep_dir = os.path.join(self.base_path, "leps", lga_dir)
        lep_docs = []
        
        if os.path.exists(lep_dir):
            for filename in os.listdir(lep_dir):
                if filename.endswith('.pdf') and 'lep' in filename.lower():
                    lep_docs.append(os.path.join(lep_dir, filename))
        
        return lep_docs
    
    def _find_dcp_documents(
        self, 
        lga: str, 
        lga_dir: str, 
        zone: str, 
        former_council: Optional[str]
    ) -> List[str]:
        """Find DCP documents with case-specific routing"""
        dcp_dir = os.path.join(self.base_path, "dcps", lga_dir)
        dcp_docs = []
        
        if not os.path.exists(dcp_dir):
            return dcp_docs
        
        for filename in os.listdir(dcp_dir):
            if not filename.endswith('.pdf'):
                continue
                
            filename_lower = filename.lower()
            
            # For Inner West - route by former council area
            if lga == "Inner West" and former_council:
                if former_council == "Ashfield" and any(term in filename_lower for term in ['ashfield', 'chapter e', 'haberfield']):
                    dcp_docs.append(os.path.join(dcp_dir, filename))
                elif former_council == "Leichhardt" and any(term in filename_lower for term in ['leichhardt', 'part g', 'part c']):
                    dcp_docs.append(os.path.join(dcp_dir, filename))
                elif former_council == "Marrickville" and 'marrickville' in filename_lower:
                    dcp_docs.append(os.path.join(dcp_dir, filename))
            else:
                # Generic LGA matching
                lga_name = lga.lower().replace(' ', '')
                if lga_name in filename_lower:
                    dcp_docs.append(os.path.join(dcp_dir, filename))
        
        return dcp_docs
    
    def _determine_former_council(self, lga: str, suburb: str) -> Optional[str]:
        """Determine former council area from suburb"""
        if lga in FORMER_COUNCIL_MAPPING and suburb in FORMER_COUNCIL_MAPPING[lga]:
            return FORMER_COUNCIL_MAPPING[lga][suburb]
        return None
    
    def get_processing_summary(
        self,
        lga: str,
        zone: str, 
        development_type: str,
        suburb: Optional[str] = None
    ) -> Dict[str, any]:
        """Get detailed summary of document processing plan"""
        documents = self.get_documents_for_property(lga, zone, development_type, suburb)
        former_council = self._determine_former_council(lga, suburb) if suburb else None
        
        return {
            "property_context": {
                "lga": lga,
                "zone": zone,
                "development_type": development_type,
                "suburb": suburb,
                "former_council": former_council
            },
            "regulatory_hierarchy": {
                "SEPP_count": len(documents["SEPP"]),
                "LEP_count": len(documents["LEP"]),
                "DCP_count": len(documents["DCP"]),
                "total_documents": sum(len(docs) for docs in documents.values())
            },
            "processing_order": ["SEPP", "LEP", "DCP"],
            "precedence_rules": [
                "SEPP rules override LEP and DCP",
                "LEP rules override DCP",
                "DCP provides detailed local controls"
            ],
            "documents": documents
        }
    
    def get_dcp_year(self, area: FormerCouncilArea) -> str:
        """Get the DCP year for a council area"""
        year_map = {
            FormerCouncilArea.ASHFIELD: "2016",
            FormerCouncilArea.LEICHHARDT: "2013", 
            FormerCouncilArea.MARRICKVILLE: "2011"
        }
        
        return year_map.get(area, "2014")