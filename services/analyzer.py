"""Technical analysis service using pandas_ta."""

import pandas as pd
import pandas_ta as ta
from typing import Dict, List, Any, Optional
from loguru import logger

from core.base_exchange import BaseExchange


class Analyzer:
    """Technical analysis service for calculating indicators."""

    def __init__(self):
        """Initialize analyzer."""
        pass

    def calculate_indicators(self, ohlcv_data: List[List[Any]]) -> Dict[str, float]:
        """
        Calculate technical indicators from OHLCV data.
        
        Args:
            ohlcv_data: List of OHLCV candles [[timestamp, open, high, low, close, volume], ...]
            
        Returns:
            Dictionary of calculated indicators
        """
        try:
            # Convert to DataFrame
            df = self._ohlcv_to_dataframe(ohlcv_data)
            
            if df.empty or len(df) < 50:
                logger.warning(f"Insufficient data for analysis (got {len(df)} candles)")
                return self._get_default_indicators()
            
            # Calculate indicators
            indicators = {}
            
            # RSI(14)
            rsi = ta.rsi(df['close'], length=14)
            indicators['rsi'] = float(rsi.iloc[-1]) if not rsi.empty else 50.0
            
            # ATR(14) for volatility
            atr = ta.atr(df['high'], df['low'], df['close'], length=14)
            indicators['atr'] = float(atr.iloc[-1]) if not atr.empty else 0.0
            
            # EMA(20) and EMA(50)
            ema_20 = ta.ema(df['close'], length=20)
            ema_50 = ta.ema(df['close'], length=50)
            indicators['ema_20'] = float(ema_20.iloc[-1]) if not ema_20.empty else 0.0
            indicators['ema_50'] = float(ema_50.iloc[-1]) if not ema_50.empty else 0.0
            
            # Current price
            indicators['current_price'] = float(df['close'].iloc[-1])
            
            # Volume
            indicators['volume'] = float(df['volume'].iloc[-1])
            
            # Calculate additional useful metrics
            indicators['price_change_pct'] = self._calculate_price_change(df)
            
            logger.debug(
                f"Indicators calculated: RSI={indicators['rsi']:.2f}, "
                f"EMA20={indicators['ema_20']:.2f}, EMA50={indicators['ema_50']:.2f}, "
                f"ATR={indicators['atr']:.4f}"
            )
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return self._get_default_indicators()

    def _ohlcv_to_dataframe(self, ohlcv_data: List[List[Any]]) -> pd.DataFrame:
        """
        Convert OHLCV data to pandas DataFrame.
        
        Args:
            ohlcv_data: Raw OHLCV data
            
        Returns:
            DataFrame with OHLCV columns
        """
        df = pd.DataFrame(
            ohlcv_data,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert to proper types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Set timestamp as index
        df.set_index('timestamp', inplace=True)
        
        return df

    def _calculate_price_change(self, df: pd.DataFrame) -> float:
        """
        Calculate price change percentage over the dataset.
        
        Args:
            df: OHLCV DataFrame
            
        Returns:
            Price change percentage
        """
        try:
            if len(df) < 2:
                return 0.0
            
            first_price = df['close'].iloc[0]
            last_price = df['close'].iloc[-1]
            change_pct = ((last_price - first_price) / first_price) * 100
            
            return float(change_pct)
            
        except Exception:
            return 0.0

    def _get_default_indicators(self) -> Dict[str, float]:
        """
        Get default indicators when calculation fails.
        
        Returns:
            Dictionary with safe default values
        """
        return {
            'rsi': 50.0,
            'atr': 0.0,
            'ema_20': 0.0,
            'ema_50': 0.0,
            'current_price': 0.0,
            'volume': 0.0,
            'price_change_pct': 0.0
        }

    def is_trending_up(self, indicators: Dict[str, float]) -> bool:
        """
        Check if market is in uptrend based on EMA.
        
        Args:
            indicators: Calculated indicators
            
        Returns:
            True if EMA20 > EMA50 (bullish trend)
        """
        return indicators.get('ema_20', 0) > indicators.get('ema_50', 0)

    def is_oversold(self, indicators: Dict[str, float], threshold: float = 30.0) -> bool:
        """
        Check if RSI indicates oversold conditions.
        
        Args:
            indicators: Calculated indicators
            threshold: RSI threshold for oversold (default: 30)
            
        Returns:
            True if RSI < threshold
        """
        return indicators.get('rsi', 50) < threshold

    def is_overbought(self, indicators: Dict[str, float], threshold: float = 70.0) -> bool:
        """
        Check if RSI indicates overbought conditions.
        
        Args:
            indicators: Calculated indicators
            threshold: RSI threshold for overbought (default: 70)
            
        Returns:
            True if RSI > threshold
        """
        return indicators.get('rsi', 50) > threshold

    async def scan_top_volume_coins(
        self, 
        exchange: BaseExchange, 
        limit: int = 20,
        quote_currency: str = "USDT"
    ) -> List[Dict[str, Any]]:
        """
        Scan top volume coins on the exchange.
        
        Args:
            exchange: Exchange provider instance
            limit: Number of top coins to return
            quote_currency: Quote currency to filter by
            
        Returns:
            List of top coins with volume data
        """
        try:
            logger.info(f"Scanning top {limit} volume coins...")
            
            # Fetch tickers for all markets
            if not hasattr(exchange, 'exchange') or not exchange.exchange:
                logger.error("Exchange not initialized")
                return []
            
            tickers = await exchange.exchange.fetch_tickers()
            
            # Filter USDT pairs and exclude stablecoins
            usdt_pairs = []
            excluded = {'USDT', 'USDC', 'BUSD', 'DAI', 'TUSD'}
            
            for symbol, ticker in tickers.items():
                if not symbol.endswith(f'/{quote_currency}'):
                    continue
                
                base = symbol.split('/')[0]
                if base in excluded:
                    continue
                
                # Get 24h volume in quote currency
                volume = ticker.get('quoteVolume', 0) or 0
                
                if volume > 0:
                    usdt_pairs.append({
                        'symbol': symbol,
                        'volume': volume,
                        'price': ticker.get('last', 0),
                        'change_pct': ticker.get('percentage', 0)
                    })
            
            # Sort by volume and get top N
            usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
            top_coins = usdt_pairs[:limit]
            
            logger.info(
                f"Found {len(top_coins)} top volume coins. "
                f"Top 3: {', '.join([c['symbol'] for c in top_coins[:3]])}"
            )
            
            return top_coins
            
        except Exception as e:
            logger.error(f"Error scanning top volume coins: {e}")
            return []

    async def calculate_screening_metrics(
        self,
        exchange: BaseExchange,
        symbols: List[Dict[str, Any]],
        lookback_days: int = 7
    ) -> List[Dict[str, Any]]:
        """
        Calculate screening metrics (7-day ATR) for given symbols.
        
        Args:
            exchange: Exchange provider instance
            symbols: List of symbol dictionaries from scan_top_volume_coins
            lookback_days: Number of days for ATR calculation
            
        Returns:
            List of symbols with screening metrics
        """
        logger.info(f"Calculating screening metrics for {len(symbols)} symbols...")
        
        results = []
        
        for coin in symbols:
            symbol = coin['symbol']
            
            try:
                # Fetch daily candles for volatility calculation
                ohlcv = await exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    limit=lookback_days + 14  # Extra for ATR calculation
                )
                
                if not ohlcv or len(ohlcv) < 14:
                    logger.debug(f"Insufficient data for {symbol}, skipping")
                    continue
                
                # Convert to DataFrame
                df = self._ohlcv_to_dataframe(ohlcv)
                
                # Calculate 7-day ATR for volatility
                atr_7d = ta.atr(df['high'], df['low'], df['close'], length=7)
                
                if atr_7d.empty:
                    continue
                
                current_atr = float(atr_7d.iloc[-1])
                current_price = float(df['close'].iloc[-1])
                
                # Calculate ATR as percentage of price (normalized volatility)
                atr_pct = (current_atr / current_price) * 100 if current_price > 0 else 0
                
                # Also calculate 30m RSI for momentum
                ohlcv_30m = await exchange.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='30m',
                    limit=50
                )
                
                rsi = 50.0  # Default
                if ohlcv_30m and len(ohlcv_30m) >= 14:
                    df_30m = self._ohlcv_to_dataframe(ohlcv_30m)
                    rsi_calc = ta.rsi(df_30m['close'], length=14)
                    if not rsi_calc.empty:
                        rsi = float(rsi_calc.iloc[-1])
                
                results.append({
                    'symbol': symbol,
                    'volume_24h': coin['volume'],
                    'price': current_price,
                    'change_pct_24h': coin.get('change_pct', 0),
                    'atr_7d': current_atr,
                    'atr_pct': atr_pct,
                    'rsi_30m': rsi
                })
                
                logger.debug(
                    f"{symbol}: ATR={atr_pct:.2f}%, RSI={rsi:.1f}, "
                    f"Volume=${coin['volume']:,.0f}"
                )
                
            except Exception as e:
                logger.warning(f"Error calculating metrics for {symbol}: {e}")
                continue
        
        logger.success(
            f"Calculated metrics for {len(results)}/{len(symbols)} symbols"
        )
        
        return results
