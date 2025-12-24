"""Main entry point for Sentinel AI Trading Bot."""

import asyncio
import sys
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from config import settings
from core.engine import TradingEngine
from providers.bybit import BybitProvider
from providers.grok import GrokProvider
from services.analyzer import Analyzer
from services.risk_manager import RiskManager
from services.analytics import Analytics
from services.report_generator import ReportGenerator
from services.validator import SafetyValidator
from services.ai_optimizer import AIOptimizer
from services.sqlite_scheduler import SQLiteScheduler
from storage.state_manager import StateManager
from utils.error_handler import (
    log_error_with_context, ErrorCode, ErrorCategory, ErrorSeverity, error_handler
)


async def determine_market_phase(exchange: BybitProvider) -> str:
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


def setup_logging():
    """Configure loguru logging."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        level=settings.log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    
    # File logging with rotation
    logger.add(
        "logs/sentinel_{time:YYYY-MM-DD}.log",
        rotation=settings.log_rotation,
        retention=settings.log_retention,
        level=settings.log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )
    
    logger.info("Logging configured")


async def run_daily_screening(engine: TradingEngine, analyzer: Analyzer, ai_provider: GrokProvider, exchange: BybitProvider):
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
        logger.info("STARTING DAILY SCREENING")
        logger.info("="*80)
        
        # Step 1: Scan top volume coins
        top_coins = await analyzer.scan_top_volume_coins(
            exchange=exchange,
            limit=settings.screener_top_n,
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
            max_symbols=settings.screener_max_symbols,
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
        logger.info("DAILY SCREENING COMPLETED")
        logger.info("="*80)
        
    except Exception as e:
        log_error_with_context(
            e, ErrorCode.BUSINESS_LOGIC_ERROR,
            ErrorCategory.BUSINESS_LOGIC_ERROR, ErrorSeverity.HIGH,
            "DailyScreening", operation="run_daily_screening",
            metadata={"max_symbols": settings.screener_max_symbols}
        )


async def main():
    """Main application entry point."""
    
    # Setup logging
    setup_logging()
    
    # Validate configuration
    logger.info("Validating configuration...")
    readiness = SafetyValidator.check_production_readiness()
    
    if readiness['blockers']:
        logger.error("=" * 80)
        logger.error("CONFIGURATION ERRORS DETECTED")
        logger.error("=" * 80)
        for blocker in readiness['blockers']:
            logger.error(f"❌ {blocker}")
        logger.error("=" * 80)
        logger.error("Please fix these issues before starting the bot.")
        sys.exit(1)
    
    config_validation = readiness.get('config_validation', {})
    if config_validation.get('warnings'):
        logger.warning("=" * 80)
        logger.warning("CONFIGURATION WARNINGS")
        logger.warning("=" * 80)
        for warning in config_validation['warnings']:
            logger.warning(f"⚠️  {warning}")
        logger.warning("=" * 80)
    
    if readiness['recommendations']:
        logger.info("Recommendations:")
        for rec in readiness['recommendations']:
            logger.info(f"💡 {rec}")
    
    logger.info(f"Production Readiness: {readiness['status']} (Score: {readiness['score']}/100)")
    logger.info("=" * 80)
    logger.info("SENTINEL AI TRADING BOT WITH DAILY SCREENER")
    logger.info("=" * 80)
    logger.info(f"Version: MVP 2.0")
    logger.info(f"Daily Screening: Enabled (every {settings.screener_interval_hours}h)")
    logger.info(f"Top N Coins: {settings.screener_top_n}")
    logger.info(f"Max Symbols: {settings.screener_max_symbols}")
    logger.info(f"Trading Timeframe: {settings.trading_timeframe}")
    logger.info(f"Cycle Interval: {settings.cycle_interval_minutes} minutes")
    logger.info(f"Dry Run Mode: {settings.dry_run}")
    logger.info(f"Initial Balance: ${settings.trading_balance}")
    logger.info("=" * 80)
    
    # Initialize components with dependency injection
    logger.info("Initializing components...")
    
    # Exchange provider
    exchange = BybitProvider(
        api_key=settings.bybit_api_key,
        api_secret=settings.bybit_api_secret,
        testnet=settings.bybit_testnet
    )
    
    # AI provider
    ai_provider = GrokProvider(
        api_key=settings.grok_api_key,
        model=settings.grok_model
    )
    
    # AI Optimizer (for caching and rate limiting)
    ai_optimizer = AIOptimizer(
        ai_provider=ai_provider,
        cache_ttl_minutes=30  # Cache for 30 minutes
    )
    
    # Services
    analyzer = Analyzer()
    risk_manager = RiskManager(
        balance=settings.trading_balance,
        stop_loss_pct=settings.stop_loss_pct,
        min_risk_reward=settings.min_risk_reward
    )
    state_manager = StateManager(storage_path=settings.storage_path)
    analytics = Analytics(storage_path="storage/analytics")
    report_generator = ReportGenerator(analytics=analytics, state_manager=state_manager)
    
    # Trading engine (initially with fallback symbol)
    initial_symbols = [settings.trading_symbol] if hasattr(settings, 'trading_symbol') else ["BTC/USDT"]
    engine = TradingEngine(
        exchange=exchange,
        ai_provider=ai_provider,
        analyzer=analyzer,
        risk_manager=risk_manager,
        state_manager=state_manager,
        analytics=analytics,
        ai_optimizer=ai_optimizer,  # Pass AI optimizer
        symbols=initial_symbols,
        timeframe=settings.trading_timeframe,
        dry_run=settings.dry_run
    )
    
    # Initialize engine
    await engine.initialize()
    
    logger.success("All components initialized successfully")
    
    # Setup scheduler
    scheduler = AsyncIOScheduler()
    
    # Add daily screening job (runs every 24 hours)
    scheduler.add_job(
        run_daily_screening,
        trigger=IntervalTrigger(hours=settings.screener_interval_hours),
        args=[engine, analyzer, ai_provider, exchange],
        id='daily_screening',
        name='Daily Symbol Screening',
        replace_existing=True
    )
    
    # Add trading cycle job (runs every 30 minutes)
    scheduler.add_job(
        engine.run_cycle,
        trigger=IntervalTrigger(minutes=settings.cycle_interval_minutes),
        id='trading_cycle',
        name='Trading Cycle',
        replace_existing=True
    )
    
    # Add daily report generation job (runs once per day at midnight UTC)
    async def generate_daily_report_job():
        """Generate and log daily report."""
        try:
            report = await report_generator.generate_daily_report()
            logger.info("\n" + report)
        except Exception as e:
            logger.error(f"Error generating daily report: {e}")
    
    from apscheduler.triggers.cron import CronTrigger
    
    # Add daily report generation job (runs once per day at midnight UTC)
    scheduler.add_job(
        generate_daily_report_job,
        trigger=CronTrigger(hour=0, minute=0),  # Midnight UTC
        id='daily_report',
        name='Daily Report Generation',
        replace_existing=True
    )
    
    # Add daily file rotation job (runs once per day at midnight UTC)
    async def daily_rotation_job():
        """Perform daily file rotation for trade storage."""
        try:
            await state_manager.perform_daily_rotation()
            logger.info("Daily file rotation completed")
        except Exception as e:
            logger.error(f"Error in daily rotation job: {e}")
    
    scheduler.add_job(
        daily_rotation_job,
        trigger=CronTrigger(hour=0, minute=0),  # Midnight UTC
        id='daily_rotation',
        name='Daily File Rotation',
        replace_existing=True
    )
    
    # Add old files cleanup job (runs once per day at 1 AM UTC)
    async def cleanup_old_files_job():
        """Clean up old trade files based on retention policy."""
        try:
            await state_manager.cleanup_old_files(retention_days=settings.storage_retention_days)
            logger.info(f"Old files cleanup completed (retention: {settings.storage_retention_days} days)")
        except Exception as e:
            logger.error(f"Error in cleanup job: {e}")
    
    scheduler.add_job(
        cleanup_old_files_job,
        trigger=CronTrigger(hour=1, minute=0),  # 1 AM UTC (after rotation)
        id='cleanup_old_files',
        name='Old Files Cleanup',
        replace_existing=True
    )
    
    logger.info(
        f"Scheduler configured: "
        f"Screening every {settings.screener_interval_hours}h, "
        f"Trading every {settings.cycle_interval_minutes}min"
    )
    
    # Run daily screening immediately to select initial symbols
    logger.info("Running initial daily screening...")
    await run_daily_screening(engine, analyzer, ai_provider, exchange)
    
    # Start scheduler
    scheduler.start()
    logger.success("Scheduler started - bot is now running")
    
    try:
        # Keep the application running
        while True:
            await asyncio.sleep(1)
            
    except (KeyboardInterrupt, SystemExit):
        logger.warning("Shutdown signal received")
        
    finally:
        # Cleanup
        logger.info("Shutting down...")
        scheduler.shutdown()
        await engine.shutdown()
        logger.success("Shutdown complete")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)
