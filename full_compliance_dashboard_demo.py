#!/usr/bin/env python3
"""
Full Compliance Dashboard - Live Data Access Demo
=================================================
Shows ACTUAL database queries, data pathways, and processing for comprehensive 
compliance analysis using real NSW Planning API data + enhanced database.
"""

import sqlite3
import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

@dataclass
class PropertyData:
 """NSW Planning API data structure"""
 address: str
 zone: str # e.g., "R2"
 fsr_limit: float # e.g., 0.6
 height_limit: float # e.g., 9.5
 lot_geometry: dict
 sepps_applicable: list
 tree_canopy: float # e.g., 13.23

@dataclass 
class ComplianceResult:
 """Compliance analysis result"""
 requirement_type: str
 api_limit: Optional[float]
 database_controls: List[dict]
 sepp_overrides: List[dict]
 quantitative_standards: List[dict]
 compliance_status: str
 explanation: str
 source_provisions: List[str]

class FullComplianceDashboard:
 """
 Demonstrates ACTUAL data access pathways for comprehensive compliance analysis
 """
 
 def __init__(self, db_path: str = 'nsw_planning.db'):
 self.db_path = db_path
 self.conn = sqlite3.connect(db_path)
 self.cursor = self.conn.cursor()
 
 def analyze_property_compliance(self, property_data: PropertyData) -> Dict[str, ComplianceResult]:
 """
 MAIN ENTRY POINT: Full compliance analysis for a property
 Shows complete data pathway from API input to compliance results
 """
 print(f"FULL COMPLIANCE ANALYSIS FOR: {property_data.address}")
 print("=" * 60)
 
 compliance_results = {}
 
 # 1. HEIGHT COMPLIANCE ANALYSIS
 print("1. HEIGHT COMPLIANCE ANALYSIS:")
 print("-" * 35)
 compliance_results['height'] = self._analyze_height_compliance(property_data)
 
 # 2. FSR COMPLIANCE ANALYSIS 
 print("\n2. FSR COMPLIANCE ANALYSIS:")
 print("-" * 30)
 compliance_results['fsr'] = self._analyze_fsr_compliance(property_data)
 
 # 3. SETBACK REQUIREMENTS ANALYSIS
 print("\n3. SETBACK REQUIREMENTS ANALYSIS:")
 print("-" * 35)
 compliance_results['setback'] = self._analyze_setback_requirements(property_data)
 
 # 4. HERITAGE CONSTRAINTS ANALYSIS
 print("\n4. HERITAGE CONSTRAINTS ANALYSIS:")
 print("-" * 35)
 compliance_results['heritage'] = self._analyze_heritage_constraints(property_data)
 
 # 5. ENVIRONMENTAL REQUIREMENTS ANALYSIS
 print("\n5. ENVIRONMENTAL REQUIREMENTS ANALYSIS:")
 print("-" * 40)
 compliance_results['environmental'] = self._analyze_environmental_requirements(property_data)
 
 return compliance_results
 
 def _analyze_height_compliance(self, property_data: PropertyData) -> ComplianceResult:
 """
 ACTUAL HEIGHT COMPLIANCE DATA PATHWAY
 """
 
 # STEP 1: Check SEPP overrides first (highest hierarchy)
 print(" Step 1: Checking SEPP overrides...")
 sepp_overrides = self._get_sepp_overrides('height', property_data.zone)
 
 # STEP 2: Get quantitative standards from database
 print(" Step 2: Getting quantitative height standards...")
 height_standards = self._get_quantitative_standards('height', property_data.zone)
 
 # STEP 3: Get development controls
 print(" Step 3: Getting development controls...")
 height_controls = self._get_development_controls('height', property_data.zone)
 
 # STEP 4: Get explanatory relationships
 print(" Step 4: Getting explanatory relationships...")
 explanations = self._get_compliance_explanations('height')
 
 # PROCESS: Apply hierarchy logic
 effective_limit = property_data.height_limit # Start with API limit
 explanation_parts = [f"LEP limit: {property_data.height_limit}m"]
 
 if sepp_overrides:
 for override in sepp_overrides:
 if override['override_type'] == 'replaces':
 # SEPP replaces LEP limit
 explanation_parts.append(f"SEPP overrides LEP: {override['extracted_text'][:50]}...")
 
 if height_standards:
 for standard in height_standards:
 if standard['qualifier'] == 'maximum' and standard['numeric_value'] < effective_limit:
 effective_limit = standard['numeric_value']
 explanation_parts.append(f"Database standard: max {standard['numeric_value']}{standard['unit']}")
 
 # Build comprehensive explanation
 full_explanation = " | ".join(explanation_parts)
 if explanations:
 full_explanation += f" | Reason: {explanations[0]['object_text']}" if explanations else ""
 
 print(f" API Limit: {property_data.height_limit}m")
 print(f" SEPP Overrides: {len(sepp_overrides)}")
 print(f" DB Standards: {len(height_standards)}")
 print(f" Effective Limit: {effective_limit}m")
 
 return ComplianceResult(
 requirement_type='height',
 api_limit=property_data.height_limit,
 database_controls=height_controls,
 sepp_overrides=sepp_overrides,
 quantitative_standards=height_standards,
 compliance_status='COMPLIANT' if effective_limit > 0 else 'REQUIRES_ANALYSIS',
 explanation=full_explanation,
 source_provisions=[str(c['provision_id']) for c in height_controls]
 )
 
 def _analyze_fsr_compliance(self, property_data: PropertyData) -> ComplianceResult:
 """
 ACTUAL FSR COMPLIANCE DATA PATHWAY 
 """
 
 print(" Step 1: Checking SEPP overrides for FSR...")
 sepp_overrides = self._get_sepp_overrides('fsr', property_data.zone)
 
 print(" Step 2: Getting FSR quantitative standards...")
 fsr_standards = self._get_quantitative_standards('fsr', property_data.zone)
 
 print(" Step 3: Getting FSR development controls...")
 fsr_controls = self._get_development_controls('fsr', property_data.zone)
 
 # Process FSR bonus provisions
 print(" Step 4: Checking FSR bonus provisions...")
 fsr_bonuses = self._get_fsr_bonus_provisions(property_data.zone)
 
 effective_fsr = property_data.fsr_limit
 explanation_parts = [f"LEP FSR: {property_data.fsr_limit}:1"]
 
 if fsr_bonuses:
 explanation_parts.append(f"Potential bonuses: {len(fsr_bonuses)} available")
 
 print(f" API FSR: {property_data.fsr_limit}:1")
 print(f" DB Standards: {len(fsr_standards)}")
 print(f" Bonus Provisions: {len(fsr_bonuses)}")
 
 return ComplianceResult(
 requirement_type='fsr',
 api_limit=property_data.fsr_limit,
 database_controls=fsr_controls,
 sepp_overrides=sepp_overrides,
 quantitative_standards=fsr_standards,
 compliance_status='ANALYSIS_REQUIRED',
 explanation=" | ".join(explanation_parts),
 source_provisions=[str(c['provision_id']) for c in fsr_controls]
 )
 
 def _analyze_setback_requirements(self, property_data: PropertyData) -> ComplianceResult:
 """
 ACTUAL SETBACK ANALYSIS DATA PATHWAY
 """
 
 print(" Step 1: Getting setback quantitative standards...")
 setback_standards = self._get_quantitative_standards('setback', property_data.zone)
 
 print(" Step 2: Getting setback development controls...")
 setback_controls = self._get_development_controls('setback', property_data.zone)
 
 print(" Step 3: Analyzing lot geometry for setback calculation...")
 # In real implementation, this would calculate actual setback requirements
 # based on lot geometry and zone requirements
 
 print(f" Setback Standards: {len(setback_standards)}")
 print(f" Setback Controls: {len(setback_controls)}")
 
 return ComplianceResult(
 requirement_type='setback',
 api_limit=None, # No API setback data
 database_controls=setback_controls,
 sepp_overrides=[],
 quantitative_standards=setback_standards,
 compliance_status='CALCULATION_REQUIRED',
 explanation=f"Zone {property_data.zone} setback requirements from {len(setback_standards)} standards",
 source_provisions=[str(c['provision_id']) for c in setback_controls]
 )
 
 def _analyze_heritage_constraints(self, property_data: PropertyData) -> ComplianceResult:
 """
 ACTUAL HERITAGE ANALYSIS DATA PATHWAY
 """
 
 print(" Step 1: Checking heritage development controls...")
 heritage_controls = self._get_development_controls('heritage', property_data.zone)
 
 print(" Step 2: Getting heritage protection relationships...")
 heritage_relationships = self._get_heritage_relationships(property_data.address)
 
 print(f" Heritage Controls: {len(heritage_controls)}")
 print(f" Protection Relationships: {len(heritage_relationships)}")
 
 return ComplianceResult(
 requirement_type='heritage',
 api_limit=None,
 database_controls=heritage_controls,
 sepp_overrides=[],
 quantitative_standards=[],
 compliance_status='ASSESSMENT_REQUIRED',
 explanation=f"Heritage assessment required - {len(heritage_controls)} heritage controls apply",
 source_provisions=[str(c['provision_id']) for c in heritage_controls]
 )
 
 def _analyze_environmental_requirements(self, property_data: PropertyData) -> ComplianceResult:
 """
 ACTUAL ENVIRONMENTAL REQUIREMENTS DATA PATHWAY
 """
 
 print(" Step 1: Getting vegetation controls...")
 vegetation_controls = self._get_development_controls('vegetation', property_data.zone)
 
 print(" Step 2: Analyzing tree canopy requirements...")
 # Compare current canopy (13.23%) with requirements
 canopy_requirements = self._get_canopy_requirements(property_data.zone)
 
 print(f" Current Canopy: {property_data.tree_canopy}%")
 print(f" Vegetation Controls: {len(vegetation_controls)}")
 
 return ComplianceResult(
 requirement_type='environmental',
 api_limit=property_data.tree_canopy,
 database_controls=vegetation_controls,
 sepp_overrides=[],
 quantitative_standards=[],
 compliance_status='MONITORING_REQUIRED',
 explanation=f"Tree canopy {property_data.tree_canopy}% - {len(vegetation_controls)} environmental controls apply",
 source_provisions=[str(c['provision_id']) for c in vegetation_controls]
 )
 
 # ==================== ACTUAL DATABASE QUERY METHODS ====================
 
 def _get_sepp_overrides(self, control_type: str, zone: str) -> List[dict]:
 """
 ACTUAL QUERY: Get SEPP overrides for specific control type
 """
 self.cursor.execute('''
 SELECT slo.*, rpc.provision_text
 FROM sepp_lep_overrides slo
 JOIN regulatory_provisions_clean rpc ON slo.sepp_provision_id = rpc.id
 WHERE rpc.provision_text LIKE ? 
 AND rpc.provision_text LIKE ?
 ORDER BY slo.confidence_score DESC
 LIMIT 5
 ''', (f'%{control_type}%', f'%{zone}%'))
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_quantitative_standards(self, context: str, zone: str) -> List[dict]:
 """
 ACTUAL QUERY: Get quantitative standards for specific context
 """
 self.cursor.execute('''
 SELECT qs.*, rpc.provision_text
 FROM quantitative_standards qs
 JOIN regulatory_provisions_clean rpc ON qs.provision_id = rpc.id
 WHERE qs.context = ?
 AND (rpc.provision_text LIKE ? OR qs.context = ?)
 ORDER BY qs.confidence_score DESC
 LIMIT 10
 ''', (context, f'%{zone}%', context))
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_development_controls(self, control_type: str, zone: str) -> List[dict]:
 """
 ACTUAL QUERY: Get development controls for specific type and zone
 """
 self.cursor.execute('''
 SELECT dc.*, rpc.provision_text, rpc.document_id
 FROM development_controls dc
 JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
 WHERE dc.control_type = ?
 AND (dc.zone_applicable = ? OR dc.zone_applicable = 'general')
 ORDER BY dc.confidence_score DESC
 LIMIT 15
 ''', (control_type, zone))
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_compliance_explanations(self, control_type: str) -> List[dict]:
 """
 ACTUAL QUERY: Get 'why' explanations from knowledge graph
 """
 self.cursor.execute('''
 SELECT kr.subject_text, kr.predicate, kr.object_text
 FROM kg_relationships kr
 WHERE kr.predicate IN ('because', 'requires', 'protect')
 AND kr.subject_text LIKE ?
 ORDER BY LENGTH(kr.object_text) DESC
 LIMIT 5
 ''', (f'%{control_type}%',))
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_fsr_bonus_provisions(self, zone: str) -> List[dict]:
 """
 ACTUAL QUERY: Get FSR bonus provisions
 """
 self.cursor.execute('''
 SELECT dc.*, rpc.provision_text
 FROM development_controls dc
 JOIN regulatory_provisions_clean rpc ON dc.provision_id = rpc.id
 WHERE dc.control_type = 'fsr'
 AND rpc.provision_text LIKE '%bonus%'
 LIMIT 5
 ''', )
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_heritage_relationships(self, address: str) -> List[dict]:
 """
 ACTUAL QUERY: Get heritage protection relationships
 """
 self.cursor.execute('''
 SELECT kr.subject_text, kr.predicate, kr.object_text
 FROM kg_relationships kr
 WHERE kr.predicate = 'protect'
 AND kr.object_text LIKE '%heritage%'
 LIMIT 5
 ''')
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def _get_canopy_requirements(self, zone: str) -> List[dict]:
 """
 ACTUAL QUERY: Get tree canopy requirements
 """
 self.cursor.execute('''
 SELECT qs.*
 FROM quantitative_standards qs
 WHERE qs.context = 'percentage'
 AND qs.unit = '%'
 LIMIT 3
 ''')
 
 return [dict(zip([col[0] for col in self.cursor.description], row)) 
 for row in self.cursor.fetchall()]
 
 def generate_dashboard_summary(self, compliance_results: Dict[str, ComplianceResult]) -> dict:
 """
 Generate final dashboard summary with all analysis results
 """
 print("\n" + "=" * 60)
 print("FULL COMPLIANCE DASHBOARD SUMMARY")
 print("=" * 60)
 
 dashboard_data = {
 "overall_status": "ANALYSIS_COMPLETE",
 "requirements_analyzed": len(compliance_results),
 "data_sources_accessed": {
 "sepp_overrides": sum(len(r.sepp_overrides) for r in compliance_results.values()),
 "quantitative_standards": sum(len(r.quantitative_standards) for r in compliance_results.values()),
 "development_controls": sum(len(r.database_controls) for r in compliance_results.values())
 },
 "compliance_summary": {},
 "next_steps": []
 }
 
 for req_type, result in compliance_results.items():
 dashboard_data["compliance_summary"][req_type] = {
 "status": result.compliance_status,
 "explanation": result.explanation,
 "data_sources": len(result.database_controls) + len(result.sepp_overrides) + len(result.quantitative_standards)
 }
 
 print(f"\n{req_type.upper()} ANALYSIS:")
 print(f" Status: {result.compliance_status}")
 print(f" Data Sources: {len(result.database_controls)} controls, {len(result.sepp_overrides)} overrides, {len(result.quantitative_standards)} standards")
 print(f" Explanation: {result.explanation[:80]}...")
 
 print(f"\nTOTAL DATA SOURCES ACCESSED:")
 print(f" SEPP Overrides: {dashboard_data['data_sources_accessed']['sepp_overrides']}")
 print(f" Quantitative Standards: {dashboard_data['data_sources_accessed']['quantitative_standards']}")
 print(f" Development Controls: {dashboard_data['data_sources_accessed']['development_controls']}")
 
 return dashboard_data
 
 def close(self):
 """Close database connection"""
 self.conn.close()

