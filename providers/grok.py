"""Grok AI provider using x.ai API."""

import json
import httpx
from typing import Dict, List, Optional, Any
from loguru import logger

from core.base_ai import BaseAI, AIDecision


class GrokProvider(BaseAI):
    """Grok AI implementation using x.ai API."""

    def __init__(self, api_key: str, model: str = "grok-beta"):
        """
        Initialize Grok provider.
        
        Args:
            api_key: x.ai API key
            model: Model name (default: 'grok-beta')
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.x.ai/v1"
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
        )

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for Grok trading bot.
        
        Returns:
            Comprehensive system prompt defining trading behavior
        """
        return """You are Sentinel AI, an expert cryptocurrency trading analyst.

Your role is to analyze market data and technical indicators to make informed trading decisions.

STRICT RULES:
1. Only recommend BUY when confidence is > 80% and market conditions are favorable
2. Consider the feedback from recent trades to avoid repeating mistakes
3. Be conservative - it's better to HOLD than to make a losing trade
4. Pay attention to RSI (overbought > 70, oversold < 30)
5. Consider trend direction using EMA crossovers (EMA20 vs EMA50)
6. Use ATR to assess market volatility

OUTPUT FORMAT (strict JSON only):
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "reasoning": "detailed explanation of your decision",
    "risk_level": "low" | "medium" | "high"
}

DECISION CRITERIA:
- BUY: Strong uptrend (EMA20 > EMA50), RSI 30-70, high confidence, positive market context
- SELL: Already in position and profit target reached or stop-loss triggered
- HOLD: Unclear signals, low confidence, recent losses with similar patterns

Never output anything except the JSON object. No additional text, no markdown.
"""

    async def analyze(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        memory: Optional[List[Dict[str, Any]]] = None
    ) -> AIDecision:
        """
        Analyze market conditions using Grok AI.
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data (price, volume, etc.)
            technical_indicators: Calculated indicators (RSI, EMA, ATR, etc.)
            memory: Recent trade history for feedback loop
            
        Returns:
            AIDecision object
        """
        try:
            # Build context message
            user_message = self._build_analysis_prompt(
                symbol, market_data, technical_indicators, memory
            )
            
            # Call Grok API
            response = await self._call_grok_api(user_message)
            
            # Parse response
            decision = self._parse_response(response)
            
            logger.info(
                f"Grok decision for {symbol}: {decision.action} "
                f"(confidence: {decision.confidence}%)"
            )
            
            return decision
            
        except Exception as e:
            logger.error(f"Error in Grok analysis: {e}")
            # Return safe default decision on error
            return AIDecision(
                action="HOLD",
                confidence=0.0,
                reasoning=f"Error during analysis: {str(e)}",
                risk_level="high"
            )

    def _build_analysis_prompt(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        memory: Optional[List[Dict[str, Any]]]
    ) -> str:
        """Build the analysis prompt with all context."""
        
        prompt_parts = [
            f"Analyze {symbol} for trading decision.\n",
            "\nCURRENT MARKET DATA:",
            f"- Price: ${market_data.get('price', 0):.2f}",
            f"- 24h Volume: ${market_data.get('volume', 0):.2f}",
            f"- 24h Change: {market_data.get('change_pct', 0):.2f}%",
            "\nTECHNICAL INDICATORS:",
            f"- RSI(14): {technical_indicators.get('rsi', 0):.2f}",
            f"- EMA(20): {technical_indicators.get('ema_20', 0):.2f}",
            f"- EMA(50): {technical_indicators.get('ema_50', 0):.2f}",
            f"- ATR(14): {technical_indicators.get('atr', 0):.4f}",
        ]
        
        # Add trend analysis
        ema_20 = technical_indicators.get('ema_20', 0)
        ema_50 = technical_indicators.get('ema_50', 0)
        if ema_20 > ema_50:
            prompt_parts.append(f"- Trend: BULLISH (EMA20 > EMA50)")
        elif ema_20 < ema_50:
            prompt_parts.append(f"- Trend: BEARISH (EMA20 < EMA50)")
        else:
            prompt_parts.append(f"- Trend: NEUTRAL")
        
        # Add memory (feedback loop)
        if memory and len(memory) > 0:
            prompt_parts.append("\nRECENT TRADE HISTORY (learn from these):")
            for i, trade in enumerate(memory[:3], 1):  # Last 3 trades
                result = trade.get('result', 'unknown')
                pnl = trade.get('pnl_pct', 0)
                reason = trade.get('entry_reason', 'N/A')
                prompt_parts.append(
                    f"Trade {i}: {result.upper()} (P&L: {pnl:+.2f}%) - Reason: {reason}"
                )
        
        prompt_parts.append("\nProvide your decision in JSON format as specified.")
        
        return "\n".join(prompt_parts)

    async def _call_grok_api(self, user_message: str) -> str:
        """
        Call Grok API with the analysis prompt.
        
        Args:
            user_message: The analysis prompt
            
        Returns:
            API response text
        """
        try:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.get_system_prompt()},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.3,  # Lower temperature for more consistent trading decisions
                "max_tokens": 500
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            
            content = data['choices'][0]['message']['content']
            return content.strip()
            
        except httpx.HTTPError as e:
            logger.error(f"HTTP error calling Grok API: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling Grok API: {e}")
            raise

    def _parse_response(self, response: str) -> AIDecision:
        """
        Parse Grok's JSON response into AIDecision.
        
        Args:
            response: JSON string from Grok
            
        Returns:
            AIDecision object
        """
        try:
            # Try to extract JSON if wrapped in markdown or other text
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
                response = response.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(response)
            
            # Validate required fields
            required_fields = ["action", "confidence", "reasoning"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Create AIDecision
            return AIDecision(
                action=data["action"],
                confidence=float(data["confidence"]),
                reasoning=data["reasoning"],
                risk_level=data.get("risk_level", "medium")
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Grok response as JSON: {e}")
            logger.debug(f"Response was: {response}")
            # Return HOLD decision on parse error
            return AIDecision(
                action="HOLD",
                confidence=0.0,
                reasoning=f"Failed to parse AI response: {str(e)}",
                risk_level="high"
            )
        except Exception as e:
            logger.error(f"Error parsing Grok response: {e}")
            return AIDecision(
                action="HOLD",
                confidence=0.0,
                reasoning=f"Error parsing response: {str(e)}",
                risk_level="high"
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("Grok client closed")

    async def select_trading_symbols(
        self,
        candidates: List[Dict[str, Any]],
        max_symbols: int = 2
    ) -> List[str]:
        """
        Use Grok to select the most promising trading symbols from candidates.
        
        Args:
            candidates: List of symbol data with metrics
            max_symbols: Maximum number of symbols to select
            
        Returns:
            List of selected symbol names
        """
        try:
            system_prompt = """You are a cryptocurrency market expert specializing in symbol selection.

Your task is to analyze market data and select the 1-2 BEST symbols for short-term trading (24 hours).

SELECTION CRITERIA:
1. High volume = good liquidity
2. Moderate volatility (ATR 3-8%) = good profit potential without excessive risk
3. RSI between 35-65 = not overbought/oversold
4. Positive momentum indicators
5. Avoid symbols with extreme movements (pump & dump risk)

OUTPUT FORMAT (strict JSON only):
{
    "selected_symbols": ["BTC/USDT", "ETH/USDT"],
    "reasoning": "brief explanation for each selection"
}

Never output anything except the JSON object. No additional text, no markdown."""

            # Build candidates description
            candidates_text = "\n\nCANDIDATES:\n"
            for i, candidate in enumerate(candidates[:20], 1):  # Limit to top 20
                candidates_text += (
                    f"{i}. {candidate['symbol']}: "
                    f"Volume=${candidate['volume_24h']:,.0f}, "
                    f"Price=${candidate['price']:.2f}, "
                    f"24h Change={candidate['change_pct_24h']:+.2f}%, "
                    f"Volatility(ATR)={candidate['atr_pct']:.2f}%, "
                    f"RSI={candidate['rsi_30m']:.1f}\n"
                )
            
            user_message = (
                f"Analyze these {len(candidates)} coins and select the best {max_symbols} "
                f"for trading in the next 24 hours.{candidates_text}\n"
                f"Select {max_symbols} symbol(s) and provide your reasoning."
            )
            
            # Call Grok API
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.4,
                "max_tokens": 500
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # Parse response
            selection = self._parse_symbol_selection(content)
            
            logger.info(
                f"Grok selected: {', '.join(selection['symbols'])} - "
                f"{selection['reasoning']}"
            )
            
            return selection['symbols'][:max_symbols]
            
        except Exception as e:
            logger.error(f"Error in symbol selection: {e}")
            # Fallback: return top volume symbols
            fallback = [c['symbol'] for c in candidates[:max_symbols]]
            logger.warning(f"Using fallback selection: {', '.join(fallback)}")
            return fallback

    def _parse_symbol_selection(self, response: str) -> Dict[str, Any]:
        """
        Parse Grok's symbol selection response.
        
        Args:
            response: JSON string from Grok
            
        Returns:
            Dictionary with selected symbols and reasoning
        """
        try:
            # Clean markdown if present
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
                response = response.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(response)
            
            return {
                'symbols': data.get('selected_symbols', []),
                'reasoning': data.get('reasoning', 'No reasoning provided')
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse symbol selection: {e}")
            logger.debug(f"Response was: {response}")
            return {
                'symbols': [],
                'reasoning': f"Parse error: {str(e)}"
            }
