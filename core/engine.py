"""Main trading engine orchestrating all components."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from loguru import logger

from core.base_exchange import BaseExchange
from core.base_ai import BaseAI
from services.analyzer import Analyzer
from services.risk_manager import RiskManager
from services.analytics import Analytics
from services.ai_optimizer import AIOptimizer
from storage.state_manager import StateManager
from utils.error_handler import (
    log_error_with_context, ErrorCode, ErrorCategory, ErrorSeverity
)


class TradingEngine:
    """Main orchestration engine for the trading bot."""

    def __init__(
        self,
        exchange: BaseExchange,
        ai_provider: BaseAI,
        analyzer: Analyzer,
        risk_manager: RiskManager,
        state_manager: StateManager,
        analytics: Optional[Analytics] = None,
        ai_optimizer: Optional[AIOptimizer] = None,
        symbols: Optional[List[str]] = None,
        timeframe: str = "30m",
        dry_run: bool = True
    ):
        """
        Initialize trading engine.
        
        Args:
            exchange: Exchange provider instance
            ai_provider: AI provider instance
            analyzer: Technical analyzer instance
            risk_manager: Risk manager instance
            state_manager: State manager instance
            analytics: Analytics service instance
            ai_optimizer: AI optimizer with caching (optional, will be created if None)
            symbols: List of trading pair symbols (default: ["BTC/USDT"])
            timeframe: Candle timeframe
            dry_run: If True, no real trades will be executed
        """
        self.exchange = exchange
        self.ai_provider = ai_provider
        self.analyzer = analyzer
        self.risk_manager = risk_manager
        self.state_manager = state_manager
        self.analytics = analytics
        self.active_symbols = symbols or ["BTC/USDT"]
        self.timeframe = timeframe
        self.dry_run = dry_run
        
        # Initialize AI optimizer if not provided
        if ai_optimizer is None:
            self.ai_optimizer = AIOptimizer(ai_provider, cache_ttl_minutes=30)
        else:
            self.ai_optimizer = ai_optimizer
        
        # Track positions per symbol
        self.positions: Dict[str, Optional[dict]] = {}
        for symbol in self.active_symbols:
            self.positions[symbol] = None

    def update_active_symbols(self, symbols: List[str]) -> None:
        """
        Update the list of active trading symbols.
        
        Args:
            symbols: New list of symbols to trade
        """
        self.active_symbols = symbols
        
        # Initialize positions for new symbols
        for symbol in symbols:
            if symbol not in self.positions:
                self.positions[symbol] = None
        
        logger.info(f"Active symbols updated: {', '.join(symbols)}")

    async def run_cycle(self) -> None:
        """
        Execute one complete trading cycle for all active symbols.
        
        This is the main loop that runs every 30 minutes.
        """
        try:
            logger.info(f"{'='*60}")
            logger.info(f"Starting trading cycle for {len(self.active_symbols)} symbol(s)")
            logger.info(f"Active symbols: {', '.join(self.active_symbols)}")
            logger.info(f"Dry run mode: {self.dry_run}")
            logger.info(f"{'='*60}")
            
            # Run cycle for each active symbol
            for symbol in self.active_symbols:
                await self._run_symbol_cycle(symbol)
            
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.BUSINESS_LOGIC_ERROR,
                ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.CRITICAL,
                "TradingEngine", operation="run_cycle",
                metadata={"symbols_count": len(self.active_symbols)}
            )

    async def _run_symbol_cycle(self, symbol: str) -> None:
        """
        Execute trading cycle for a single symbol.
        
        Args:
            symbol: Trading pair symbol
        """
        try:
            logger.info(f"\n--- Analyzing {symbol} ---")
            
            # Step 1: Fetch market data
            ohlcv_data = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=self.timeframe,
                limit=100
            )
            
            if not ohlcv_data or len(ohlcv_data) < 50:
                log_error_with_context(
                    ValueError(f"Insufficient market data: got {len(ohlcv_data) if ohlcv_data else 0} candles, need 50"),
                    ErrorCode.DATA_INSUFFICIENT,
                    ErrorCategory.DATA_ERROR, ErrorSeverity.MEDIUM,
                    "TradingEngine", symbol=symbol, operation="fetch_ohlcv",
                    metadata={"candles_received": len(ohlcv_data) if ohlcv_data else 0, "required": 50}
                )
                return
            
            # Step 2: Calculate technical indicators
            indicators = self.analyzer.calculate_indicators(ohlcv_data)
            logger.info(
                f"Indicators: RSI={indicators.get('rsi', 0):.2f}, "
                f"EMA20={indicators.get('ema_20', 0):.2f}, "
                f"EMA50={indicators.get('ema_50', 0):.2f}, "
                f"ATR%={indicators.get('atr_pct', 0):.2f}"
            )
            
            # Step 2.1: Technical filter - skip AI if signals don't pass
            if not self._technical_filter_passed(indicators, symbol):
                logger.info(f"{symbol}: Technical filter failed - skipping AI call")
                return
            
            # Step 3: Get current ticker for precise price
            ticker = await self.exchange.get_ticker(symbol)
            current_price = ticker.get('last', indicators.get('current_price', 0))
            
            # Step 3.1: Get BTC trend for market context (if not BTC itself)
            btc_trend = None
            btc_rsi = None
            if symbol != "BTC/USDT":
                try:
                    btc_ohlcv = await self.exchange.fetch_ohlcv("BTC/USDT", timeframe=self.timeframe, limit=50)
                    if btc_ohlcv and len(btc_ohlcv) >= 50:
                        btc_indicators = self.analyzer.calculate_indicators(btc_ohlcv)
                        btc_trend = "bullish" if btc_indicators.get('ema_20', 0) > btc_indicators.get('ema_50', 0) else "bearish"
                        btc_rsi = btc_indicators.get('rsi', 50)
                except Exception as e:
                    logger.debug(f"Could not fetch BTC trend: {e}")
            
            # Get market session and day of week
            from datetime import datetime
            utc_now = datetime.utcnow()
            hour = utc_now.hour
            day_of_week = utc_now.strftime('%A')
            
            # Determine market session
            if 0 <= hour < 8:
                market_session = "Asia"
            elif 8 <= hour < 16:
                market_session = "Europe"
            else:
                market_session = "US"
            
            market_data = {
                'price': current_price,
                'volume': ticker.get('baseVolume', indicators.get('volume', 0)),
                'change_pct': ticker.get('percentage', 0),
                'market_session': market_session,
                'day_of_week': day_of_week,
                'hour_utc': hour,
                'btc_trend': btc_trend,
                'btc_rsi': btc_rsi if 'btc_rsi' in locals() else None
            }
            
            # Step 4: Get trading memory (last 5 trades for better learning)
            memory = await self.state_manager.get_recent_trades(limit=5)
            
            # Step 5: Get AI decision with optimizer (caching + rate limiting)
            logger.debug(f"Requesting AI decision for {symbol}...")
            logger.debug(f"Memory context: {len(memory)} recent trades")
            
            # Check if we have an open position
            has_position = self.positions.get(symbol) is not None
            
            # Use AI optimizer for smart caching
            decision = await self.ai_optimizer.get_analysis(
                symbol=symbol,
                market_data=market_data,
                technical_indicators=indicators,
                has_position=has_position,
                memory=memory,
                force=False
            )
            
            # If None returned (rate limited or cached), skip this cycle
            if decision is None:
                logger.debug(f"{symbol}: AI call skipped (rate limited or cached)")
                return
            
            # Log decision with full context
            logger.info(
                f"AI Decision: {decision.action} "
                f"(Confidence: {decision.confidence}%) - {decision.reasoning}"
            )
            
            # Log validation result if available
            validation = decision.additional_context.get('validation', {}) if decision.additional_context else {}
            if validation:
                is_valid = validation.get('is_valid', True)
                warnings = validation.get('warnings', [])
                logger.debug(f"Decision validation: {'VALID' if is_valid else 'INVALID'}")
                if warnings:
                    logger.debug(f"Validation warnings: {len(warnings)}")
                    for warning in warnings:
                        logger.debug(f"  ⚠️  {warning}")
            
            # Detect anomalies in AI decision (Task 6)
            if self.analytics:
                anomaly_data = self.analytics.detect_anomalies(
                    decision=decision.to_dict(),
                    market_data=market_data,
                    technical_indicators=indicators
                )
                
                if anomaly_data.get('has_anomalies'):
                    await self.analytics.record_anomaly(
                        symbol=symbol,
                        decision=decision.to_dict(),
                        market_data=market_data,
                        technical_indicators=indicators,
                        anomaly_data=anomaly_data
                    )
            
            # Record AI decision for analytics and get timestamp
            decision_timestamp = None
            if self.analytics:
                decision_timestamp = datetime.utcnow().isoformat()
                await self.analytics.record_ai_decision(
                    symbol=symbol,
                    decision=decision.to_dict(),
                    market_data=market_data,
                    technical_indicators=indicators,
                    context={'memory': memory}
                )
                
                # Record market condition
                await self.analytics.record_market_condition(
                    symbol=symbol,
                    indicators=indicators,
                    price=current_price,
                    volume=market_data.get('volume', 0)
                )
            
            # Step 6: Execute trading logic based on decision
            current_position = self.positions.get(symbol)
            
            # Log execution decision logic
            logger.debug(f"Execution check for {symbol}:")
            logger.debug(f"  Decision action: {decision.action}")
            logger.debug(f"  Should execute: {decision.should_execute()}")
            logger.debug(f"  Current position: {'Yes' if current_position else 'No'}")
            logger.debug(f"  Confidence: {decision.confidence}% (min required: 80%)")
            
            if decision.should_execute() and not current_position:
                logger.info(f"{symbol}: Executing BUY - confidence {decision.confidence}% >= 80%, no open position")
                await self._execute_buy(
                    symbol, 
                    current_price, 
                    decision, 
                    decision_timestamp,
                    indicators=indicators,
                    market_data=market_data
                )
            elif not decision.should_execute() and decision.action == "BUY":
                reason = "confidence too low" if decision.confidence < 80.0 else "action not BUY"
                logger.info(f"{symbol}: NOT executing BUY - {reason} (confidence: {decision.confidence}%)")
                if self.analytics and decision_timestamp:
                    await self.analytics.update_decision_result(
                        decision_timestamp=decision_timestamp,
                        executed=False,
                        trade_result={'reason': reason}
                    )
            elif current_position:
                logger.debug(f"{symbol}: Checking exit conditions for open position")
                await self._check_exit_conditions(symbol, current_price)
            else:
                logger.info(f"{symbol}: Holding - no action taken")
                # Update analytics that decision was not executed
                if self.analytics and decision_timestamp:
                    await self.analytics.update_decision_result(
                        decision_timestamp=decision_timestamp,
                        executed=False,
                        trade_result={'reason': 'HOLD decision'}
                    )
            
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.BUSINESS_LOGIC_ERROR,
                ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.HIGH,
                "TradingEngine", symbol=symbol, operation="run_symbol_cycle",
                metadata={
                    "timeframe": self.timeframe,
                    "has_position": self.positions.get(symbol) is not None
                }
            )
    
    def _technical_filter_passed(
        self, 
        indicators: Dict[str, float],
        symbol: str
    ) -> bool:
        """
        Quick technical filter to skip AI calls for unpromising signals.
        
        Only passes signals that show clear potential, saving API costs.
        
        Args:
            indicators: Technical indicators dictionary
            symbol: Trading pair symbol
            
        Returns:
            True if technical signals pass filter
        """
        rsi = indicators.get('rsi', 50)
        ema_20 = indicators.get('ema_20', 0)
        ema_50 = indicators.get('ema_50', 0)
        volume_spike = indicators.get('volume_change_pct', 0) > 20  # 20% volume increase
        atr_pct = indicators.get('atr_pct', 0)
        
        # Determine EMA trend
        ema_trend = 'up' if ema_20 > ema_50 else 'down' if ema_20 < ema_50 else 'neutral'
        
        # Check if we have an open position
        has_position = self.positions.get(symbol) is not None
        
        if has_position:
            # For open positions: look for exit signals
            sell_signal = (
                rsi > 70 or  # Overbought
                ema_trend == 'down'  # Downtrend
            )
            if sell_signal:
                logger.debug(
                    f"{symbol}: Technical filter PASSED (exit signal: "
                    f"RSI={rsi:.1f}, EMA_trend={ema_trend})"
                )
                return True
        else:
            # For new positions: look for entry signals
            buy_signal = (
                rsi < 40 and  # Oversold
                ema_trend == 'up' and  # Uptrend
                (volume_spike or atr_pct < 10)  # Volume spike or moderate volatility
            )
            if buy_signal:
                logger.debug(
                    f"{symbol}: Technical filter PASSED (entry signal: "
                    f"RSI={rsi:.1f}, EMA_trend={ema_trend}, "
                    f"volume_spike={volume_spike}, ATR%={atr_pct:.2f})"
                )
                return True
        
        # If no clear signal, still allow if RSI is in neutral zone
        # (to avoid missing opportunities)
        if 35 <= rsi <= 65:
            logger.debug(
                f"{symbol}: Technical filter PASSED (neutral zone: RSI={rsi:.1f})"
            )
            return True
        
        logger.debug(
            f"{symbol}: Technical filter FAILED (RSI={rsi:.1f}, "
            f"EMA_trend={ema_trend}, volume_spike={volume_spike})"
        )
        return False

    async def _execute_buy(
        self, 
        symbol: str, 
        current_price: float, 
        decision, 
        decision_timestamp: Optional[str] = None,
        indicators: Optional[Dict[str, Any]] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Execute a buy order.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            decision: AI decision object
            decision_timestamp: Timestamp of the AI decision
            indicators: Technical indicators at entry
            market_data: Market data at entry
        """
        try:
            # Check if symbol is allowed
            if not self.risk_manager.is_symbol_allowed(symbol):
                logger.warning(f"Symbol {symbol} is blacklisted, skipping buy")
                return
            
            # Get trade parameters with dynamic calculations
            volatility = indicators.get('atr_pct') if indicators else None
            confidence = decision.confidence if decision else None
            
            trade_params = self.risk_manager.get_trade_params(
                entry_price=current_price,
                volatility=volatility,
                confidence=confidence,
                side='buy'
            )
            
            # Validate trade
            logger.debug(f"Validating trade for {symbol}...")
            logger.debug(f"  Entry price: ${current_price:.2f}")
            logger.debug(f"  Position size: {trade_params['position_size']:.6f}")
            logger.debug(f"  Stop-loss: ${trade_params['stop_loss']:.2f} ({trade_params.get('stop_loss_pct', 0):.2f}%)")
            logger.debug(f"  Take-profit: ${trade_params['take_profit']:.2f} ({trade_params.get('take_profit_pct', 0):.2f}%)")
            
            validation = self.risk_manager.validate_trade(
                symbol,
                current_price,
                trade_params['position_size']
            )
            
            logger.debug(f"Risk validation result: {'VALID' if validation['is_valid'] else 'INVALID'}")
            if validation.get('reasons'):
                for reason in validation['reasons']:
                    logger.debug(f"  Validation reason: {reason}")
            
            if not validation['is_valid']:
                logger.warning(f"Trade validation failed for {symbol}: {validation['reasons']}")
                return
            
            logger.info(f"Executing BUY order for {symbol}")
            logger.info(f"Entry: ${trade_params['entry_price']:.2f}")
            logger.info(f"Stop-Loss: ${trade_params['stop_loss']:.2f}")
            logger.info(f"Take-Profit: ${trade_params['take_profit']:.2f}")
            logger.info(f"Position size: {trade_params['position_size']:.6f}")
            
            if not self.dry_run:
                # Execute real order
                order = await self.exchange.create_market_order(
                    symbol=symbol,
                    side='buy',
                    amount=trade_params['position_size']
                )
                
                logger.info(f"Order executed: {order.get('id')}")
            else:
                logger.info("[DRY RUN] Order simulated (not executed)")
            
            # Save position
            self.positions[symbol] = {
                'symbol': symbol,
                'entry_price': current_price,
                'position_size': trade_params['position_size'],
                'stop_loss': trade_params['stop_loss'],
                'take_profit': trade_params['take_profit'],
                'entry_reason': decision.reasoning
            }
            
            # Add to history with full context for Grok learning
            # Use indicators and market_data from parameters if provided, otherwise use defaults
            entry_indicators = indicators if indicators is not None else {}
            entry_market_data = market_data if market_data is not None else {}
            
            # Extract AI metadata from decision
            ai_metadata = decision.additional_context.get('ai_metadata') if decision.additional_context else None
            
            await self.state_manager.add_trade(
                symbol=symbol,
                entry_price=current_price,
                exit_price=None,
                position_size=trade_params['position_size'],
                side='buy',
                entry_reason=decision.reasoning,
                status='open',
                entry_indicators=entry_indicators,
                entry_market_data=entry_market_data,
                ai_confidence=decision.confidence,
                stop_loss=trade_params['stop_loss'],
                take_profit=trade_params['take_profit'],
                ai_metadata=ai_metadata
            )
            
            # Update analytics that decision was executed
            if self.analytics and decision_timestamp:
                await self.analytics.update_decision_result(
                    decision_timestamp=decision_timestamp,
                    executed=True
                )
            
            logger.success(f"Position opened: {symbol} @ ${current_price:.2f}")
            
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.BUSINESS_LOGIC_ERROR,
                ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.CRITICAL,
                "TradingEngine", symbol=symbol, operation="execute_buy",
                metadata={
                    "entry_price": current_price,
                    "dry_run": self.dry_run,
                    "decision_confidence": decision.confidence if decision else None
                }
            )

    async def _check_exit_conditions(self, symbol: str, current_price: float) -> None:
        """
        Check if exit conditions are met for current position.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
        """
        position = self.positions.get(symbol)
        if not position:
            return
        
        try:
            entry_price = position['entry_price']
            stop_loss = position['stop_loss']
            take_profit = position['take_profit']
            
            exit_reason = None
            
            # Check stop-loss
            if current_price <= stop_loss:
                exit_reason = f"Stop-loss hit (${stop_loss:.2f})"
                logger.warning(exit_reason)
            
            # Check take-profit
            elif current_price >= take_profit:
                exit_reason = f"Take-profit hit (${take_profit:.2f})"
                logger.success(exit_reason)
            
            # Execute exit if conditions met
            if exit_reason:
                await self._execute_sell(symbol, current_price, exit_reason)
            else:
                # Log current position status
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                logger.info(
                    f"{symbol} position: ${current_price:.2f} "
                    f"(P&L: {pnl_pct:+.2f}%, SL: ${stop_loss:.2f}, TP: ${take_profit:.2f})"
                )
                
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.BUSINESS_LOGIC_ERROR,
                ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.HIGH,
                "TradingEngine", symbol=symbol, operation="check_exit_conditions",
                metadata={"current_price": current_price}
            )

    async def _execute_sell(self, symbol: str, current_price: float, exit_reason: str) -> None:
        """
        Execute a sell order to close position.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            exit_reason: Reason for exit
        """
        position = self.positions.get(symbol)
        if not position:
            return
        
        try:
            position_size = position['position_size']
            entry_price = position['entry_price']
            
            # Calculate P&L
            pnl_pct = ((current_price - entry_price) / entry_price) * 100
            pnl_usdt = (current_price - entry_price) * position_size
            
            logger.info(f"Executing SELL order for {symbol}")
            logger.info(f"Exit: ${current_price:.2f}")
            logger.info(f"P&L: {pnl_pct:+.2f}% (${pnl_usdt:+.2f})")
            
            if not self.dry_run:
                # Execute real order
                order = await self.exchange.create_market_order(
                    symbol=symbol,
                    side='sell',
                    amount=position_size
                )
                
                logger.info(f"Order executed: {order.get('id')}")
            else:
                logger.info("[DRY RUN] Order simulated (not executed)")
            
            # Update trade in history
            # Find the last open trade for this symbol
            history = await self.state_manager.load_history()
            trades = history.get('trades', [])
            
            # Find the most recent open trade for this symbol
            open_trade = None
            for trade in reversed(trades):
                if (trade.get('symbol') == symbol and 
                    trade.get('status') == 'open'):
                    open_trade = trade
                    break
            
            if open_trade:
                # Get current indicators for exit context
                ohlcv_data = await self.exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe=self.timeframe,
                    limit=100
                )
                exit_indicators = self.analyzer.calculate_indicators(ohlcv_data) if ohlcv_data else {}
                ticker = await self.exchange.get_ticker(symbol)
                exit_market_data = {
                    'price': current_price,
                    'volume': ticker.get('baseVolume', 0),
                    'change_pct': ticker.get('percentage', 0)
                }
                
                await self.state_manager.update_trade_exit(
                    trade_id=open_trade['trade_id'],
                    exit_price=current_price,
                    exit_reason=exit_reason,
                    pnl=pnl_usdt,
                    exit_indicators=exit_indicators,
                    exit_market_data=exit_market_data
                )
                
                # Update analytics with trade result
                if self.analytics:
                        # Find the decision that led to this trade
                        data = await self.analytics._load_data()
                        for ai_decision in reversed(data.get('ai_decisions', [])):
                            if (ai_decision.get('symbol') == symbol and 
                                ai_decision.get('executed') and 
                                not ai_decision.get('trade_result')):
                                ai_decision['trade_result'] = {
                                    'pnl': pnl_usdt,
                                    'pnl_pct': pnl_pct,
                                    'exit_reason': exit_reason,
                                    'exit_price': current_price
                                }
                                await self.analytics._save_data(data)
                                break
            
            # Clear position
            self.positions[symbol] = None
            
            result = "PROFIT" if pnl_usdt > 0 else "LOSS"
            logger.success(f"Position closed: {result} of ${pnl_usdt:+.2f}")
            
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.BUSINESS_LOGIC_ERROR,
                ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.CRITICAL,
                "TradingEngine", symbol=symbol, operation="execute_sell",
                metadata={
                    "exit_price": current_price,
                    "exit_reason": exit_reason,
                    "dry_run": self.dry_run
                }
            )

    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing trading engine...")
        await self.exchange.initialize()
        logger.success("Trading engine initialized")

    async def shutdown(self) -> None:
        """Shutdown all components."""
        logger.info("Shutting down trading engine...")
        await self.exchange.close()
        await self.ai_provider.close()
        logger.success("Trading engine shutdown complete")
