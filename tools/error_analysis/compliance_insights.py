#!/usr/bin/env python3
"""
tools/compliance_insights.py
Generate insights for potential compliance standards based on error patterns
"""

import os
import sys
import json
import argparse
from datetime import datetime

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.error_analysis.error_analysis import ErrorAnalyzer
from tools.error_analysis.error_query import ErrorQuery

class ComplianceInsights:
    """Generate compliance insights from error analysis."""
    
    def __init__(self):
        self.analyzer = ErrorAnalyzer()
        self.query = ErrorQuery()
    
    async def generate_compliance_opportunities(self, days: int = 7) -> dict:
        """Generate a comprehensive list of compliance opportunities."""
        
        # Get error analysis
        analysis = await self.analyzer.analyze_error_patterns(days)
        
        # Get cross-module patterns
        patterns = self.query.get_error_patterns(days)
        
        # Identify top opportunities
        opportunities = []
        
        # 1. High-frequency single errors
        for error in analysis['summary']['errors'][:10]:
            if error['count'] > 10:  # Significant frequency
                opportunity = {
                    'type': 'high_frequency_error',
                    'priority': 'high' if error['count'] > 100 else 'medium',
                    'error_code': error['code'],
                    'module': error['module_id'],
                    'frequency': error['count'],
                    'potential_standard': self._suggest_standard_for_error(error),
                    'impact': f"Prevents {error['count']} error occurrences"
                }
                opportunities.append(opportunity)
        
        # 2. Cross-module patterns
        for pattern in patterns:
            if pattern['modules_affected'] > 1:  # Multi-module issue
                opportunity = {
                    'type': 'cross_module_pattern',
                    'priority': 'high',
                    'error_code': pattern['code'],
                    'modules_affected': pattern['modules_affected'],
                    'total_frequency': pattern['total_occurrences'],
                    'affected_modules': pattern['affected_modules'],
                    'potential_standard': self._suggest_standard_for_pattern(pattern),
                    'impact': f"Standardizes behavior across {pattern['modules_affected']} modules"
                }
                opportunities.append(opportunity)
        
        # 3. Module-specific hotspots
        module_hotspots = []
        for module_id, module_data in analysis['by_module'].items():
            if module_data['total_count'] > 50:  # High error volume
                hotspot = {
                    'type': 'module_hotspot',
                    'priority': 'medium',
                    'module': module_id,
                    'error_types': len(module_data['errors']),
                    'total_errors': module_data['total_count'],
                    'top_errors': [e['code'] for e in module_data['errors'][:3]],
                    'potential_standard': f"Module Quality Standard for {module_id}",
                    'impact': f"Improves stability for {module_id}"
                }
                module_hotspots.append(hotspot)
                opportunities.append(hotspot)
        
        # Sort by priority and impact
        opportunities.sort(key=lambda x: (
            0 if x['priority'] == 'high' else 1,
            -x.get('frequency', x.get('total_frequency', 0))
        ))
        
        return {
            'analysis_period_days': days,
            'total_opportunities': len(opportunities),
            'high_priority': len([o for o in opportunities if o['priority'] == 'high']),
            'opportunities': opportunities,
            'summary': {
                'total_error_types': analysis['summary']['total_error_types'],
                'by_category': analysis['by_error_type'],
                'module_hotspots': len(module_hotspots)
            }
        }
    
    def _suggest_standard_for_error(self, error: dict) -> str:
        """Suggest a compliance standard name for a specific error."""
        code = error['code'].lower()
        
        if 'unknown_type' in code or 'validation' in code:
            return "Type Validation Standard"
        elif 'service_init' in code or 'init_failed' in code:
            return "Service Initialization Standard"
        elif 'connection' in code or 'timeout' in code:
            return "Connection Resilience Standard"
        elif 'settings' in code or 'config' in code:
            return "Configuration Management Standard"
        elif 'database' in code or 'db' in code:
            return "Database Operations Standard"
        elif 'api' in code or 'request' in code:
            return "API Integration Standard"
        elif 'import' in code or 'module' in code:
            return "Module Import Standard"
        else:
            category = error['code'].split('_')[1] if '_' in error['code'] else 'general'
            return f"{category.title()} Error Prevention Standard"
    
    def _suggest_standard_for_pattern(self, pattern: dict) -> str:
        """Suggest a compliance standard name for a cross-module pattern."""
        code = pattern['code'].lower()
        
        if 'service_init' in code:
            return "Cross-Module Service Initialization Standard"
        elif 'validation' in code:
            return "Cross-Module Validation Standard"
        elif 'connection' in code:
            return "Cross-Module Connection Standard"
        elif 'api' in code:
            return "Cross-Module API Standard"
        else:
            return f"Cross-Module {pattern['code'].split('_')[-1].title()} Standard"
    
    async def generate_weekly_report(self) -> dict:
        """Generate a weekly compliance insights report."""
        insights = await self.generate_compliance_opportunities(7)
        
        # Add trending analysis
        recent_insights = await self.generate_compliance_opportunities(1)
        
        # Compare trends
        trending = {
            'new_error_types': recent_insights['summary']['total_error_types'],
            'weekly_error_types': insights['summary']['total_error_types'],
            'active_modules': len(recent_insights['summary']['by_category']),
            'recommendation': self._generate_recommendation(insights)
        }
        
        return {
            'report_date': datetime.now().isoformat(),
            'period': '7 days',
            'insights': insights,
            'trending': trending,
            'top_recommendations': insights['opportunities'][:5]
        }
    
    def _generate_recommendation(self, insights: dict) -> str:
        """Generate a recommendation based on insights."""
        high_priority = insights['high_priority']
        total_opportunities = insights['total_opportunities']
        
        if high_priority == 0:
            return "System stability is good. Consider implementing medium-priority standards for long-term improvement."
        elif high_priority <= 2:
            return f"Focus on {high_priority} high-priority compliance standard(s) to address major error patterns."
        else:
            return f"System has {high_priority} critical areas needing compliance standards. Prioritize service initialization and validation patterns."

