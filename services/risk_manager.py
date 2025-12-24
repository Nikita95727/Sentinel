"""Risk management service for position sizing and stop-loss/take-profit calculation."""

from typing import Dict, Optional, Set
from loguru import logger


class RiskManager:
    """Risk management calculations for trading."""

    # Blacklist of low-liquidity memecoins to avoid
    BLACKLIST: Set[str] = {
        'SHIB/USDT',
        'PEPE/USDT',
        'FLOKI/USDT',
        'BABYDOGE/USDT',
        # Add more as needed
    }

    def __init__(
        self,
        balance: float = 10.0,
        stop_loss_pct: float = 2.0,
        min_risk_reward: float = 1.5
    ):
        """
        Initialize risk manager.
        
        Args:
            balance: Account balance in USDT (default: $10)
            stop_loss_pct: Stop-loss percentage (default: 2%)
            min_risk_reward: Minimum risk/reward ratio (default: 1.5)
        """
        self.balance = balance
        self.stop_loss_pct = stop_loss_pct
        self.min_risk_reward = min_risk_reward

    def is_symbol_allowed(self, symbol: str) -> bool:
        """
        Check if symbol is not in blacklist.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if symbol is allowed for trading
        """
        is_allowed = symbol not in self.BLACKLIST
        
        if not is_allowed:
            logger.warning(f"Symbol {symbol} is blacklisted")
        
        return is_allowed

    def calculate_position_size(
        self,
        entry_price: float,
        stop_loss_price: Optional[float] = None,
        volatility: Optional[float] = None,
        confidence: Optional[float] = None,
        max_risk_pct: Optional[float] = None
    ) -> float:
        """
        Calculate position size dynamically based on volatility and AI confidence.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop-loss price (if None, will be calculated)
            volatility: ATR as percentage of price (for dynamic sizing)
            confidence: AI confidence score (0-1, for dynamic sizing)
            max_risk_pct: Maximum risk percentage (overrides default)
            
        Returns:
            Position size in base currency
        """
        try:
            if entry_price <= 0:
                logger.error("Invalid entry price")
                return 0.0
            
            # Use provided max_risk_pct or default
            risk_pct = max_risk_pct if max_risk_pct is not None else self.stop_loss_pct
            
            # Calculate stop-loss price if not provided
            if stop_loss_price is None:
                stop_loss_price = self.calculate_stop_loss(entry_price, volatility)
            
            # Base risk amount
            risk_amount = self.balance * (risk_pct / 100)
            
            # Dynamic adjustments
            volatility_factor = 1.0
            confidence_factor = 1.0
            
            # Adjust for volatility: high volatility = smaller position
            if volatility is not None and volatility > 0:
                # Normalize volatility (assume 1-10% is normal range)
                # High volatility (>5%) reduces position size
                volatility_factor = 1.0 / (1.0 + (volatility / 5.0))
                logger.debug(f"Volatility factor: {volatility_factor:.2f} (volatility: {volatility:.2f}%)")
            
            # Adjust for AI confidence: low confidence = smaller position
            if confidence is not None:
                # confidence 0.5 = 50% size, 1.0 = 100% size
                confidence_factor = max(0.5, min(1.0, confidence / 100.0))
                logger.debug(f"Confidence factor: {confidence_factor:.2f} (confidence: {confidence:.1f}%)")
            
            # Calculate price distance to stop-loss
            price_distance = abs(entry_price - stop_loss_price)
            
            if price_distance == 0:
                logger.error("Stop-loss price equals entry price")
                return 0.0
            
            # Base position size
            base_position_size = risk_amount / price_distance
            
            # Apply dynamic factors
            adjusted_position_size = base_position_size * volatility_factor * confidence_factor
            
            # For spot, we can use up to balance / entry_price
            max_position_size = self.balance / entry_price
            
            # Take the minimum to ensure we don't exceed balance
            final_position_size = min(adjusted_position_size, max_position_size)
            
            # Minimum position size ($5 worth)
            min_position_usd = 5.0
            min_position_size = min_position_usd / entry_price
            final_position_size = max(final_position_size, min_position_size)
            
            logger.info(
                f"Position size calculated: {final_position_size:.6f} "
                f"(entry=${entry_price:.2f}, SL=${stop_loss_price:.2f}, "
                f"risk=${risk_amount:.2f}, vol_factor={volatility_factor:.2f}, "
                f"conf_factor={confidence_factor:.2f})"
            )
            
            return final_position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def calculate_stop_loss(
        self, 
        entry_price: float,
        volatility: Optional[float] = None,
        side: str = 'buy'
    ) -> float:
        """
        Calculate stop-loss dynamically based on ATR (volatility).
        
        Args:
            entry_price: Entry price for the trade
            volatility: ATR as percentage of price (if None, uses fixed %)
            side: Trade side ('buy' or 'sell')
            
        Returns:
            Stop-loss price
        """
        if volatility is not None and volatility > 0:
            # Dynamic stop-loss: 2x ATR from entry
            atr_multiplier = 2.0
            stop_distance = volatility * atr_multiplier
            
            if side == 'buy':
                stop_loss = entry_price * (1 - stop_distance / 100)
            else:  # sell
                stop_loss = entry_price * (1 + stop_distance / 100)
            
            logger.debug(
                f"Dynamic stop-loss: ${stop_loss:.2f} "
                f"({stop_distance:.2f}% from ${entry_price:.2f}, "
                f"ATR={volatility:.2f}%, multiplier={atr_multiplier}x)"
            )
        else:
            # Fallback to fixed percentage
            if side == 'buy':
                stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
            else:  # sell
                stop_loss = entry_price * (1 + self.stop_loss_pct / 100)
            
            logger.debug(
                f"Fixed stop-loss: ${stop_loss:.2f} "
                f"({self.stop_loss_pct}% from ${entry_price:.2f})"
            )
        
        return stop_loss

    def calculate_take_profit(
        self,
        entry_price: float,
        stop_loss_price: Optional[float] = None
    ) -> float:
        """
        Calculate take-profit price based on risk/reward ratio.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop-loss price (if None, will be calculated)
            
        Returns:
            Take-profit price (minimum 1.5x risk)
        """
        if stop_loss_price is None:
            stop_loss_price = self.calculate_stop_loss(entry_price)
        
        # Calculate risk (distance from entry to stop-loss)
        risk = entry_price - stop_loss_price
        
        # Take-profit = entry + (risk * risk_reward_ratio)
        take_profit = entry_price + (risk * self.min_risk_reward)
        
        logger.debug(
            f"Take-profit calculated: ${take_profit:.2f} "
            f"(R:R = 1:{self.min_risk_reward}, risk=${risk:.2f})"
        )
        
        return take_profit

    def validate_trade(
        self,
        symbol: str,
        entry_price: float,
        position_size: float
    ) -> Dict[str, any]:
        """
        Validate if a trade meets all risk management criteria.
        
        Args:
            symbol: Trading pair symbol
            entry_price: Proposed entry price
            position_size: Proposed position size
            
        Returns:
            Dictionary with validation result and details
        """
        validation = {
            'is_valid': True,
            'reasons': []
        }
        
        logger.debug(f"Risk validation for {symbol}:")
        logger.debug(f"  Entry price: ${entry_price:.2f}")
        logger.debug(f"  Position size: {position_size:.6f}")
        logger.debug(f"  Balance: ${self.balance:.2f}")
        
        # Check blacklist
        if not self.is_symbol_allowed(symbol):
            validation['is_valid'] = False
            reason = f"Symbol {symbol} is blacklisted"
            validation['reasons'].append(reason)
            logger.warning(f"  ❌ {reason}")
        else:
            logger.debug(f"  ✅ Symbol not blacklisted")
        
        # Check entry price
        if entry_price <= 0:
            validation['is_valid'] = False
            reason = "Invalid entry price"
            validation['reasons'].append(reason)
            logger.warning(f"  ❌ {reason}")
        else:
            logger.debug(f"  ✅ Entry price valid")
        
        # Check position size
        if position_size <= 0:
            validation['is_valid'] = False
            reason = "Invalid position size"
            validation['reasons'].append(reason)
            logger.warning(f"  ❌ {reason}")
        else:
            logger.debug(f"  ✅ Position size valid")
        
        # Check if position size exceeds balance
        trade_value = entry_price * position_size
        logger.debug(f"  Trade value: ${trade_value:.2f}")
        if trade_value > self.balance:
            validation['is_valid'] = False
            reason = f"Trade value ${trade_value:.2f} exceeds balance ${self.balance:.2f}"
            validation['reasons'].append(reason)
            logger.warning(f"  ❌ {reason}")
        else:
            logger.debug(f"  ✅ Trade value within balance")
        
        if validation['is_valid']:
            logger.info(f"Trade validation passed for {symbol}")
        else:
            logger.warning(
                f"Trade validation failed for {symbol}: {', '.join(validation['reasons'])}"
            )
        
        return validation

    def get_trade_params(
        self, 
        entry_price: float,
        volatility: Optional[float] = None,
        confidence: Optional[float] = None,
        side: str = 'buy'
    ) -> Dict[str, float]:
        """
        Get complete trade parameters with dynamic calculations.
        
        Args:
            entry_price: Entry price for the trade
            volatility: ATR as percentage of price
            confidence: AI confidence score (0-100)
            side: Trade side ('buy' or 'sell')
            
        Returns:
            Dictionary with all trade parameters
        """
        stop_loss = self.calculate_stop_loss(entry_price, volatility, side)
        take_profit = self.calculate_take_profit(entry_price, stop_loss, side)
        position_size = self.calculate_position_size(
            entry_price, 
            stop_loss, 
            volatility, 
            confidence
        )
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'risk_pct': self.stop_loss_pct,
            'risk_reward_ratio': self.min_risk_reward,
            'volatility': volatility,
            'confidence': confidence
        }
