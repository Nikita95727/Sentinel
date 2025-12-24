"""State manager for persisting trading history in daily JSONL files optimized for Grok learning."""

import json
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from loguru import logger
import asyncio


class StateManager:
    """Manages trading history in daily JSONL files for optimal Grok learning."""

    def __init__(self, storage_path: str = "storage/trades"):
        """
        Initialize state manager with daily file rotation.
        
        Args:
            storage_path: Path to storage directory (will create daily files inside)
        """
        self.storage_dir = Path(storage_path)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        
        # Current date for file naming
        self._current_date: Optional[date] = None
        self._current_file_path: Optional[Path] = None
        
        # Statistics cache (calculated on demand)
        self._stats_cache: Optional[Dict[str, Any]] = None
        
        # Ensure daily rotation on init
        self._ensure_daily_rotation()
    
    def _get_current_file_path(self) -> Path:
        """
        Get path to current day's trade file.
        Automatically handles daily rotation.
        
        Returns:
            Path to current day's JSONL file
        """
        today = date.today()
        
        # Check if we need to rotate (new day)
        if self._current_date != today:
            self._ensure_daily_rotation()
            self._current_date = today
        
        # Return current file path
        if self._current_file_path is None:
            filename = f"trades_{today.isoformat()}.jsonl"
            self._current_file_path = self.storage_dir / filename
        
        return self._current_file_path
    
    def _ensure_daily_rotation(self) -> None:
        """
        Ensure daily file rotation is handled.
        Checks if we need to rotate to a new day's file.
        """
        today = date.today()
        
        # If current file is from a different day, we need to rotate
        if self._current_file_path and self._current_date and self._current_date != today:
            # Old file is already correctly named (trades_YYYY-MM-DD.jsonl)
            # Just need to create new file for today
            logger.info(f"Daily rotation: New day detected ({today.isoformat()})")
        
        filename = f"trades_{today.isoformat()}.jsonl"
        self._current_file_path = self.storage_dir / filename
        self._current_date = today
        
        # Ensure file exists (create empty if needed)
        if not self._current_file_path.exists():
            self._current_file_path.touch()
            logger.debug(f"Created new daily trade file: {self._current_file_path}")
    
    async def perform_daily_rotation(self) -> None:
        """
        Perform daily file rotation (called by scheduler at midnight).
        Ensures we're using the correct file for the new day.
        """
        try:
            old_date = self._current_date
            self._ensure_daily_rotation()
            
            if old_date and old_date != self._current_date:
                logger.info(
                    f"Daily rotation completed: "
                    f"{old_date.isoformat()} → {self._current_date.isoformat()}"
                )
            else:
                logger.debug("Daily rotation check: No rotation needed")
                
        except Exception as e:
            logger.error(f"Error during daily rotation: {e}", exc_info=True)
    
    def _get_all_trade_files(self, days_back: Optional[int] = None) -> List[Path]:
        """
        Get all trade files, optionally limited to last N days.
        
        Args:
            days_back: Number of days to look back (None = all files)
            
        Returns:
            List of trade file paths, sorted by date (newest first)
        """
        files = []
        
        # Get all trade files
        for file_path in self.storage_dir.glob("trades_*.jsonl"):
            try:
                # Extract date from filename (trades_YYYY-MM-DD.jsonl)
                date_str = file_path.stem.replace("trades_", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                
                # Filter by days_back if specified
                if days_back is None:
                    files.append((file_date, file_path))
                else:
                    days_ago = (date.today() - file_date).days
                    if 0 <= days_ago <= days_back:
                        files.append((file_date, file_path))
            except (ValueError, AttributeError):
                # Skip files with invalid names
                continue
        
        # Sort by date (newest first)
        files.sort(key=lambda x: x[0], reverse=True)
        
        return [file_path for _, file_path in files]

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
        take_profit: Optional[float] = None,
        # Metadata for decision analysis
        ai_metadata: Optional[Dict[str, Any]] = None
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
                
                # Decision ID for linking AI decision to trade
                "decision_id": decision_id,
                
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
                    "btc_trend": entry_market_data.get('btc_trend') if entry_market_data else None,
                    "btc_rsi": entry_market_data.get('btc_rsi') if entry_market_data else None,
                    # Indicator changes (delta)
                    "indicator_changes": {
                        "rsi_change": entry_indicators.get('rsi_change') if entry_indicators else None,
                        "ema_20_change": entry_indicators.get('ema_20_change') if entry_indicators else None,
                        "ema_50_change": entry_indicators.get('ema_50_change') if entry_indicators else None,
                    } if entry_indicators else None,
                    # Volume trend
                    "volume_trend": entry_indicators.get('volume_trend') if entry_indicators else None,
                    "volume_ratio": entry_indicators.get('volume_ratio') if entry_indicators else None,
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
                
                # AI Decision Metadata (for analysis and learning)
                "ai_metadata": {
                    "full_prompt": ai_metadata.get('full_prompt') if ai_metadata else None,
                    "raw_response": ai_metadata.get('raw_response') if ai_metadata else None,
                    "api_latency_ms": ai_metadata.get('api_latency_ms') if ai_metadata else None,
                    "tokens_used": ai_metadata.get('tokens_used') if ai_metadata else None,
                    "prompt_tokens": ai_metadata.get('prompt_tokens') if ai_metadata else None,
                    "completion_tokens": ai_metadata.get('completion_tokens') if ai_metadata else None,
                    "validation_passed": ai_metadata.get('validation_passed') if ai_metadata else None,
                    "validation_warnings": ai_metadata.get('validation_warnings') if ai_metadata else None,
                    "is_fallback": ai_metadata.get('is_fallback') if ai_metadata else None,
                } if ai_metadata else None,
                
                # Market context summary
                "market_context": {
                    "volatility_atr_pct": entry_indicators.get('atr_pct') if entry_indicators else None,
                    "btc_correlation": entry_market_data.get('btc_trend') if entry_market_data else None,
                    "market_session": entry_market_data.get('market_session') if entry_market_data else None,
                    "day_of_week": entry_market_data.get('day_of_week') if entry_market_data else None,
                } if entry_indicators or entry_market_data else None,
                
                # Metadata
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Append to current day's JSONL file
            current_file = self._get_current_file_path()
            async with aiofiles.open(current_file, 'a') as f:
                await f.write(json.dumps(trade_record, ensure_ascii=False) + '\n')
            
            # Validate data quality (Task 2)
            validation_result = self._validate_trade_record(trade_record)
            if not validation_result['is_valid']:
                logger.warning(
                    f"Trade data quality issues for {symbol}: {validation_result['warnings']}"
                )
            
            # Invalidate stats cache
            self._stats_cache = None
            
            logger.info(f"Trade recorded: {symbol} {side} @ ${entry_price:.2f} (Status: {status})")
            
        except Exception as e:
            logger.error(f"Error adding trade: {e}", exc_info=True)
    
    def _validate_trade_record(self, trade_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate quality of trade record data.
        
        Args:
            trade_record: Trade record to validate
            
        Returns:
            Dictionary with validation result
        """
        validation = {
            'is_valid': True,
            'warnings': []
        }
        
        # Required fields
        required_fields = [
            'trade_id', 'symbol', 'side', 'status', 'entry'
        ]
        
        for field in required_fields:
            if field not in trade_record:
                validation['is_valid'] = False
                validation['warnings'].append(f"Missing required field: {field}")
        
        # Validate entry data
        entry = trade_record.get('entry', {})
        if entry:
            required_entry_fields = ['price', 'time', 'position_size']
            for field in required_entry_fields:
                if field not in entry:
                    validation['warnings'].append(f"Missing entry field: {field}")
            
            # Validate price
            if 'price' in entry:
                price = entry['price']
                if not isinstance(price, (int, float)) or price <= 0:
                    validation['warnings'].append(f"Invalid entry price: {price}")
            
            # Validate position size
            if 'position_size' in entry:
                size = entry['position_size']
                if not isinstance(size, (int, float)) or size <= 0:
                    validation['warnings'].append(f"Invalid position size: {size}")
        
        # Validate exit data if closed
        if trade_record.get('status') == 'closed':
            exit_data = trade_record.get('exit')
            if not exit_data:
                validation['warnings'].append("Missing exit data for closed trade")
            else:
                if 'price' not in exit_data:
                    validation['warnings'].append("Missing exit price")
                if 'time' not in exit_data:
                    validation['warnings'].append("Missing exit time")
        
        # Validate AI metadata (should be present for learning)
        if not trade_record.get('ai_metadata'):
            validation['warnings'].append("Missing AI metadata (important for learning)")
        
        # Validate technical indicators (should be present)
        entry_indicators = entry.get('technical_indicators', {})
        if not entry_indicators:
            validation['warnings'].append("Missing entry technical indicators")
        
        return validation
    
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
        """Get next trade ID by counting existing trades across all files."""
        try:
            count = 0
            # Count trades in all files
            for file_path in self._get_all_trade_files():
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        async for line in f:
                            if line.strip():
                                count += 1
                except (FileNotFoundError, IOError):
                    continue
            return count + 1
        except Exception:
            return 1

    async def get_recent_trades(self, limit: int = 3, days_back: int = 7) -> List[Dict[str, Any]]:
        """
        Get recent closed trades for AI memory from multiple daily files.
        Optimized format for Grok to read and learn from.
        
        Args:
            limit: Number of recent trades to retrieve
            days_back: Number of days to look back for trades (default: 7)
            
        Returns:
            List of recent trades in Grok-friendly format
        """
        try:
            trades = []
            
            # Get trade files from last N days (newest first)
            trade_files = self._get_all_trade_files(days_back=days_back)
            
            if not trade_files:
                return []
            
            # Read from all files (newest first)
            for file_path in trade_files:
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        async for line in f:
                            if line.strip():
                                try:
                                    trade = json.loads(line.strip())
                                    if trade.get('status') == 'closed':
                                        trades.append(trade)
                                except json.JSONDecodeError:
                                    continue
                except (FileNotFoundError, IOError) as e:
                    logger.debug(f"Could not read {file_path}: {e}")
                    continue
            
            # Sort by exit time (most recent first)
            trades.sort(
                key=lambda x: x.get('exit', {}).get('time', '') or x.get('timestamp', ''),
                reverse=True
            )
            
            recent = trades[:limit]
            
            logger.debug(
                f"Retrieved {len(recent)} recent trades from {len(trade_files)} files "
                f"(searched last {days_back} days)"
            )
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
        exit_market_data: Optional[Dict[str, Any]] = None,
        mfe_percent: Optional[float] = None,
        mae_percent: Optional[float] = None
    ) -> None:
        """
        Update a trade with exit information.
        Since JSONL is append-only, we need to rewrite the file containing the trade.
        
        Args:
            trade_id: ID of the trade to update
            exit_price: Exit price
            exit_reason: Reason for exit
            pnl: Profit/Loss in USDT
            exit_indicators: Technical indicators at exit
            exit_market_data: Market data at exit
        """
        try:
            # Find which file contains this trade
            target_file = None
            trades = []
            
            # Search in all files (newest first for efficiency)
            for file_path in self._get_all_trade_files():
                try:
                    file_trades = []
                    async with aiofiles.open(file_path, 'r') as f:
                        async for line in f:
                            if line.strip():
                                try:
                                    trade = json.loads(line.strip())
                                    file_trades.append(trade)
                                    # Check if this is our trade
                                    if trade.get('trade_id') == trade_id:
                                        target_file = file_path
                                        trades = file_trades
                                        break
                                except json.JSONDecodeError:
                                    continue
                    
                    if target_file:
                        break
                except (FileNotFoundError, IOError):
                    continue
            
            if not target_file:
                logger.warning(f"Trade {trade_id} not found in any file")
                return
            
            if not trades:
                # Re-read the file if we didn't collect all trades
                trades = []
                async with aiofiles.open(target_file, 'r') as f:
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
                    
                    # Update results with MFE/MAE
                    trade['results'] = {
                        "pnl_usdt": pnl,
                        "pnl_percent": pnl_pct,
                        "holding_time_hours": None,  # Could calculate if needed
                        "mfe_percent": mfe_percent if mfe_percent is not None else None,
                        "mae_percent": mae_percent if mae_percent is not None else None
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
            
            # Rewrite the file containing the trade
            async with aiofiles.open(target_file, 'w') as f:
                for trade in trades:
                    await f.write(json.dumps(trade, ensure_ascii=False) + '\n')
            
            # Invalidate stats cache
            self._stats_cache = None
            
            logger.info(f"Trade {trade_id} updated with exit info (P&L: ${pnl:.2f})")
            
        except Exception as e:
            logger.error(f"Error updating trade exit: {e}", exc_info=True)

    async def load_history(self, days_back: Optional[int] = None) -> Dict[str, Any]:
        """
        Load all trades from daily files for backward compatibility.
        
        Args:
            days_back: Number of days to load (None = all files)
        
        Returns:
            Dictionary with trades and statistics
        """
        try:
            trades = []
            
            # Read from all trade files
            for file_path in self._get_all_trade_files(days_back=days_back):
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        async for line in f:
                            if line.strip():
                                try:
                                    trade = json.loads(line.strip())
                                    trades.append(trade)
                                except json.JSONDecodeError:
                                    continue
                except (FileNotFoundError, IOError):
                    continue
            
            # Sort by timestamp (oldest first for consistency)
            trades.sort(key=lambda x: x.get('timestamp', ''))
            
            stats = await self.get_statistics()
            
            return {
                'trades': trades,
                'statistics': stats
            }
            
        except Exception as e:
            logger.error(f"Error loading history: {e}")
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

    async def get_statistics(self, days_back: Optional[int] = None) -> Dict[str, Any]:
        """
        Calculate trading statistics from all daily JSONL files.
        
        Args:
            days_back: Number of days to include (None = all files)
        
        Returns:
            Dictionary with performance statistics
        """
        # Use cache if available
        if self._stats_cache:
            return self._stats_cache
        
        try:
            closed_trades = []
            
            # Read from all trade files
            for file_path in self._get_all_trade_files(days_back=days_back):
                try:
                    async with aiofiles.open(file_path, 'r') as f:
                        async for line in f:
                            if line.strip():
                                try:
                                    trade = json.loads(line.strip())
                                    if trade.get('status') == 'closed':
                                        closed_trades.append(trade)
                                except json.JSONDecodeError:
                                    continue
                except (FileNotFoundError, IOError):
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
    
    async def cleanup_old_files(self, retention_days: int = 30) -> Dict[str, Any]:
        """
        Clean up old trade files based on retention policy.
        
        Args:
            retention_days: Number of days to keep files (default: 30)
            
        Returns:
            Dictionary with cleanup statistics
        """
        try:
            today = date.today()
            deleted_count = 0
            deleted_size = 0
            errors = []
            
            # Get all trade files
            for file_path in self.storage_dir.glob("trades_*.jsonl"):
                try:
                    # Extract date from filename
                    date_str = file_path.stem.replace("trades_", "")
                    file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    # Calculate days old
                    days_old = (today - file_date).days
                    
                    # Delete if older than retention period
                    if days_old > retention_days:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        deleted_count += 1
                        deleted_size += file_size
                        logger.info(
                            f"Deleted old trade file: {file_path.name} "
                            f"({days_old} days old, {file_size} bytes)"
                        )
                except (ValueError, AttributeError, OSError) as e:
                    errors.append(f"{file_path.name}: {str(e)}")
                    continue
            
            result = {
                'deleted_files': deleted_count,
                'deleted_size_bytes': deleted_size,
                'errors': errors
            }
            
            if deleted_count > 0:
                logger.info(
                    f"Cleanup completed: Deleted {deleted_count} files "
                    f"({deleted_size / 1024 / 1024:.2f} MB)"
                )
            else:
                logger.debug("Cleanup: No old files to delete")
            
            return result
            
        except Exception as e:
            logger.error(f"Error cleaning up old files: {e}", exc_info=True)
            return {
                'deleted_files': 0,
                'deleted_size_bytes': 0,
                'errors': [str(e)]
            }
