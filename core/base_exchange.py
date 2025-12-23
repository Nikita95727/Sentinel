"""Base abstract class for exchange providers."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime


class BaseExchange(ABC):
    """Abstract base class defining the exchange interface."""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize the exchange connection."""
        pass

    @abstractmethod
    async def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "30m",
        limit: int = 100
    ) -> List[List[Any]]:
        """
        Fetch OHLCV (candlestick) data.
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            timeframe: Candle timeframe (e.g., '30m')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV data: [[timestamp, open, high, low, close, volume], ...]
        """
        pass

    @abstractmethod
    async def get_balance(self, currency: str = "USDT") -> float:
        """
        Get account balance for a specific currency.
        
        Args:
            currency: Currency code (e.g., 'USDT')
            
        Returns:
            Available balance
        """
        pass

    @abstractmethod
    async def create_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a market order.
        
        Args:
            symbol: Trading pair symbol
            side: 'buy' or 'sell'
            amount: Order amount in base currency
            params: Additional order parameters
            
        Returns:
            Order information
        """
        pass

    @abstractmethod
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open orders
        """
        pass

    @abstractmethod
    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            Cancellation result
        """
        pass

    @abstractmethod
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker data.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker data including current price
        """
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the exchange connection."""
        pass
