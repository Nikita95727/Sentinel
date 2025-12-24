"""Grok AI provider using x.ai API."""

import json
import httpx
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from core.base_ai import BaseAI, AIDecision
from utils.resilience import retry_on_error, ai_circuit
from utils.error_handler import (
    log_error_with_context, ErrorCode, ErrorCategory, ErrorSeverity
)


class GrokProvider(BaseAI):
    """Grok AI implementation using x.ai API."""

    def __init__(self, api_key: str, model: str = "grok-4-1-fast-reasoning"):
        """
        Initialize Grok provider.
        
        Args:
            api_key: x.ai API key
            model: Model name (default: 'grok-4-1-fast-reasoning')
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
        return """You are Sentinel AI, an expert cryptocurrency trading analyst with deep understanding of market dynamics and risk management.

Your role is to analyze market data, technical indicators, and historical performance to make informed trading decisions that maximize risk-adjusted returns.

CORE PRINCIPLES:
1. Capital preservation is paramount - only trade when probability of success is high
2. Learn from past mistakes - analyze recent trade history to avoid repeating patterns
3. Quality over quantity - better to HOLD than to force trades
4. Risk management is non-negotiable - every trade must have clear stop-loss and take-profit
5. AVOID FOMO (Fear of Missing Out) - missing a trade is better than taking a bad trade

STRICT RULES:
1. Only recommend BUY when confidence is >= 80% AND all conditions align favorably
2. Consider feedback from recent trades - if similar patterns led to losses, be more cautious
3. RSI interpretation (CRITICAL THRESHOLDS):
   - RSI < 25: Severely oversold - DANGER ZONE, avoid entries (could crash further)
   - RSI 25-30: Oversold - wait for bullish confirmation before entry
   - RSI 30-50: Neutral to slightly bearish - NOT ideal for entries
   - RSI 50-65: OPTIMAL ZONE for entries (healthy bullish momentum)
   - RSI 65-75: Overbought territory - AVOID new entries
   - RSI > 75: Severely overbought - STRICT NO ENTRY ZONE
4. EMA trend analysis (MANDATORY):
   - EMA20 > EMA50: Bullish trend (REQUIRED for BUY)
   - EMA20 < EMA50: Bearish trend (STRICTLY AVOID long entries)
   - EMA20 crossing above EMA50: Bullish momentum building (good signal)
   - Price MUST be above EMA20 for BUY (momentum confirmation)
5. ATR indicates volatility - higher ATR = wider stop-loss needed
6. Volume confirmation - prefer entries when volume is above average (volume_ratio > 1.2)

OUTPUT FORMAT (strict JSON only, no markdown, no additional text):
{
    "action": "BUY" | "SELL" | "HOLD",
    "confidence": 0-100,
    "reasoning": "STRUCTURED FORMAT: [Market Context] → [Indicator Analysis] → [Risk Assessment] → [Decision Rationale]",
    "risk_level": "low" | "medium" | "high"
}

REASONING STRUCTURE (MANDATORY):
Your reasoning MUST follow this structure:
1. Market Context: Describe current market conditions (trend, session, BTC correlation)
2. Indicator Analysis: Analyze RSI, EMA, ATR, Volume with specific values
3. Risk Assessment: Evaluate risk factors and potential downsides
4. Decision Rationale: Explain why this specific action was chosen

EXAMPLE GOOD REASONING:
"Market Context: Bullish BTC trend, US session (high liquidity). Indicator Analysis: RSI 55 (optimal zone), EMA20 > EMA50 (bullish), price above EMA20 (+1.2%), volume 1.5x average. Risk Assessment: ATR 2.1% allows tight stop-loss, no recent losses with similar pattern. Decision Rationale: Strong bullish alignment with multiple confirmations, high probability setup."

EXAMPLE BAD REASONING (AVOID):
"Looks good" or "Trend is up" - TOO VAGUE, REJECTED

DECISION CRITERIA WITH EXAMPLES:

BUY (confidence >= 80%) - EXAMPLE GOOD SETUP:
✅ RSI = 58 (optimal 50-65 zone)
✅ EMA20 = $50,200 > EMA50 = $49,800 (bullish trend)
✅ Price = $50,500 > EMA20 (momentum +0.6%)
✅ Volume ratio = 1.4x (above average)
✅ ATR = 2.0% (reasonable stop-loss)
✅ No recent losses with similar pattern
→ Confidence: 85-90%

BUY (confidence >= 80%) - EXAMPLE BAD SETUP (AVOID):
❌ RSI = 78 (overbought >75) → REJECT, use HOLD
❌ EMA20 < EMA50 (bearish) → REJECT, use HOLD
❌ Price below EMA20 → REJECT, use HOLD
❌ Recent loss with similar RSI/EMA pattern → REJECT, use HOLD

HOLD (default when uncertain) - EXAMPLES:
- RSI > 75 or < 25 (extreme zones without confirmation)
- EMA20 < EMA50 (bearish trend - NEVER buy in bearish trend)
- Confidence < 80% (insufficient edge)
- Recent losses with similar market conditions (learn from mistakes)
- Unclear market direction (wait for clarity)
- High volatility (ATR > 5%) without clear edge
- Low volume (volume_ratio < 0.8) - weak interest

SELL:
- Already in position (this is handled by exit logic, not entry decision)
- For entry decisions, use HOLD instead of SELL

CONFIDENCE CALIBRATION (BE HONEST):
- 80-85%: Good setup, but some reservations (minor concerns)
- 85-90%: Strong setup with clear edge (multiple confirmations)
- 90-95%: Excellent setup, multiple strong confirmations (rare)
- 95-100%: Exceptional setup, all conditions perfect (very rare, verify carefully)

COMMON MISTAKES TO AVOID:
1. ❌ FOMO: "Price is rising, must buy now" → WRONG, wait for proper setup
2. ❌ Overbought entries: RSI > 75 but "momentum is strong" → WRONG, wait for pullback
3. ❌ Bearish trend entries: EMA20 < EMA50 but "oversold RSI" → WRONG, avoid counter-trend
4. ❌ Ignoring history: Similar pattern lost money but "this time is different" → WRONG, learn from mistakes
5. ❌ Vague reasoning: "Looks good" → WRONG, provide structured analysis

