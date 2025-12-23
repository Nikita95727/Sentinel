"""Main trading engine orchestrating all components."""

from typing import Optional
from loguru import logger

from core.base_exchange import BaseExchange
from core.base_ai import BaseAI
from services.analyzer import Analyzer
from services.risk_manager import RiskManager
from storage.state_manager import StateManager


class TradingEngine:
    """Main orchestration engine for the trading bot."""

    def __init__(
        self,
        exchange: BaseExchange,
        ai_provider: BaseAI,
        analyzer: Analyzer,
        risk_manager: RiskManager,
        state_manager: StateManager,
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
            symbols: List of trading pair symbols (default: ["BTC/USDT"])
            timeframe: Candle timeframe
            dry_run: If True, no real trades will be executed
        """
        self.exchange = exchange
        self.ai_provider = ai_provider
        self.analyzer = analyzer
        self.risk_manager = risk_manager
        self.state_manager = state_manager
        self.active_symbols = symbols or ["BTC/USDT"]
        self.timeframe = timeframe
        self.dry_run = dry_run
        
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
            logger.error(f"Error in trading cycle: {e}", exc_info=True)

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
                logger.warning(f"Insufficient market data for {symbol}, skipping")
                return
            
            # Step 2: Calculate technical indicators
            indicators = self.analyzer.calculate_indicators(ohlcv_data)
            logger.info(
                f"Indicators: RSI={indicators.get('rsi', 0):.2f}, "
                f"EMA20={indicators.get('ema_20', 0):.2f}, "
                f"EMA50={indicators.get('ema_50', 0):.2f}"
            )
            
            # Step 3: Get current ticker for precise price
            ticker = await self.exchange.get_ticker(symbol)
            current_price = ticker.get('last', indicators.get('current_price', 0))
            
            market_data = {
                'price': current_price,
                'volume': ticker.get('baseVolume', indicators.get('volume', 0)),
                'change_pct': ticker.get('percentage', 0)
            }
            
            # Step 4: Get trading memory (last 3 trades)
            memory = await self.state_manager.get_recent_trades(limit=3)
            
            # Step 5: Get AI decision
            decision = await self.ai_provider.analyze(
                symbol=symbol,
                market_data=market_data,
                technical_indicators=indicators,
                memory=memory
            )
            
            logger.info(
                f"AI Decision: {decision.action} "
                f"(Confidence: {decision.confidence}%) - {decision.reasoning}"
            )
            
            # Step 6: Execute trading logic based on decision
            current_position = self.positions.get(symbol)
            
            if decision.should_execute() and not current_position:
                await self._execute_buy(symbol, current_price, decision)
            elif current_position:
                await self._check_exit_conditions(symbol, current_price)
            else:
                logger.info(f"{symbol}: Holding - no action taken")
            
        except Exception as e:
            logger.error(f"Error in cycle for {symbol}: {e}", exc_info=True)

    async def _execute_buy(self, symbol: str, current_price: float, decision) -> None:
        """
        Execute a buy order.
        
        Args:
            symbol: Trading pair symbol
            current_price: Current market price
            decision: AI decision object
        """
        try:
            # Check if symbol is allowed
            if not self.risk_manager.is_symbol_allowed(symbol):
                logger.warning(f"Symbol {symbol} is blacklisted, skipping buy")
                return
            
            # Get trade parameters
            trade_params = self.risk_manager.get_trade_params(current_price)
            
            # Validate trade
            validation = self.risk_manager.validate_trade(
                symbol,
                current_price,
                trade_params['position_size']
            )
            
            if not validation['is_valid']:
                logger.warning(f"Trade validation failed: {validation['reasons']}")
                return
            
            logger.info(f"Executing BUY order for {symbol}")
            logger.info(f"Entry: ${trade_params['entry_price']:.2f}")
            logger.info(f"Stop-Loss: ${trade_params['stop_loss']:.2f}")
            logger.info(f"Take-Profit: ${trade_params['take_profit']:.2f}")
            logger.info(f"Position size: {trade_params['position_size']:.6f}")
            
            if not self.dry_run:
                # Execute real order
                order = await self.exchange.create_market_order(
                    symbol=self.symbol,
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
            
            # Add to history
            await self.state_manager.add_trade(
                symbol=symbol,
                entry_price=current_price,
                exit_price=None,
                position_size=trade_params['position_size'],
                side='buy',
                entry_reason=decision.reasoning,
                status='open'
            )
            
            logger.success(f"Position opened: {symbol} @ ${current_price:.2f}")
            
        except Exception as e:
            logger.error(f"Error executing buy: {e}", exc_info=True)

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
            logger.error(f"Error checking exit conditions: {e}", exc_info=True)

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
                    symbol=self.symbol,
                    side='sell',
                    amount=position_size
                )
                
                logger.info(f"Order executed: {order.get('id')}")
            else:
                logger.info("[DRY RUN] Order simulated (not executed)")
            
            # Update trade in history
            # Note: This is simplified - in production, you'd track trade IDs properly
            history = await self.state_manager.load_history()
            trades = history.get('trades', [])
            if trades:
                last_trade = trades[-1]
                if last_trade.get('status') == 'open':
                    await self.state_manager.update_trade_exit(
                        trade_id=last_trade['id'],
                        exit_price=current_price,
                        exit_reason=exit_reason,
                        pnl=pnl_usdt
                    )
            
            # Clear position
            self.positions[symbol] = None
            
            result = "PROFIT" if pnl_usdt > 0 else "LOSS"
            logger.success(f"Position closed: {result} of ${pnl_usdt:+.2f}")
            
        except Exception as e:
            logger.error(f"Error executing sell: {e}", exc_info=True)

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
