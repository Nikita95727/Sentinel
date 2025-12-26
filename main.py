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
    from config import settings
    
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


async def main():
    """Main application entry point."""
    setup_logging()
    
    logger.info("=" * 80)
    logger.info("SENTINEL AI TRADING BOT - MODULAR ARCHITECTURE")
    logger.info("=" * 80)
    logger.info(f"Version: MVP 2.0 (Modular)")
    logger.info("=" * 80)
    
    # Load configuration
    from config import settings
    
    config = {
        'bybit_api_key': settings.bybit_api_key,
        'bybit_api_secret': settings.bybit_api_secret,
        'bybit_testnet': settings.bybit_testnet,
        'grok_api_key': settings.grok_api_key,
        'grok_model': settings.grok_model,
        'dry_run': settings.dry_run,
    }
    
    logger.info(f"Dry Run Mode: {settings.dry_run}")
    logger.info(f"Testnet: {settings.bybit_testnet}")
    logger.info("=" * 80)
    
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
        
        # Register modules based on .env configuration
        modules_registered = 0
        
        # Conservative module (default: enabled)
        if settings.enable_conservative_module:
            from modules.conservative.module import ConservativeModule
            conservative_module = ConservativeModule(app.core_context)
            app.register_module(conservative_module)
            modules_registered += 1
            logger.info("✅ Conservative module enabled")
        else:
            logger.info("⏸️  Conservative module disabled (ENABLE_CONSERVATIVE_MODULE=false)")
        
        # Launch sniper module (default: disabled)
        if settings.enable_launch_sniper_module:
            from modules.launch_sniper.module import LaunchSniperModule
            launch_sniper_module = LaunchSniperModule(app.core_context)
            app.register_module(launch_sniper_module)
            modules_registered += 1
            logger.info("✅ Launch sniper module enabled")
        else:
            logger.info("⏸️  Launch sniper module disabled (ENABLE_LAUNCH_SNIPER_MODULE=false)")
        
        if modules_registered == 0:
            logger.warning("⚠️  No modules enabled! Please enable at least one module in .env")
            logger.warning("   Set ENABLE_CONSERVATIVE_MODULE=true or ENABLE_LAUNCH_SNIPER_MODULE=true")
            sys.exit(1)
        
        logger.info(f"Registered {modules_registered} module(s)")
        
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

