"""
Reasoning Agent - Generates natural language explanations for trading decisions.
"""
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

from services.config import Config


class ReasoningAgent:
    """Agent that generates human-readable explanations for trading decisions."""
    
    def __init__(self):
        """Initialize the reasoning agent."""
        self.config = Config()
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize AI clients
        if self.config.OPENAI_API_KEY:
            self.openai_client = openai.OpenAI(api_key=self.config.OPENAI_API_KEY)
        if self.config.CLAUDE_API_KEY:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=self.config.CLAUDE_API_KEY)
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic client: {e}")
                self.anthropic_client = None
    
    async def explain_trade(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                           recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a comprehensive explanation for a trading recommendation."""
        try:
            ticker = setup.get('ticker', 'Unknown')
            logger.info(f"Generating trade explanation for {ticker}")
            
            explanation = {
                'ticker': ticker,
                'timestamp': datetime.now().isoformat(),
                'summary': '',
                'technical_reasoning': '',
                'sentiment_reasoning': '',
                'risk_analysis': '',
                'confidence_reasoning': '',
                'plain_english': ''
            }
            
            # Generate AI explanation if available
            if self.openai_client:
                ai_explanation = await self._generate_openai_explanation(setup, sentiment, recommendation)
                explanation.update(ai_explanation)
            elif self.anthropic_client:
                ai_explanation = await self._generate_claude_explanation(setup, sentiment, recommendation)
                explanation.update(ai_explanation)
            else:
                # Fallback to template-based explanation
                template_explanation = self._generate_template_explanation(setup, sentiment, recommendation)
                explanation.update(template_explanation)
            
            # Always generate a concise summary
            explanation['summary'] = self._generate_summary(setup, sentiment, recommendation)
            
            logger.info(f"Trade explanation generated for {ticker}")
            return explanation
            
        except Exception as e:
            logger.error(f"Error generating trade explanation: {e}")
            return self._generate_fallback_explanation(setup, sentiment, recommendation)
    
    async def _generate_openai_explanation(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                         recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation using OpenAI."""
        try:
            ticker = setup.get('ticker', 'Unknown')
            
            prompt = self._build_explanation_prompt(setup, sentiment, recommendation)
            
            response = await asyncio.to_thread(
                self.openai_client.chat.completions.create,
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert day trader explaining trade setups in clear, concise language."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            return self._parse_ai_explanation(content)
            
        except Exception as e:
            logger.error(f"Error with OpenAI explanation: {e}")
            return self._generate_template_explanation(setup, sentiment, recommendation)
    
    async def _generate_claude_explanation(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                         recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation using Claude."""
        try:
            prompt = self._build_explanation_prompt(setup, sentiment, recommendation)
            
            response = await asyncio.to_thread(
                self.anthropic_client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            content = response.content[0].text
            return self._parse_ai_explanation(content)
            
        except Exception as e:
            logger.error(f"Error with Claude explanation: {e}")
            return self._generate_template_explanation(setup, sentiment, recommendation)
    
    def _build_explanation_prompt(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                 recommendation: Dict[str, Any]) -> str:
        """Build the prompt for AI explanation generation."""
        ticker = setup.get('ticker', 'Unknown')
        entry = recommendation.get('entry', 0)
        stop_loss = recommendation.get('stop_loss', 0)
        take_profit = recommendation.get('take_profit', 0)
        confidence = recommendation.get('confidence', 0)
        
        # Technical signals
        technical_signals = recommendation.get('technical_signals', [])
        technical_text = ', '.join(technical_signals) if technical_signals else 'Multiple technical factors'
        
        # Sentiment signals
        sentiment_signals = recommendation.get('sentiment_signals', [])
        sentiment_text = ', '.join(sentiment_signals) if sentiment_signals else 'Neutral sentiment'
        
        # Risk/reward
        rr_ratio = recommendation.get('risk_reward_ratio', 0)
        
        prompt = f"""
        Explain this day trading setup for {ticker} in clear, professional language:

        TRADE DETAILS:
        - Entry: ${entry}
        - Stop Loss: ${stop_loss}
        - Take Profit: ${take_profit}
        - Risk/Reward: {rr_ratio}:1
        - Confidence: {confidence}/10

        TECHNICAL ANALYSIS:
        {technical_text}

        SENTIMENT ANALYSIS:
        {sentiment_text}

        SETUP TYPE:
        {recommendation.get('setup_type', 'Multi-factor setup')}

        Please provide:
        1. A brief summary (1-2 sentences)
        2. Technical reasoning (2-3 sentences explaining the technical setup)
        3. Sentiment impact (1-2 sentences about news/sentiment)
        4. Risk analysis (1-2 sentences about risk management)
        5. Plain English explanation suitable for WhatsApp (2-3 sentences, casual but professional)

        Keep it concise, actionable, and easy to understand.
        """
        
        return prompt
    
    def _parse_ai_explanation(self, content: str) -> Dict[str, Any]:
        """Parse AI-generated explanation into structured format."""
        try:
            explanation = {
                'technical_reasoning': '',
                'sentiment_reasoning': '',
                'risk_analysis': '',
                'plain_english': content  # Default to full content
            }
            
            # Try to extract structured sections
            lines = content.split('\n')
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Identify sections
                if any(keyword in line.lower() for keyword in ['summary', 'brief']):
                    current_section = 'summary'
                    explanation['summary'] = line
                elif any(keyword in line.lower() for keyword in ['technical', 'setup']):
                    current_section = 'technical_reasoning'
                elif any(keyword in line.lower() for keyword in ['sentiment', 'news']):
                    current_section = 'sentiment_reasoning'
                elif any(keyword in line.lower() for keyword in ['risk', 'management']):
                    current_section = 'risk_analysis'
                elif any(keyword in line.lower() for keyword in ['plain', 'whatsapp', 'casual']):
                    current_section = 'plain_english'
                else:
                    # Add to current section
                    if current_section and current_section in explanation:
                        if explanation[current_section]:
                            explanation[current_section] += ' ' + line
                        else:
                            explanation[current_section] = line
            
            # Clean up and ensure we have content
            for key in explanation:
                if not explanation[key] and key != 'summary':
                    explanation[key] = content[:200] + '...' if len(content) > 200 else content
            
            return explanation
            
        except Exception as e:
            logger.error(f"Error parsing AI explanation: {e}")
            return {'plain_english': content}
    
    def _generate_template_explanation(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                     recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate explanation using templates as fallback."""
        try:
            ticker = setup.get('ticker', 'Unknown')
            setup_type = recommendation.get('setup_type', 'Multi-factor')
            confidence = recommendation.get('confidence', 0)
            
            # Technical reasoning
            technical_signals = recommendation.get('technical_signals', [])
            if technical_signals:
                technical_reasoning = f"Technical analysis shows {', '.join(technical_signals[:3])}. "
            else:
                technical_reasoning = "Multiple technical indicators align for this setup. "
            
            # Add setup-specific reasoning
            if 'VWAP' in setup_type:
                technical_reasoning += f"{ticker} has bounced cleanly off VWAP support with good volume confirmation."
            elif 'RSI' in setup_type:
                technical_reasoning += f"{ticker} is oversold with RSI showing potential reversal signals."
            elif 'MACD' in setup_type:
                technical_reasoning += f"{ticker} shows bullish momentum with MACD crossover confirmation."
            else:
                technical_reasoning += f"{ticker} meets multiple technical criteria for a high-probability setup."
            
            # Sentiment reasoning
            news_sentiment = sentiment.get('news_sentiment', 'neutral')
            news_count = sentiment.get('news_count', 0)
            
            if news_count > 0:
                if news_sentiment == 'bullish':
                    sentiment_reasoning = f"Recent news sentiment is positive with {news_count} bullish articles supporting upward momentum."
                elif news_sentiment == 'bearish':
                    sentiment_reasoning = f"News sentiment is mixed with {news_count} articles, requiring careful risk management."
                else:
                    sentiment_reasoning = f"Market sentiment is neutral with {news_count} recent news items providing context."
            else:
                sentiment_reasoning = "No significant news catalyst, relying on technical analysis for entry timing."
            
            # Risk analysis
            rr_ratio = recommendation.get('risk_reward_ratio', 0)
            stop_loss = recommendation.get('stop_loss', 0)
            
            risk_analysis = f"Risk is controlled with {rr_ratio:.1f}:1 reward-to-risk ratio. "
            risk_analysis += f"Stop loss at ${stop_loss:.2f} limits downside to 2-3% while targeting 4-6% upside."
            
            # Confidence reasoning
            if confidence >= 8:
                confidence_reasoning = "High confidence setup with multiple confirming signals and strong technical foundation."
            elif confidence >= 7:
                confidence_reasoning = "Good confidence level with solid technical setup and manageable risk."
            else:
                confidence_reasoning = "Moderate confidence requiring careful position sizing and strict risk management."
            
            # Plain English summary
            entry = recommendation.get('entry', 0)
            take_profit = recommendation.get('take_profit', 0)
            
            plain_english = f"🎯 {ticker} @ ${entry:.2f} - {setup_type} with {confidence:.1f}/10 confidence. "
            plain_english += f"Target ${take_profit:.2f} ({rr_ratio:.1f}:1 R:R). "
            plain_english += f"Technical indicators align well and risk is controlled."
            
            return {
                'technical_reasoning': technical_reasoning,
                'sentiment_reasoning': sentiment_reasoning,
                'risk_analysis': risk_analysis,
                'confidence_reasoning': confidence_reasoning,
                'plain_english': plain_english
            }
            
        except Exception as e:
            logger.error(f"Error generating template explanation: {e}")
            return self._generate_fallback_explanation(setup, sentiment, recommendation)
    
    def _generate_summary(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                         recommendation: Dict[str, Any]) -> str:
        """Generate a concise summary of the trade."""
        try:
            ticker = setup.get('ticker', 'Unknown')
            setup_type = recommendation.get('setup_type', 'Setup')
            confidence = recommendation.get('confidence', 0)
            rr_ratio = recommendation.get('risk_reward_ratio', 0)
            
            return f"{ticker} {setup_type} - {confidence:.1f}/10 confidence, {rr_ratio:.1f}:1 R:R"
            
        except Exception:
            return f"Trade setup for {setup.get('ticker', 'Unknown')}"
    
    def _generate_fallback_explanation(self, setup: Dict[str, Any], sentiment: Dict[str, Any], 
                                     recommendation: Dict[str, Any]) -> Dict[str, Any]:
        """Generate basic explanation as last resort."""
        ticker = setup.get('ticker', 'Unknown')
        confidence = recommendation.get('confidence', 0)
        
        basic_explanation = f"Trade setup identified for {ticker} with {confidence:.1f}/10 confidence based on technical analysis."
        
        return {
            'summary': f"{ticker} trade setup - {confidence:.1f}/10 confidence",
            'technical_reasoning': basic_explanation,
            'sentiment_reasoning': "Sentiment analysis completed.",
            'risk_analysis': "Risk managed with appropriate position sizing.",
            'confidence_reasoning': f"Confidence level: {confidence:.1f}/10",
            'plain_english': basic_explanation
        }
    
    async def explain_exit_signal(self, ticker: str, exit_reason: str, 
                                 current_price: float, entry_price: float) -> str:
        """Generate explanation for trade exit."""
        try:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            if exit_reason == 'take_profit':
                return f"🎯 {ticker} hit take profit target at ${current_price:.2f} (+{pnl_percent:.1f}%)"
            elif exit_reason == 'stop_loss':
                return f"🛑 {ticker} stopped out at ${current_price:.2f} ({pnl_percent:.1f}%)"
            elif exit_reason == 'time_exit':
                return f"⏰ {ticker} time-based exit at ${current_price:.2f} ({pnl_percent:+.1f}%)"
            else:
                return f"📤 {ticker} manual exit at ${current_price:.2f} ({pnl_percent:+.1f}%)"
                
        except Exception as e:
            logger.error(f"Error explaining exit: {e}")
            return f"Trade exit: {ticker} at ${current_price:.2f}"
    
    async def generate_daily_insight(self, trades: List[Dict[str, Any]], 
                                   performance: Dict[str, Any]) -> str:
        """Generate daily trading insight."""
        try:
            total_trades = len(trades)
            win_rate = performance.get('win_rate', 0) * 100
            avg_rr = performance.get('average_rr', 0)
            pnl = performance.get('daily_pnl', 0)
            
            if total_trades == 0:
                return "📊 No trades executed today. Market conditions may not have met our criteria."
            
            insight = f"📊 Daily Summary: {total_trades} trades, {win_rate:.0f}% win rate, "
            insight += f"{avg_rr:.1f}:1 avg R:R, {pnl:+.1f}% PnL"
            
            if win_rate >= 60:
                insight += "\n✅ Strong performance today with good trade selection."
            elif win_rate >= 40:
                insight += "\n⚖️ Decent performance, continue following the plan."
            else:
                insight += "\n🔍 Below-average day, review setups for improvements."
            
            return insight
            
        except Exception as e:
            logger.error(f"Error generating daily insight: {e}")
            return "📊 Daily trading summary completed."
