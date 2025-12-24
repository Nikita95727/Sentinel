"""Report generator for trading performance and calibration insights."""

from typing import Dict, Any
from datetime import datetime
from loguru import logger
from pathlib import Path

from services.analytics import Analytics
from storage.state_manager import StateManager


class ReportGenerator:
    """Generate comprehensive reports for calibration and analysis."""

    def __init__(self, analytics: Analytics, state_manager: StateManager):
        """
        Initialize report generator.
        
        Args:
            analytics: Analytics service instance
            state_manager: State manager instance
        """
        self.analytics = analytics
        self.state_manager = state_manager

    async def generate_daily_report(self) -> str:
        """
        Generate daily performance report.
        
        Returns:
            Formatted report string
        """
        try:
            # Get performance metrics
            metrics = await self.analytics.calculate_performance_metrics()
            ai_analysis = await self.analytics.analyze_ai_performance()
            history = await self.state_manager.load_history()
            stats = history.get('statistics', {})
            
            report_lines = [
                "=" * 80,
                f"DAILY TRADING REPORT - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                "=" * 80,
                "",
                "📊 PERFORMANCE METRICS",
                "-" * 80,
                f"Total Trades: {stats.get('total_trades', 0)}",
                f"Winning Trades: {stats.get('winning_trades', 0)}",
                f"Losing Trades: {stats.get('losing_trades', 0)}",
                f"Win Rate: {stats.get('win_rate', 0):.2f}%",
                f"Total P&L: ${stats.get('total_pnl', 0):.2f}",
                "",
                "📈 ADVANCED METRICS",
                "-" * 80,
                f"Average P&L per Trade: ${metrics.get('avg_pnl_per_trade', 0):.2f}",
                f"Average Winning Trade: ${metrics.get('avg_winning_trade', 0):.2f}",
                f"Average Losing Trade: ${metrics.get('avg_losing_trade', 0):.2f}",
                f"Average Holding Time: {metrics.get('avg_holding_time_hours', 0):.2f} hours",
                f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}",
                f"Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%",
                "",
                "🤖 AI PERFORMANCE ANALYSIS",
                "-" * 80,
                f"Total AI Decisions: {ai_analysis.get('total_decisions', 0)}",
                f"Executed Decisions: {ai_analysis.get('executed_decisions', 0)}",
                f"Successful Patterns: {ai_analysis.get('successful_patterns_count', 0)}",
                f"Failed Patterns: {ai_analysis.get('failed_patterns_count', 0)}",
                "",
                "🎯 CONFIDENCE CALIBRATION",
                "-" * 80,
            ]
            
            # Add confidence bucket analysis
            win_rates = ai_analysis.get('win_rate_by_confidence', {})
            for bucket, rate in win_rates.items():
                report_lines.append(f"Confidence {bucket}%: Win Rate {rate:.2f}%")
            
            calibration = ai_analysis.get('confidence_calibration', {})
            if calibration:
                report_lines.extend([
                    "",
                    f"Avg Confidence (Wins): {calibration.get('avg_confidence_wins', 0):.2f}%",
                    f"Avg Confidence (Losses): {calibration.get('avg_confidence_losses', 0):.2f}%"
                ])
            
            report_lines.extend([
                "",
                "=" * 80,
                "💡 CALIBRATION INSIGHTS",
                "-" * 80,
            ])
            
            # Generate insights
            insights = self._generate_insights(metrics, ai_analysis, stats)
            report_lines.extend(insights)
            
            report_lines.append("")
            report_lines.append("=" * 80)
            
            report = "\n".join(report_lines)
            
            # Save to file
            report_path = Path("storage") / f"daily_report_{datetime.utcnow().strftime('%Y%m%d')}.txt"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            with open(report_path, 'w') as f:
                f.write(report)
            
            logger.info(f"Daily report generated: {report_path}")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
            return f"Error generating report: {e}"

    def _generate_insights(self, metrics: Dict, ai_analysis: Dict, stats: Dict) -> list:
        """Generate calibration insights."""
        insights = []
        
        win_rate = stats.get('win_rate', 0)
        total_trades = stats.get('total_trades', 0)
        
        if total_trades < 10:
            insights.append("⚠️  Insufficient data for reliable insights. Need at least 10 closed trades.")
            return insights
        
        # Win rate insights
        if win_rate < 40:
            insights.append("🔴 Low win rate detected. Consider:")
            insights.append("   - Increasing confidence threshold above 85%")
            insights.append("   - Being more selective with entry conditions")
            insights.append("   - Reviewing failed patterns in analytics")
        elif win_rate < 50:
            insights.append("🟡 Moderate win rate. Optimization opportunities:")
            insights.append("   - Analyze confidence buckets to find optimal threshold")
            insights.append("   - Review successful vs failed patterns")
        else:
            insights.append("🟢 Good win rate! Consider:")
            insights.append("   - Maintaining current strategy")
            insights.append("   - Potentially increasing position size if Sharpe > 1.0")
        
        # Confidence calibration
        calibration = ai_analysis.get('confidence_calibration', {})
        avg_conf_wins = calibration.get('avg_confidence_wins', 0)
        avg_conf_losses = calibration.get('avg_confidence_losses', 0)
        
        if avg_conf_wins > 0 and avg_conf_losses > 0:
            if avg_conf_losses > avg_conf_wins:
                insights.append("")
                insights.append("⚠️  Losses have higher confidence than wins!")
                insights.append("   - AI may be overconfident in losing scenarios")
                insights.append("   - Review reasoning in failed high-confidence decisions")
        
        # Sharpe ratio insights
        sharpe = metrics.get('sharpe_ratio', 0)
        if sharpe < 0:
            insights.append("")
            insights.append("🔴 Negative Sharpe ratio - strategy is underperforming")
        elif sharpe < 1:
            insights.append("")
            insights.append("🟡 Sharpe ratio < 1.0 - moderate risk-adjusted returns")
        else:
            insights.append("")
            insights.append("🟢 Sharpe ratio > 1.0 - good risk-adjusted returns!")
        
        # Drawdown insights
        max_dd = metrics.get('max_drawdown_pct', 0)
        if max_dd > 20:
            insights.append("")
            insights.append("🔴 High drawdown detected (>20%)")
            insights.append("   - Consider tighter stop-losses")
            insights.append("   - Review risk management parameters")
        
        return insights

