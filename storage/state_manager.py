"""State manager for persisting trading history in JSONL format optimized for Grok learning."""

import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class StateManager:
    """Manages trading history in JSONL format for optimal Grok learning."""

    def __init__(self, storage_path: str = "storage/trades.jsonl"):
        """
        Initialize state manager.
        
        Args:
            storage_path: Path to history JSONL file
        """
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Statistics cache (calculated on demand)
        self._stats_cache: Optional[Dict[str, Any]] = None

    async def add_trade(
        self,
        symbol: str,
        entry_price: float,
        exit_price: Optional[float],
        position_size: float,
        side: str,
        entry_reason: str,
        exit_reason: Optional[str] = None,
        pnl: Optional[float] = None,
        status: str = "open",
        # Additional context for Grok learning
        entry_indicators: Optional[Dict[str, float]] = None,
        exit_indicators: Optional[Dict[str, float]] = None,
        entry_market_data: Optional[Dict[str, Any]] = None,
        exit_market_data: Optional[Dict[str, Any]] = None,
        ai_confidence: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None
    ) -> None:
        """
        Add a new trade to history in JSONL format.
        
        Format optimized for Grok to read and learn from:
        - Complete market context at entry/exit
        - AI reasoning and confidence
        - Clear outcome and lessons
        
        Args:
            symbol: Trading pair symbol
            entry_price: Entry price
            exit_price: Exit price (None if still open)
            position_size: Position size
            side: 'buy' or 'sell'
            entry_reason: AI reasoning for entering
            exit_reason: Reason for exiting (if closed)
            pnl: Profit/Loss in USDT (if closed)
            status: Trade status ('open' or 'closed')
            entry_indicators: Technical indicators at entry
            exit_indicators: Technical indicators at exit
            entry_market_data: Market data at entry
            exit_market_data: Market data at exit
            ai_confidence: AI confidence level at entry
            stop_loss: Stop-loss price
            take_profit: Take-profit price
        """
        try:
            # Calculate P&L percentage if exit price available
            pnl_pct = None
            if exit_price and entry_price:
                pnl_pct = ((exit_price - entry_price) / entry_price) * 100
            
            # Determine outcome
            outcome = None
            if status == 'closed' and pnl is not None:
                outcome = "WIN" if pnl > 0 else "LOSS"
            
            # Create comprehensive trade record optimized for Grok
            trade_record = {
                # Core trade information
                "trade_id": await self._get_next_trade_id(),
                "symbol": symbol,
                "side": side,
                "status": status,
                "outcome": outcome,
                
                # Entry information
                "entry": {
                    "price": entry_price,
                    "time": datetime.utcnow().isoformat(),
                    "position_size": position_size,
                    "reason": entry_reason,
                    "ai_confidence": ai_confidence,
                    "market_data": entry_market_data or {},
                    "technical_indicators": entry_indicators or {},
                    # Additional context for learning
                    "market_session": entry_market_data.get('market_session') if entry_market_data else None,
                    "day_of_week": entry_market_data.get('day_of_week') if entry_market_data else None,
                    "btc_trend": entry_market_data.get('btc_trend') if entry_market_data else None
                },
                
                # Exit information (if closed)
                "exit": {
                    "price": exit_price,
                    "time": datetime.utcnow().isoformat() if status == 'closed' else None,
                    "reason": exit_reason,
                    "market_data": exit_market_data or {},
                    "technical_indicators": exit_indicators or {}
                } if status == 'closed' else None,
                
                # Risk management
                "risk_management": {
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "risk_pct": abs((entry_price - stop_loss) / entry_price * 100) if stop_loss else None,
                    "reward_pct": abs((take_profit - entry_price) / entry_price * 100) if take_profit else None
                } if stop_loss or take_profit else None,
                
                # Results (if closed)
                "results": {
                    "pnl_usdt": pnl,
                    "pnl_percent": pnl_pct,
                    "holding_time_hours": None  # Will be calculated if both times available
                } if status == 'closed' else None,
                
                # Learning insights (for Grok)
                "lessons": self._generate_lessons(
                    outcome, entry_indicators, exit_indicators, 
                    entry_reason, exit_reason, pnl_pct
                ) if status == 'closed' else None,
                
                # Metadata
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Append to JSONL file
            async with aiofiles.open(self.storage_path, 'a') as f:
                await f.write(json.dumps(trade_record, ensure_ascii=False) + '\n')
            
            # Invalidate stats cache
            self._stats_cache = None
            
            logger.info(f"Trade recorded: {symbol} {side} @ ${entry_price:.2f} (Status: {status})")
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}", exc_info=True)

    def _generate_lessons(
        self,
        outcome: Optional[str],
        entry_indicators: Optional[Dict[str, float]],
        exit_indicators: Optional[Dict[str, float]],
        entry_reason: str,
        exit_reason: Optional[str],
        pnl_pct: Optional[float]
    ) -> Dict[str, Any]:
        """
        Generate learning insights from trade outcome.
        
        Args:
            outcome: WIN or LOSS
            entry_indicators: Technical indicators at entry
            exit_indicators: Technical indicators at exit
            entry_reason: Entry reasoning
            exit_reason: Exit reasoning
            pnl_pct: P&L percentage
            
        Returns:
            Dictionary with lessons for AI learning
        """
        lessons = {
            "outcome": outcome,
            "key_factors": [],
            "what_worked": [],
            "what_failed": [],
            "recommendations": []
        }
        
        if not entry_indicators:
            return lessons
        
        rsi_entry = entry_indicators.get('rsi', 50)
        ema_20_entry = entry_indicators.get('ema_20', 0)
        ema_50_entry = entry_indicators.get('ema_50', 0)
        
        # Analyze based on outcome
        if outcome == "WIN":
            lessons["what_worked"].append(f"RSI at entry: {rsi_entry:.1f}")
            if ema_20_entry > ema_50_entry:
                lessons["what_worked"].append("Bullish EMA trend (EMA20 > EMA50)")
            lessons["key_factors"].append(f"Entry reasoning was correct: {entry_reason[:100]}")
            
        elif outcome == "LOSS":
            lessons["what_failed"].append(f"RSI at entry: {rsi_entry:.1f}")
            if rsi_entry > 70:
                lessons["what_failed"].append("Entered when RSI was overbought")
            elif rsi_entry < 30:
                lessons["what_failed"].append("Entered when RSI was oversold (may have continued down)")
            
            if ema_20_entry < ema_50_entry:
                lessons["what_failed"].append("Entered during bearish trend (EMA20 < EMA50)")
            
            if exit_reason:
                lessons["key_factors"].append(f"Exit reason: {exit_reason}")
            
            # Generate recommendations
            if rsi_entry > 70:
                lessons["recommendations"].append("Avoid entries when RSI > 70 (overbought)")
            if ema_20_entry < ema_50_entry:
                lessons["recommendations"].append("Wait for bullish EMA crossover before entering")
        
        return lessons

    async def _get_next_trade_id(self) -> int:
        """Get next trade ID by counting existing trades."""
        try:
            count = 0
            async with aiofiles.open(self.storage_path, 'r') as f:
                async for line in f:
                    if line.strip():
                        count += 1
            return count + 1
        except FileNotFoundError:
            return 1
        except Exception:
            return 1

    async def get_recent_trades(self, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get recent closed trades for AI memory.
        Optimized format for Grok to read and learn from.
        
        Args:
            limit: Number of recent trades to retrieve
            
        Returns:
            List of recent trades in Grok-friendly format
        """
        try:
            trades = []
            
            # Read file backwards (last lines first)
            if not self.storage_path.exists():
                return []
            
            # Read all lines and filter closed trades
            async with aiofiles.open(self.storage_path, 'r') as f:
                async for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            if trade.get('status') == 'closed':
                                trades.append(trade)
                        except json.JSONDecodeError:
                            continue
            
            # Sort by exit time (most recent first)
            trades.sort(
                key=lambda x: x.get('exit', {}).get('time', '') or '',
                reverse=True
            )
            
            recent = trades[:limit]
            
            logger.debug(f"Retrieved {len(recent)} recent trades for Grok memory")
            return recent
            
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []

    async def get_trades_for_grok_context(self, limit: int = 5) -> str:
        """
        Get trades formatted specifically for Grok prompt context.
        Returns a human-readable string that Grok can easily understand.
        
        Args:
            limit: Number of recent trades to include
            
        Returns:
            Formatted string for Grok prompt
        """
        trades = await self.get_recent_trades(limit=limit)
        
        if not trades:
            return "No previous trades to learn from."
        
        context_parts = [
            f"RECENT TRADE HISTORY (Last {len(trades)} closed trades):",
            ""
        ]
        
        for i, trade in enumerate(trades, 1):
            entry = trade.get('entry', {})
            exit_data = trade.get('exit', {})
            results = trade.get('results', {})
            lessons = trade.get('lessons', {})
            
            outcome = trade.get('outcome', 'UNKNOWN')
            symbol = trade.get('symbol', 'N/A')
            
            context_parts.append(f"Trade {i}: {symbol} - {outcome}")
            context_parts.append(f"  Entry: ${entry.get('price', 0):.2f} | Confidence: {entry.get('ai_confidence', 0):.0f}%")
            context_parts.append(f"  Entry Reason: {entry.get('reason', 'N/A')}")
            
            indicators = entry.get('technical_indicators', {})
            if indicators:
                context_parts.append(
                    f"  Entry Conditions: RSI={indicators.get('rsi', 0):.1f}, "
                    f"EMA20={indicators.get('ema_20', 0):.2f}, EMA50={indicators.get('ema_50', 0):.2f}"
                )
            
            if exit_data:
                context_parts.append(f"  Exit: ${exit_data.get('price', 0):.2f} | Reason: {exit_data.get('reason', 'N/A')}")
            
            if results:
                pnl_pct = results.get('pnl_percent', 0)
                context_parts.append(f"  Result: {pnl_pct:+.2f}% P&L")
            
            if lessons:
                what_worked = lessons.get('what_worked', [])
                what_failed = lessons.get('what_failed', [])
                
                if what_worked:
                    context_parts.append(f"  ✅ What worked: {', '.join(what_worked)}")
                if what_failed:
                    context_parts.append(f"  ❌ What failed: {', '.join(what_failed)}")
                
                recommendations = lessons.get('recommendations', [])
                if recommendations:
                    context_parts.append(f"  💡 Lessons: {', '.join(recommendations)}")
            
            context_parts.append("")
        
        return "\n".join(context_parts)

    async def update_trade_exit(
        self,
        trade_id: int,
        exit_price: float,
        exit_reason: str,
        pnl: float,
        exit_indicators: Optional[Dict[str, float]] = None,
        exit_market_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update a trade with exit information.
        Since JSONL is append-only, we need to rewrite the file.
        
        Args:
            trade_id: ID of the trade to update
            exit_price: Exit price
            exit_reason: Reason for exit
            pnl: Profit/Loss in USDT
            exit_indicators: Technical indicators at exit
            exit_market_data: Market data at exit
        """
        try:
            # Read all trades
            trades = []
            async with aiofiles.open(self.storage_path, 'r') as f:
                async for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            trades.append(trade)
                        except json.JSONDecodeError:
                            continue
            
            # Find and update the trade
            updated = False
            for trade in trades:
                if trade.get('trade_id') == trade_id:
                    entry_price = trade.get('entry', {}).get('price', 0)
                    pnl_pct = ((exit_price - entry_price) / entry_price * 100) if entry_price else 0
                    outcome = "WIN" if pnl > 0 else "LOSS"
                    
                    # Update exit information
                    trade['exit'] = {
                        "price": exit_price,
                        "time": datetime.utcnow().isoformat(),
                        "reason": exit_reason,
                        "market_data": exit_market_data or {},
                        "technical_indicators": exit_indicators or {}
                    }
                    
                    # Update results
                    trade['results'] = {
                        "pnl_usdt": pnl,
                        "pnl_percent": pnl_pct,
                        "holding_time_hours": None  # Could calculate if needed
                    }
                    
                    # Update status and outcome
                    trade['status'] = 'closed'
                    trade['outcome'] = outcome
                    
                    # Regenerate lessons
                    entry_indicators = trade.get('entry', {}).get('technical_indicators', {})
                    entry_reason = trade.get('entry', {}).get('reason', '')
                    trade['lessons'] = self._generate_lessons(
                        outcome, entry_indicators, exit_indicators,
                        entry_reason, exit_reason, pnl_pct
                    )
                    
                    updated = True
                    break
            
            if not updated:
                logger.warning(f"Trade {trade_id} not found for update")
                return
            
            # Rewrite file
            async with aiofiles.open(self.storage_path, 'w') as f:
                for trade in trades:
                    await f.write(json.dumps(trade, ensure_ascii=False) + '\n')
            
            # Invalidate stats cache
            self._stats_cache = None
            
            logger.info(f"Trade {trade_id} updated with exit info (P&L: ${pnl:.2f})")
            
        except Exception as e:
            logger.error(f"Error updating trade exit: {e}", exc_info=True)

    async def load_history(self) -> Dict[str, Any]:
        """
        Load all trades for backward compatibility.
        
        Returns:
            Dictionary with trades and statistics
        """
        try:
            trades = []
            async with aiofiles.open(self.storage_path, 'r') as f:
                async for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            trades.append(trade)
                        except json.JSONDecodeError:
                            continue
            
            stats = await self.get_statistics()
            
            return {
                'trades': trades,
                'statistics': stats
            }
            
        except FileNotFoundError:
            return {
                'trades': [],
                'statistics': {
                    'total_trades': 0,
                    'winning_trades': 0,
                    'losing_trades': 0,
                    'total_pnl': 0.0,
                    'win_rate': 0.0
                }
            }
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            return {
                'trades': [],
                'statistics': {}
            }

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Calculate trading statistics from JSONL file.
        
        Returns:
            Dictionary with performance statistics
        """
        # Use cache if available
        if self._stats_cache:
            return self._stats_cache
        
        try:
            closed_trades = []
            async with aiofiles.open(self.storage_path, 'r') as f:
                async for line in f:
                    if line.strip():
                        try:
                            trade = json.loads(line.strip())
                            if trade.get('status') == 'closed':
                                closed_trades.append(trade)
                        except json.JSONDecodeError:
                            continue
            
            total_trades = len(closed_trades)
            winning_trades = sum(1 for t in closed_trades if t.get('outcome') == 'WIN')
            losing_trades = total_trades - winning_trades
            total_pnl = sum(t.get('results', {}).get('pnl_usdt', 0) for t in closed_trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
            
            stats = {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'losing_trades': losing_trades,
                'total_pnl': total_pnl,
                'win_rate': win_rate
            }
            
            # Cache stats
            self._stats_cache = stats
            
            return stats
            
        except FileNotFoundError:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'total_pnl': 0.0,
                'win_rate': 0.0
            }
        except Exception as e:
            logger.error(f"Error calculating statistics: {e}")
            return {}