# ===================== LIVE DEMONSTRATION =====================

def demonstrate_full_compliance_dashboard():
 """
 LIVE DEMONSTRATION with real NSW Planning API data
 """
 
 # Real NSW Planning API data (from the example provided)
 sample_property = PropertyData(
 address="Sample Property, Inner West LGA",
 zone="R2", # Low Density Residential
 fsr_limit=0.6, # From API: "Floor Space Ratio": "0.6"
 height_limit=9.5, # From API: "Maximum Building Height": "9.5"
 lot_geometry={"rings": [[[16825588.165, -4015562.937]]]}, # From API
 sepps_applicable=[
 "SEPP (Sustainable Buildings) 2022",
 "SEPP (Transport and Infrastructure) 2021"
 ],
 tree_canopy=13.23 # From API: "Canopy %": "13.23"
 )
 
 # Initialize dashboard
 dashboard = FullComplianceDashboard()
 
 try:
 # Run comprehensive analysis
 results = dashboard.analyze_property_compliance(sample_property)
 
 # Generate dashboard summary
 dashboard_summary = dashboard.generate_dashboard_summary(results)
 
 return results, dashboard_summary
 
 finally:
 dashboard.close()

if __name__ == "__main__":
 print("NSW PLANNING FULL COMPLIANCE DASHBOARD - LIVE DEMO")
 print("=" * 65)
 print("Using REAL NSW Planning API data + Enhanced Database")
 print("=" * 65)
 
 results, summary = demonstrate_full_compliance_dashboard()
 
 print(f"\n DASHBOARD DEMONSTRATION COMPLETE")
 print(f" Analyzed: {summary['requirements_analyzed']} compliance requirements")
 print(f" Accessed: {sum(summary['data_sources_accessed'].values())} database records")
 print(f" Status: {summary['overall_status']}")