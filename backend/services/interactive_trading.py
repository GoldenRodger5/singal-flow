"""
Interactive Trading Service for WhatsApp confirmations.
Handles buy/sell confirmations via WhatsApp with fast response times.
"""
import asyncio
import time
from typing import Dict, Any, Optional, Set
from loguru import logger
import json
from datetime import datetime, timedelta

from services.config import Config
from services.twilio_whatsapp import WhatsAppNotifier
from services.alpaca_trading import AlpacaTradingService


class InteractiveTradingService:
    """Service for interactive trading with WhatsApp confirmations."""
    
    def __init__(self):
        """Initialize interactive trading service."""
        self.config = Config()
        self.whatsapp = WhatsAppNotifier()
        self.alpaca = AlpacaTradingService()
        self.pending_confirmations: Dict[str, Dict[str, Any]] = {}
        self.confirmation_responses: Dict[str, str] = {}
        
        # Affirmative phrases for confirmation
        self.affirmative_phrases = {
            'yes', 'y', 'buy', 'go', 'execute', 'confirm', 'ok', 'okay', 
            'proceed', 'do it', 'send it', 'place order', 'buy it', 'sell it',
            'sell', 'exit', 'close', 'take profit', 'stop out', '✅', 'green light'
        }
        
        # Negative phrases for rejection
        self.negative_phrases = {
            'no', 'n', 'cancel', 'stop', 'abort', 'skip', 'pass', 'reject',
            'dont', "don't", 'negative', 'nope', 'nah', '❌', 'red light'
        }
    
    async def request_buy_confirmation(self, recommendation: Dict[str, Any], explanation: str) -> bool:
        """Request buy confirmation via WhatsApp and wait for response."""
        try:
            ticker = recommendation['ticker']
            entry_price = recommendation['entry']
            stop_loss = recommendation['stop_loss']
            take_profit = recommendation['take_profit']
            confidence = recommendation['confidence']
            rr_ratio = recommendation['risk_reward_ratio']
            position_size = recommendation['position_size']['percentage'] * 100
            
            # Generate unique confirmation ID
            confirmation_id = f"BUY_{ticker}_{int(time.time())}"
            
            # Create confirmation message
            message = f"""🤖 SIGNAL FLOW - BUY CONFIRMATION NEEDED
            
📊 TICKER: {ticker}
💰 ENTRY: ${entry_price}
🛑 STOP: ${stop_loss}
🎯 TARGET: ${take_profit}
📈 R:R: {rr_ratio}:1
⭐ CONFIDENCE: {confidence}/10
💼 POSITION: {position_size:.1f}% of account

🧠 REASONING:
{explanation[:200]}...

⚡ RESPOND QUICKLY:
• Reply "YES" to BUY
• Reply "NO" to SKIP

⏰ Auto-expires in {self.config.TRADE_CONFIRMATION_TIMEOUT} seconds"""
            
            # Store pending confirmation
            self.pending_confirmations[confirmation_id] = {
                'type': 'buy',
                'recommendation': recommendation,
                'explanation': explanation,
                'timestamp': time.time(),
                'ticker': ticker
            }
            
            # Send WhatsApp message
            await self.whatsapp.send_message(message)
            logger.info(f"Buy confirmation requested for {ticker} (ID: {confirmation_id})")
            
            # Wait for response with timeout
            response = await self._wait_for_confirmation(confirmation_id)
            
            if response:
                return await self._process_buy_response(confirmation_id, response)
            else:
                logger.info(f"Buy confirmation for {ticker} timed out")
                await self.whatsapp.send_message(f"⏰ Buy confirmation for {ticker} expired. Opportunity missed.")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting buy confirmation: {e}")
            return False
    
    async def request_sell_confirmation(self, ticker: str, shares: int, reason: str) -> bool:
        """Request sell confirmation via WhatsApp."""
        try:
            # Get current position info
            position = self.alpaca.get_position(ticker)
            if not position:
                logger.error(f"No position found for {ticker}")
                return False
            
            current_price = position['market_value'] / position['shares']
            unrealized_pl = position['unrealized_pl']
            pl_percent = (unrealized_pl / position['cost_basis']) * 100
            
            # Generate unique confirmation ID
            confirmation_id = f"SELL_{ticker}_{int(time.time())}"
            
            # Create confirmation message
            message = f"""🤖 SIGNAL FLOW - SELL CONFIRMATION NEEDED

📊 TICKER: {ticker}
📈 SHARES: {shares}
💰 CURRENT PRICE: ${current_price:.2f}
💵 P&L: ${unrealized_pl:.2f} ({pl_percent:+.1f}%)

🎯 REASON: {reason}

⚡ RESPOND QUICKLY:
• Reply "YES" to SELL
• Reply "NO" to HOLD

⏰ Auto-expires in {self.config.TRADE_CONFIRMATION_TIMEOUT} seconds"""
            
            # Store pending confirmation
            self.pending_confirmations[confirmation_id] = {
                'type': 'sell',
                'ticker': ticker,
                'shares': shares,
                'reason': reason,
                'timestamp': time.time(),
                'position': position
            }
            
            # Send WhatsApp message
            await self.whatsapp.send_message(message)
            logger.info(f"Sell confirmation requested for {ticker} (ID: {confirmation_id})")
            
            # Wait for response with timeout
            response = await self._wait_for_confirmation(confirmation_id)
            
            if response:
                return await self._process_sell_response(confirmation_id, response)
            else:
                logger.info(f"Sell confirmation for {ticker} timed out")
                await self.whatsapp.send_message(f"⏰ Sell confirmation for {ticker} expired. Position held.")
                return False
                
        except Exception as e:
            logger.error(f"Error requesting sell confirmation: {e}")
            return False
    
    async def _wait_for_confirmation(self, confirmation_id: str) -> Optional[str]:
        """Wait for user response to confirmation request."""
        timeout = self.config.TRADE_CONFIRMATION_TIMEOUT
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Check if response received (would be set by webhook or polling)
            if confirmation_id in self.confirmation_responses:
                response = self.confirmation_responses.pop(confirmation_id)
                return response.lower().strip()
            
            # Small delay to prevent busy waiting
            await asyncio.sleep(0.5)
        
        return None
    
    async def _process_buy_response(self, confirmation_id: str, response: str) -> bool:
        """Process buy confirmation response."""
        try:
            confirmation = self.pending_confirmations.pop(confirmation_id, None)
            if not confirmation:
                return False
            
            ticker = confirmation['ticker']
            
            if self._is_affirmative(response):
                # Execute buy order
                order_result = await self.alpaca.place_buy_order(confirmation['recommendation'])
                
                if order_result:
                    await self.whatsapp.send_message(
                        f"✅ BUY ORDER EXECUTED\n"
                        f"📊 {ticker}: {order_result['shares']} shares\n"
                        f"💰 Order ID: {order_result['order_id']}\n"
                        f"🎯 Monitoring for exit signals..."
                    )
                    
                    # Add to execution monitor
                    from agents.execution_monitor_agent import ExecutionMonitorAgent
                    monitor = ExecutionMonitorAgent()
                    await monitor.add_trade({
                        'ticker': ticker,
                        'entry_price': confirmation['recommendation']['entry'],
                        'stop_loss': confirmation['recommendation']['stop_loss'],
                        'take_profit': confirmation['recommendation']['take_profit'],
                        'shares': order_result['shares'],
                        'order_id': order_result['order_id']
                    })
                    
                    logger.info(f"Buy order executed for {ticker}")
                    return True
                else:
                    await self.whatsapp.send_message(f"❌ Failed to execute buy order for {ticker}")
                    return False
            else:
                await self.whatsapp.send_message(f"👍 Okay, skipping {ticker} trade.")
                logger.info(f"Buy order declined for {ticker}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing buy response: {e}")
            return False
    
    async def _process_sell_response(self, confirmation_id: str, response: str) -> bool:
        """Process sell confirmation response."""
        try:
            confirmation = self.pending_confirmations.pop(confirmation_id, None)
            if not confirmation:
                return False
            
            ticker = confirmation['ticker']
            shares = confirmation['shares']
            
            if self._is_affirmative(response):
                # Execute sell order
                order_result = await self.alpaca.place_sell_order(ticker, shares)
                
                if order_result:
                    position = confirmation['position']
                    unrealized_pl = position['unrealized_pl']
                    
                    await self.whatsapp.send_message(
                        f"✅ SELL ORDER EXECUTED\n"
                        f"📊 {ticker}: {shares} shares sold\n"
                        f"💰 P&L: ${unrealized_pl:.2f}\n"
                        f"📋 Order ID: {order_result['order_id']}"
                    )
                    
                    logger.info(f"Sell order executed for {ticker}")
                    return True
                else:
                    await self.whatsapp.send_message(f"❌ Failed to execute sell order for {ticker}")
                    return False
            else:
                await self.whatsapp.send_message(f"👍 Okay, holding {ticker} position.")
                logger.info(f"Sell order declined for {ticker}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing sell response: {e}")
            return False
    
    def _is_affirmative(self, response: str) -> bool:
        """Check if response is affirmative."""
        response_clean = response.lower().strip()
        
        # Check exact matches
        if response_clean in self.affirmative_phrases:
            return True
        
        # Check if any affirmative phrase is contained in response
        for phrase in self.affirmative_phrases:
            if phrase in response_clean:
                return True
        
        return False
    
    def add_response(self, confirmation_id: str, response: str):
        """Add user response to confirmation (called by webhook or polling)."""
        self.confirmation_responses[confirmation_id] = response
        logger.info(f"Response received for {confirmation_id}: {response}")
    
    def get_pending_confirmations(self) -> Dict[str, Dict[str, Any]]:
        """Get all pending confirmations."""
        return self.pending_confirmations.copy()
    
    def cleanup_expired_confirmations(self):
        """Remove expired confirmations."""
        current_time = time.time()
        timeout = self.config.TRADE_CONFIRMATION_TIMEOUT
        
        expired_ids = [
            conf_id for conf_id, conf in self.pending_confirmations.items()
            if current_time - conf['timestamp'] > timeout
        ]
        
        for conf_id in expired_ids:
            del self.pending_confirmations[conf_id]
            if conf_id in self.confirmation_responses:
                del self.confirmation_responses[conf_id]
