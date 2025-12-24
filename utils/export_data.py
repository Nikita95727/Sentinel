"""Utility script to export trading data for analysis."""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.analytics import Analytics
from services.report_generator import ReportGenerator
from storage.state_manager import StateManager
from loguru import logger


async def export_all_data():
    """Export all trading data for analysis."""
    logger.info("Starting data export...")
    
    # Initialize services
    analytics = Analytics()
    state_manager = StateManager()
    report_generator = ReportGenerator(analytics=analytics, state_manager=state_manager)
    
    # Generate daily report
    logger.info("Generating daily report...")
    report = await report_generator.generate_daily_report()
    print("\n" + report)
    
    # Export analytics to CSV
    logger.info("Exporting analytics to CSV...")
    await analytics.export_to_csv("storage/analytics_export.csv")
    
    # Calculate and display metrics
    logger.info("Calculating performance metrics...")
    metrics = await analytics.calculate_performance_metrics()
    ai_analysis = await analytics.analyze_ai_performance()
    
    print("\n" + "="*80)
    print("PERFORMANCE METRICS")
    print("="*80)
    for key, value in metrics.items():
        print(f"{key}: {value}")
    
    print("\n" + "="*80)
    print("AI PERFORMANCE ANALYSIS")
    print("="*80)
    for key, value in ai_analysis.items():
        print(f"{key}: {value}")
    
    logger.success("Data export complete!")
    logger.info("Files saved:")
    logger.info("  - storage/daily_report_YYYYMMDD.txt")
    logger.info("  - storage/analytics_export.csv")


if __name__ == "__main__":
    asyncio.run(export_all_data())

