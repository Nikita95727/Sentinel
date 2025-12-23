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
        stop_loss_price: Optional[float] = None
    ) -> float:
        """
        Calculate position size based on balance and risk.
        
        Args:
            entry_price: Entry price for the trade
            stop_loss_price: Stop-loss price (if None, will be calculated)
            
        Returns:
            Position size in base currency
        """
        try:
            if entry_price <= 0:
                logger.error("Invalid entry price")
                return 0.0
            
            # Calculate stop-loss price if not provided
            if stop_loss_price is None:
                stop_loss_price = self.calculate_stop_loss(entry_price)
            
            # Calculate risk per trade (in USDT)
            # Using 100% of balance for spot trading (no leverage)
            # The actual risk is determined by stop-loss distance
            risk_amount = self.balance * (self.stop_loss_pct / 100)
            
            # Calculate price distance to stop-loss
            price_distance = abs(entry_price - stop_loss_price)
            
            if price_distance == 0:
                logger.error("Stop-loss price equals entry price")
                return 0.0
            
            # Position size = risk amount / price distance
            position_size = risk_amount / price_distance
            
            # For spot, we can use up to balance / entry_price
            max_position_size = self.balance / entry_price
            
            # Take the minimum to ensure we don't exceed balance
            final_position_size = min(position_size, max_position_size)
            
            logger.info(
                f"Position size calculated: {final_position_size:.6f} "
                f"(entry=${entry_price:.2f}, SL=${stop_loss_price:.2f}, "
                f"risk=${risk_amount:.2f})"
            )
            
            return final_position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0.0

    def calculate_stop_loss(self, entry_price: float) -> float:
        """
        Calculate stop-loss price based on entry and percentage.
        
        Args:
            entry_price: Entry price for the trade
            
        Returns:
            Stop-loss price (2% below entry for long positions)
        """
        stop_loss = entry_price * (1 - self.stop_loss_pct / 100)
        logger.debug(f"Stop-loss calculated: ${stop_loss:.2f} ({self.stop_loss_pct}% below ${entry_price:.2f})")
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
        
        # Check blacklist
        if not self.is_symbol_allowed(symbol):
            validation['is_valid'] = False
            validation['reasons'].append(f"Symbol {symbol} is blacklisted")
        
        # Check entry price
        if entry_price <= 0:
            validation['is_valid'] = False
            validation['reasons'].append("Invalid entry price")
        
        # Check position size
        if position_size <= 0:
            validation['is_valid'] = False
            validation['reasons'].append("Invalid position size")
        
        # Check if position size exceeds balance
        trade_value = entry_price * position_size
        if trade_value > self.balance:
            validation['is_valid'] = False
            validation['reasons'].append(
                f"Trade value ${trade_value:.2f} exceeds balance ${self.balance:.2f}"
            )
        
        if validation['is_valid']:
            logger.info(f"Trade validation passed for {symbol}")
        else:
            logger.warning(
                f"Trade validation failed for {symbol}: {', '.join(validation['reasons'])}"
            )
        
        return validation

    def get_trade_params(self, entry_price: float) -> Dict[str, float]:
        """
        Get complete trade parameters (position size, SL, TP).
        
        Args:
            entry_price: Entry price for the trade
            
        Returns:
            Dictionary with all trade parameters
        """
        stop_loss = self.calculate_stop_loss(entry_price)
        take_profit = self.calculate_take_profit(entry_price, stop_loss)
        position_size = self.calculate_position_size(entry_price, stop_loss)
        
        return {
            'entry_price': entry_price,
            'stop_loss': stop_loss,
            'take_profit': take_profit,
            'position_size': position_size,
            'risk_pct': self.stop_loss_pct,
            'risk_reward_ratio': self.min_risk_reward
        }
