"""
Rule Generator using AutoSchemaKG to convert RAG-extracted data to structured compliance rules
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from pathlib import Path

# Try to import AutoSchemaKG
try:
    from autoschemakg import AutoSchemaKG
    AUTOSCHEMAKG_AVAILABLE = True
except ImportError:
    AUTOSCHEMAKG_AVAILABLE = False
    logging.warning("AutoSchemaKG not available, using structured rule generation")

from ..models import FormerCouncilArea, SetbackRule

class ComplianceRuleGenerator:
    """Generate structured compliance rules from RAG-extracted data"""
    
    def __init__(self):
        self.schema_engine = None
        if AUTOSCHEMAKG_AVAILABLE:
            try:
                self.schema_engine = AutoSchemaKG()
                logging.info("AutoSchemaKG engine initialized")
            except Exception as e:
                logging.error(f"Failed to initialize AutoSchemaKG: {e}")
                self.schema_engine = None
        
        # Rule templates for different setback types
        self.rule_templates = {
            'rear_setback': {
                'id_pattern': '{council}_{zone}_REAR_SETBACK',
                'jurisdiction': 'DCP',
                'section_pattern': 'Residential Development - Building Envelope',
                'applies_to_zones': ['R2', 'R3', 'R4']
            },
            'side_setback': {
                'id_pattern': '{council}_{zone}_SIDE_SETBACK', 
                'jurisdiction': 'DCP',
                'section_pattern': 'Residential Development - Building Envelope',
                'applies_to_zones': ['R2', 'R3', 'R4']
            },
            'front_setback': {
                'id_pattern': '{council}_{zone}_FRONT_SETBACK',
                'jurisdiction': 'DCP', 
                'section_pattern': 'Residential Development - Building Envelope',
                'applies_to_zones': ['R2', 'R3', 'R4']
            },
            'height_in_setback': {
                'id_pattern': '{council}_{zone}_HEIGHT_IN_SETBACK',
                'jurisdiction': 'DCP',
                'section_pattern': 'Residential Development - Building Envelope',
                'applies_to_zones': ['R2', 'R3', 'R4']
            }
        }
    
    def generate_rules_from_extraction(self, extraction_result: Dict) -> List[Dict]:
        """
        Generate structured compliance rules from RAG extraction results
        
        Args:
            extraction_result: Output from RAGEnhancedProcessor
            
        Returns:
            List of structured compliance rules ready for the deterministic engine
        """
        logging.info(f"Generating rules from extraction: {extraction_result.get('source_file', 'unknown')}")
        
        if not extraction_result.get('extracted_rules'):
            logging.warning("No extracted rules to process")
            return []
        
        council_area = extraction_result.get('council_area', 'Unknown')
        source_file = extraction_result.get('source_file', '')
        extraction_method = extraction_result.get('extraction_method', 'Unknown')
        
        generated_rules = []
        
        # Process each extracted rule type
        for rule_type, rule_data in extraction_result['extracted_rules'].items():
            try:
                if self.schema_engine:
                    # Use AutoSchemaKG for enhanced rule generation
                    rules = self._generate_with_autoschema(rule_type, rule_data, council_area, source_file)
                else:
                    # Use structured template-based generation
                    rules = self._generate_with_templates(rule_type, rule_data, council_area, source_file)
                
                # Add extraction metadata
                for rule in rules:
                    rule['extraction_metadata'] = {
                        'method': extraction_method,
                        'quality_score': extraction_result.get('quality_score', 0.0),
                        'extracted_at': datetime.now().isoformat(),
                        'source_file': os.path.basename(source_file)
                    }
                
                generated_rules.extend(rules)
                
            except Exception as e:
                logging.error(f"Failed to generate rule for {rule_type}: {e}")
                continue
        
        logging.info(f"Generated {len(generated_rules)} compliance rules")
        return generated_rules
    
    def _generate_with_autoschema(self, rule_type: str, rule_data: Dict, council_area: str, source_file: str) -> List[Dict]:
        """Generate rules using AutoSchemaKG for enhanced structured output"""
        
        # Prepare input for AutoSchemaKG
        input_data = {
            'rule_type': rule_type,
            'extracted_data': rule_data,
            'context': {
                'council': council_area,
                'document': os.path.basename(source_file),
                'jurisdiction': 'Local DCP'
            }
        }
        
        try:
            # Use AutoSchemaKG to generate structured schema
            schema_result = self.schema_engine.generate_schema(input_data)
            
            # Convert AutoSchemaKG output to compliance rule format
            rule = self._convert_schema_to_rule(schema_result, rule_type, council_area, source_file)
            return [rule] if rule else []
            
        except Exception as e:
            logging.error(f"AutoSchemaKG generation failed: {e}")
            # Fallback to template-based generation
            return self._generate_with_templates(rule_type, rule_data, council_area, source_file)
    
    def _generate_with_templates(self, rule_type: str, rule_data: Dict, council_area: str, source_file: str) -> List[Dict]:
        """Generate rules using structured templates"""
        
        if rule_type not in self.rule_templates:
            logging.warning(f"No template for rule type: {rule_type}")
            return []
        
        template = self.rule_templates[rule_type]
        
        # Extract the measurement value
        value = rule_data.get('value')
        if value is None:
            logging.warning(f"No value found for {rule_type}")
            return []
        
        # Determine confidence level based on extraction quality
        confidence = self._determine_confidence_level(rule_data, rule_type)
        
        # Generate rule for each applicable zone
        rules = []
        for zone in template['applies_to_zones']:
            rule = {
                'id': template['id_pattern'].format(
                    council=council_area.upper().replace(' ', '_'),
                    zone=zone
                ),
                'jurisdiction': template['jurisdiction'],
                'authority': f"{council_area} Council",
                'applies_to': {
                    'lga': 'Inner West',
                    'zones': [zone],
                    'former_council': council_area
                },
                'requirements': [{
                    'type': self._map_rule_type_to_requirement(rule_type),
                    'subtype': self._extract_subtype(rule_type),
                    'operator': self._determine_operator(rule_type),
                    'value': value,
                    'units': rule_data.get('units', 'metres'),
                    'context': rule_data.get('context', f"{rule_type} requirement"),
                    'confidence': confidence
                }],
                'source': {
                    'document': self._extract_document_name(source_file),
                    'section': template['section_pattern'],
                    'clause': self._extract_clause_reference(rule_data, source_file),
                    'url': self._generate_source_url(council_area),
                    'effective_date': self._estimate_effective_date(source_file)
                },
                'priority': self._determine_priority(template['jurisdiction']),
                'validation': {
                    'value_range': self._get_reasonable_range(rule_type),
                    'source_count': rule_data.get('source_count', 1),
                    'all_extracted_values': rule_data.get('all_values', [value])
                }
            }
            rules.append(rule)
        
        return rules
    
    def _determine_confidence_level(self, rule_data: Dict, rule_type: str) -> str:
        """Determine confidence level based on extraction quality"""
        confidence_score = rule_data.get('confidence', 0.5)
        source_count = rule_data.get('source_count', 1)
        value = rule_data.get('value', 0)
        
        # Check if value is in reasonable range
        min_val, max_val = self._get_reasonable_range(rule_type)
        is_reasonable = min_val <= value <= max_val
        
        # High confidence: good score, multiple sources, reasonable value
        if confidence_score >= 0.8 and source_count >= 2 and is_reasonable:
            return 'VERIFIED'
        
        # Medium confidence: decent score or single good source
        elif confidence_score >= 0.6 and is_reasonable:
            return 'EXTRACTED'
        
        # Low confidence: everything else
        else:
            return 'TENTATIVE'
    
    def _map_rule_type_to_requirement(self, rule_type: str) -> str:
        """Map internal rule types to requirement types"""
        mapping = {
            'rear_setback': 'min_setback',
            'side_setback': 'min_setback', 
            'front_setback': 'min_setback',
            'height_in_setback': 'max_height_in_area'
        }
        return mapping.get(rule_type, 'min_setback')
    
    def _extract_subtype(self, rule_type: str) -> Optional[str]:
        """Extract subtype from rule type"""
        if 'rear' in rule_type:
            return 'rear'
        elif 'side' in rule_type:
            return 'side'
        elif 'front' in rule_type:
            return 'front'
        return None
    
    def _determine_operator(self, rule_type: str) -> str:
        """Determine the comparison operator for the rule"""
        if 'setback' in rule_type:
            return '>='  # Setbacks are minimums
        elif 'height' in rule_type:
            return '<='  # Heights are maximums
        return '>='
    
    def _get_reasonable_range(self, rule_type: str) -> Tuple[float, float]:
        """Get reasonable value range for validation"""
        ranges = {
            'rear_setback': (1.0, 15.0),
            'side_setback': (0.5, 10.0),
            'front_setback': (0.0, 20.0),  # Front can be 0 in some cases
            'height_in_setback': (2.5, 12.0)
        }
        return ranges.get(rule_type, (0.5, 20.0))
    
    def _extract_document_name(self, source_file: str) -> str:
        """Extract clean document name from file path"""
        filename = os.path.basename(source_file)
        
        # Clean up the filename
        if 'Ashfield DCP' in filename:
            return 'Inner West Ashfield DCP 2016'
        elif 'Leichhardt DCP' in filename:
            return 'Leichhardt DCP 2013'
        elif 'Marrickville DCP' in filename:
            return 'Marrickville DCP 2011'
        
        # Generic cleanup
        clean_name = filename.replace('.pdf', '').replace('_', ' ')
        return clean_name[:100]  # Limit length
    
    def _extract_clause_reference(self, rule_data: Dict, source_file: str) -> str:
        """Extract clause reference from context or filename"""
        context = rule_data.get('context', '')
        
        # Look for clause patterns in context
        clause_patterns = [
            r'clause\s*(\d+(?:\.\d+)*)',
            r'section\s*(\d+(?:\.\d+)*)', 
            r'part\s*([A-Z]\d*)',
            r'chapter\s*([A-Z]\d*)'
        ]
        
        for pattern in clause_patterns:
            import re
            match = re.search(pattern, context, re.IGNORECASE)
            if match:
                return f"Clause {match.group(1)}"
        
        # Extract from filename if available
        filename = os.path.basename(source_file)
        if 'Chapter F' in filename:
            return 'Chapter F - Development Category'
        elif 'Part C' in filename:
            return 'Part C - Place'
        
        return 'Building Envelope Requirements'
    
    def _generate_source_url(self, council_area: str) -> str:
        """Generate appropriate source URL"""
        base_url = "https://www.innerwest.nsw.gov.au/development/development-control-plans"
        
        # Could be enhanced with specific document URLs
        return base_url
    
    def _estimate_effective_date(self, source_file: str) -> str:
        """Estimate effective date from filename"""
        import re
        
        filename = os.path.basename(source_file)
        
        # Look for year patterns
        year_match = re.search(r'20(\d{2})', filename)
        if year_match:
            year = f"20{year_match.group(1)}"
            return f"{year}-01-01"  # Assume January 1st
        
        # Default dates for known DCPs
        if 'Ashfield' in filename:
            return '2016-01-01'
        elif 'Leichhardt' in filename:
            return '2013-01-01'
        elif 'Marrickville' in filename:
            return '2011-01-01'
        
        return '2016-01-01'  # Conservative default
    
    def _determine_priority(self, jurisdiction: str) -> int:
        """Determine rule priority based on jurisdiction hierarchy"""
        priorities = {
            'LEP': 1,  # Highest priority
            'SEPP': 2,
            'DCP': 3   # Lowest priority
        }
        return priorities.get(jurisdiction, 3)
    
    def _convert_schema_to_rule(self, schema_result, rule_type: str, council_area: str, source_file: str) -> Optional[Dict]:
        """Convert AutoSchemaKG output to compliance rule format"""
        
        try:
            # This would need to be adapted based on AutoSchemaKG's actual output format
            # For now, implementing a basic conversion structure
            
            if not schema_result:
                return None
            
            # Extract structured information from schema result
            # This is a placeholder - would need real AutoSchemaKG integration
            rule = {
                'id': f"AUTOSCHEMA_{council_area.upper()}_{rule_type.upper()}",
                'jurisdiction': 'DCP',
                'authority': f"{council_area} Council",
                'generated_by': 'AutoSchemaKG',
                'schema_result': schema_result,
                # ... additional fields would be populated from schema_result
            }
            
            return rule
            
        except Exception as e:
            logging.error(f"Failed to convert schema result: {e}")
            return None
    
    def save_rules_to_file(self, rules: List[Dict], output_path: str) -> bool:
        """Save generated rules to JSON file"""
        try:
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            output_data = {
                'generated_at': datetime.now().isoformat(),
                'rule_count': len(rules),
                'rules': rules,
                'metadata': {
                    'generator': 'ComplianceRuleGenerator',
                    'autoschema_available': AUTOSCHEMAKG_AVAILABLE,
                    'version': '1.0'
                }
            }
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            
            logging.info(f"Saved {len(rules)} rules to {output_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to save rules: {e}")
            return False
    
    def validate_rule_quality(self, rules: List[Dict]) -> Dict:
        """Validate the quality of generated rules"""
        
        validation_result = {
            'total_rules': len(rules),
            'confidence_distribution': {},
            'value_validation': {'passed': 0, 'failed': 0, 'warnings': []},
            'coverage': {'rear': 0, 'side': 0, 'front': 0, 'height': 0},
            'overall_quality': 0.0
        }
        
        for rule in rules:
            # Count confidence levels
            for req in rule.get('requirements', []):
                confidence = req.get('confidence', 'UNKNOWN')
                validation_result['confidence_distribution'][confidence] = \
                    validation_result['confidence_distribution'].get(confidence, 0) + 1
                
                # Validate value ranges
                rule_type = req.get('subtype', req.get('type', ''))
                value = req.get('value')
                
                if value and rule_type:
                    min_val, max_val = self._get_reasonable_range(f"{rule_type}_setback")
                    
                    if min_val <= value <= max_val:
                        validation_result['value_validation']['passed'] += 1
                    else:
                        validation_result['value_validation']['failed'] += 1
                        validation_result['value_validation']['warnings'].append(
                            f"Rule {rule.get('id', 'unknown')}: {rule_type} value {value}m outside reasonable range [{min_val}-{max_val}]"
                        )
                    
                    # Count coverage
                    if rule_type in validation_result['coverage']:
                        validation_result['coverage'][rule_type] += 1
        
        # Calculate overall quality score
        total_checks = validation_result['value_validation']['passed'] + validation_result['value_validation']['failed']
        if total_checks > 0:
            validation_result['overall_quality'] = validation_result['value_validation']['passed'] / total_checks
        
        return validation_result