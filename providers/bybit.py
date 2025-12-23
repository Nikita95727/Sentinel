"""Bybit exchange provider using ccxt.pro."""

import ccxt.pro as ccxtpro
from typing import Dict, List, Optional, Any
from loguru import logger

from core.base_exchange import BaseExchange


class BybitProvider(BaseExchange):
    """Bybit exchange implementation using ccxt.pro for async operations."""

    def __init__(self, api_key: str, api_secret: str, testnet: bool = False):
        """
        Initialize Bybit provider.
        
        Args:
            api_key: Bybit API key
            api_secret: Bybit API secret
            testnet: Use testnet instead of mainnet
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        self.exchange: Optional[ccxtpro.bybit] = None
        
    async def initialize(self) -> None:
        """Initialize the exchange connection."""
        try:
            self.exchange = ccxtpro.bybit({
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'testnet': self.testnet
                }
            })
            
            # Load markets
            await self.exchange.load_markets()
            logger.info(f"Bybit connection initialized (testnet: {self.testnet})")
            
        except Exception as e:
            logger.error(f"Failed to initialize Bybit: {e}")
            raise

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
            timeframe: Candle timeframe (default: '30m')
            limit: Number of candles to fetch
            
        Returns:
            List of OHLCV data: [[timestamp, open, high, low, close, volume], ...]
        """
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol=symbol,
                timeframe=timeframe,
                limit=limit
            )
            
            logger.debug(f"Fetched {len(ohlcv)} candles for {symbol} ({timeframe})")
            return ohlcv
            
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error fetching OHLCV for {symbol}: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error fetching OHLCV for {symbol}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching OHLCV for {symbol}: {e}")
            raise

    async def get_balance(self, currency: str = "USDT") -> float:
        """
        Get account balance for a specific currency.
        
        Args:
            currency: Currency code (default: 'USDT')
            
        Returns:
            Available balance
        """
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            balance = await self.exchange.fetch_balance()
            free_balance = balance.get('free', {}).get(currency, 0.0)
            
            logger.debug(f"Balance for {currency}: {free_balance}")
            return float(free_balance)
            
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error fetching balance: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error fetching balance: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching balance: {e}")
            raise

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
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            order = await self.exchange.create_market_order(
                symbol=symbol,
                side=side,
                amount=amount,
                params=params or {}
            )
            
            logger.info(f"Market {side} order created: {symbol} amount={amount}, order_id={order.get('id')}")
            return order
            
        except ccxtpro.InsufficientFunds as e:
            logger.error(f"Insufficient funds for order: {e}")
            raise
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error creating order: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error creating order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating order: {e}")
            raise

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all open orders.
        
        Args:
            symbol: Optional symbol filter
            
        Returns:
            List of open orders
        """
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            orders = await self.exchange.fetch_open_orders(symbol=symbol)
            logger.debug(f"Fetched {len(orders)} open orders")
            return orders
            
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error fetching open orders: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error fetching open orders: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching open orders: {e}")
            raise

    async def cancel_order(self, order_id: str, symbol: str) -> Dict[str, Any]:
        """
        Cancel an order.
        
        Args:
            order_id: Order ID to cancel
            symbol: Trading pair symbol
            
        Returns:
            Cancellation result
        """
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            result = await self.exchange.cancel_order(id=order_id, symbol=symbol)
            logger.info(f"Order cancelled: {order_id}")
            return result
            
        except ccxtpro.OrderNotFound as e:
            logger.error(f"Order not found: {e}")
            raise
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error cancelling order: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error cancelling order: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error cancelling order: {e}")
            raise

    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get current ticker data.
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Ticker data including current price
        """
        try:
            if not self.exchange:
                raise RuntimeError("Exchange not initialized")
                
            ticker = await self.exchange.fetch_ticker(symbol)
            logger.debug(f"Ticker for {symbol}: last={ticker.get('last')}")
            return ticker
            
        except ccxtpro.NetworkError as e:
            logger.error(f"Network error fetching ticker: {e}")
            raise
        except ccxtpro.ExchangeError as e:
            logger.error(f"Exchange error fetching ticker: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching ticker: {e}")
            raise

    async def close(self) -> None:
        """Close the exchange connection."""
        if self.exchange:
            await self.exchange.close()
            logger.info("Bybit connection closed")
