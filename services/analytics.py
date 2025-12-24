"""Advanced analytics and performance tracking for calibration."""

import json
import aiofiles
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd


class Analytics:
    """Advanced analytics service for trading performance and AI calibration."""

    def __init__(self, storage_path: str = "storage/analytics.json"):
        """
        Initialize analytics service.
        
        Args:
            storage_path: Path to analytics JSON file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not self.storage_path.exists():
            self._initialize_storage()

    def _initialize_storage(self) -> None:
        """Initialize empty analytics storage."""
        initial_data = {
            'ai_decisions': [],
            'market_conditions': [],
            'performance_metrics': {
                'daily_pnl': [],
                'win_rate_by_confidence': {},
                'win_rate_by_rsi': {},
                'win_rate_by_trend': {},
                'avg_holding_time': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown': 0.0
            },
            'ai_learning_data': {
                'successful_patterns': [],
                'failed_patterns': [],
                'confidence_calibration': []
            },
            'created_at': datetime.utcnow().isoformat(),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        with open(self.storage_path, 'w') as f:
            json.dump(initial_data, f, indent=2)
        
        logger.info(f"Initialized analytics storage at {self.storage_path}")

    async def record_ai_decision(
        self,
        symbol: str,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record AI decision with full context for analysis.
        
        Args:
            symbol: Trading pair symbol
            decision: AI decision data (action, confidence, reasoning)
            market_data: Current market data
            technical_indicators: Technical indicators at decision time
            context: Additional context (memory, etc.)
        """
        try:
            data = await self._load_data()
            
            record = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'decision': decision,
                'market_data': market_data,
                'technical_indicators': technical_indicators,
                'context': context or {},
                'executed': False  # Will be updated when trade is executed
            }
            
            data['ai_decisions'].append(record)
            data['last_updated'] = datetime.utcnow().isoformat()
            
            await self._save_data(data)
            logger.debug(f"Recorded AI decision for {symbol}: {decision.get('action')}")
            
        except Exception as e:
            logger.error(f"Error recording AI decision: {e}")

    async def record_market_condition(
        self,
        symbol: str,
        indicators: Dict[str, float],
        price: float,
        volume: float
    ) -> None:
        """
        Record market condition snapshot for pattern analysis.
        
        Args:
            symbol: Trading pair symbol
            indicators: Technical indicators
            price: Current price
            volume: Current volume
        """
        try:
            data = await self._load_data()
            
            condition = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'price': price,
                'volume': volume,
                'indicators': indicators
            }
            
            data['market_conditions'].append(condition)
            
            # Keep only last 10000 records to avoid file bloat
            if len(data['market_conditions']) > 10000:
                data['market_conditions'] = data['market_conditions'][-10000:]
            
            await self._save_data(data)
            
        except Exception as e:
            logger.error(f"Error recording market condition: {e}")

    async def update_decision_result(
        self,
        decision_id: Optional[str] = None,
        decision_timestamp: Optional[str] = None,  # Backward compatibility
        executed: bool = False,
        trade_result: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update AI decision with execution result.
        
        Args:
            decision_timestamp: Timestamp of the original decision
            executed: Whether the decision was executed
            trade_result: Trade result data (P&L, exit reason, etc.)
        """
        try:
            data = await self._load_data()
            
            # Find the decision
            for decision in data['ai_decisions']:
                if decision['timestamp'] == decision_timestamp:
                    decision['executed'] = executed
                    if trade_result:
                        decision['trade_result'] = trade_result
                    break
            
            await self._save_data(data)
            
        except Exception as e:
            logger.error(f"Error updating decision result: {e}")

    async def calculate_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Returns:
            Dictionary with performance metrics
        """
        try:
            from storage.state_manager import StateManager
            
            # Load trade history
            state_manager = StateManager()
            history = await state_manager.load_history()
            trades = history.get('trades', [])
            
            if not trades:
                return {}
            
            closed_trades = [t for t in trades if t.get('status') == 'closed']
            
            if not closed_trades:
                return {}
            
            # Calculate metrics
            total_pnl = sum(t.get('pnl', 0) for t in closed_trades)
            winning_trades = [t for t in closed_trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in closed_trades if t.get('pnl', 0) <= 0]
            
            win_rate = (len(winning_trades) / len(closed_trades)) * 100 if closed_trades else 0
            
            # Calculate average holding time
            holding_times = []
            for trade in closed_trades:
                entry_time = trade.get('entry_time')
                exit_time = trade.get('exit_time')
                if entry_time and exit_time:
                    entry = datetime.fromisoformat(entry_time.replace('Z', '+00:00'))
                    exit = datetime.fromisoformat(exit_time.replace('Z', '+00:00'))
                    holding_times.append((exit - entry).total_seconds() / 3600)  # hours
            
            avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0
            
            # Calculate Sharpe ratio (simplified)
            returns = [t.get('pnl_pct', 0) for t in closed_trades]
            if len(returns) > 1:
                try:
                    import numpy as np
                    mean_return = np.mean(returns)
                    std_return = np.std(returns)
                    sharpe = (mean_return / std_return) * np.sqrt(252) if std_return > 0 else 0
                except ImportError:
                    # Fallback calculation without numpy
                    mean_return = sum(returns) / len(returns)
                    variance = sum((x - mean_return) ** 2 for x in returns) / len(returns)
                    std_return = variance ** 0.5
                    sharpe = (mean_return / std_return) * (252 ** 0.5) if std_return > 0 else 0
            else:
                sharpe = 0
            
            # Calculate max drawdown
            cumulative_pnl = []
            running_total = 0
            for trade in closed_trades:
                running_total += trade.get('pnl', 0)
                cumulative_pnl.append(running_total)
            
            if cumulative_pnl:
                peak = cumulative_pnl[0]
                max_dd = 0
                for value in cumulative_pnl:
                    if value > peak:
                        peak = value
                    dd = (peak - value) / peak * 100 if peak > 0 else 0
                    if dd > max_dd:
                        max_dd = dd
            else:
                max_dd = 0
            
            metrics = {
                'total_trades': len(closed_trades),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_pnl_per_trade': total_pnl / len(closed_trades) if closed_trades else 0,
                'avg_winning_trade': sum(t.get('pnl', 0) for t in winning_trades) / len(winning_trades) if winning_trades else 0,
                'avg_losing_trade': sum(t.get('pnl', 0) for t in losing_trades) / len(losing_trades) if losing_trades else 0,
                'avg_holding_time_hours': avg_holding_time,
                'sharpe_ratio': sharpe,
                'max_drawdown_pct': max_dd
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}

    async def analyze_ai_performance(self) -> Dict[str, Any]:
        """
        Analyze AI decision quality and calibration needs.
        
        Returns:
            Dictionary with AI performance analysis
        """
        try:
            data = await self._load_data()
            decisions = data.get('ai_decisions', [])
            
            if not decisions:
                return {}
            
            # Analyze by confidence levels
            confidence_buckets = {
                '80-85': [],
                '85-90': [],
                '90-95': [],
                '95-100': []
            }
            
            for decision in decisions:
                if not decision.get('executed'):
                    continue
                
                confidence = decision.get('decision', {}).get('confidence', 0)
                trade_result = decision.get('trade_result', {})
                pnl = trade_result.get('pnl', 0) if trade_result else 0
                
                if 80 <= confidence < 85:
                    confidence_buckets['80-85'].append(pnl)
                elif 85 <= confidence < 90:
                    confidence_buckets['85-90'].append(pnl)
                elif 90 <= confidence < 95:
                    confidence_buckets['90-95'].append(pnl)
                elif confidence >= 95:
                    confidence_buckets['95-100'].append(pnl)
            
            # Calculate win rates by confidence
            win_rates = {}
            for bucket, pnls in confidence_buckets.items():
                if pnls:
                    wins = sum(1 for pnl in pnls if pnl > 0)
                    win_rates[bucket] = (wins / len(pnls)) * 100
                else:
                    win_rates[bucket] = 0
            
            # Analyze patterns
            successful_patterns = []
            failed_patterns = []
            
            for decision in decisions:
                if not decision.get('executed'):
                    continue
                
                trade_result = decision.get('trade_result', {})
                pnl = trade_result.get('pnl', 0) if trade_result else 0
                
                pattern = {
                    'rsi': decision.get('technical_indicators', {}).get('rsi', 0),
                    'ema_trend': 'bullish' if decision.get('technical_indicators', {}).get('ema_20', 0) > 
                                decision.get('technical_indicators', {}).get('ema_50', 0) else 'bearish',
                    'confidence': decision.get('decision', {}).get('confidence', 0)
                }
                
                if pnl > 0:
                    successful_patterns.append(pattern)
                else:
                    failed_patterns.append(pattern)
            
            analysis = {
                'total_decisions': len(decisions),
                'executed_decisions': sum(1 for d in decisions if d.get('executed')),
                'win_rate_by_confidence': win_rates,
                'successful_patterns_count': len(successful_patterns),
                'failed_patterns_count': len(failed_patterns),
                'confidence_calibration': {
                    'avg_confidence_wins': sum(p.get('confidence', 0) for p in successful_patterns) / len(successful_patterns) if successful_patterns else 0,
                    'avg_confidence_losses': sum(p.get('confidence', 0) for p in failed_patterns) / len(failed_patterns) if failed_patterns else 0
                }
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing AI performance: {e}")
            return {}

    async def export_to_csv(self, output_path: str = "storage/analytics_export.csv") -> None:
        """
        Export analytics data to CSV for external analysis.
        
        Args:
            output_path: Path to output CSV file
        """
        try:
            data = await self._load_data()
            decisions = data.get('ai_decisions', [])
            
            if not decisions:
                logger.warning("No decisions to export")
                return
            
            # Prepare DataFrame
            rows = []
            for decision in decisions:
                row = {
                    'timestamp': decision.get('timestamp'),
                    'symbol': decision.get('symbol'),
                    'action': decision.get('decision', {}).get('action'),
                    'confidence': decision.get('decision', {}).get('confidence'),
                    'reasoning': decision.get('decision', {}).get('reasoning'),
                    'rsi': decision.get('technical_indicators', {}).get('rsi'),
                    'ema_20': decision.get('technical_indicators', {}).get('ema_20'),
                    'ema_50': decision.get('technical_indicators', {}).get('ema_50'),
                    'atr': decision.get('technical_indicators', {}).get('atr'),
                    'price': decision.get('market_data', {}).get('price'),
                    'volume': decision.get('market_data', {}).get('volume'),
                    'executed': decision.get('executed', False),
                    'pnl': decision.get('trade_result', {}).get('pnl') if decision.get('trade_result') else None,
                    'pnl_pct': decision.get('trade_result', {}).get('pnl_pct') if decision.get('trade_result') else None
                }
                rows.append(row)
            
            df = pd.DataFrame(rows)
            df.to_csv(output_path, index=False)
            
            logger.success(f"Exported {len(rows)} decisions to {output_path}")
            
        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")

    async def _load_data(self) -> Dict[str, Any]:
        """Load analytics data from file."""
        try:
            async with aiofiles.open(self.storage_path, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Error loading analytics data: {e}")
            return {
                'ai_decisions': [],
                'market_conditions': [],
                'performance_metrics': {},
                'ai_learning_data': {}
            }

    async def _save_data(self, data: Dict[str, Any]) -> None:
        """Save analytics data to file."""
        try:
            data['last_updated'] = datetime.utcnow().isoformat()
            async with aiofiles.open(self.storage_path, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Error saving analytics data: {e}")

    def detect_anomalies(
        self,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Detect anomalies in AI decisions (stupid decisions).
        
        Args:
            decision: AI decision (action, confidence, reasoning)
            market_data: Current market data
            technical_indicators: Technical indicators
            
        Returns:
            Dictionary with anomaly flags and details
        """
        anomalies = {
            'has_anomalies': False,
            'flags': [],
            'severity': 'none'  # 'low', 'medium', 'high'
        }
        
        action = decision.get('action', '').upper()
        confidence = decision.get('confidence', 0)
        reasoning = decision.get('reasoning', '').lower()
        
        # Get indicators
        rsi = technical_indicators.get('rsi', 0)
        ema_20 = technical_indicators.get('ema_20', 0)
        ema_50 = technical_indicators.get('ema_50', 0)
        price = market_data.get('price', 0)
        volume_ratio = technical_indicators.get('volume_ratio', 1.0)
        
        # Flag 1: BUY при bearish тренде
        if action == 'BUY' and ema_20 < ema_50:
            anomalies['has_anomalies'] = True
            anomalies['flags'].append({
                'type': 'bearish_trend_buy',
                'description': f'BUY decision in bearish trend (EMA20={ema_20:.2f} < EMA50={ema_50:.2f})',
                'severity': 'high'
            })
            if anomalies['severity'] != 'high':
                anomalies['severity'] = 'high'
        
        # Flag 2: Высокий confidence при плохих условиях
        if action == 'BUY' and confidence >= 85:
            bad_conditions = []
            
            if rsi > 75:
                bad_conditions.append(f'RSI overbought ({rsi:.1f} > 75)')
            if rsi < 25:
                bad_conditions.append(f'RSI oversold ({rsi:.1f} < 25)')
            if price < ema_20:
                bad_conditions.append(f'Price below EMA20 ({price:.2f} < {ema_20:.2f})')
            if volume_ratio < 0.8:
                bad_conditions.append(f'Low volume (ratio={volume_ratio:.2f} < 0.8)')
            
            if bad_conditions:
                anomalies['has_anomalies'] = True
                anomalies['flags'].append({
                    'type': 'high_confidence_bad_conditions',
                    'description': f'High confidence ({confidence}%) with bad conditions: {", ".join(bad_conditions)}',
                    'severity': 'medium'
                })
                if anomalies['severity'] == 'none':
                    anomalies['severity'] = 'medium'
        
        # Flag 3: Reasoning не соответствует решению
        if action == 'BUY':
            reasoning_negative = any(word in reasoning for word in ['bearish', 'oversold', 'decline', 'drop', 'fall', 'weak'])
            if reasoning_negative and confidence >= 80:
                anomalies['has_anomalies'] = True
                anomalies['flags'].append({
                    'type': 'reasoning_mismatch',
                    'description': f'BUY decision with negative reasoning (confidence: {confidence}%)',
                    'severity': 'medium'
                })
                if anomalies['severity'] == 'none':
                    anomalies['severity'] = 'medium'
        
        # Flag 4: Противоречивые данные
        if action == 'BUY':
            contradictions = []
            if rsi > 70 and 'bullish' in reasoning:
                contradictions.append('RSI overbought but reasoning mentions bullish')
            if ema_20 < ema_50 and 'trend' in reasoning and 'up' in reasoning:
                contradictions.append('Bearish trend but reasoning mentions uptrend')
            
            if contradictions:
                anomalies['has_anomalies'] = True
                anomalies['flags'].append({
                    'type': 'contradictory_data',
                    'description': f'Contradictions: {", ".join(contradictions)}',
                    'severity': 'low'
                })
                if anomalies['severity'] == 'none':
                    anomalies['severity'] = 'low'
        
        return anomalies

    async def record_anomaly(
        self,
        symbol: str,
        decision: Dict[str, Any],
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        anomaly_data: Dict[str, Any]
    ) -> None:
        """
        Record detected anomaly for monitoring.
        
        Args:
            symbol: Trading pair symbol
            decision: AI decision
            market_data: Market data
            technical_indicators: Technical indicators
            anomaly_data: Anomaly detection results
        """
        try:
            data = await self._load_data()
            
            if 'anomalies' not in data:
                data['anomalies'] = []
            
            anomaly_record = {
                'timestamp': datetime.utcnow().isoformat(),
                'symbol': symbol,
                'decision': decision,
                'market_data': market_data,
                'technical_indicators': technical_indicators,
                'anomaly_flags': anomaly_data.get('flags', []),
                'severity': anomaly_data.get('severity', 'none')
            }
            
            data['anomalies'].append(anomaly_record)
            
            # Keep only last 1000 anomalies
            if len(data['anomalies']) > 1000:
                data['anomalies'] = data['anomalies'][-1000:]
            
            await self._save_data(data)
            
            # Log anomaly
            flags_summary = ', '.join([f['type'] for f in anomaly_data.get('flags', [])])
            logger.warning(
                f"🚨 ANOMALY DETECTED for {symbol}: {flags_summary} "
                f"(severity: {anomaly_data.get('severity', 'none')})"
            )
            
        except Exception as e:
            logger.error(f"Error recording anomaly: {e}")

    async def get_anomaly_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about detected anomalies.
        
        Returns:
            Dictionary with anomaly statistics
        """
        try:
            data = await self._load_data()
            anomalies = data.get('anomalies', [])
            
            if not anomalies:
                return {
                    'total_anomalies': 0,
                    'by_severity': {},
                    'by_type': {},
                    'anomaly_rate': 0.0
                }
            
            # Count by severity
            by_severity = {'low': 0, 'medium': 0, 'high': 0}
            for anomaly in anomalies:
                severity = anomaly.get('severity', 'none')
                if severity in by_severity:
                    by_severity[severity] += 1
            
            # Count by type
            by_type = {}
            for anomaly in anomalies:
                for flag in anomaly.get('anomaly_flags', []):
                    flag_type = flag.get('type', 'unknown')
                    by_type[flag_type] = by_type.get(flag_type, 0) + 1
            
            # Calculate anomaly rate (vs total decisions)
            total_decisions = len(data.get('ai_decisions', []))
            anomaly_rate = (len(anomalies) / total_decisions * 100) if total_decisions > 0 else 0.0
            
            return {
                'total_anomalies': len(anomalies),
                'by_severity': by_severity,
                'by_type': by_type,
                'anomaly_rate': round(anomaly_rate, 2),
                'recent_anomalies': anomalies[-10:] if len(anomalies) >= 10 else anomalies
            }
            
        except Exception as e:
            logger.error(f"Error getting anomaly statistics: {e}")
            return {}

    async def get_decision_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about AI decisions.
        
        Returns:
            Dictionary with decision statistics
        """
        try:
            data = await self._load_data()
            decisions = data.get('ai_decisions', [])
            
            if not decisions:
                return {
                    'total_decisions': 0,
                    'by_action': {},
                    'avg_confidence': 0.0,
                    'parsing_errors': 0
                }
            
            # Count by action
            by_action = {'BUY': 0, 'SELL': 0, 'HOLD': 0}
            confidences = []
            
            for decision in decisions:
                action = decision.get('decision', {}).get('action', '').upper()
                if action in by_action:
                    by_action[action] += 1
                
                confidence = decision.get('decision', {}).get('confidence', 0)
                if confidence > 0:
                    confidences.append(confidence)
            
            # Count parsing errors (decisions with validation warnings)
            parsing_errors = 0
            for decision in decisions:
                context = decision.get('context', {})
                validation = context.get('validation', {})
                if not validation.get('is_valid', True):
                    parsing_errors += 1
            
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                'total_decisions': len(decisions),
                'by_action': by_action,
                'avg_confidence': round(avg_confidence, 2),
                'parsing_errors': parsing_errors,
                'parsing_error_rate': round((parsing_errors / len(decisions) * 100) if decisions else 0, 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting decision statistics: {e}")
            return {}

