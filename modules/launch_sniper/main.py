"""
Main entry point for launch sniper module.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import main bot components if needed
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from modules.launch_sniper.core.orchestrator import LaunchSniperOrchestrator
from modules.launch_sniper.config import LaunchSniperConfig

# Setup logging (try to use main bot's logger, fallback to basic)
try:
    from utils.logger_config import setup_logging
    setup_logging(
        log_dir=LaunchSniperConfig.LOG_DIR,
        log_prefix="launch_sniper"
    )
except ImportError:
    # Fallback if main bot's logger not available
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

logger = logging.getLogger(__name__)


async def main():
    """Main function."""
    logger.info("=" * 80)
    logger.info("LAUNCH SNIPER MODULE")
    logger.info("=" * 80)
    logger.info(f"Version: {__import__('modules.launch_sniper').__version__}")
    logger.info(f"Dry Run: {LaunchSniperConfig.DRY_RUN}")
    logger.info(f"Testnet: {LaunchSniperConfig.BYBIT_TESTNET}")
    logger.info("=" * 80)
    
    # Validate config
    if not LaunchSniperConfig.validate():
        logger.error("Configuration validation failed")
        logger.error("Required: BYBIT_API_KEY, BYBIT_API_SECRET")
        if LaunchSniperConfig.AI_ENABLED:
            logger.error("Also required: GROK_API_KEY")
        return
    
    # Create orchestrator
    orchestrator = LaunchSniperOrchestrator()
    
    try:
        # Initialize
        await orchestrator.initialize()
        
        # Run discovery
        events = await orchestrator.run_discovery_phase()
        
        if not events:
            logger.info("No new listing events found")
            return
        
        # Process each event
        for event in events:
            logger.info(f"Processing event: {event.symbol}")
            trade_result = await orchestrator.process_event(event)
            
            if trade_result:
                logger.info(f"Trade completed: PnL {trade_result.pnl_percent:.2f}%")
            else:
                logger.info(f"Trade aborted or skipped")
        
        # Monitor active events (if any are scheduled for future)
        if orchestrator.active_events:
            logger.info(f"Monitoring {len(orchestrator.active_events)} active events...")
            # Run monitoring in background
            monitor_task = asyncio.create_task(orchestrator.monitor_active_events())
            
            try:
                await monitor_task
            except KeyboardInterrupt:
                logger.info("Shutting down...")
                monitor_task.cancel()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        await orchestrator.close()
        logger.info("Launch sniper stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

