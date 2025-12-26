"""
Phase C: Deterministic Validation Layer - Mathematical filters and sanity checks.
"""
import logging
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

from modules.launch_sniper.core.events import LaunchEvent, AIDecision, ValidationResult
from modules.launch_sniper.config import LaunchSniperConfig

logger = logging.getLogger(__name__)


class ValidationService:
    """Deterministic validation service."""
    
    def __init__(self):
        self.config = LaunchSniperConfig
    
    async def validate_launch(
        self,
        event: LaunchEvent,
        ai_decision: Optional[AIDecision] = None,
        market_data: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate launch event using deterministic rules.
        
        IMPORTANT: This is the ONLY place where GO/ABORT decision is made.
        AI decision is NOT used for validation - only for context.
        
        Args:
            event: Launch event
            ai_decision: AI decision (for context only, not used in validation)
            market_data: Market data (prices, FDV, etc.)
            
        Returns:
            ValidationResult with GO or ABORT_REASON_*
        """
        validated_facts = {}
        abort_reasons = []
        
        # Fact 1: Check listing time
        time_until_listing = (event.listing_time - datetime.utcnow()).total_seconds() / 3600
        validated_facts['time_until_listing_hours'] = time_until_listing
        
        if time_until_listing < 0:
            abort_reasons.append("ABORT_REASON_LISTING_STARTED")
        
        if time_until_listing > self.config.LISTING_WINDOW_HOURS:
            abort_reasons.append("ABORT_REASON_TOO_FAR_FUTURE")
        
        # Fact 2: Check budget
        budget = self.config.MIN_BUDGET_USDT
        validated_facts['budget_usdt'] = budget
        
        if budget < self.config.MIN_BUDGET_USDT:
            abort_reasons.append("ABORT_REASON_INSUFFICIENT_BUDGET")
        
        if budget > self.config.MAX_BUDGET_USDT:
            abort_reasons.append("ABORT_REASON_BUDGET_EXCEEDED")
        
        # Fact 3: Check market data availability
        if market_data:
            # Extract reference price if available
            p_ref = market_data.get('reference_price', 0.0)
            validated_facts['p_ref'] = p_ref
            validated_facts['market_data_available'] = True
            
            # Check price limits (if Bybit provides)
            min_price = market_data.get('min_price', 0.0)
            max_price = market_data.get('max_price', float('inf'))
            validated_facts['price_limits'] = {'min': min_price, 'max': max_price}
            
            if p_ref <= 0:
                abort_reasons.append("ABORT_REASON_INVALID_PRICE")
            
            if p_ref < min_price or p_ref > max_price:
                abort_reasons.append("ABORT_REASON_PRICE_OUT_OF_LIMITS")
            
            # Check liquidity estimate
            estimated_liquidity = market_data.get('estimated_liquidity_usdt', 0.0)
            validated_facts['estimated_liquidity_usdt'] = estimated_liquidity
            
            if estimated_liquidity < self.config.MIN_LIQUIDITY_USDT:
                abort_reasons.append("ABORT_REASON_INSUFFICIENT_LIQUIDITY")
        else:
            validated_facts['market_data_available'] = False
            # If no market data, we can't validate properly
            # But we might still proceed if other checks pass
            p_ref = 0.0
        
        # Fact 4: Calculate price ladder
        price_ladder = self._calculate_price_ladder(p_ref)
        validated_facts['price_ladder'] = price_ladder
        
        # Fact 5: Check feasibility
        if p_ref > 0:
            # Check if we can afford entry
            min_entry_price = min(price_ladder) if price_ladder else p_ref
            max_position_size = budget / min_entry_price if min_entry_price > 0 else 0
            validated_facts['max_position_size'] = max_position_size
            
            if max_position_size < 0.001:  # Minimum tradeable size
                abort_reasons.append("ABORT_REASON_POSITION_TOO_SMALL")
        
        # Final decision
        if abort_reasons:
            decision = abort_reasons[0]  # First abort reason
        else:
            decision = "GO"
        
        result = ValidationResult(
            event_id=event.event_id,
            decision=decision,
            p_ref=p_ref,
            price_ladder=price_ladder,
            validated_facts=validated_facts
        )
        
        logger.info(f"Validation for {event.symbol}: {decision}")
        if abort_reasons:
            logger.info(f"Abort reasons: {', '.join(abort_reasons)}")
        
        return result
    
    def _calculate_price_ladder(self, p_ref: float) -> list:
        """
        Calculate price ladder for entry orders.
        
        Returns:
            List of prices: [optimistic, realistic, pessimistic]
        """
        if p_ref <= 0:
            return []
        
        # Optimistic: p_ref * 1.02 (2% above)
        # Realistic: p_ref (at reference)
        # Pessimistic: p_ref * 0.98 (2% below)
        
        optimistic = p_ref * 1.02
        realistic = p_ref
        pessimistic = p_ref * 0.98
        
        return [optimistic, realistic, pessimistic]
    
    def check_circuit_breaker(
        self,
        current_spread_pct: float,
        initial_liquidity: float,
        current_liquidity: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check circuit breaker conditions.
        
        Returns:
            (should_abort, reason)
        """
        # Spread circuit breaker
        if current_spread_pct > self.config.CIRCUIT_BREAKER_SPREAD_PCT:
            return True, "CIRCUIT_BREAKER_SPREAD"
        
        # Liquidity circuit breaker
        if initial_liquidity > 0:
            liquidity_drop_pct = (initial_liquidity - current_liquidity) / initial_liquidity
            if liquidity_drop_pct > self.config.CIRCUIT_BREAKER_LIQUIDITY_DROP_PCT:
                return True, "CIRCUIT_BREAKER_LIQUIDITY"
        
        return False, None