def print_insights(insights: dict):
    """Print formatted compliance insights."""
    print(f"\nCompliance Insights ({insights['analysis_period_days']} days)")
    print("=" * 60)
    print(f"Total Opportunities: {insights['total_opportunities']}")
    print(f"High Priority: {insights['high_priority']}")
    print(f"Error Types: {insights['summary']['total_error_types']}")
    
    print(f"\nTop Compliance Opportunities:")
    print("-" * 60)
    
    for i, opp in enumerate(insights['opportunities'][:10], 1):
        priority_marker = "[HIGH]" if opp['priority'] == 'high' else "[MED]"
        print(f"{i:2d}. {priority_marker} {opp['potential_standard']}")
        
        if opp['type'] == 'high_frequency_error':
            print(f"     Error: {opp['error_code']}")
            print(f"     Module: {opp['module']}")
            print(f"     Frequency: {opp['frequency']} occurrences")
        elif opp['type'] == 'cross_module_pattern':
            print(f"     Pattern: {opp['error_code']}")
            print(f"     Modules: {opp['modules_affected']} ({', '.join(opp['affected_modules'][:3])})")
            print(f"     Frequency: {opp['total_frequency']} occurrences")
        elif opp['type'] == 'module_hotspot':
            print(f"     Module: {opp['module']}")
            print(f"     Error Types: {opp['error_types']}")
            print(f"     Total Errors: {opp['total_errors']}")
        
        print(f"     Impact: {opp['impact']}")
        print()

def print_report(report: dict):
    """Print formatted weekly report."""
    print(f"\nWeekly Compliance Report")
    print("=" * 60)
    print(f"Report Date: {report['report_date'][:10]}")
    print(f"Period: {report['period']}")
    
    trending = report['trending']
    print(f"\nTrending:")
    print(f"  Recent Error Types: {trending['new_error_types']}")
    print(f"  Weekly Error Types: {trending['weekly_error_types']}")
    print(f"  Active Modules: {trending['active_modules']}")
    
    print(f"\nRecommendation:")
    print(f"  {trending['recommendation']}")
    
    print(f"\nTop 5 Recommendations:")
    print("-" * 40)
    
    for i, rec in enumerate(report['top_recommendations'][:5], 1):
        priority_marker = "[HIGH]" if rec['priority'] == 'high' else "[MED]"
        print(f"{i}. {priority_marker} {rec['potential_standard']}")
        print(f"   {rec['impact']}")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Generate compliance insights from error patterns')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--report', action='store_true', help='Generate weekly report')
    parser.add_argument('--save', type=str, help='Save results to JSON file')
    
    args = parser.parse_args()
    
    insights_tool = ComplianceInsights()
    
    try:
        if args.report:
            report = await insights_tool.generate_weekly_report()
            print_report(report)
            
            if args.save:
                with open(args.save, 'w') as f:
                    json.dump(report, f, indent=2)
                print(f"\nReport saved to: {args.save}")
        else:
            insights = await insights_tool.generate_compliance_opportunities(args.days)
            print_insights(insights)
            
            if args.save:
                with open(args.save, 'w') as f:
                    json.dump(insights, f, indent=2)
                print(f"\nInsights saved to: {args.save}")
    
    except Exception as e:
        print(f"Error generating insights: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())