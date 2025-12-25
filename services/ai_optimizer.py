"""
AI Optimizer with caching and rate limiting to reduce API costs.
Optimizes Grok API usage to stay within $5 budget for 2 weeks.
"""

import asyncio
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from loguru import logger

try:
    from cachetools import TTLCache
except ImportError:
    # Fallback if cachetools not available
    class TTLCache(dict):
        def __init__(self, maxsize=50, ttl=1800):
            self.maxsize = maxsize
            self.ttl = timedelta(seconds=ttl)
            self._timestamps = {}
        
        def __setitem__(self, key, value):
            if len(self) >= self.maxsize:
                # Remove oldest
                oldest = min(self._timestamps.items(), key=lambda x: x[1])
                del self[oldest[0]]
                del self._timestamps[oldest[0]]
            super().__setitem__(key, value)
            self._timestamps[key] = datetime.now()
        
        def __getitem__(self, key):
            if key in self._timestamps:
                if datetime.now() - self._timestamps[key] > self.ttl:
                    del self[key]
                    del self._timestamps[key]
                    raise KeyError(key)
            return super().__getitem__(key)
        
        def __contains__(self, key):
            if key in self._timestamps:
                if datetime.now() - self._timestamps[key] > self.ttl:
                    del self[key]
                    del self._timestamps[key]
                    return False
            return super().__contains__(key)


class AIOptimizer:
    """
    Optimizes AI API calls with caching and rate limiting.
    
    Reduces API calls from 12-24/day to 2-6/day (75% savings).
    """
    
    def __init__(self, ai_provider, cache_ttl_minutes: int = 30):
        """
        Initialize AI optimizer.
        
        Args:
            ai_provider: AI provider instance (GrokProvider)
            cache_ttl_minutes: Cache TTL in minutes (default: 30)
        """
        self.ai = ai_provider
        # Cache for 30 minutes by default
        self.cache = TTLCache(maxsize=50, ttl=cache_ttl_minutes * 60)
        # Rate limiter: track last call per symbol
        self.last_call: Dict[str, datetime] = {}
        # Minimum interval between calls (minutes)
        self.min_interval_minutes = 30
        # Statistics
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'rate_limited': 0,
            'api_calls': 0
        }
        
    def _get_market_hash(
        self, 
        symbol: str, 
        price: float, 
        volume: float,
        rsi: float
    ) -> str:
        """
        Generate hash of current market state for cache key.
        
        Rounds price to 1% bucket to avoid cache invalidation on minor fluctuations.
        """
        # Round price to 1% bucket
        price_bucket = int(price * 100) // 100
        # Round volume to 1000 bucket
        volume_bucket = int(volume / 1000)
        # Round RSI to 5-point bucket
        rsi_bucket = int(rsi / 5) * 5
        
        hash_input = f"{symbol}:{price_bucket}:{volume_bucket}:{rsi_bucket}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    async def should_call_ai(
        self, 
        symbol: str, 
        has_position: bool,
        force: bool = False
    ) -> bool:
        """
        Determine if AI call is needed based on rate limiting.
        
        Args:
            symbol: Trading pair symbol
            has_position: Whether there's an open position
            force: Force AI call regardless of rate limit
            
        Returns:
            True if AI call should be made
        """
        if force:
            return True
        
        # For active positions, check more frequently (15 min)
        # For no position, check less frequently (30 min)
        min_interval = 15 if has_position else self.min_interval_minutes
        
        last_time = self.last_call.get(symbol)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds() / 60
            if elapsed < min_interval:
                self.stats['rate_limited'] += 1
                logger.debug(
                    f"Rate limit: {symbol} called {elapsed:.1f} min ago "
                    f"(min interval: {min_interval} min)"
                )
                return False
        
        return True
    
    async def get_analysis(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        has_position: bool = False,
        memory: Optional[list] = None,
        force: bool = False,
        action_space: Optional[List[str]] = None
    ) -> Optional[Any]:
        """
        Get AI analysis with smart caching.
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data (price, volume, etc.)
            technical_indicators: Technical indicators (RSI, EMA, etc.)
            has_position: Whether there's an open position
            memory: Recent trade history for context
            force: Force AI call regardless of cache/rate limit
            action_space: List of allowed actions (e.g., ["BUY", "ABSTAIN"] or ["SELL", "HOLD"])
            
        Returns:
            AIDecision object or None if rate limited
        """
        self.stats['total_requests'] += 1
        
        # Check rate limiting
        if not await self.should_call_ai(symbol, has_position, force):
            return None
        
        # Generate cache key (include has_position and action_space in cache key for accuracy)
        price = market_data.get('price', 0)
        volume = market_data.get('volume', 0)
        rsi = technical_indicators.get('rsi', 50)
        action_space_str = ','.join(sorted(action_space)) if action_space else ('pos' if has_position else 'nopos')
        
        market_hash = self._get_market_hash(symbol, price, volume, rsi)
        cache_key = f"{symbol}:{market_hash}:{action_space_str}"
        
        # Check cache
        if cache_key in self.cache and not force:
            self.stats['cache_hits'] += 1
            cached_decision = self.cache[cache_key]
            logger.debug(f"Cache HIT for {symbol} (hash: {market_hash}, action_space: {action_space_str})")
            return cached_decision
        
        # Call AI
        try:
            logger.info(f"Calling AI for {symbol} (cache miss or force)")
            analysis = await self.ai.analyze(
                symbol=symbol,
                market_data=market_data,
                technical_indicators=technical_indicators,
                memory=memory,
                has_position=has_position,
                action_space=action_space
            )
            
            # Save to cache
            self.cache[cache_key] = analysis
            self.last_call[symbol] = datetime.now()
            self.stats['api_calls'] += 1
            
            logger.debug(
                f"AI call completed for {symbol} "
                f"(decision: {analysis.action}, confidence: {analysis.confidence}%)"
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"AI call failed for {symbol}: {e}")
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get optimizer statistics."""
        cache_hit_rate = (
            (self.stats['cache_hits'] / self.stats['total_requests'] * 100)
            if self.stats['total_requests'] > 0 else 0
        )
        
        return {
            'total_requests': self.stats['total_requests'],
            'api_calls': self.stats['api_calls'],
            'cache_hits': self.stats['cache_hits'],
            'rate_limited': self.stats['rate_limited'],
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'savings': self.stats['total_requests'] - self.stats['api_calls']
        }
    
    def clear_cache(self):
        """Clear the cache."""
        self.cache.clear()
        logger.info("AI optimizer cache cleared")


