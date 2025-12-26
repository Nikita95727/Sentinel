"""
New main entry point for Sentinel bot.
Uses modular architecture.
"""
import asyncio
import sys
from pathlib import Path
from loguru import logger

# Setup logging
def setup_logging():
    """Configure loguru logging."""
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    )
    
    # File logging with rotation
    logger.add(
        "logs/sentinel_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )


async def main():
    """Main application entry point."""
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("SENTINEL AI TRADING BOT - MODULAR ARCHITECTURE")
    logger.info("=" * 80)
    
    # Load configuration
    from config import settings
    
    config = {
        'bybit_api_key': settings.bybit_api_key,
        'bybit_api_secret': settings.bybit_api_secret,
        'bybit_testnet': settings.bybit_testnet,
        'grok_api_key': settings.grok_api_key,
        'grok_model': settings.grok_model,
    }
    
    # Validate configuration
    from services.validator import SafetyValidator
    readiness = SafetyValidator.check_production_readiness()
    
    if readiness['blockers']:
        logger.error("=" * 80)
        logger.error("CONFIGURATION ERRORS DETECTED")
        logger.error("=" * 80)
        for blocker in readiness['blockers']:
            logger.error(f"❌ {blocker}")
        sys.exit(1)
    
    # Initialize core application
    from core.app import SentinelApp
    app = SentinelApp(config)
    
    try:
        await app.initialize()
        
        # Register modules
        from modules.conservative.module import ConservativeModule
        
        conservative_module = ConservativeModule(app.core_context)
        app.register_module(conservative_module)
        
        # Optional: Register launch_sniper if needed
        # from launch_sniper.module import LaunchSniperModule
        # launch_sniper_module = LaunchSniperModule(app.core_context)
        # app.register_module(launch_sniper_module)
        
        # Start all modules
        await app.start_all()
        
        logger.success("All modules started successfully")
        
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.warning("Shutdown signal received")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await app.stop_all()
        await app.close()
        logger.success("Application stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application terminated by user")
    except Exception as e:
        logger.critical(f"Critical error: {e}", exc_info=True)
        sys.exit(1)

