#!/usr/bin/env python3
"""
PRP-K8: Automatic Completion Tracking System
Monitors zone extraction progress with completion markers
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict

@dataclass
class ZoneCompletionMetrics:
    """Completion metrics for zone assignment"""
    timestamp: str
    total_provisions: int
    provisions_with_zones: int
    zone_coverage_percentage: float
    regulatory_provisions_total: int
    regulatory_provisions_with_zones: int
    regulatory_coverage_percentage: float
    unique_zones_count: int
    top_zones: List[Tuple[str, int]]
    completion_status: str  # 'IN_PROGRESS', 'COMPLETED', 'FAILED'
    phase_completed: str    # Phase 1-4 from PRP-K8

class PRPK8CompletionTracker:
    """Tracks completion of PRP-K8 zone extraction implementation"""
    
    def __init__(self, db_path: str = "nsw_planning.db"):
        self.db_path = db_path
        self.checkpoint_file = "prp_k8_checkpoints.json"
        self.target_regulatory_coverage = 100.0  # 100% for regulatory provisions
        self.target_overall_coverage = 20.0      # 20% overall is realistic
        
        # Critical provision types that MUST have zones
        self.critical_provision_types = [
            'height_limit', 'setback', 'fsr', 'parking', 'landscaping',
            'subdivision', 'provision_height', 'provision_setback',
            'provision_design', 'formal_Planning Controls'
        ]
    
    def get_current_metrics(self) -> ZoneCompletionMetrics:
        """Calculate current zone coverage metrics"""
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total provisions
        cursor.execute("SELECT COUNT(*) FROM regulatory_provisions;")
        total_provisions = cursor.fetchone()[0]
        
        # Provisions with zones
        cursor.execute("""
            SELECT COUNT(*) FROM regulatory_provisions 
            WHERE zone IS NOT NULL AND zone != '';
        """)
        provisions_with_zones = cursor.fetchone()[0]
        
        # Zone coverage percentage
        zone_coverage = (provisions_with_zones / total_provisions * 100) if total_provisions > 0 else 0
        
        # Critical/regulatory provisions
        placeholders = ','.join(['?' for _ in self.critical_provision_types])
        cursor.execute(f"""
            SELECT COUNT(*) FROM regulatory_provisions 
            WHERE provision_type IN ({placeholders});
        """, self.critical_provision_types)
        regulatory_total = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM regulatory_provisions 
            WHERE provision_type IN ({placeholders})
            AND zone IS NOT NULL AND zone != '';
        """, self.critical_provision_types)
        regulatory_with_zones = cursor.fetchone()[0]
        
        regulatory_coverage = (regulatory_with_zones / regulatory_total * 100) if regulatory_total > 0 else 0
        
        # Unique zones
        cursor.execute("""
            SELECT COUNT(DISTINCT zone) FROM regulatory_provisions 
            WHERE zone IS NOT NULL AND zone != '';
        """)
        unique_zones = cursor.fetchone()[0]
        
        # Top zones by provision count
        cursor.execute("""
            SELECT zone, COUNT(*) as count FROM regulatory_provisions 
            WHERE zone IS NOT NULL AND zone != ''
            GROUP BY zone ORDER BY count DESC LIMIT 10;
        """)
        top_zones = cursor.fetchall()
        
        conn.close()
        
        # Determine completion status
        completion_status = self._determine_completion_status(
            zone_coverage, regulatory_coverage
        )
        
        # Determine current phase
        phase_completed = self._determine_current_phase(
            zone_coverage, regulatory_coverage, unique_zones
        )
        
        return ZoneCompletionMetrics(
            timestamp=datetime.now().isoformat(),
            total_provisions=total_provisions,
            provisions_with_zones=provisions_with_zones,
            zone_coverage_percentage=round(zone_coverage, 2),
            regulatory_provisions_total=regulatory_total,
            regulatory_provisions_with_zones=regulatory_with_zones,
            regulatory_coverage_percentage=round(regulatory_coverage, 2),
            unique_zones_count=unique_zones,
            top_zones=top_zones,
            completion_status=completion_status,
            phase_completed=phase_completed
        )
    
    def _determine_completion_status(self, overall_coverage: float, regulatory_coverage: float) -> str:
        """Determine if PRP-K8 is completed based on metrics"""
        
        if regulatory_coverage >= 95.0 and overall_coverage >= 18.0:
            return 'COMPLETED'
        elif regulatory_coverage >= 50.0 or overall_coverage >= 10.0:
            return 'IN_PROGRESS'
        else:
            return 'FAILED'
    
    def _determine_current_phase(self, overall_coverage: float, regulatory_coverage: float, unique_zones: int) -> str:
        """Determine which phase of PRP-K8 is completed"""
        
        if regulatory_coverage >= 95.0:
            return 'Phase 4: Quality Assurance'
        elif regulatory_coverage >= 70.0:
            return 'Phase 3: Planning API Integration'
        elif overall_coverage >= 5.0 and unique_zones >= 15:
            return 'Phase 2: Zone Inference Engine'
        elif unique_zones >= 10:
            return 'Phase 1: Document Structure'
        else:
            return 'Phase 0: Initial Setup'
    
    def save_checkpoint(self, metrics: ZoneCompletionMetrics, notes: str = "") -> None:
        """Save completion checkpoint to file"""
        
        checkpoint_data = {
            'metrics': asdict(metrics),
            'notes': notes,
            'prp_id': 'PRP-K8',
            'prp_title': 'Comprehensive Zone Extraction Engine'
        }
        
        # Load existing checkpoints
        checkpoints = []
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                checkpoints = json.load(f)
        
        # Add new checkpoint
        checkpoints.append(checkpoint_data)
        
        # Save back to file
        with open(self.checkpoint_file, 'w') as f:
            json.dump(checkpoints, f, indent=2)
    
    def generate_progress_report(self, metrics: ZoneCompletionMetrics) -> str:
        """Generate detailed progress report"""
        
        report = f"""
📊 PRP-K8: ZONE EXTRACTION PROGRESS REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Status: {metrics.completion_status} | Phase: {metrics.phase_completed}

🎯 OVERALL METRICS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total provisions:              {metrics.total_provisions:,}
Provisions with zones:         {metrics.provisions_with_zones:,}
Overall zone coverage:         {metrics.zone_coverage_percentage}%
Target coverage:               {self.target_overall_coverage}%

🔧 REGULATORY PROVISIONS (CRITICAL):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Regulatory provisions total:   {metrics.regulatory_provisions_total:,}
Regulatory with zones:         {metrics.regulatory_provisions_with_zones:,}
Regulatory coverage:           {metrics.regulatory_coverage_percentage}%
Target coverage:               {self.target_regulatory_coverage}%

📍 ZONE DISTRIBUTION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Unique zones identified:       {metrics.unique_zones_count}
"""
        
        if metrics.top_zones:
            report += "\nTop zones by provision count:\n"
            for zone, count in metrics.top_zones[:5]:
                report += f"  {zone}: {count:,} provisions\n"
        
        # Progress indicators
        overall_progress = min(100, (metrics.zone_coverage_percentage / self.target_overall_coverage) * 100)
        regulatory_progress = min(100, (metrics.regulatory_coverage_percentage / self.target_regulatory_coverage) * 100)
        
        report += f"\n📈 PROGRESS TO TARGETS:\n"
        report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        report += f"Overall progress:              {overall_progress:.1f}%\n"
        report += f"Regulatory progress:           {regulatory_progress:.1f}%\n"
        
        # Status assessment
        report += f"\n🚦 STATUS ASSESSMENT:\n"
        report += f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        if metrics.completion_status == 'COMPLETED':
            report += "✅ PRP-K8 COMPLETED SUCCESSFULLY\n"
            report += "   All regulatory provisions have zone coverage\n"
            report += "   System ready for production deployment\n"
        elif metrics.completion_status == 'IN_PROGRESS':
            report += "🔄 PRP-K8 IN PROGRESS\n"
            report += f"   Current phase: {metrics.phase_completed}\n"
            
            if metrics.regulatory_coverage_percentage < 50:
                report += "   🎯 Priority: Improve regulatory provision zone coverage\n"
            elif metrics.zone_coverage_percentage < 15:
                report += "   🎯 Priority: Expand overall zone inference coverage\n"
            else:
                report += "   🎯 Priority: Validate accuracy with Planning API\n"
        else:
            report += "❌ PRP-K8 NEEDS ATTENTION\n"
            report += "   Zone extraction not performing adequately\n"
            report += "   Review inference algorithms and document processing\n"
        
        return report
    
    def check_completion_automatically(self) -> Dict:
        """Automatic completion check with detailed results"""
        
        print("🔍 Running PRP-K8 automatic completion check...")
        
        # Get current metrics
        metrics = self.get_current_metrics()
        
        # Generate report
        report = self.generate_progress_report(metrics)
        print(report)
        
        # Save checkpoint
        self.save_checkpoint(metrics, "Automatic completion check")
        
        # Return structured results
        return {
            'metrics': asdict(metrics),
            'report': report,
            'is_completed': metrics.completion_status == 'COMPLETED',
            'current_phase': metrics.phase_completed,
            'next_actions': self._get_next_actions(metrics)
        }
    
    def _get_next_actions(self, metrics: ZoneCompletionMetrics) -> List[str]:
        """Get recommended next actions based on current metrics"""
        
        actions = []
        
        if metrics.regulatory_coverage_percentage < 50:
            actions.append("Implement document structure parsing for regulatory provisions")
            actions.append("Focus on height_limit, setback, and FSR provision zone mapping")
        
        if metrics.zone_coverage_percentage < 10:
            actions.append("Review and improve zone inference algorithms")
            actions.append("Check document extraction completeness")
        
        if metrics.unique_zones_count < 20:
            actions.append("Extract additional LEP and DCP documents")
            actions.append("Verify zone pattern recognition in text parsing")
        
        if metrics.regulatory_coverage_percentage >= 70:
            actions.append("Run zone verification suite against Planning API")
            actions.append("Validate accuracy on sample provisions")
        
        if not actions:
            actions.append("PRP-K8 appears complete - run final validation")
            actions.append("Prepare for production deployment")
        
        return actions

def main():
    """Run completion tracking"""
    
    tracker = PRPK8CompletionTracker()
    results = tracker.check_completion_automatically()
    
    # Save detailed results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = f"prp_k8_completion_check_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Detailed results saved to: {results_file}")
    
    # Return completion status for automation
    if results['is_completed']:
        exit(0)  # Success
    else:
        exit(1)  # Not completed

if __name__ == "__main__":
    main()