LEARNING FROM HISTORY (CRITICAL):
When recent trades are provided:
- ✅ WIN patterns: What worked? (RSI zone, EMA alignment, volume) → Replicate
- ❌ LOSS patterns: What failed? (RSI too high, bearish trend, low volume) → Avoid
- 📊 Confidence calibration: Were you overconfident in losses? → Lower confidence for similar setups
- 📊 Missed opportunities: Were you too conservative in wins? → Consider similar setups with appropriate confidence

CRITICAL: Never output anything except the JSON object. No markdown, no code blocks, no explanations outside JSON.
"""

    @ai_circuit.call
    @retry_on_error(max_attempts=2, delay_seconds=10, exceptions=(httpx.HTTPStatusError, httpx.TimeoutException, httpx.RequestError))
    async def analyze(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        memory: Optional[List[Dict[str, Any]]] = None
    ) -> AIDecision:
        """
        Analyze market conditions using Grok AI with validation and fallback.
        
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
            
            # Log full prompt for debugging (DEBUG level to avoid spam)
            logger.debug(f"Full prompt sent to Grok for {symbol}:\n{user_message}")
            logger.debug(f"Prompt length: {len(user_message)} characters")
            
            # Log market context before decision
            logger.debug(f"Market context for {symbol}:")
            logger.debug(f"  Price: ${market_data.get('price', 0):.2f}")
            logger.debug(f"  Session: {market_data.get('market_session', 'unknown')}")
            logger.debug(f"  Day: {market_data.get('day_of_week', 'unknown')}")
            logger.debug(f"  BTC Trend: {market_data.get('btc_trend', 'N/A')}")
            
            # Log all indicators with changes
            logger.debug(f"Technical indicators for {symbol}:")
            logger.debug(f"  RSI: {technical_indicators.get('rsi', 0):.2f} (change: {technical_indicators.get('rsi_change', 0):+.2f})")
            logger.debug(f"  EMA20: ${technical_indicators.get('ema_20', 0):.2f} (change: {technical_indicators.get('ema_20_change', 0):+.2f}%)")
            logger.debug(f"  EMA50: ${technical_indicators.get('ema_50', 0):.2f} (change: {technical_indicators.get('ema_50_change', 0):+.2f}%)")
            logger.debug(f"  ATR: ${technical_indicators.get('atr', 0):.2f} ({technical_indicators.get('atr_pct', 0):.2f}% of price)")
            logger.debug(f"  Volume Trend: {technical_indicators.get('volume_trend', 'unknown')}")
            logger.debug(f"  Volume Ratio: {technical_indicators.get('volume_ratio', 1.0):.2f}x")
            logger.debug(f"  Trend Strength: {technical_indicators.get('trend_strength', 0):.2f}%")
            
            # Call Grok API with timing
            import time
            api_start_time = time.time()
            response, usage_info = await self._call_grok_api(user_message)
            api_latency = (time.time() - api_start_time) * 1000  # Convert to milliseconds
            
            # Log API call metrics
            logger.info(
                f"Grok API call for {symbol}: "
                f"latency={api_latency:.0f}ms, "
                f"tokens={usage_info.get('total_tokens', 0)}, "
                f"prompt_tokens={usage_info.get('prompt_tokens', 0)}, "
                f"completion_tokens={usage_info.get('completion_tokens', 0)}"
            )
            
            # Parse response with validation
            decision = self._parse_response(response)
            
            # Logical validation of decision
            validation_result = self._validate_decision(
                decision, symbol, market_data, technical_indicators
            )
            
            # If validation failed and decision is BUY, try fallback
            if not validation_result["is_valid"] and decision.action == "BUY":
                logger.warning(
                    f"⚠️  Logical validation failed for {symbol}: {validation_result['warnings']}. "
                    f"Decision: {decision.action} (confidence: {decision.confidence}%)"
                )
                
                # Fallback: Request clarification from Grok
                logger.info(f"🔄 Requesting clarification from Grok for {symbol}...")
                fallback_decision = await self._request_clarification(
                    symbol, market_data, technical_indicators, decision, validation_result
                )
                
                # Validate fallback decision
                fallback_validation = self._validate_decision(
                    fallback_decision, symbol, market_data, technical_indicators
                )
                
                if fallback_validation["is_valid"]:
                    logger.info(f"✅ Fallback decision validated for {symbol}")
                    decision = fallback_decision
                    decision.additional_context = decision.additional_context or {}
                    decision.additional_context["is_fallback"] = True
                    decision.additional_context["original_validation_failed"] = True
                else:
                    logger.warning(
                        f"⚠️  Fallback decision also failed validation for {symbol}. "
                        f"Using HOLD with low confidence."
                    )
                    # Return HOLD with low confidence
                    decision = AIDecision(
                        action="HOLD",
                        confidence=30.0,
                        reasoning=(
                            f"Original decision failed validation: {validation_result['warnings']}. "
                            f"Fallback also failed: {fallback_validation['warnings']}. "
                            f"Too risky to proceed."
                        ),
                        risk_level="high",
                        additional_context={
                            "validation_failed": True,
                            "fallback_used": True,
                            "original_decision": decision.to_dict()
                        }
                    )
            elif not validation_result["is_valid"]:
                # For non-BUY decisions, log warning but proceed
                logger.warning(
                    f"⚠️  Validation warnings for {symbol} ({decision.action}): "
                    f"{validation_result['warnings']}"
                )
            
            # Add validation context to decision
            decision.additional_context = decision.additional_context or {}
            decision.additional_context["validation"] = validation_result
            
            # Store metadata for JSONL (for learning and analysis)
            decision.additional_context["ai_metadata"] = {
                "full_prompt": user_message,
                "raw_response": response,
                "api_latency_ms": api_latency,
                "tokens_used": usage_info.get('total_tokens', 0),
                "prompt_tokens": usage_info.get('prompt_tokens', 0),
                "completion_tokens": usage_info.get('completion_tokens', 0),
                "validation_passed": validation_result.get('is_valid', True),
                "validation_warnings": validation_result.get('warnings', []),
                "is_fallback": decision.additional_context.get('is_fallback', False)
            }
            
            logger.info(
                f"Grok decision for {symbol}: {decision.action} "
                f"(confidence: {decision.confidence}%, "
                f"validated: {validation_result['is_valid']})"
            )
            
            return decision
            
        except httpx.HTTPStatusError as e:
            error_code = ErrorCode.API_SERVER_ERROR if e.response.status_code >= 500 else ErrorCode.API_INVALID_RESPONSE
            log_error_with_context(
                e, error_code,
                ErrorCategory.API_ERROR, ErrorSeverity.HIGH,
                "GrokProvider", symbol=symbol, operation="analyze",
                metadata={
                    "status_code": e.response.status_code,
                    "response": str(e.response.text)[:200] if hasattr(e.response, 'text') else None
                }
            )
            # Try technical fallback
            try:
                logger.warning(f"Using technical fallback for {symbol} due to API error")
                return self._technical_fallback(technical_indicators, symbol)
            except Exception as fallback_error:
                log_error_with_context(
                    fallback_error, ErrorCode.AI_FALLBACK_USED,
                    ErrorCategory.AI_ERROR, ErrorSeverity.CRITICAL,
                    "GrokProvider", symbol=symbol, operation="technical_fallback"
                )
                return AIDecision(
                    action="HOLD",
                    confidence=0.0,
                    reasoning=f"API error and fallback failed: {str(e)}",
                    risk_level="high",
                    additional_context={"error": str(e), "fallback_failed": True}
                )
        except httpx.TimeoutException as e:
            log_error_with_context(
                e, ErrorCode.AI_TIMEOUT,
                ErrorCategory.AI_ERROR, ErrorSeverity.HIGH,
                "GrokProvider", symbol=symbol, operation="analyze",
                metadata={"timeout": 30.0}
            )
            # Try technical fallback
            try:
                logger.warning(f"Using technical fallback for {symbol} due to timeout")
                return self._technical_fallback(technical_indicators, symbol)
            except Exception as fallback_error:
                log_error_with_context(
                    fallback_error, ErrorCode.AI_FALLBACK_USED,
                    ErrorCategory.AI_ERROR, ErrorSeverity.CRITICAL,
                    "GrokProvider", symbol=symbol, operation="technical_fallback"
                )
                return AIDecision(
                    action="HOLD",
                    confidence=0.0,
                    reasoning=f"API timeout and fallback failed: {str(e)}",
                    risk_level="high",
                    additional_context={"error": str(e), "fallback_failed": True}
                )
        except Exception as e:
            log_error_with_context(
                e, ErrorCode.AI_INVALID_DECISION,
                ErrorCategory.AI_ERROR, ErrorSeverity.HIGH,
                "GrokProvider", symbol=symbol, operation="analyze",
                metadata={"error_type": type(e).__name__}
            )
            # Try technical fallback before returning error
            try:
                logger.warning(f"Using technical fallback for {symbol} due to unexpected error")
                return self._technical_fallback(technical_indicators, symbol)
            except Exception as fallback_error:
                log_error_with_context(
                    fallback_error, ErrorCode.AI_FALLBACK_USED,
                    ErrorCategory.AI_ERROR, ErrorSeverity.CRITICAL,
                    "GrokProvider", symbol=symbol, operation="technical_fallback"
                )
                # Return safe default decision on error
                return AIDecision(
                    action="HOLD",
                    confidence=0.0,
                    reasoning=f"Error during analysis: {str(e)}",
                    risk_level="high",
                    additional_context={"error": str(e), "fallback_failed": True}
                )
    
    def _technical_fallback(
        self, 
        technical_indicators: Dict[str, float],
        symbol: str
    ) -> AIDecision:
        """
        Fallback decision based on technical indicators when AI fails.
        
        Args:
            technical_indicators: Technical indicators dictionary
            symbol: Trading pair symbol
            
        Returns:
            AIDecision based on technical analysis only
        """
        rsi = technical_indicators.get('rsi', 50)
        ema_20 = technical_indicators.get('ema_20', 0)
        ema_50 = technical_indicators.get('ema_50', 0)
        
        # Simple logic based on RSI and EMA
        if rsi < 30 and ema_20 > ema_50:
            return AIDecision(
                action="BUY",
                confidence=60.0,
                reasoning=(
                    f"Technical fallback: RSI {rsi:.1f} (oversold), "
                    f"EMA20 > EMA50 (bullish trend). "
                    f"AI unavailable, using technical indicators only."
                ),
                risk_level="medium",
                additional_context={"source": "fallback", "rsi": rsi, "ema_trend": "bullish"}
            )
        elif rsi > 70 or ema_20 < ema_50:
            return AIDecision(
                action="SELL",
                confidence=60.0,
                reasoning=(
                    f"Technical fallback: RSI {rsi:.1f} (overbought) or "
                    f"EMA20 < EMA50 (bearish trend). "
                    f"AI unavailable, using technical indicators only."
                ),
                risk_level="medium",
                additional_context={"source": "fallback", "rsi": rsi, "ema_trend": "bearish"}
            )
        else:
            return AIDecision(
                action="HOLD",
                confidence=50.0,
                reasoning=(
                    f"Technical fallback: RSI {rsi:.1f} (neutral), "
                    f"no clear signal. AI unavailable."
                ),
                risk_level="low",
                additional_context={"source": "fallback", "rsi": rsi}
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
            "\n" + "="*60,
            "CURRENT MARKET DATA:",
            "="*60,
            f"- Price: ${market_data.get('price', 0):.2f}",
            f"- 24h Volume: ${market_data.get('volume', 0):,.0f}",
            f"- 24h Change: {market_data.get('change_pct', 0):+.2f}%",
        ]
        
        # Add market context (session, day, BTC trend)
        market_session = market_data.get('market_session', 'unknown')
        day_of_week = market_data.get('day_of_week', 'unknown')
        btc_trend = market_data.get('btc_trend')
        btc_rsi = market_data.get('btc_rsi')
        
        prompt_parts.append(f"\nMARKET CONTEXT:")
        prompt_parts.append(f"- Market Session: {market_session} (UTC hour: {market_data.get('hour_utc', 'N/A')})")
        prompt_parts.append(f"- Day of Week: {day_of_week}")
        if btc_trend:
            prompt_parts.append(f"- BTC Market Trend: {btc_trend.upper()}" + (f" (RSI: {btc_rsi:.1f})" if btc_rsi else ""))
            if symbol != "BTC/USDT":
                prompt_parts.append(f"  → {symbol} correlation: Consider BTC trend when analyzing")
        
        prompt_parts.append("\n" + "="*60)
        prompt_parts.append("TECHNICAL INDICATORS:")
        prompt_parts.append("="*60)
        
        rsi = technical_indicators.get('rsi', 0)
        rsi_change = technical_indicators.get('rsi_change', 0)
        ema_20 = technical_indicators.get('ema_20', 0)
        ema_50 = technical_indicators.get('ema_50', 0)
        ema_20_change = technical_indicators.get('ema_20_change', 0)
        ema_50_change = technical_indicators.get('ema_50_change', 0)
        atr = technical_indicators.get('atr', 0)
        atr_pct = technical_indicators.get('atr_pct', 0)
        price_vs_ema20 = technical_indicators.get('price_vs_ema20', 0)
        price_vs_ema50 = technical_indicators.get('price_vs_ema50', 0)
        trend_strength = technical_indicators.get('trend_strength', 0)
        volume_trend = technical_indicators.get('volume_trend', 'unknown')
        volume_ratio = technical_indicators.get('volume_ratio', 1.0)
        
        prompt_parts.append(f"- RSI(14): {rsi:.2f} (Change: {rsi_change:+.2f})")
        if rsi < 30:
            prompt_parts.append("  ⚠️  RSI < 30: Oversold zone - wait for confirmation before entry")
        elif rsi > 70:
            prompt_parts.append("  ⚠️  RSI > 70: Overbought zone - avoid new entries")
        elif 35 <= rsi <= 65:
            prompt_parts.append("  ✅ RSI in optimal range (35-65) for entries")
        
        prompt_parts.append(f"- EMA(20): ${ema_20:.2f} (Change: {ema_20_change:+.2f}%)")
        prompt_parts.append(f"- EMA(50): ${ema_50:.2f} (Change: {ema_50_change:+.2f}%)")
        
        # Trend analysis with strength
        if ema_20 > ema_50:
            trend_direction = "BULLISH"
            trend_emoji = "📈"
        elif ema_20 < ema_50:
            trend_direction = "BEARISH"
            trend_emoji = "📉"
        else:
            trend_direction = "NEUTRAL"
            trend_emoji = "➡️"
        
        prompt_parts.append(f"- Trend: {trend_direction} {trend_emoji} (EMA20 vs EMA50)")
        prompt_parts.append(f"  Trend Strength: {trend_strength:.2f}% (distance between EMAs)")
        
        # Price position relative to EMAs
        prompt_parts.append(f"- Price vs EMA20: {price_vs_ema20:+.2f}%")
        prompt_parts.append(f"- Price vs EMA50: {price_vs_ema50:+.2f}%")
        if price_vs_ema20 > 0 and price_vs_ema50 > 0:
            prompt_parts.append("  ✅ Price above both EMAs - strong bullish momentum")
        elif price_vs_ema20 < 0 and price_vs_ema50 < 0:
            prompt_parts.append("  ⚠️  Price below both EMAs - bearish pressure")
        
        prompt_parts.append(f"- ATR(14): ${atr:.4f} ({atr_pct:.2f}% of price)")
        if atr_pct > 5:
            prompt_parts.append("  ⚠️  High volatility - wider stop-loss needed")
        elif atr_pct < 1:
            prompt_parts.append("  ℹ️  Low volatility - tight stop-loss possible")
        
        # Volume analysis
        prompt_parts.append(f"\nVOLUME ANALYSIS:")
        prompt_parts.append(f"- Current Volume: {market_data.get('volume', 0):,.0f}")
        prompt_parts.append(f"- Volume Trend: {volume_trend.upper()}")
        prompt_parts.append(f"- Volume Ratio: {volume_ratio:.2f}x average")
        if volume_ratio > 1.5:
            prompt_parts.append("  ✅ High volume - strong interest")
        elif volume_ratio < 0.7:
            prompt_parts.append("  ⚠️  Low volume - weak interest, be cautious")
        
        # Add memory (feedback loop) - use Grok-friendly format
        if memory and len(memory) > 0:
            prompt_parts.append("\n" + "="*60)
            prompt_parts.append("RECENT TRADE HISTORY - LEARN FROM THESE:")
            prompt_parts.append("="*60)
            
            for i, trade in enumerate(memory[:5], 1):  # Last 5 trades for better learning
                outcome = trade.get('outcome', 'UNKNOWN')
                symbol_trade = trade.get('symbol', 'N/A')
                entry = trade.get('entry', {})
                exit_data = trade.get('exit', {})
                results = trade.get('results', {})
                lessons = trade.get('lessons', {})
                
                prompt_parts.append(f"\nTrade {i}: {symbol_trade} - {outcome}")
                prompt_parts.append(f"  Entry: ${entry.get('price', 0):.2f} | Confidence: {entry.get('ai_confidence', 0):.0f}%")
                prompt_parts.append(f"  Entry Reason: {entry.get('reason', 'N/A')}")
                
                # Entry conditions
                entry_indicators = entry.get('technical_indicators', {})
                if entry_indicators:
                    prompt_parts.append(
                        f"  Entry Conditions: RSI={entry_indicators.get('rsi', 0):.1f}, "
                        f"EMA20={entry_indicators.get('ema_20', 0):.2f}, "
                        f"EMA50={entry_indicators.get('ema_50', 0):.2f}"
                    )
                
                # Exit info
                if exit_data:
                    prompt_parts.append(f"  Exit: ${exit_data.get('price', 0):.2f} | Reason: {exit_data.get('reason', 'N/A')}")
                
                # Results
                if results:
                    pnl_pct = results.get('pnl_percent', 0)
                    prompt_parts.append(f"  Result: {pnl_pct:+.2f}% P&L")
                
                # Lessons learned
                if lessons:
                    what_worked = lessons.get('what_worked', [])
                    what_failed = lessons.get('what_failed', [])
                    recommendations = lessons.get('recommendations', [])
                    
                    if what_worked:
                        prompt_parts.append(f"  ✅ What worked: {', '.join(what_worked)}")
                    if what_failed:
                        prompt_parts.append(f"  ❌ What failed: {', '.join(what_failed)}")
                    if recommendations:
                        prompt_parts.append(f"  💡 Lessons: {', '.join(recommendations)}")
            
            prompt_parts.append("\n" + "="*60)
            prompt_parts.append("Use this history to avoid repeating mistakes and replicate successful patterns.")
            prompt_parts.append("="*60)
        
        prompt_parts.append("\nProvide your decision in JSON format as specified.")
        
        return "\n".join(prompt_parts)

    async def _call_grok_api(self, user_message: str) -> tuple[str, dict]:
        """
        Call Grok API with the analysis prompt (with retry logic).
        
        Args:
            user_message: The analysis prompt
            
        Returns:
            Tuple of (API response text, usage info dict)
        """
        import asyncio
        
        # Validate prompt before sending
        if not user_message or len(user_message.strip()) == 0:
            raise ValueError("Empty prompt cannot be sent to Grok API")
        
        max_retries = 3
        base_delay = 1.0  # Start with 1 second
        
        for attempt in range(max_retries):
            try:
                payload = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": self.get_system_prompt()},
                        {"role": "user", "content": user_message}
                    ],
                    "temperature": 0.1,  # Very low temperature for deterministic trading decisions
                    "max_tokens": 500
                }
                
                import time
                start_time = time.time()
                
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                )
                
                latency_ms = (time.time() - start_time) * 1000
                
                response.raise_for_status()
                data = response.json()
                
                content = data['choices'][0]['message']['content']
                
                # Log API response details for debugging
                usage = data.get('usage', {})
                total_tokens = usage.get('total_tokens', 0)
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                
                logger.debug(
                    f"Grok API response: "
                    f"latency={latency_ms:.0f}ms, "
                    f"tokens={total_tokens}, "
                    f"prompt_tokens={prompt_tokens}, "
                    f"completion_tokens={completion_tokens}"
                )
                logger.debug(f"Raw Grok response: {content[:200]}..." if len(content) > 200 else f"Raw Grok response: {content}")
                
                # Return response and usage info
                usage_info = {
                    'total_tokens': total_tokens,
                    'prompt_tokens': prompt_tokens,
                    'completion_tokens': completion_tokens,
                    'latency_ms': latency_ms
                }
                return content.strip(), usage_info
                
            except httpx.HTTPStatusError as e:
                # Retry on 5xx errors (server errors)
                if e.response.status_code >= 500 and attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Grok API server error (status {e.response.status_code}), "
                        f"retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Grok API HTTP error: {e}")
                    raise
                    
            except httpx.TimeoutException as e:
                # Retry on timeout
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Grok API timeout, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Grok API timeout after {max_retries} attempts: {e}")
                    raise
                    
            except httpx.RequestError as e:
                # Retry on network errors
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(
                        f"Grok API network error, retrying in {delay:.1f}s (attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Grok API network error after {max_retries} attempts: {e}")
                    raise
                    
            except Exception as e:
                # Don't retry on other errors (validation, parsing, etc.)
                logger.error(f"Error calling Grok API: {e}")
                raise
        
        # Should not reach here, but just in case
        raise Exception(f"Failed to call Grok API after {max_retries} attempts")

    def _parse_response(self, response: str) -> AIDecision:
        """
        Parse Grok's JSON response into AIDecision with strict validation.
        
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
            try:
                data = json.loads(response)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Grok response as JSON: {e}")
                logger.debug(f"Response was: {response[:500]}...")
                raise ValueError(f"Invalid JSON format: {str(e)}")
            
            # Validate required fields
            required_fields = ["action", "confidence", "reasoning"]
            missing_fields = [f for f in required_fields if f not in data]
            if missing_fields:
                raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
            
            # Validate action type and value
            action = str(data["action"]).upper().strip()
            valid_actions = ["BUY", "SELL", "HOLD"]
            if action not in valid_actions:
                logger.warning(f"Invalid action '{action}', expected one of {valid_actions}. Defaulting to HOLD.")
                action = "HOLD"
            
            # Validate confidence type and range
            try:
                confidence = float(data["confidence"])
            except (ValueError, TypeError):
                raise ValueError(f"Confidence must be a number, got: {type(data['confidence'])}")
            
            if not (0 <= confidence <= 100):
                logger.warning(f"Confidence {confidence} out of range [0-100], clamping to valid range.")
                confidence = max(0.0, min(100.0, confidence))
            
            # Validate reasoning type
            reasoning = str(data.get("reasoning", "")).strip()
            if not reasoning:
                logger.warning("Empty reasoning provided, using default.")
                reasoning = "No reasoning provided by AI"
            
            # Validate risk_level
            risk_level = str(data.get("risk_level", "medium")).lower().strip()
            valid_risk_levels = ["low", "medium", "high"]
            if risk_level not in valid_risk_levels:
                logger.warning(f"Invalid risk_level '{risk_level}', defaulting to 'medium'.")
                risk_level = "medium"
            
            # Log validation success
            logger.debug(
                f"✅ JSON validation passed: action={action}, "
                f"confidence={confidence:.1f}%, risk={risk_level}"
            )
            
            # Create AIDecision
            return AIDecision(
                action=action,
                confidence=confidence,
                reasoning=reasoning,
                risk_level=risk_level,
                additional_context={
                    "validation_passed": True,
                    "original_response": response[:200]  # Store first 200 chars for debugging
                }
            )
            
        except ValueError as e:
            logger.error(f"Validation error in Grok response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return AIDecision(
                action="HOLD",
                confidence=0.0,
                reasoning=f"Validation failed: {str(e)}",
                risk_level="high",
                additional_context={"validation_passed": False, "error": str(e)}
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing Grok response: {e}")
            logger.debug(f"Response was: {response[:500]}...")
            return AIDecision(
                action="HOLD",
                confidence=0.0,
                reasoning=f"Error parsing response: {str(e)}",
                risk_level="high",
                additional_context={"validation_passed": False, "error": str(e)}
            )

    def _validate_decision(
        self,
        decision: AIDecision,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validate decision logic against market conditions and indicators.
        
        Args:
            decision: AI decision to validate
            symbol: Trading symbol
            market_data: Current market data
            technical_indicators: Technical indicators
            
        Returns:
            Dict with 'is_valid' (bool) and 'warnings' (list of strings)
        """
        warnings = []
        is_valid = True
        
        rsi = technical_indicators.get("rsi", 50)
        ema_20 = technical_indicators.get("ema_20", 0)
        ema_50 = technical_indicators.get("ema_50", 0)
        current_price = market_data.get("price", 0)
        trend_strength = technical_indicators.get("trend_strength", 0)
        volume_ratio = technical_indicators.get("volume_ratio", 1.0)
        btc_trend = market_data.get("btc_trend", "").lower()
        
        # Validate BUY decisions
        if decision.action == "BUY":
            # Check RSI overbought condition
            if rsi > 75:
                warnings.append(f"RSI {rsi:.1f} is overbought (>75) - risky BUY")
                is_valid = False
            
            # Check RSI oversold (actually good for BUY, but validate confidence)
            if rsi < 30 and decision.confidence < 70:
                warnings.append(f"RSI {rsi:.1f} is oversold but confidence {decision.confidence:.1f}% is low")
            
            # Check bearish trend
            if ema_20 < ema_50 and trend_strength > 2:
                warnings.append(f"Bearish trend (EMA20 < EMA50, strength: {trend_strength:.2f}%) - counter-trend BUY")
                if decision.confidence > 80:
                    warnings.append("High confidence BUY in bearish trend is suspicious")
                    is_valid = False
            
            # Check price below both EMAs
            if current_price < ema_20 and current_price < ema_50:
                warnings.append("Price below both EMAs - strong bearish signal")
                if decision.confidence > 75:
                    warnings.append("High confidence BUY below EMAs is suspicious")
                    is_valid = False
            
            # Check BTC correlation
            if btc_trend == "bearish" and decision.confidence > 85:
                warnings.append("High confidence BUY during bearish BTC market")
            
            # Check low volume
            if volume_ratio < 0.7:
                warnings.append(f"Low volume (ratio: {volume_ratio:.2f}x) - weak interest")
                if decision.confidence > 80:
                    warnings.append("High confidence with low volume is suspicious")
            
            # Check confidence vs conditions
            if decision.confidence > 90:
                # Very high confidence should have strong signals
                if rsi < 40 or rsi > 60:
                    warnings.append(f"Very high confidence ({decision.confidence:.1f}%) but RSI {rsi:.1f} is not optimal")
                if ema_20 <= ema_50:
                    warnings.append(f"Very high confidence but bearish EMA trend")
        
        # Validate SELL decisions
        elif decision.action == "SELL":
            # Check RSI oversold condition
            if rsi < 25:
                warnings.append(f"RSI {rsi:.1f} is oversold (<25) - risky SELL")
            
            # Check bullish trend
            if ema_20 > ema_50 and trend_strength > 2:
                warnings.append(f"Bullish trend (EMA20 > EMA50, strength: {trend_strength:.2f}%) - counter-trend SELL")
        
        # Validate HOLD decisions
        elif decision.action == "HOLD":
            # HOLD is usually safe, but check if conditions are too good to hold
            if rsi > 70 and ema_20 > ema_50 and decision.confidence > 60:
                warnings.append("Strong bullish signals but HOLD - might miss opportunity")
        
        # General validations
        if decision.confidence > 95:
            warnings.append(f"Extremely high confidence {decision.confidence:.1f}% - unusual, verify reasoning")
        
        if decision.confidence < 20 and decision.action == "BUY":
            warnings.append("Very low confidence BUY - should probably be HOLD")
            is_valid = False
        
        # Check reasoning quality
        reasoning_lower = decision.reasoning.lower()
        if len(decision.reasoning) < 20:
            warnings.append("Reasoning is too short - might be incomplete")
        
        # Log validation result
        if warnings:
            logger.debug(
                f"Decision validation for {symbol}: "
                f"{'✅ VALID' if is_valid else '❌ INVALID'} - "
                f"{len(warnings)} warning(s)"
            )
            for warning in warnings:
                logger.debug(f"  ⚠️  {warning}")
        else:
            logger.debug(f"✅ Decision validation for {symbol}: VALID (no warnings)")
        
        return {
            "is_valid": is_valid,
            "warnings": warnings,
            "validation_timestamp": datetime.utcnow().isoformat()
        }
    
    async def _request_clarification(
        self,
        symbol: str,
        market_data: Dict[str, Any],
        technical_indicators: Dict[str, float],
        original_decision: AIDecision,
        validation_result: Dict[str, Any]
    ) -> AIDecision:
        """
        Request clarification from Grok when original decision fails validation.
        
        Args:
            symbol: Trading symbol
            market_data: Market data
            technical_indicators: Technical indicators
            original_decision: Original decision that failed validation
            validation_result: Validation result with warnings
            
        Returns:
            New AIDecision from Grok
        """
        clarification_prompt = f"""Your previous decision for {symbol} failed logical validation.

ORIGINAL DECISION:
- Action: {original_decision.action}
- Confidence: {original_decision.confidence}%
- Reasoning: {original_decision.reasoning}

VALIDATION WARNINGS:
{chr(10).join(f"- {w}" for w in validation_result['warnings'])}

CURRENT CONDITIONS:
- RSI: {technical_indicators.get('rsi', 0):.1f}
- EMA20: ${technical_indicators.get('ema_20', 0):.2f}
- EMA50: ${technical_indicators.get('ema_50', 0):.2f}
- Price: ${market_data.get('price', 0):.2f}
- Trend: {'Bullish' if technical_indicators.get('ema_20', 0) > technical_indicators.get('ema_50', 0) else 'Bearish'}

Please reconsider your decision. Address the validation warnings in your reasoning.
If the warnings are valid concerns, you should:
- Lower confidence if conditions are not ideal
- Change to HOLD if risk is too high
- Provide stronger reasoning if you maintain your original decision

Provide your REVISED decision in JSON format as specified."""
        
        try:
            logger.debug(f"Requesting clarification from Grok for {symbol}")
            response, usage_info = await self._call_grok_api(clarification_prompt)
            logger.debug(f"Clarification API: tokens={usage_info.get('total_tokens', 0)}")
            decision = self._parse_response(response)
            decision.additional_context = decision.additional_context or {}
            decision.additional_context["is_clarification"] = True
            decision.additional_context["original_decision"] = original_decision.to_dict()
            return decision
        except Exception as e:
            logger.error(f"Error requesting clarification: {e}")
            # Return safe HOLD decision
            return AIDecision(
                action="HOLD",
                confidence=30.0,
                reasoning=f"Clarification request failed: {str(e)}",
                risk_level="high"
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self.client.aclose()
        logger.debug("Grok client closed")

    async def select_trading_symbols(
        self,
        candidates: List[Dict[str, Any]],
        max_symbols: int = 2,
        market_phase: Optional[str] = None
    ) -> List[str]:
        """
        Use Grok to select the most promising trading symbols from candidates.
        
        Args:
            candidates: List of symbol data with metrics
            max_symbols: Maximum number of symbols to select
            market_phase: Current market phase (bullish/bearish/sideways)
            
        Returns:
            List of selected symbol names
        """
        try:
            # Pre-filter: Remove coins with volume < $50M or ATR > 150% of average
            filtered_candidates = self._pre_filter_candidates(candidates)
            
            if not filtered_candidates:
                logger.warning("All candidates filtered out by pre-filters")
                return []
            
            logger.info(f"Pre-filtered: {len(candidates)} -> {len(filtered_candidates)} candidates")
            
            # Determine market phase if not provided
            if market_phase is None:
                market_phase = "sideways"  # Default fallback
            
            system_prompt = """You are a cryptocurrency market expert specializing in symbol selection.

Your task is to analyze market data and select the 1-2 BEST symbols for short-term trading (24 hours).

SELECTION CRITERIA:
1. High volume = good liquidity (prefer > $50M daily volume)
2. Moderate volatility (ATR 3-8%) = good profit potential without excessive risk
3. RSI between 35-65 = not overbought/oversold (avoid RSI > 80 or < 20)
4. Positive momentum indicators
5. Avoid symbols with extreme movements (pump & dump risk)
6. Consider current market phase when selecting

FEW-SHOT EXAMPLES:

Example 1 (GOOD selection - coin later gained):
Input: BTC/USDT: Volume=$2.5B, Price=$43,200, 24h Change=+2.1%, ATR=3.2%, RSI=58.5
Market Phase: Bullish
Output: {"selected_coins": ["BTCUSDT"], "reasoning": "High liquidity, optimal RSI zone, moderate volatility, bullish market alignment", "confidence": 0.88, "risk_level": "low", "avoid_coins": []}

Example 2 (BAD selection - coin later dumped):
Input: MEME/USDT: Volume=$45M, Price=$0.0012, 24h Change=+45%, ATR=25%, RSI=85.2
Market Phase: Bearish
Output: {"selected_coins": [], "reasoning": "Extreme volatility (ATR 25%), overbought (RSI 85), pump risk, low volume", "confidence": 0.15, "risk_level": "high", "avoid_coins": ["MEMEUSDT"]}

Example 3 (NEUTRAL selection - sideways):
Input: ETH/USDT: Volume=$1.2B, Price=$2,450, 24h Change=-0.5%, ATR=4.1%, RSI=52.3
Market Phase: Sideways
Output: {"selected_coins": ["ETHUSDT"], "reasoning": "Good liquidity, neutral RSI, stable in sideways market, moderate risk", "confidence": 0.72, "risk_level": "medium", "avoid_coins": []}

ВАЖНО: Отвечай ИСКЛЮЧИТЕЛЬНО валидным JSON в следующем формате, без какого-либо дополнительного текста, markdown, объяснений или кода:

{
  "selected_coins": ["BTCUSDT", "ETHUSDT"],
  "reasoning": "Краткое, но точное объяснение выбора (максимум 200 слов)",
  "confidence": 0.85,
  "risk_level": "low|medium|high",
  "avoid_coins": ["SOLUSDT", "DOGEUSDT"]
}

Если не уверен или данных недостаточно — верни пустой список selected_coins."""

            # Build prompt using dedicated function
            user_message = self._build_prompt({
                'candidates': filtered_candidates,
                'max_symbols': max_symbols,
                'market_phase': market_phase
            })
            
            # Call Grok API with low temperature for deterministic selection
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.1,  # Low temperature for more deterministic selection
                "max_tokens": 500
            }
            
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                json=payload
            )
            
            response.raise_for_status()
            data = response.json()
            content = data['choices'][0]['message']['content'].strip()
            
            # Parse response with new structured format
            selection = self._parse_symbol_selection(content)
            
            # Post-filter: Remove coins with RSI > 80 or < 20
            filtered_selection = self._post_filter_selection(selection, filtered_candidates)
            
            logger.info(
                f"Grok selected: {', '.join(filtered_selection['symbols'])} - "
                f"{filtered_selection['reasoning']} (confidence: {filtered_selection.get('confidence', 0):.2f})"
            )
            
            return filtered_selection['symbols'][:max_symbols]
            
        except Exception as e:
            logger.error(f"Error in symbol selection: {e}")
            # Fallback: return top volume symbols
            fallback = [c['symbol'] for c in candidates[:max_symbols]]
            logger.warning(f"Using fallback selection: {', '.join(fallback)}")
            return fallback

    def _pre_filter_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Pre-filter candidates before sending to Grok.
        Remove coins with volume < $50M or ATR > 150% of average.
        
        Args:
            candidates: List of candidate symbols
            
        Returns:
            Filtered list of candidates
        """
        if not candidates:
            return []
        
        # Calculate average ATR
        atr_values = [c.get('atr_pct', 0) for c in candidates if c.get('atr_pct', 0) > 0]
        avg_atr = sum(atr_values) / len(atr_values) if atr_values else 0
        max_atr = avg_atr * 1.5  # 150% of average
        
        filtered = []
        for candidate in candidates:
            volume_24h = candidate.get('volume_24h', 0)
            atr_pct = candidate.get('atr_pct', 0)
            
            # Filter: volume >= $50M and ATR <= 150% of average
            if volume_24h >= 50_000_000 and atr_pct <= max_atr:
                filtered.append(candidate)
            else:
                logger.debug(
                    f"Filtered out {candidate.get('symbol', 'N/A')}: "
                    f"volume=${volume_24h:,.0f} (< $50M) or ATR={atr_pct:.2f}% (> {max_atr:.2f}%)"
                )
        
        return filtered
    
    def _post_filter_selection(
        self, 
        selection: Dict[str, Any], 
        candidates: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Post-filter Grok's selection: remove coins with RSI > 80 or < 20.
        
        Args:
            selection: Grok's selection result
            candidates: Original candidates list for RSI lookup
            
        Returns:
            Filtered selection
        """
        selected_symbols = selection.get('symbols', [])
        if not selected_symbols:
            return selection
        
        # Create lookup for RSI values
        candidate_map = {c['symbol']: c for c in candidates}
        
        filtered_symbols = []
        warnings = []
        
        for symbol in selected_symbols:
            # Convert format if needed (BTCUSDT -> BTC/USDT)
            lookup_symbol = symbol
            if '/' not in symbol and 'USDT' in symbol:
                # Try to find matching candidate
                for cand_symbol in candidate_map.keys():
                    if cand_symbol.replace('/', '') == symbol:
                        lookup_symbol = cand_symbol
                        break
            
            candidate = candidate_map.get(lookup_symbol, {})
            rsi = candidate.get('rsi_30m', candidate.get('rsi', 50))
            
            # Filter: RSI should be between 20 and 80
            if rsi > 80:
                warnings.append(f"{symbol}: RSI {rsi:.1f} > 80 (overbought)")
                logger.warning(f"⚠️  Post-filter: Ignoring {symbol} - RSI {rsi:.1f} > 80 (overbought)")
            elif rsi < 20:
                warnings.append(f"{symbol}: RSI {rsi:.1f} < 20 (oversold)")
                logger.warning(f"⚠️  Post-filter: Ignoring {symbol} - RSI {rsi:.1f} < 20 (oversold)")
            else:
                filtered_symbols.append(symbol)
        
        if warnings:
            selection['warnings'] = warnings
        
        selection['symbols'] = filtered_symbols
        return selection

    def _build_prompt(self, data: dict) -> str:
        """
        Build prompt for symbol selection with structured output instructions.
        
        Args:
            data: Dictionary containing:
                - candidates: List of candidate symbols with metrics
                - max_symbols: Maximum number of symbols to select
                - market_phase: Current market phase (bullish/bearish/sideways)
        
        Returns:
            Complete prompt string for Grok
        """
        candidates = data.get('candidates', [])
        max_symbols = data.get('max_symbols', 2)
        market_phase = data.get('market_phase', 'sideways')
        
        prompt_parts = [
            "You are a cryptocurrency market expert specializing in symbol selection.",
            "",
            "Your task is to analyze market data and select the 1-2 BEST symbols for short-term trading (24 hours).",
            "",
            "SELECTION CRITERIA:",
            "1. High volume = good liquidity (prefer > $50M daily volume)",
            "2. Moderate volatility (ATR 3-8%) = good profit potential without excessive risk",
            "3. RSI between 35-65 = not overbought/oversold (avoid RSI > 80 or < 20)",
            "4. Positive momentum indicators",
            "5. Avoid symbols with extreme movements (pump & dump risk)",
            "6. Consider current market phase when selecting",
            "",
            "FEW-SHOT EXAMPLES:",
            "",
            "Previous example (GOOD selection - coin later gained):",
            "Input: BTC/USDT: Volume=$2.5B, Price=$43,200, 24h Change=+2.1%, ATR=3.2%, RSI=58.5, Market Phase: Bullish",
            "Output: {\"selected_coins\": [\"BTCUSDT\"], \"reasoning\": \"High liquidity, optimal RSI zone (58.5), moderate volatility (ATR 3.2%), bullish market alignment. Strong fundamentals with stable momentum.\", \"confidence\": 0.88, \"risk_level\": \"low\", \"avoid_coins\": []}",
            "",
            "Previous example (BAD selection - coin later dumped):",
            "Input: MEME/USDT: Volume=$45M, Price=$0.0012, 24h Change=+45%, ATR=25%, RSI=85.2, Market Phase: Bearish",
            "Output: {\"selected_coins\": [], \"reasoning\": \"Extreme volatility (ATR 25%) indicates pump risk. Overbought RSI (85.2) suggests imminent correction. Low volume ($45M) below threshold. Bearish market phase adds additional risk.\", \"confidence\": 0.15, \"risk_level\": \"high\", \"avoid_coins\": [\"MEMEUSDT\"]}",
            "",
            f"Current market phase: {market_phase}. Consider this when making your selection.",
            "",
            "CANDIDATES:"
        ]
        
        # Add candidates table
        for i, candidate in enumerate(candidates[:20], 1):
            prompt_parts.append(
                f"{i}. {candidate['symbol']}: "
                f"Volume=${candidate.get('volume_24h', 0):,.0f}, "
                f"Price=${candidate.get('price', 0):.2f}, "
                f"24h Change={candidate.get('change_pct_24h', 0):+.2f}%, "
                f"Volatility(ATR)={candidate.get('atr_pct', 0):.2f}%, "
                f"RSI={candidate.get('rsi_30m', candidate.get('rsi', 50)):.1f}"
            )
        
        prompt_parts.extend([
            "",
            f"Analyze these {len(candidates)} coins and select the best {max_symbols} for trading in the next 24 hours.",
            "",
            "CRITICAL INSTRUCTION: Your response MUST be EXCLUSIVELY valid JSON in the exact format below.",
            "Do NOT include any additional text, explanations, markdown formatting, code blocks, or greetings.",
            "If no coin meets the criteria or confidence is low — return an empty array for selected_coins.",
            "",
            "REQUIRED JSON FORMAT:",
            "{",
            '  "selected_coins": ["BTCUSDT", "ETHUSDT"],',
            '  "reasoning": "Brief but precise explanation of your choice (maximum 150 words)",',
            '  "confidence": 0.82,',
            '  "risk_level": "low|medium|high",',
            '  "avoid_coins": ["XRPUSDT", "DOGEUSDT"]  // optional: coins you strongly recommend avoiding',
            "}",
            "",
            "Remember: Output ONLY the JSON object. No markdown, no code blocks, no additional text."
        ])
        
        return "\n".join(prompt_parts)

    def _parse_symbol_selection(self, response: str) -> Dict[str, Any]:
        """
        Parse Grok's symbol selection response with new structured format.
        
        Args:
            response: JSON string from Grok
            
        Returns:
            Dictionary with selected symbols, reasoning, confidence, etc.
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
            
            # Support both old and new format
            selected_coins = data.get('selected_coins', [])
            selected_symbols = data.get('selected_symbols', [])
            
            # Convert coin format to symbol format if needed (BTCUSDT -> BTC/USDT)
            symbols = []
            for coin in (selected_coins if selected_coins else selected_symbols):
                if '/' not in coin and 'USDT' in coin:
                    # Convert BTCUSDT to BTC/USDT
                    base = coin.replace('USDT', '')
                    symbols.append(f"{base}/USDT")
                else:
                    symbols.append(coin)
            
            return {
                'symbols': symbols,
                'reasoning': data.get('reasoning', 'No reasoning provided'),
                'confidence': data.get('confidence', 0.5),
                'risk_level': data.get('risk_level', 'medium'),
                'avoid_coins': data.get('avoid_coins', [])
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse symbol selection: {e}")
            logger.debug(f"Response was: {response}")
            # Fallback: try to extract symbols from text
            return {
                'symbols': [],
                'reasoning': f"Parse error: {str(e)}",
                'confidence': 0.0,
                'risk_level': 'high'
            }
