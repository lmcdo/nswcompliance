#!/usr/bin/env python3
"""
Complete pipeline: RAG-Anything → AutoSchemaKG → Validated Rules → JSON Output
Replaces hardcoded rules with properly extracted and validated DCP rules
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime

# Setup paths
script_dir = Path(__file__).parent
project_root = script_dir.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Ensure directories exist
os.makedirs(project_root / 'logs', exist_ok=True)
os.makedirs(project_root / 'public' / 'regulatory-data', exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(project_root / 'logs' / 'rule_generation.log'),
        logging.StreamHandler()
    ]
)

from processing.rag_enhanced_processor import RAGEnhancedProcessor
from processing.rule_generator import ComplianceRuleGenerator
from models import FormerCouncilArea

class ComplianceRulePipeline:
    """Complete pipeline for extracting and generating compliance rules"""
    
    def __init__(self):
        self.rag_processor = RAGEnhancedProcessor()
        self.rule_generator = ComplianceRuleGenerator()
        self.docs_path = project_root / "docs" / "dcps" / "INNERWEST"
        self.output_path = project_root / "public" / "regulatory-data"
        
        # Ensure output directory exists
        os.makedirs(self.output_path, exist_ok=True)
        os.makedirs(project_root / 'logs', exist_ok=True)
    
    def run_complete_pipeline(self):
        """Run the complete RAG → AutoSchema → Rules pipeline"""
        
        logging.info("Starting Complete Compliance Rule Generation Pipeline")
        logging.info("=" * 60)
        
        # Document mapping for each council area
        council_documents = {
            FormerCouncilArea.ASHFIELD: [
                "Inner West Ashfield DCP 2016 - Chapter F - Development Category with IWLEP 2022 amendment.pdf"
            ],
            FormerCouncilArea.LEICHHARDT: [
                "leichhardt/Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23.pdf"
            ],
            FormerCouncilArea.MARRICKVILLE: [
                "Marrickville/Marrickville DCP 2011 - Contents Nov 22.pdf"
            ]
        }
        
        all_generated_rules = []
        pipeline_report = {
            'started_at': datetime.now().isoformat(),
            'councils_processed': 0,
            'documents_processed': 0,
            'total_rules_generated': 0,
            'quality_summary': {},
            'processing_details': []
        }
        
        # Process each council area
        for council_area, documents in council_documents.items():
            logging.info(f"\n{council_area.value} Council Processing")
            logging.info("-" * 40)
            
            council_rules = []
            council_details = {
                'council': council_area.value,
                'documents': [],
                'rules_generated': 0,
                'average_quality': 0.0
            }
            
            for doc_name in documents:
                doc_path = self.docs_path / doc_name
                
                if not doc_path.exists():
                    logging.warning(f"Document not found: {doc_name}")
                    continue
                
                logging.info(f"Processing: {doc_name}")
                
                try:
                    # Step 1: RAG-Anything extraction
                    logging.info("  → RAG-Anything extraction...")
                    extraction_result = self.rag_processor.process_dcp_document(
                        str(doc_path), council_area
                    )
                    
                    if extraction_result['quality_score'] == 0:
                        logging.warning(f"  ✗ No quality data extracted from {doc_name}")
                        continue
                    
                    logging.info(f"  ✓ Extraction quality: {extraction_result['quality_score']:.2f}")
                    logging.info(f"  ✓ Rule types found: {list(extraction_result['extracted_rules'].keys())}")
                    
                    # Step 2: AutoSchemaKG rule generation
                    logging.info("  → AutoSchemaKG rule generation...")
                    generated_rules = self.rule_generator.generate_rules_from_extraction(extraction_result)
                    
                    if not generated_rules:
                        logging.warning(f"  ✗ No rules generated from {doc_name}")
                        continue
                    
                    logging.info(f"  ✓ Generated {len(generated_rules)} compliance rules")
                    
                    # Step 3: Rule validation
                    logging.info("  → Rule validation...")
                    validation_result = self.rule_generator.validate_rule_quality(generated_rules)
                    
                    logging.info(f"  ✓ Validation passed: {validation_result['value_validation']['passed']}")
                    logging.info(f"  ✓ Overall quality: {validation_result['overall_quality']:.2f}")
                    
                    if validation_result['value_validation']['warnings']:
                        for warning in validation_result['value_validation']['warnings']:
                            logging.warning(f"  ⚠ {warning}")
                    
                    council_rules.extend(generated_rules)
                    
                    # Record document details
                    doc_details = {
                        'document': doc_name,
                        'extraction_method': extraction_result['extraction_method'],
                        'quality_score': extraction_result['quality_score'],
                        'rules_generated': len(generated_rules),
                        'validation_result': validation_result
                    }
                    council_details['documents'].append(doc_details)
                    
                except Exception as e:
                    logging.error(f"  ✗ Failed to process {doc_name}: {e}")
                    continue
            
            # Save council-specific rules
            if council_rules:
                council_output_path = self.output_path / f"{council_area.value.lower()}-rules.json"
                success = self.rule_generator.save_rules_to_file(council_rules, str(council_output_path))
                
                if success:
                    logging.info(f"✓ Saved {len(council_rules)} {council_area.value} rules to {council_output_path}")
                    all_generated_rules.extend(council_rules)
                    
                    council_details['rules_generated'] = len(council_rules)
                    council_details['average_quality'] = sum(
                        doc['quality_score'] for doc in council_details['documents']
                    ) / len(council_details['documents']) if council_details['documents'] else 0.0
                    
                    pipeline_report['councils_processed'] += 1
                    pipeline_report['documents_processed'] += len(council_details['documents'])
            
            pipeline_report['processing_details'].append(council_details)
        
        # Save combined rules for all councils
        if all_generated_rules:
            combined_output_path = self.output_path / "inner-west-compliance-rules.json"
            success = self.rule_generator.save_rules_to_file(all_generated_rules, str(combined_output_path))
            
            if success:
                logging.info(f"✓ Saved {len(all_generated_rules)} combined rules to {combined_output_path}")
            
            # Generate overall quality summary
            overall_validation = self.rule_generator.validate_rule_quality(all_generated_rules)
            pipeline_report['total_rules_generated'] = len(all_generated_rules)
            pipeline_report['quality_summary'] = overall_validation
        
        # Save pipeline report
        pipeline_report['completed_at'] = datetime.now().isoformat()
        report_path = self.output_path / "rule-generation-report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(pipeline_report, f, indent=2, ensure_ascii=False)
        
        # Print final summary
        self.print_pipeline_summary(pipeline_report)
        
        return pipeline_report
    
    def print_pipeline_summary(self, report: dict):
        """Print a comprehensive pipeline summary"""
        
        print("\n" + "=" * 60)
        print("COMPLIANCE RULE GENERATION PIPELINE - COMPLETE")
        print("=" * 60)
        
        print(f"\n📊 PROCESSING SUMMARY:")
        print(f"   Councils processed: {report['councils_processed']}/3")
        print(f"   Documents processed: {report['documents_processed']}")
        print(f"   Total rules generated: {report['total_rules_generated']}")
        
        if report['quality_summary']:
            quality = report['quality_summary']
            print(f"\n📈 QUALITY SUMMARY:")
            print(f"   Overall quality score: {quality['overall_quality']:.2f}")
            print(f"   Value validation passed: {quality['value_validation']['passed']}")
            print(f"   Value validation failed: {quality['value_validation']['failed']}")
            
            if quality['confidence_distribution']:
                print(f"   Confidence distribution:")
                for conf, count in quality['confidence_distribution'].items():
                    print(f"     {conf}: {count} rules")
            
            print(f"   Coverage:")
            for coverage_type, count in quality['coverage'].items():
                print(f"     {coverage_type.title()}: {count} rules")
        
        print(f"\n📋 COUNCIL DETAILS:")
        for council_detail in report['processing_details']:
            council = council_detail['council']
            rules = council_detail['rules_generated']
            quality = council_detail['average_quality']
            
            print(f"   {council}: {rules} rules (avg quality: {quality:.2f})")
            
            for doc in council_detail['documents']:
                doc_name = os.path.basename(doc['document'])[:50]
                print(f"     └─ {doc_name}: {doc['rules_generated']} rules")
        
        if report['quality_summary'].get('value_validation', {}).get('warnings'):
            print(f"\n⚠️  VALIDATION WARNINGS:")
            for warning in report['quality_summary']['value_validation']['warnings'][:5]:  # Show first 5
                print(f"   • {warning}")
            
            remaining = len(report['quality_summary']['value_validation']['warnings']) - 5
            if remaining > 0:
                print(f"   ... and {remaining} more warnings")
        
        print(f"\n📁 OUTPUT FILES:")
        print(f"   Combined rules: public/regulatory-data/inner-west-compliance-rules.json")
        print(f"   Individual councils: public/regulatory-data/<council>-rules.json")
        print(f"   Pipeline report: public/regulatory-data/rule-generation-report.json")
        
        print(f"\n🔄 NEXT STEPS:")
        print(f"   1. Review validation warnings and fix any unrealistic values")
        print(f"   2. Update deterministic compliance engine to load these rules")
        print(f"   3. Test compliance checking with real property addresses")
        
        print(f"\n✅ Pipeline completed successfully!")
        print("=" * 60)

def main():
    """Run the complete compliance rule generation pipeline"""
    
    try:
        pipeline = ComplianceRulePipeline()
        report = pipeline.run_complete_pipeline()
        
        # Exit with appropriate code
        if report['total_rules_generated'] > 0:
            sys.exit(0)  # Success
        else:
            print("\n❌ Pipeline completed but no rules were generated")
            sys.exit(1)  # Failure
            
    except KeyboardInterrupt:
        print("\n⏹️ Pipeline interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n💥 Pipeline failed with error: {e}")
        logging.exception("Pipeline failed")
        sys.exit(1)

if __name__ == "__main__":
    main()