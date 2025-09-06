#!/usr/bin/env python3
"""
Comprehensive evaluation framework for RAG output and schema effectiveness
Tests extraction quality, validation accuracy, and rule generation reliability
"""

import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class GroundTruthRule:
    """Known correct setback values for validation"""
    council: str
    rule_type: str  # rear_setback, side_setback, front_setback
    zone: str
    expected_value: float
    source_document: str
    confidence: str  # How sure we are about this ground truth

@dataclass
class EvaluationMetric:
    """Evaluation metric result"""
    metric_name: str
    score: float
    max_score: float
    details: Dict
    passed: bool

class RAGEffectivenessEvaluator:
    """Evaluate the effectiveness of RAG extraction and schema generation"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.rules_path = self.project_root / "public" / "regulatory-data" / "inner-west-compliance-rules.json"
        
        # Ground truth data - manually verified setback values
        self.ground_truth = [
            # Ashfield Council - manually verified from DCPs
            GroundTruthRule("Ashfield", "side_setback", "R2", 0.9, "Ashfield DCP 2016", "HIGH"),
            GroundTruthRule("Ashfield", "rear_setback", "R2", 6.0, "Ashfield DCP 2016", "MEDIUM"),
            GroundTruthRule("Ashfield", "front_setback", "R2", 6.0, "Ashfield DCP 2016", "LOW"),  # This varies by streetscape
            
            # Leichhardt Council - manually verified
            GroundTruthRule("Leichhardt", "side_setback", "R2", 1.0, "Leichhardt DCP 2013", "MEDIUM"),
            GroundTruthRule("Leichhardt", "rear_setback", "R2", 6.0, "Leichhardt DCP 2013", "MEDIUM"),
            
            # Marrickville Council - estimated from typical DCP patterns
            GroundTruthRule("Marrickville", "side_setback", "R2", 1.0, "Marrickville DCP 2011", "LOW"),
            GroundTruthRule("Marrickville", "rear_setback", "R2", 6.0, "Marrickville DCP 2011", "LOW"),
        ]
        
        # Quality thresholds
        self.thresholds = {
            'accuracy_threshold': 0.8,      # 80% of extracted values should be accurate
            'coverage_threshold': 0.7,      # 70% of expected rules should be found
            'precision_tolerance': 0.5,     # ±0.5m tolerance for setback measurements
            'confidence_threshold': 0.6,    # Minimum confidence for extracted rules
        }
    
    def run_complete_evaluation(self) -> Dict:
        """Run comprehensive evaluation of RAG effectiveness"""
        
        print("RAG EFFECTIVENESS EVALUATION")
        print("=" * 50)
        
        # Load generated rules
        if not self.rules_path.exists():
            print("ERROR: No generated rules found! Run the pipeline first.")
            return {'error': 'No rules file found'}
        
        with open(self.rules_path, 'r', encoding='utf-8') as f:
            rules_data = json.load(f)
        
        extracted_rules = rules_data.get('rules', [])
        
        print(f"Evaluating {len(extracted_rules)} extracted rules")
        print(f"Against {len(self.ground_truth)} ground truth values")
        
        # Run evaluation metrics
        evaluation_results = {
            'timestamp': datetime.now().isoformat(),
            'rules_evaluated': len(extracted_rules),
            'ground_truth_count': len(self.ground_truth),
            'metrics': {},
            'detailed_results': {},
            'overall_score': 0.0,
            'passed': False
        }
        
        # Metric 1: Accuracy (how close are extracted values to ground truth?)
        accuracy_result = self.evaluate_accuracy(extracted_rules)
        evaluation_results['metrics']['accuracy'] = accuracy_result
        
        # Metric 2: Coverage (how many expected rules were found?)
        coverage_result = self.evaluate_coverage(extracted_rules)
        evaluation_results['metrics']['coverage'] = coverage_result
        
        # Metric 3: Precision (are values within reasonable tolerance?)
        precision_result = self.evaluate_precision(extracted_rules)
        evaluation_results['metrics']['precision'] = precision_result
        
        # Metric 4: Confidence Distribution (are confidence levels appropriate?)
        confidence_result = self.evaluate_confidence_distribution(extracted_rules)
        evaluation_results['metrics']['confidence'] = confidence_result
        
        # Metric 5: Schema Quality (are generated rules well-formed?)
        schema_result = self.evaluate_schema_quality(extracted_rules)
        evaluation_results['metrics']['schema'] = schema_result
        
        # Metric 6: Extraction Consistency (do we get consistent results?)
        consistency_result = self.evaluate_extraction_consistency(extracted_rules)
        evaluation_results['metrics']['consistency'] = consistency_result
        
        # Calculate overall score
        all_metrics = [accuracy_result, coverage_result, precision_result, 
                      confidence_result, schema_result, consistency_result]
        
        total_score = sum(m.score for m in all_metrics)
        max_total = sum(m.max_score for m in all_metrics)
        evaluation_results['overall_score'] = total_score / max_total if max_total > 0 else 0.0
        evaluation_results['passed'] = evaluation_results['overall_score'] >= 0.7  # 70% threshold
        
        # Generate detailed analysis
        evaluation_results['detailed_results'] = self.generate_detailed_analysis(extracted_rules)
        
        # Print results
        self.print_evaluation_results(evaluation_results)
        
        # Save evaluation report
        self.save_evaluation_report(evaluation_results)
        
        return evaluation_results
    
    def evaluate_accuracy(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate how accurate extracted values are compared to ground truth"""
        
        matches = []
        misses = []
        
        for ground_truth in self.ground_truth:
            # Find matching extracted rule
            matching_rule = self.find_matching_rule(extracted_rules, ground_truth)
            
            if matching_rule:
                extracted_value = matching_rule['requirements'][0]['value']
                expected_value = ground_truth.expected_value
                
                # Calculate accuracy (inverse of relative error)
                error = abs(extracted_value - expected_value) / expected_value
                accuracy = max(0, 1 - error)  # 0 to 1 scale
                
                match_result = {
                    'rule': f"{ground_truth.council} {ground_truth.rule_type}",
                    'extracted': extracted_value,
                    'expected': expected_value,
                    'accuracy': accuracy,
                    'error_meters': abs(extracted_value - expected_value),
                    'within_tolerance': abs(extracted_value - expected_value) <= self.thresholds['precision_tolerance']
                }
                matches.append(match_result)
            else:
                misses.append({
                    'rule': f"{ground_truth.council} {ground_truth.rule_type}",
                    'expected': ground_truth.expected_value,
                    'reason': 'Not extracted'
                })
        
        # Calculate overall accuracy
        if matches:
            avg_accuracy = sum(m['accuracy'] for m in matches) / len(matches)
            within_tolerance_count = sum(1 for m in matches if m['within_tolerance'])
            tolerance_rate = within_tolerance_count / len(matches)
        else:
            avg_accuracy = 0.0
            tolerance_rate = 0.0
        
        return EvaluationMetric(
            metric_name="Accuracy",
            score=avg_accuracy * 100,
            max_score=100,
            details={
                'matches': matches,
                'misses': misses,
                'average_accuracy': avg_accuracy,
                'within_tolerance_rate': tolerance_rate,
                'tolerance_threshold': self.thresholds['precision_tolerance']
            },
            passed=avg_accuracy >= self.thresholds['accuracy_threshold']
        )
    
    def evaluate_coverage(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate what percentage of expected rules were extracted"""
        
        expected_rules = set()
        found_rules = set()
        missing_rules = []
        
        # Build expected rule set
        for gt in self.ground_truth:
            rule_key = f"{gt.council}_{gt.rule_type}_{gt.zone}"
            expected_rules.add(rule_key)
        
        # Check what was actually found
        for rule in extracted_rules:
            council = rule['applies_to']['former_council']
            rule_type = rule['requirements'][0]['subtype'] + '_setback'
            zone = rule['applies_to']['zones'][0] if rule['applies_to']['zones'] else 'R2'
            
            rule_key = f"{council}_{rule_type}_{zone}"
            found_rules.add(rule_key)
        
        # Find missing rules
        missing = expected_rules - found_rules
        for missing_key in missing:
            parts = missing_key.split('_')
            missing_rules.append({
                'council': parts[0],
                'rule_type': parts[1] + '_' + parts[2],
                'zone': parts[3] if len(parts) > 3 else 'R2'
            })
        
        coverage_rate = len(found_rules) / len(expected_rules) if expected_rules else 0
        
        return EvaluationMetric(
            metric_name="Coverage",
            score=coverage_rate * 100,
            max_score=100,
            details={
                'expected_count': len(expected_rules),
                'found_count': len(found_rules),
                'coverage_rate': coverage_rate,
                'missing_rules': missing_rules,
                'found_rules': list(found_rules)
            },
            passed=coverage_rate >= self.thresholds['coverage_threshold']
        )
    
    def evaluate_precision(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate if extracted values are within reasonable ranges"""
        
        reasonable_ranges = {
            'rear_setback': (1.0, 15.0),
            'side_setback': (0.3, 8.0),
            'front_setback': (0.0, 20.0)
        }
        
        valid_rules = []
        invalid_rules = []
        
        for rule in extracted_rules:
            req = rule['requirements'][0]
            rule_type = req['subtype'] + '_setback'
            value = req['value']
            
            if rule_type in reasonable_ranges:
                min_val, max_val = reasonable_ranges[rule_type]
                
                if min_val <= value <= max_val:
                    valid_rules.append({
                        'rule_id': rule['id'],
                        'value': value,
                        'range': f"{min_val}-{max_val}m",
                        'valid': True
                    })
                else:
                    invalid_rules.append({
                        'rule_id': rule['id'],
                        'value': value,
                        'range': f"{min_val}-{max_val}m",
                        'valid': False,
                        'reason': f"Value {value}m outside reasonable range"
                    })
        
        precision_rate = len(valid_rules) / len(extracted_rules) if extracted_rules else 0
        
        return EvaluationMetric(
            metric_name="Precision",
            score=precision_rate * 100,
            max_score=100,
            details={
                'total_rules': len(extracted_rules),
                'valid_rules': len(valid_rules),
                'invalid_rules': len(invalid_rules),
                'precision_rate': precision_rate,
                'invalid_details': invalid_rules,
                'reasonable_ranges': reasonable_ranges
            },
            passed=precision_rate >= 0.9  # 90% should be within reasonable ranges
        )
    
    def evaluate_confidence_distribution(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate if confidence levels are appropriate"""
        
        confidence_counts = {}
        low_confidence_rules = []
        
        for rule in extracted_rules:
            conf = rule['requirements'][0].get('confidence', 'UNKNOWN')
            confidence_counts[conf] = confidence_counts.get(conf, 0) + 1
            
            # Flag rules with unreasonably high confidence given extraction method
            if conf == 'VERIFIED' and rule['extraction_metadata']['method'] == 'Pattern Matching + Validation':
                low_confidence_rules.append({
                    'rule_id': rule['id'],
                    'confidence': conf,
                    'method': rule['extraction_metadata']['method'],
                    'issue': 'Pattern matching should not give VERIFIED confidence'
                })
        
        # Calculate confidence appropriateness score
        total_rules = len(extracted_rules)
        appropriate_confidence = total_rules - len(low_confidence_rules)
        confidence_score = appropriate_confidence / total_rules if total_rules else 0
        
        return EvaluationMetric(
            metric_name="Confidence",
            score=confidence_score * 100,
            max_score=100,
            details={
                'confidence_distribution': confidence_counts,
                'inappropriate_confidence': low_confidence_rules,
                'appropriateness_rate': confidence_score
            },
            passed=confidence_score >= 0.8
        )
    
    def evaluate_schema_quality(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate if generated rule schema is well-formed"""
        
        required_fields = ['id', 'jurisdiction', 'authority', 'applies_to', 'requirements', 'source']
        required_requirement_fields = ['type', 'subtype', 'operator', 'value', 'units']
        
        valid_rules = []
        invalid_rules = []
        
        for rule in extracted_rules:
            issues = []
            
            # Check top-level fields
            for field in required_fields:
                if field not in rule:
                    issues.append(f"Missing field: {field}")
            
            # Check requirement fields
            if 'requirements' in rule and rule['requirements']:
                req = rule['requirements'][0]
                for field in required_requirement_fields:
                    if field not in req:
                        issues.append(f"Missing requirement field: {field}")
                
                # Validate specific field values
                if 'operator' in req and req['operator'] not in ['>=', '<=', '>', '<', '=']:
                    issues.append(f"Invalid operator: {req['operator']}")
                
                if 'units' in req and req['units'] != 'metres':
                    issues.append(f"Unexpected units: {req['units']}")
            
            if issues:
                invalid_rules.append({
                    'rule_id': rule.get('id', 'unknown'),
                    'issues': issues
                })
            else:
                valid_rules.append(rule['id'])
        
        schema_quality = len(valid_rules) / len(extracted_rules) if extracted_rules else 0
        
        return EvaluationMetric(
            metric_name="Schema Quality",
            score=schema_quality * 100,
            max_score=100,
            details={
                'valid_rules': len(valid_rules),
                'invalid_rules': len(invalid_rules),
                'schema_quality_rate': schema_quality,
                'validation_issues': invalid_rules
            },
            passed=schema_quality >= 0.95  # 95% should be well-formed
        )
    
    def evaluate_extraction_consistency(self, extracted_rules: List[Dict]) -> EvaluationMetric:
        """Evaluate consistency of extraction across similar rule types"""
        
        # Group rules by type and council
        rule_groups = {}
        for rule in extracted_rules:
            council = rule['applies_to']['former_council']
            rule_type = rule['requirements'][0]['subtype']
            
            key = f"{council}_{rule_type}"
            if key not in rule_groups:
                rule_groups[key] = []
            rule_groups[key].append(rule)
        
        # Check for inconsistencies within groups
        inconsistencies = []
        total_groups = len(rule_groups)
        consistent_groups = 0
        
        for group_key, rules in rule_groups.items():
            if len(rules) > 1:
                # Multiple rules of same type for same council - should be consistent
                values = [r['requirements'][0]['value'] for r in rules]
                value_range = max(values) - min(values)
                
                if value_range > 0.2:  # More than 0.2m difference is inconsistent
                    inconsistencies.append({
                        'group': group_key,
                        'rule_count': len(rules),
                        'values': values,
                        'range': value_range,
                        'issue': 'Inconsistent values for same rule type'
                    })
                else:
                    consistent_groups += 1
            else:
                consistent_groups += 1  # Single rule is consistent by definition
        
        consistency_rate = consistent_groups / total_groups if total_groups else 1
        
        return EvaluationMetric(
            metric_name="Consistency",
            score=consistency_rate * 100,
            max_score=100,
            details={
                'total_groups': total_groups,
                'consistent_groups': consistent_groups,
                'inconsistencies': inconsistencies,
                'consistency_rate': consistency_rate
            },
            passed=consistency_rate >= 0.9
        )
    
    def find_matching_rule(self, extracted_rules: List[Dict], ground_truth: GroundTruthRule) -> Optional[Dict]:
        """Find extracted rule matching ground truth"""
        
        for rule in extracted_rules:
            council = rule['applies_to']['former_council']
            rule_type = rule['requirements'][0]['subtype'] + '_setback'
            zone = rule['applies_to']['zones'][0] if rule['applies_to']['zones'] else 'R2'
            
            if (council == ground_truth.council and 
                rule_type == ground_truth.rule_type and 
                zone == ground_truth.zone):
                return rule
        
        return None
    
    def generate_detailed_analysis(self, extracted_rules: List[Dict]) -> Dict:
        """Generate detailed analysis of extraction results"""
        
        analysis = {
            'extraction_summary': {
                'total_rules': len(extracted_rules),
                'councils': set(),
                'rule_types': set(),
                'confidence_levels': set()
            },
            'value_analysis': {
                'value_distribution': {},
                'outliers': [],
                'common_values': {}
            },
            'source_analysis': {
                'documents_processed': set(),
                'extraction_methods': set(),
                'quality_scores': []
            }
        }
        
        # Analyze extracted rules
        for rule in extracted_rules:
            council = rule['applies_to']['former_council']
            rule_type = rule['requirements'][0]['subtype']
            confidence = rule['requirements'][0].get('confidence', 'UNKNOWN')
            value = rule['requirements'][0]['value']
            
            analysis['extraction_summary']['councils'].add(council)
            analysis['extraction_summary']['rule_types'].add(rule_type)
            analysis['extraction_summary']['confidence_levels'].add(confidence)
            
            # Value analysis
            if rule_type not in analysis['value_analysis']['value_distribution']:
                analysis['value_analysis']['value_distribution'][rule_type] = []
            analysis['value_analysis']['value_distribution'][rule_type].append(value)
            
            # Source analysis
            if 'extraction_metadata' in rule:
                method = rule['extraction_metadata'].get('method', 'Unknown')
                quality = rule['extraction_metadata'].get('quality_score', 0)
                
                analysis['source_analysis']['extraction_methods'].add(method)
                analysis['source_analysis']['quality_scores'].append(quality)
            
            if 'source' in rule:
                doc = rule['source'].get('document', 'Unknown')
                analysis['source_analysis']['documents_processed'].add(doc)
        
        # Convert sets to lists for JSON serialization
        for key in analysis['extraction_summary']:
            if isinstance(analysis['extraction_summary'][key], set):
                analysis['extraction_summary'][key] = list(analysis['extraction_summary'][key])
        
        analysis['source_analysis']['documents_processed'] = list(analysis['source_analysis']['documents_processed'])
        analysis['source_analysis']['extraction_methods'] = list(analysis['source_analysis']['extraction_methods'])
        
        return analysis
    
    def print_evaluation_results(self, results: Dict):
        """Print comprehensive evaluation results"""
        
        print(f"\n" + "=" * 60)
        print("RAG EFFECTIVENESS EVALUATION RESULTS")
        print("=" * 60)
        
        # Overall score
        overall_score = results['overall_score'] * 100
        status = "✅ PASSED" if results['passed'] else "❌ FAILED"
        
        print(f"\n🎯 OVERALL SCORE: {overall_score:.1f}% {status}")
        print(f"📊 Rules Evaluated: {results['rules_evaluated']}")
        print(f"📋 Ground Truth Items: {results['ground_truth_count']}")
        
        # Individual metrics
        print(f"\n📈 DETAILED METRICS:")
        for metric_name, metric in results['metrics'].items():
            status_icon = "✅" if metric.passed else "❌"
            print(f"   {status_icon} {metric.metric_name}: {metric.score:.1f}/{metric.max_score}")
        
        # Key findings
        print(f"\n🔍 KEY FINDINGS:")
        
        accuracy = results['metrics']['accuracy']
        print(f"   • Accuracy: {len(accuracy.details['matches'])} matches, {len(accuracy.details['misses'])} misses")
        if accuracy.details['matches']:
            avg_error = sum(m['error_meters'] for m in accuracy.details['matches']) / len(accuracy.details['matches'])
            print(f"   • Average error: {avg_error:.1f}m")
        
        coverage = results['metrics']['coverage']
        print(f"   • Coverage: {coverage.details['found_count']}/{coverage.details['expected_count']} expected rules found")
        
        precision = results['metrics']['precision']
        if precision.details['invalid_rules']:
            print(f"   • Precision issues: {len(precision.details['invalid_rules'])} rules outside reasonable ranges")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if not results['passed']:
            print("   ❌ Overall evaluation failed. Key improvements needed:")
            
            if not accuracy.passed:
                print("   • Improve extraction accuracy - values too far from expected")
            if not coverage.passed:
                print("   • Increase extraction coverage - missing expected rules")
            if not precision.passed:
                print("   • Add better validation - some values are unrealistic")
            
        else:
            print("   ✅ Extraction system is performing well!")
            print("   • Continue monitoring extraction quality")
            print("   • Consider expanding to additional council areas")
        
        print("=" * 60)
    
    def save_evaluation_report(self, results: Dict):
        """Save evaluation report to file"""
        
        report_path = self.project_root / "public" / "regulatory-data" / "rag-evaluation-report.json"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"📁 Evaluation report saved: {report_path}")

def main():
    """Run RAG effectiveness evaluation"""
    
    evaluator = RAGEffectivenessEvaluator()
    results = evaluator.run_complete_evaluation()
    
    # Return appropriate exit code
    sys.exit(0 if results.get('passed', False) else 1)

if __name__ == "__main__":
    main()