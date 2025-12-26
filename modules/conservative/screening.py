"""
Daily screening logic for conservative module.
"""
# Use loguru for consistency with main bot
try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from modules.conservative.config import ConservativeConfig
from utils.error_handler import (
    log_error_with_context, ErrorCode, ErrorCategory, ErrorSeverity
)


async def determine_market_phase(exchange) -> str:
    """
    Determine current market phase based on BTC 7-day performance.
    
    Args:
        exchange: Exchange provider instance
        
    Returns:
        Market phase: "bullish", "bearish", or "sideways"
    """
    try:
        # Fetch BTC daily candles for last 7 days
        btc_ohlcv = await exchange.fetch_ohlcv(
            symbol="BTC/USDT",
            timeframe='1d',
            limit=8  # 7 days + current day
        )
        
        if not btc_ohlcv or len(btc_ohlcv) < 8:
            logger.warning("Insufficient BTC data for market phase determination")
            return "sideways"
        
        # Get price 7 days ago and current price
        price_7d_ago = float(btc_ohlcv[0][4])  # Close price 7 days ago
        current_price = float(btc_ohlcv[-1][4])  # Current close price
        
        # Calculate 7-day change percentage
        change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        # Determine phase
        if change_7d > 10:
            phase = "bullish"
        elif change_7d < -10:
            phase = "bearish"
        else:
            phase = "sideways"
        
        logger.debug(f"BTC 7-day change: {change_7d:+.2f}% → Market phase: {phase}")
        return phase
        
    except Exception as e:
        logger.error(f"Error determining market phase: {e}")
        return "sideways"  # Safe default


async def run_daily_screening(engine, analyzer, ai_provider, exchange):
    """
    Daily screening job to select the most promising symbols.
    
    Args:
        engine: Trading engine instance
        analyzer: Analyzer instance
        ai_provider: Grok provider instance  
        exchange: Exchange provider instance
    """
    try:
        logger.info("="*80)
        logger.info("STARTING DAILY SCREENING (Conservative Module)")
        logger.info("="*80)
        
        config = ConservativeConfig
        
        # Step 1: Scan top volume coins
        top_coins = await analyzer.scan_top_volume_coins(
            exchange=exchange,
            limit=config.SCREENER_TOP_N,
            quote_currency="USDT"
        )
        
        if not top_coins:
            logger.warning("No coins found during screening, keeping current symbols")
            return
        
        logger.info(f"Found {len(top_coins)} top volume coins")
        
        # Step 2: Calculate screening metrics (7-day ATR)
        candidates = await analyzer.calculate_screening_metrics(
            exchange=exchange,
            symbols=top_coins,
            lookback_days=7
        )
        
        if not candidates:
            logger.warning("No valid candidates after metric calculation, keeping current symbols")
            return
        
        logger.info(f"Calculated metrics for {len(candidates)} candidates")
        
        # Step 2.5: Determine market phase based on BTC 7-day performance
        market_phase = await determine_market_phase(exchange)
        logger.info(f"Current market phase: {market_phase}")
        
        # Step 3: Use Grok to select best symbols
        selected_symbols = await ai_provider.select_trading_symbols(
            candidates=candidates,
            max_symbols=config.SCREENER_MAX_SYMBOLS,
            market_phase=market_phase
        )
        
        if not selected_symbols:
            logger.warning("Grok did not select any symbols, keeping current symbols")
            return
        
        logger.success(
            f"Daily screening complete. Selected symbols: {', '.join(selected_symbols)}"
        )
        
        # Step 4: Update engine's active symbols
        engine.update_active_symbols(selected_symbols)
        
        logger.info("="*80)
        logger.info("DAILY SCREENING COMPLETED (Conservative Module)")
        logger.info("="*80)
        
    except Exception as e:
        log_error_with_context(
            e, ErrorCode.BUSINESS_LOGIC_ERROR,
            ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.HIGH,
            "ConservativeDailyScreening", operation="run_daily_screening",
            metadata={"max_symbols": config.SCREENER_MAX_SYMBOLS}
        )

