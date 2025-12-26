"""
Phase A: Discovery - Find new listing announcements from Bybit.
"""
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Set, Dict
import ccxt.async_support as ccxt

from loguru import logger
import httpx
from modules.launch_sniper.core.events import LaunchEvent
from modules.launch_sniper.config import LaunchSniperConfig


class DiscoveryService:
    """Service for discovering new listing events."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
        self.exchange: Optional[ccxt.bybit] = None
        self.known_pairs_file = self.config.STORAGE_DIR / "known_pairs.json"
        self.known_pairs: Set[str] = set()
    
    async def initialize(self):
        """Initialize exchange connection."""
        logger.info("Initializing DiscoveryService...")
        logger.info(f"  - Testnet: {self.config.BYBIT_TESTNET}")
        logger.info(f"  - API Key: {'*' * 10 if self.config.BYBIT_API_KEY else 'NOT SET'}")
        
        try:
            logger.info("  - Creating ccxt.bybit instance...")
            self.exchange = ccxt.bybit({
                'apiKey': self.config.BYBIT_API_KEY,
                'secret': self.config.BYBIT_API_SECRET,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'test': self.config.BYBIT_TESTNET
                }
            })
            logger.info("  ✅ ccxt.bybit instance created")
            
            # Test connection
            logger.info("  - Testing connection...")
            await self.exchange.load_markets()
            logger.info("  ✅ Connection test successful")
            
            # Load known pairs
            await self._load_known_pairs()
            
            logger.info("✅ Discovery service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Failed to initialize discovery service: {e}", exc_info=True)
            raise
    
    async def _load_known_pairs(self):
        """Load previously known trading pairs from storage."""
        try:
            if self.known_pairs_file.exists():
                with open(self.known_pairs_file, 'r') as f:
                    data = json.load(f)
                    self.known_pairs = set(data.get('pairs', []))
                    logger.info(f"  ✅ Loaded {len(self.known_pairs)} known pairs from storage")
            else:
                logger.info("  ℹ️  No known pairs file found (first run)")
                self.known_pairs = set()
        except Exception as e:
            logger.warning(f"  ⚠️  Failed to load known pairs: {e}")
            self.known_pairs = set()
    
    async def _save_known_pairs(self, pairs: Set[str]):
        """Save known trading pairs to storage."""
        try:
            self.known_pairs_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.known_pairs_file, 'w') as f:
                json.dump({
                    'pairs': sorted(list(pairs)),
                    'last_updated': datetime.utcnow().isoformat()
                }, f, indent=2)
            logger.debug(f"Saved {len(pairs)} known pairs to storage")
        except Exception as e:
            logger.warning(f"Failed to save known pairs: {e}")
    
    async def discover_listings(self) -> List[LaunchEvent]:
        """
        Discover new listing announcements by detecting new trading pairs.
        
        Returns:
            List of LaunchEvent objects
        """
        logger.info("=" * 80)
        logger.info("DISCOVERY PHASE - Starting listing discovery")
        logger.info("=" * 80)
        
        if not self.exchange:
            logger.info("Exchange not initialized, initializing now...")
            await self.initialize()
        
        events = []
        
        try:
            logger.info("Step 1: Loading markets from Bybit...")
            markets = await self.exchange.load_markets(reload=True)
            logger.info(f"✅ Loaded {len(markets)} markets from Bybit")
            
            # Filter spot markets only
            spot_markets = {
                symbol: market 
                for symbol, market in markets.items() 
                if market.get('type') == 'spot' and market.get('active', True)
            }
            logger.info(f"  - Found {len(spot_markets)} active spot markets")
            
            # Get current trading pairs
            current_pairs = set(spot_markets.keys())
            logger.info(f"  - Current pairs: {len(current_pairs)}")
            logger.info(f"  - Known pairs: {len(self.known_pairs)}")
            
            # If this is first run (no known pairs), save all current pairs as known
            if len(self.known_pairs) == 0:
                logger.info("  ℹ️  First run detected - saving all current pairs as known")
                self.known_pairs = current_pairs.copy()
                await self._save_known_pairs(self.known_pairs)
                logger.info(f"  ✅ Saved {len(self.known_pairs)} pairs as baseline")
                # Don't treat existing pairs as new listings on first run
                new_pairs = set()
            else:
                # Find new pairs (only those not in known list)
                new_pairs = current_pairs - self.known_pairs
            
            if new_pairs:
                logger.info(f"Step 2: Found {len(new_pairs)} new trading pairs!")
                for pair in sorted(new_pairs):
                    logger.info(f"  🆕 New pair: {pair}")
                    
                    # Get market info
                    market = spot_markets.get(pair, {})
                    market_info = market.get('info', {})
                    
                    # Try to get listing time from market data
                    # Bybit markets have 'created' timestamp or we can use current time
                    listing_time = datetime.utcnow()
                    
                    # Try to parse creation time if available
                    if 'created' in market_info:
                        try:
                            # Bybit timestamp might be in milliseconds
                            timestamp = int(market_info['created'])
                            if timestamp > 1e10:  # milliseconds
                                timestamp = timestamp / 1000
                            listing_time = datetime.utcnow().fromtimestamp(timestamp)
                        except:
                            pass
                    
                    # Check if listing is within our window
                    time_until_listing = (listing_time - datetime.utcnow()).total_seconds() / 3600
                    
                    # If pair was just created (within last hour), treat as new listing
                    if time_until_listing >= -1 and time_until_listing <= self.config.LISTING_WINDOW_HOURS:
                        event = LaunchEvent(
                            symbol=pair.split('/')[0],  # Base currency
                            trading_pair=pair,
                            listing_time=listing_time,
                            source="bybit",
                            metadata={
                                'market_info': market_info,
                                'discovered_at': datetime.utcnow().isoformat(),
                                'market_data': {
                                    'base': market.get('base'),
                                    'quote': market.get('quote'),
                                    'active': market.get('active', True),
                                    'precision': market.get('precision', {}),
                                    'limits': market.get('limits', {})
                                }
                            }
                        )
                        events.append(event)
                        logger.info(f"  ✅ Created LaunchEvent for {pair} (listing time: {listing_time})")
                    else:
                        logger.debug(f"  ⏭️  Skipping {pair} (outside window: {time_until_listing:.1f}h)")
            else:
                logger.info("Step 2: No new trading pairs found")
                logger.info("  ℹ️  All current pairs are already known")
            
            # Update known pairs
            if new_pairs:
                self.known_pairs.update(new_pairs)
                await self._save_known_pairs(self.known_pairs)
                logger.info(f"  ✅ Updated known pairs list ({len(self.known_pairs)} total)")
            
            # Also try to get upcoming listings via Bybit API v5
            # Only if we have known pairs (not first run)
            if len(self.known_pairs) > 0:
                logger.info("Step 3: Checking Bybit API v5 for upcoming listings...")
                try:
                    upcoming_events = await self._fetch_upcoming_listings(current_pairs)
                    if upcoming_events:
                        logger.info(f"  ✅ Found {len(upcoming_events)} upcoming listings from API")
                        events.extend(upcoming_events)
                    else:
                        logger.info("  ℹ️  No upcoming listings found in API")
                except Exception as e:
                    logger.warning(f"  ⚠️  Failed to fetch upcoming listings from API: {e}")
            else:
                logger.info("Step 3: Skipping API check (first run - baseline established)")
            
        except Exception as e:
            logger.error(f"❌ Error during discovery: {e}", exc_info=True)
        
        logger.info(f"Discovery complete: {len(events)} events found")
        logger.info("=" * 80)
        return events
    
    async def _fetch_upcoming_listings(self, current_pairs: Set[str]) -> List[LaunchEvent]:
        """
        Fetch upcoming listings from Bybit API v5.
        
        Returns:
            List of LaunchEvent objects for upcoming listings
        """
        events = []
        
        try:
            # Bybit API v5 endpoint for instruments
            # We'll use the exchange's request method to call Bybit REST API directly
            if not self.exchange:
                return events
            
            # Try to get instruments list with filter for new listings
            # Bybit API v5: GET /v5/market/instruments-info
            base_url = "https://api-testnet.bybit.com" if self.config.BYBIT_TESTNET else "https://api.bybit.com"
            
            import httpx
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Get instruments info
                url = f"{base_url}/v5/market/instruments-info"
                params = {
                    'category': 'spot',
                    'status': 'Trading'  # Only active trading pairs
                }
                
                response = await client.get(url, params=params)
                response.raise_for_status()
                data = response.json()
                
                if data.get('retCode') == 0:
                    result = data.get('result', {})
                    instruments = result.get('list', [])
                    
                    logger.info(f"  - Fetched {len(instruments)} instruments from Bybit API")
                    
                    # Check each instrument for recent listing
                    for instrument in instruments:
                        symbol = instrument.get('symbol', '')
                        if not symbol:
                            continue
                        
                        # Get quote currency from instrument
                        quote_currency = instrument.get('quoteCoin', 'USDT')
                        pair = f"{symbol}/{quote_currency}"
                        
                        # Only check pairs that are not in known list
                        if pair not in self.known_pairs and pair in current_pairs:
                            # Get listing time from instrument data
                            listing_time = datetime.utcnow()
                            
                            # Check if instrument has launch time
                            if 'launchTime' in instrument:
                                try:
                                    launch_timestamp = int(instrument['launchTime'])
                                    if launch_timestamp > 1e10:
                                        launch_timestamp = launch_timestamp / 1000
                                    listing_time = datetime.utcnow().fromtimestamp(launch_timestamp)
                                except:
                                    pass
                            
                            # Check if within window and is actually new
                            time_until = (listing_time - datetime.utcnow()).total_seconds() / 3600
                            if -1 <= time_until <= self.config.LISTING_WINDOW_HOURS:
                                # Only add if pair is not in known pairs (truly new)
                                if pair not in self.known_pairs:
                                    event = LaunchEvent(
                                        symbol=symbol,
                                        trading_pair=pair,
                                        listing_time=listing_time,
                                        source="bybit_api_v5",
                                        metadata={
                                            'instrument': instrument,
                                            'discovered_at': datetime.utcnow().isoformat()
                                        }
                                    )
                                    events.append(event)
                                    logger.info(f"  ✅ Found upcoming listing: {pair} at {listing_time}")
                                else:
                                    logger.debug(f"  ⏭️  Skipping {pair} (already known)")
                
        except httpx.HTTPError as e:
            logger.debug(f"HTTP error fetching upcoming listings: {e}")
        except Exception as e:
            logger.debug(f"Error fetching upcoming listings: {e}")
        
        return events
    
    async def get_market_info(self, symbol: str) -> Optional[Dict]:
        """
        Get market information for a symbol.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            Market information dict or None
        """
        if not self.exchange:
            await self.initialize()
        
        try:
            markets = await self.exchange.load_markets()
            market = markets.get(symbol)
            if market:
                return {
                    'symbol': symbol,
                    'base': market.get('base'),
                    'quote': market.get('quote'),
                    'active': market.get('active', True),
                    'precision': market.get('precision', {}),
                    'limits': market.get('limits', {}),
                    'info': market.get('info', {})
                }
        except Exception as e:
            logger.error(f"Error getting market info for {symbol}: {e}")
        
        return None
    
    async def parse_listing_announcement(self, announcement: dict) -> Optional[LaunchEvent]:
        """
        Parse a listing announcement into LaunchEvent.
        
        Args:
            announcement: Raw announcement data
            
        Returns:
            LaunchEvent or None if invalid
        """
        try:
            # Parse announcement structure (depends on Bybit format)
            # This is a placeholder - adjust based on actual Bybit API response
            
            symbol = announcement.get('symbol', '')
            trading_pair = announcement.get('trading_pair', symbol)
            listing_time_str = announcement.get('listing_time', '')
            
            # Parse listing time
            try:
                listing_time = datetime.fromisoformat(listing_time_str.replace('Z', '+00:00'))
            except:
                listing_time = datetime.utcnow() + timedelta(hours=24)  # Default: 24h from now
            
            # Check if within window
            time_until_listing = (listing_time - datetime.utcnow()).total_seconds() / 3600
            if time_until_listing > self.config.LISTING_WINDOW_HOURS:
                logger.debug(f"Listing too far in future: {time_until_listing:.1f}h")
                return None
            
            if time_until_listing < 0:
                logger.debug(f"Listing already started: {listing_time}")
                return None
            
            event = LaunchEvent(
                symbol=symbol,
                trading_pair=trading_pair,
                listing_time=listing_time,
                source="bybit",
                metadata=announcement
            )
            
            logger.info(f"Discovered launch event: {event.symbol} at {listing_time}")
            return event
            
        except Exception as e:
            logger.error(f"Error parsing announcement: {e}")
            return None
    
    async def close(self):
        """Close exchange connection."""
        if self.exchange:
            await self.exchange.close()
            self.exchange = None

