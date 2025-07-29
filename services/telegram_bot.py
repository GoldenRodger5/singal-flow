"""
Telegram Trading Bot Service for Signal Flow AI
Provides interactive trading notifications with approval buttons.
"""
import os
import requests
import asyncio
from loguru import logger
from typing import Dict, Any, Optional


class TelegramNotifier:
    """Telegram bot for interactive trading notifications."""
    
    def __init__(self):
        """Initialize the Telegram notifier."""
        self.bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
        self.chat_id = os.getenv('TELEGRAM_CHAT_ID')
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram bot not configured. Check TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in .env")
            self.enabled = False
        else:
            self.enabled = True
            logger.info("Telegram bot notifications enabled")
    
    async def send_trading_signal(self, recommendation: Dict[str, Any], explanation: str) -> bool:
        """Send a trading signal with interactive approval buttons."""
        if not self.enabled:
            return False
            
        try:
            ticker = recommendation.get('ticker', 'UNKNOWN')
            action = recommendation.get('action', 'BUY')
            entry = recommendation.get('entry', 0)
            stop_loss = recommendation.get('stop_loss', 0)
            take_profit = recommendation.get('take_profit', 0)
            confidence = recommendation.get('confidence', 0)
            position_size = recommendation.get('position_size', 0)
            
            # Calculate potential profit/loss
            profit_potential = ((take_profit - entry) / entry * 100) if entry > 0 else 0
            loss_potential = ((entry - stop_loss) / entry * 100) if entry > 0 else 0
            
            message = f"🚀 *TRADING SIGNAL DETECTED*\n\n"
            message += f"📊 *Symbol:* {ticker}\n"
            message += f"🎯 *Action:* {action}\n"
            message += f"💰 *Entry:* ${entry:.2f}\n"
            message += f"🎯 *Target:* ${take_profit:.2f} (+{profit_potential:.1f}%)\n"
            message += f"🛑 *Stop Loss:* ${stop_loss:.2f} (-{loss_potential:.1f}%)\n"
            message += f"📈 *Position Size:* ${position_size:.0f}\n"
            message += f"⭐ *Confidence:* {confidence}/10\n\n"
            message += f"🧠 *Analysis:*\n{explanation[:200]}..."
            
            # Create inline keyboard with action buttons
            keyboard = {
                "inline_keyboard": [
                    [
                        {"text": "✅ Execute Trade", "callback_data": f"execute_{ticker}"},
                        {"text": "❌ Skip Trade", "callback_data": f"skip_{ticker}"}
                    ],
                    [
                        {"text": "⏸️ Pause Trading", "callback_data": "pause_trading"},
                        {"text": "📊 Portfolio", "callback_data": "show_portfolio"}
                    ]
                ]
            }
            
            return await self._send_message(message, keyboard)
            
        except Exception as e:
            logger.error(f"Error sending trading signal: {e}")
            return False
    
    async def send_execution_update(self, ticker: str, action: str, status: str, details: Dict[str, Any] = None) -> bool:
        """Send update about trade execution."""
        if not self.enabled:
            return False
            
        try:
            status_emoji = "✅" if status == "success" else "❌"
            
            message = f"{status_emoji} *TRADE {action.upper()} {status.upper()}*\n\n"
            message += f"📊 *Symbol:* {ticker}\n"
            
            if details:
                if 'shares' in details:
                    message += f"📈 *Shares:* {details['shares']}\n"
                if 'price' in details:
                    message += f"💰 *Price:* ${details['price']:.2f}\n"
                if 'order_id' in details:
                    message += f"🆔 *Order ID:* {details['order_id']}\n"
            
            message += f"⏰ *Time:* {details.get('timestamp', 'Now')}"
            
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending execution update: {e}")
            return False
    
    async def send_profit_update(self, ticker: str, profit_loss: float, percentage: float, action: str = "SELL") -> bool:
        """Send profit/loss update."""
        if not self.enabled:
            return False
            
        try:
            emoji = "💰" if profit_loss > 0 else "📉"
            color = "🟢" if profit_loss > 0 else "🔴"
            
            message = f"{emoji} *TRADE CLOSED*\n\n"
            message += f"📊 *Symbol:* {ticker}\n"
            message += f"🎯 *Action:* {action}\n"
            message += f"{color} *P&L:* ${profit_loss:.2f} ({percentage:+.1f}%)\n"
            message += f"⏰ *Closed:* Now"
            
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending profit update: {e}")
            return False
    
    async def send_portfolio_summary(self, summary: Dict[str, Any]) -> bool:
        """Send portfolio summary."""
        if not self.enabled:
            return False
            
        try:
            total_value = summary.get('total_value', 0)
            daily_pnl = summary.get('daily_pnl', 0)
            daily_pnl_pct = summary.get('daily_pnl_pct', 0)
            positions = summary.get('positions', 0)
            
            pnl_emoji = "💰" if daily_pnl >= 0 else "📉"
            pnl_color = "🟢" if daily_pnl >= 0 else "🔴"
            
            message = f"📊 *PORTFOLIO SUMMARY*\n\n"
            message += f"💼 *Total Value:* ${total_value:,.2f}\n"
            message += f"{pnl_emoji} *Today's P&L:* {pnl_color} ${daily_pnl:+,.2f} ({daily_pnl_pct:+.1f}%)\n"
            message += f"📈 *Open Positions:* {positions}\n"
            message += f"⏰ *Updated:* Now"
            
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending portfolio summary: {e}")
            return False
    
    async def send_simple_message(self, text: str) -> bool:
        """Send a simple text message."""
        if not self.enabled:
            return False
            
        return await self._send_message(text)
    
    async def _send_message(self, text: str, reply_markup: Dict = None) -> bool:
        """Send message to Telegram."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'Markdown'
            }
            
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            response = requests.post(url, json=data)
            
            if response.status_code == 200:
                logger.debug("Telegram message sent successfully")
                return True
            else:
                logger.error(f"Failed to send Telegram message: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending Telegram message: {e}")
            return False
    
    async def wait_for_user_response(self, timeout_seconds: int = 300) -> Optional[str]:
        """Wait for user response to interactive message."""
        # This would require webhook setup for production
        # For now, we'll use polling or assume immediate execution
        logger.info(f"Waiting for user response (timeout: {timeout_seconds}s)")
        
        # In a full implementation, you'd set up webhook handling
        # For now, return None to indicate no response handling
        return None


class InteractiveTradingService:
    """Enhanced interactive trading service with Telegram integration."""
    
    def __init__(self):
        """Initialize interactive trading service."""
        self.telegram = TelegramNotifier()
        self.pending_trades = {}
    
    async def request_buy_confirmation(self, recommendation: Dict[str, Any], explanation: str) -> bool:
        """Request confirmation for a buy trade via Telegram."""
        try:
            # Send the trading signal with interactive buttons
            success = await self.telegram.send_trading_signal(recommendation, explanation)
            
            if not success:
                logger.warning("Failed to send Telegram notification, defaulting to auto-approve")
                return True  # Default behavior if Telegram fails
            
            # For now, we'll auto-approve after sending the notification
            # In production, you'd implement webhook handling for button responses
            ticker = recommendation.get('ticker', 'UNKNOWN')
            logger.info(f"Trading signal sent to Telegram for {ticker}")
            
            # Return True to proceed with trade (paper trading mode)
            return True
            
        except Exception as e:
            logger.error(f"Error in interactive trading confirmation: {e}")
            return False
