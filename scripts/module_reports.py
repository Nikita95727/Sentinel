#!/usr/bin/env python3
"""
Generate separate reports for each trading module.
Monitors both conservative and launch_sniper modules independently.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class ModuleReporter:
    """Base class for module reporting."""
    
    def __init__(self, module_name: str, storage_path: Path):
        self.module_name = module_name
        self.storage_path = storage_path
        self.trades_dir = storage_path / "trades"
        self.analytics_dir = storage_path / "analytics"
    
    def get_trade_files(self, days: int = 7) -> List[Path]:
        """Get trade files for last N days."""
        files = []
        cutoff = datetime.now() - timedelta(days=days)
        
        if not self.trades_dir.exists():
            return files
        
        for file in self.trades_dir.glob("*.jsonl"):
            try:
                # Extract date from filename (trades_YYYY-MM-DD.jsonl)
                date_str = file.stem.split("_")[-1]
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                if file_date >= cutoff:
                    files.append(file)
            except:
                continue
        
        return sorted(files)
    
    def get_analytics_files(self, days: int = 7) -> List[Path]:
        """Get analytics files for last N days."""
        files = []
        cutoff = datetime.now() - timedelta(days=days)
        
        if not self.analytics_dir.exists():
            return files
        
        for pattern in ["ai_decisions_*.jsonl", "market_conditions_*.jsonl"]:
            for file in self.analytics_dir.glob(pattern):
                try:
                    # Extract date from filename
                    parts = file.stem.split("_")
                    date_str = parts[-1]
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    if file_date >= cutoff:
                        files.append(file)
                except:
                    continue
        
        return sorted(files)
    
    def analyze_trades(self, files: List[Path]) -> Dict[str, Any]:
        """Analyze trade files."""
        stats = {
            "total_trades": 0,
            "executed_trades": 0,
            "abstained_trades": 0,
            "total_pnl": 0.0,
            "win_rate": 0.0,
            "avg_pnl": 0.0,
            "by_date": defaultdict(lambda: {"trades": 0, "pnl": 0.0})
        }
        
        for file in files:
            try:
                with open(file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            trade = json.loads(line)
                            date = trade.get("timestamp", "").split("T")[0] if trade.get("timestamp") else file.stem.split("_")[-1]
                            
                            stats["total_trades"] += 1
                            stats["by_date"][date]["trades"] += 1
                            
                            if trade.get("execution_result") == "EXECUTED":
                                stats["executed_trades"] += 1
                                pnl = trade.get("pnl_percent", 0.0)
                                stats["total_pnl"] += pnl
                                stats["by_date"][date]["pnl"] += pnl
                            elif trade.get("execution_result") in ["ABSTAINED", "HELD"]:
                                stats["abstained_trades"] += 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                continue
        
        if stats["executed_trades"] > 0:
            stats["avg_pnl"] = stats["total_pnl"] / stats["executed_trades"]
            wins = sum(1 for d in stats["by_date"].values() if d["pnl"] > 0)
            stats["win_rate"] = (wins / stats["executed_trades"] * 100) if stats["executed_trades"] > 0 else 0.0
        
        return stats
    
    def analyze_analytics(self, files: List[Path]) -> Dict[str, Any]:
        """Analyze analytics files."""
        stats = {
            "total_decisions": 0,
            "ai_decisions": 0,
            "no_ai_calls": 0,
            "abstain_types": defaultdict(int),
            "avg_confidence": 0.0,
            "by_date": defaultdict(lambda: {"decisions": 0, "ai_calls": 0})
        }
        
        confidence_sum = 0.0
        confidence_count = 0
        
        for file in files:
            try:
                with open(file, 'r') as f:
                    for line in f:
                        if not line.strip():
                            continue
                        try:
                            data = json.loads(line)
                            date = data.get("timestamp", "").split("T")[0] if data.get("timestamp") else file.stem.split("_")[-1]
                            
                            stats["total_decisions"] += 1
                            stats["by_date"][date]["decisions"] += 1
                            
                            if data.get("event_type") == "ai_decision":
                                stats["ai_decisions"] += 1
                                stats["by_date"][date]["ai_calls"] += 1
                                
                                confidence = data.get("confidence", 0.0)
                                if confidence > 0:
                                    confidence_sum += confidence
                                    confidence_count += 1
                                
                                abstain_type = data.get("abstain_type")
                                if abstain_type:
                                    stats["abstain_types"][abstain_type] += 1
                            elif data.get("event_type") == "NO_AI_CALL":
                                stats["no_ai_calls"] += 1
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                continue
        
        if confidence_count > 0:
            stats["avg_confidence"] = confidence_sum / confidence_count
        
        return stats
    
    def generate_report(self, days: int = 7) -> Dict[str, Any]:
        """Generate comprehensive report for module."""
        trade_files = self.get_trade_files(days)
        analytics_files = self.get_analytics_files(days)
        
        trade_stats = self.analyze_trades(trade_files)
        analytics_stats = self.analyze_analytics(analytics_files)
        
        return {
            "module": self.module_name,
            "period_days": days,
            "report_date": datetime.now().isoformat(),
            "trades": {
                "files_analyzed": len(trade_files),
                "stats": trade_stats
            },
            "analytics": {
                "files_analyzed": len(analytics_files),
                "stats": analytics_stats
            }
        }


def generate_conservative_report(days: int = 7) -> Dict[str, Any]:
    """Generate report for conservative module."""
    reporter = ModuleReporter(
        "conservative",
        Path("storage/conservative")
    )
    return reporter.generate_report(days)


def generate_launch_sniper_report(days: int = 7) -> Dict[str, Any]:
    """Generate report for launch sniper module."""
    reporter = ModuleReporter(
        "launch_sniper",
        Path("storage/launch_sniper")
    )
    return reporter.generate_report(days)


def format_report(report: Dict[str, Any]) -> str:
    """Format report as human-readable text."""
    lines = []
    lines.append("=" * 80)
    lines.append(f"MODULE REPORT: {report['module'].upper()}")
    lines.append("=" * 80)
    lines.append(f"Period: Last {report['period_days']} days")
    lines.append(f"Report Date: {report['report_date']}")
    lines.append("")
    
    # Trades section
    lines.append("📊 TRADES")
    lines.append("-" * 80)
    trades = report['trades']
    stats = trades['stats']
    lines.append(f"Files Analyzed: {trades['files_analyzed']}")
    lines.append(f"Total Trades: {stats['total_trades']}")
    lines.append(f"Executed: {stats['executed_trades']}")
    lines.append(f"Abstained: {stats['abstained_trades']}")
    if stats['executed_trades'] > 0:
        lines.append(f"Total PnL: {stats['total_pnl']:.2f}%")
        lines.append(f"Average PnL: {stats['avg_pnl']:.2f}%")
        lines.append(f"Win Rate: {stats['win_rate']:.1f}%")
    lines.append("")
    
    # Analytics section
    lines.append("🤖 ANALYTICS")
    lines.append("-" * 80)
    analytics = report['analytics']
    a_stats = analytics['stats']
    lines.append(f"Files Analyzed: {analytics['files_analyzed']}")
    lines.append(f"Total Decisions: {a_stats['total_decisions']}")
    lines.append(f"AI Decisions: {a_stats['ai_decisions']}")
    lines.append(f"No AI Calls: {a_stats['no_ai_calls']}")
    if a_stats['avg_confidence'] > 0:
        lines.append(f"Average Confidence: {a_stats['avg_confidence']:.1f}%")
    if a_stats['abstain_types']:
        lines.append("Abstain Types:")
        for abstain_type, count in a_stats['abstain_types'].items():
            lines.append(f"  - {abstain_type}: {count}")
    lines.append("")
    
    # Daily breakdown
    if stats['by_date']:
        lines.append("📅 DAILY BREAKDOWN")
        lines.append("-" * 80)
        for date in sorted(stats['by_date'].keys(), reverse=True)[:7]:
            daily = stats['by_date'][date]
            lines.append(f"{date}: {daily['trades']} trades, PnL: {daily['pnl']:.2f}%")
    
    lines.append("=" * 80)
    return "\n".join(lines)


def main():
    """Generate reports for all modules."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate module reports")
    parser.add_argument("--days", type=int, default=7, help="Number of days to analyze")
    parser.add_argument("--module", choices=["conservative", "launch_sniper", "all"], default="all", help="Module to report on")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--output", type=str, help="Output file path")
    
    args = parser.parse_args()
    
    reports = []
    
    if args.module in ["conservative", "all"]:
        try:
            report = generate_conservative_report(args.days)
            reports.append(report)
        except Exception as e:
            print(f"Error generating conservative report: {e}", file=sys.stderr)
    
    if args.module in ["launch_sniper", "all"]:
        try:
            report = generate_launch_sniper_report(args.days)
            reports.append(report)
        except Exception as e:
            print(f"Error generating launch_sniper report: {e}", file=sys.stderr)
    
    if args.json:
        output = json.dumps(reports, indent=2)
    else:
        output = "\n\n".join([format_report(r) for r in reports])
    
    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Report saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

