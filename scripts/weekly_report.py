#!/usr/bin/env python3
"""
Weekly analytics script for trading bot performance analysis.

Generates comprehensive weekly reports including:
- Trade frequency and abstain rate
- Confidence vs outcome correlation
- MFE / MAE statistics
- Stop hit rate
- Analysis by market session, day of week, market regime, BTC trend
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from storage.state_manager import StateManager
from services.analytics import Analytics
from loguru import logger


def get_week_range() -> tuple[datetime, datetime]:
    """Get start and end of current week (Monday to Sunday)."""
    today = datetime.utcnow()
    # Get Monday of current week
    days_since_monday = today.weekday()
    week_start = today - timedelta(days=days_since_monday)
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)
    return week_start, week_end


def parse_trade_date(trade: Dict[str, Any]) -> Optional[datetime]:
    """Parse trade date from entry time."""
    entry = trade.get('entry', {})
    entry_time = entry.get('time')
    if not entry_time:
        return None
    try:
        return datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
    except (ValueError, AttributeError):
        return None


def get_market_session(timestamp: datetime) -> str:
    """Determine market session from UTC hour."""
    hour = timestamp.hour
    if 0 <= hour < 8:
        return "Asia"
    elif 8 <= hour < 16:
        return "Europe"
    else:
        return "US"


def get_day_of_week(timestamp: datetime) -> str:
    """Get day of week name."""
    return timestamp.strftime('%A')


def get_market_regime(trade: Dict[str, Any]) -> str:
    """Determine market regime from trade context."""
    entry_data = trade.get('entry', {})
    market_data = entry_data.get('market_data', {})
    btc_trend = market_data.get('btc_trend', '').lower()
    
    if 'bull' in btc_trend:
        return "bullish"
    elif 'bear' in btc_trend:
        return "bearish"
    else:
        return "sideways"


def get_btc_trend(trade: Dict[str, Any]) -> Optional[str]:
    """Get BTC trend from trade context."""
    entry_data = trade.get('entry', {})
    market_data = entry_data.get('market_data', {})
    return market_data.get('btc_trend')


async def generate_weekly_report(output_format: str = "json") -> Dict[str, Any]:
    """
    Generate comprehensive weekly analytics report.
    
    Args:
        output_format: Output format ('json' or 'text')
    
    Returns:
        Dictionary with weekly analytics
    """
    week_start, week_end = get_week_range()
    
    # Load trade history
    state_manager = StateManager()
    history = await state_manager.load_history()
    all_trades = history.get('trades', [])
    
    # Filter trades for this week
    week_trades = []
    for trade in all_trades:
        trade_date = parse_trade_date(trade)
        if trade_date and week_start <= trade_date < week_end:
            week_trades.append(trade)
    
    # Load AI decisions
    analytics = Analytics()
    ai_decisions = await analytics._load_events('ai_decisions', days_back=7)
    
    # Filter decisions for this week
    week_decisions = []
    for decision in ai_decisions:
        try:
            decision_time = datetime.fromisoformat(decision.get('timestamp', '').replace('Z', '+00:00'))
            if week_start <= decision_time < week_end:
                week_decisions.append(decision)
        except (ValueError, AttributeError):
            continue
    
    # Calculate metrics
    closed_trades = [t for t in week_trades if t.get('status') == 'closed']
    open_trades = [t for t in week_trades if t.get('status') == 'open']
    
    # Trade frequency
    total_trades = len(closed_trades) + len(open_trades)
    trades_per_day = total_trades / 7 if total_trades > 0 else 0
    
    # Abstain rate
    abstain_decisions = [d for d in week_decisions if d.get('decision', {}).get('action') == 'ABSTAIN']
    abstain_rate = (len(abstain_decisions) / len(week_decisions) * 100) if week_decisions else 0
    
    # Confidence vs outcome
    confidence_outcomes = []
    for trade in closed_trades:
        entry_data = trade.get('entry', {})
        ai_confidence = entry_data.get('ai_confidence')
        results = trade.get('results', {})
        pnl_percent = results.get('pnl_percent', 0)
        outcome = "WIN" if pnl_percent > 0 else "LOSS"
        
        if ai_confidence is not None:
            confidence_outcomes.append({
                'confidence': ai_confidence,
                'outcome': outcome,
                'pnl_percent': pnl_percent
            })
    
    # MFE / MAE statistics
    mfe_values = []
    mae_values = []
    for trade in closed_trades:
        results = trade.get('results', {})
        mfe = results.get('mfe_percent')
        mae = results.get('mae_percent')
        if mfe is not None:
            mfe_values.append(mfe)
        if mae is not None:
            mae_values.append(mae)
    
    # Stop hit rate
    stop_loss_hits = 0
    take_profit_hits = 0
    for trade in closed_trades:
        exit_data = trade.get('exit', {})
        exit_reason = exit_data.get('reason', '')
        if 'stop-loss' in exit_reason.lower() or 'stop loss' in exit_reason.lower():
            stop_loss_hits += 1
        elif 'take-profit' in exit_reason.lower() or 'take profit' in exit_reason.lower():
            take_profit_hits += 1
    
    stop_hit_rate = (stop_loss_hits / len(closed_trades) * 100) if closed_trades else 0
    tp_hit_rate = (take_profit_hits / len(closed_trades) * 100) if closed_trades else 0
    
    # Analysis by market session
    by_session = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0})
    for trade in closed_trades:
        trade_date = parse_trade_date(trade)
        if trade_date:
            session = get_market_session(trade_date)
            results = trade.get('results', {})
            pnl = results.get('pnl_usdt', 0)
            pnl_pct = results.get('pnl_percent', 0)
            
            by_session[session]['trades'] += 1
            by_session[session]['total_pnl'] += pnl
            if pnl_pct > 0:
                by_session[session]['wins'] += 1
            else:
                by_session[session]['losses'] += 1
    
    # Analysis by day of week
    by_day = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0})
    for trade in closed_trades:
        trade_date = parse_trade_date(trade)
        if trade_date:
            day = get_day_of_week(trade_date)
            results = trade.get('results', {})
            pnl = results.get('pnl_usdt', 0)
            pnl_pct = results.get('pnl_percent', 0)
            
            by_day[day]['trades'] += 1
            by_day[day]['total_pnl'] += pnl
            if pnl_pct > 0:
                by_day[day]['wins'] += 1
            else:
                by_day[day]['losses'] += 1
    
    # Analysis by market regime
    by_regime = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0})
    for trade in closed_trades:
        regime = get_market_regime(trade)
        results = trade.get('results', {})
        pnl = results.get('pnl_usdt', 0)
        pnl_pct = results.get('pnl_percent', 0)
        
        by_regime[regime]['trades'] += 1
        by_regime[regime]['total_pnl'] += pnl
        if pnl_pct > 0:
            by_regime[regime]['wins'] += 1
        else:
            by_regime[regime]['losses'] += 1
    
    # Analysis by BTC trend
    by_btc_trend = defaultdict(lambda: {'trades': 0, 'wins': 0, 'losses': 0, 'total_pnl': 0})
    for trade in closed_trades:
        btc_trend = get_btc_trend(trade) or "unknown"
        results = trade.get('results', {})
        pnl = results.get('pnl_usdt', 0)
        pnl_pct = results.get('pnl_percent', 0)
        
        by_btc_trend[btc_trend]['trades'] += 1
        by_btc_trend[btc_trend]['total_pnl'] += pnl
        if pnl_pct > 0:
            by_btc_trend[btc_trend]['wins'] += 1
        else:
            by_btc_trend[btc_trend]['losses'] += 1
    
    # Build report
    report = {
        'period': {
            'start': week_start.isoformat(),
            'end': week_end.isoformat(),
            'days': 7
        },
        'trade_frequency': {
            'total_trades': total_trades,
            'closed_trades': len(closed_trades),
            'open_trades': len(open_trades),
            'trades_per_day': round(trades_per_day, 2)
        },
        'abstain_rate': {
            'total_decisions': len(week_decisions),
            'abstain_decisions': len(abstain_decisions),
            'abstain_rate_percent': round(abstain_rate, 2)
        },
        'confidence_vs_outcome': {
            'total_trades_with_confidence': len(confidence_outcomes),
            'avg_confidence_wins': round(
                sum(c['confidence'] for c in confidence_outcomes if c['outcome'] == 'WIN') / 
                max(1, sum(1 for c in confidence_outcomes if c['outcome'] == 'WIN')), 2
            ) if any(c['outcome'] == 'WIN' for c in confidence_outcomes) else 0,
            'avg_confidence_losses': round(
                sum(c['confidence'] for c in confidence_outcomes if c['outcome'] == 'LOSS') / 
                max(1, sum(1 for c in confidence_outcomes if c['outcome'] == 'LOSS')), 2
            ) if any(c['outcome'] == 'LOSS' for c in confidence_outcomes) else 0,
            'correlation_data': confidence_outcomes
        },
        'mfe_mae': {
            'total_trades_with_mfe_mae': len(mfe_values),
            'avg_mfe_percent': round(sum(mfe_values) / len(mfe_values), 2) if mfe_values else 0,
            'avg_mae_percent': round(sum(mae_values) / len(mae_values), 2) if mae_values else 0,
            'max_mfe_percent': round(max(mfe_values), 2) if mfe_values else 0,
            'max_mae_percent': round(min(mae_values), 2) if mae_values else 0  # MAE is negative
        },
        'stop_hit_rate': {
            'total_closed_trades': len(closed_trades),
            'stop_loss_hits': stop_loss_hits,
            'take_profit_hits': take_profit_hits,
            'stop_hit_rate_percent': round(stop_hit_rate, 2),
            'tp_hit_rate_percent': round(tp_hit_rate, 2)
        },
        'by_market_session': {
            session: {
                'trades': stats['trades'],
                'win_rate': round(stats['wins'] / stats['trades'] * 100, 2) if stats['trades'] > 0 else 0,
                'total_pnl': round(stats['total_pnl'], 2)
            }
            for session, stats in by_session.items()
        },
        'by_day_of_week': {
            day: {
                'trades': stats['trades'],
                'win_rate': round(stats['wins'] / stats['trades'] * 100, 2) if stats['trades'] > 0 else 0,
                'total_pnl': round(stats['total_pnl'], 2)
            }
            for day, stats in by_day.items()
        },
        'by_market_regime': {
            regime: {
                'trades': stats['trades'],
                'win_rate': round(stats['wins'] / stats['trades'] * 100, 2) if stats['trades'] > 0 else 0,
                'total_pnl': round(stats['total_pnl'], 2)
            }
            for regime, stats in by_regime.items()
        },
        'by_btc_trend': {
            trend: {
                'trades': stats['trades'],
                'win_rate': round(stats['wins'] / stats['trades'] * 100, 2) if stats['trades'] > 0 else 0,
                'total_pnl': round(stats['total_pnl'], 2)
            }
            for trend, stats in by_btc_trend.items()
        }
    }
    
    return report


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate weekly trading analytics report')
    parser.add_argument('--format', choices=['json', 'text'], default='json',
                       help='Output format (default: json)')
    parser.add_argument('--output', type=str, help='Output file path (default: stdout)')
    
    args = parser.parse_args()
    
    try:
        report = await generate_weekly_report(output_format=args.format)
        
        if args.format == 'json':
            output = json.dumps(report, indent=2, ensure_ascii=False)
        else:
            # Text format
            output_lines = [
                f"Weekly Trading Report ({report['period']['start']} to {report['period']['end']})",
                "=" * 80,
                "",
                f"Trade Frequency: {report['trade_frequency']['total_trades']} trades ({report['trade_frequency']['trades_per_day']:.2f} per day)",
                f"Abstain Rate: {report['abstain_rate']['abstain_rate_percent']:.2f}%",
                "",
                "Confidence vs Outcome:",
                f"  Avg Confidence (Wins): {report['confidence_vs_outcome']['avg_confidence_wins']:.2f}%",
                f"  Avg Confidence (Losses): {report['confidence_vs_outcome']['avg_confidence_losses']:.2f}%",
                "",
                "MFE / MAE:",
                f"  Avg MFE: {report['mfe_mae']['avg_mfe_percent']:.2f}%",
                f"  Avg MAE: {report['mfe_mae']['avg_mae_percent']:.2f}%",
                "",
                "Stop Hit Rate:",
                f"  Stop-Loss Hits: {report['stop_hit_rate']['stop_hit_rate_percent']:.2f}%",
                f"  Take-Profit Hits: {report['stop_hit_rate']['tp_hit_rate_percent']:.2f}%",
                "",
            ]
            output = "\n".join(output_lines)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            logger.info(f"Report written to {args.output}")
        else:
            print(output)
            
    except Exception as e:
        logger.error(f"Error generating weekly report: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

