"""
Telegram notification service for trading alerts.
"""
import asyncio
import aiohttp
from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger

from services.config import Config


class TelegramNotifier:
    """Service for sending trading alerts via Telegram."""
    
    def __init__(self):
        """Initialize the Telegram notifier."""
        self.config = Config()
        self.session = None
        self.daily_alert_count = 0
        self.max_daily_alerts = 50
        
        if not self.config.TELEGRAM_BOT_TOKEN or not self.config.TELEGRAM_CHAT_ID:
            logger.error("Telegram configuration missing - TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
            raise ValueError("Telegram credentials required for production deployment")
        
        logger.info("Telegram notifier initialized successfully")
    
    async def send_trade_alert(self, recommendation: Dict[str, Any], explanation: Dict[str, Any]) -> bool:
        """Send a trade alert via Telegram."""
        try:
            # Check daily limits
            if self.daily_alert_count >= self.max_daily_alerts:
                logger.warning("Daily Telegram alert limit reached")
                return False
            
            # Format the trade alert message
            message = self._format_trade_alert(recommendation, explanation)
            
            # Send the message
            success = await self._send_message(message)
            
            if success:
                self.daily_alert_count += 1
                logger.info(f"Trade alert sent for {recommendation.get('ticker')}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error sending trade alert: {e}")
            return False
    
    async def send_buy_notification(self, symbol: str, quantity: int, price: float, order_id: str = None, 
                                  predicted_target: float = None, confidence: float = None, 
                                  stop_loss: float = None, reasoning: str = None) -> bool:
        """Send a detailed buy order notification with price predictions via Telegram."""
        try:
            # Calculate predicted returns if target provided
            predicted_return = ""
            if predicted_target and price > 0:
                return_pct = ((predicted_target - price) / price) * 100
                predicted_return = f"\n🎯 **Predicted Target:** ${predicted_target:.2f} (+{return_pct:.1f}%)"
                
            # Add confidence rating
            confidence_text = ""
            if confidence:
                confidence_stars = "⭐" * int(confidence * 10) if confidence <= 1 else "⭐" * int(confidence)
                confidence_text = f"\n🤖 **AI Confidence:** {confidence:.1f}/10 {confidence_stars}"
            
            # Add stop loss info
            risk_text = ""
            if stop_loss and price > 0:
                risk_pct = ((price - stop_loss) / price) * 100
                risk_text = f"\n🛑 **Stop Loss:** ${stop_loss:.2f} (-{risk_pct:.1f}%)"
            
            # Add reasoning snippet
            reasoning_text = ""
            if reasoning:
                reasoning_text = f"\n\n💡 **AI Analysis:**\n{reasoning[:120]}..."
            
            message = f"""
🟢 **BUY ORDER EXECUTED** 🟢

📈 **Symbol:** {symbol}
📊 **Quantity:** {quantity:,} shares
💰 **Entry Price:** ${price:.2f}
💵 **Total Investment:** ${quantity * price:,.2f}{predicted_return}{confidence_text}{risk_text}
🆔 **Order ID:** {order_id or 'N/A'}
⏰ **Executed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}{reasoning_text}

📊 This is a PAPER TRADE (no real money involved)
🤖 Executed by autonomous SignalFlow AI system
            """.strip()
            
            success = await self._send_message(message)
            if success:
                logger.info(f"Enhanced buy notification sent for {symbol}: {quantity} shares @ ${price}")
            return success
            
        except Exception as e:
            logger.error(f"Error sending buy notification: {e}")
            return False
    
    async def send_sell_notification(self, symbol: str, quantity: int, price: float, pnl: float = None, 
                                   order_id: str = None, entry_price: float = None, 
                                   sell_reason: str = None, target_hit: bool = False) -> bool:
        """Send a detailed sell order notification with profit analysis via Telegram."""
        try:
            pnl_emoji = "🟢" if pnl and pnl > 0 else "🔴" if pnl and pnl < 0 else "⚪"
            pnl_text = f"\n💰 **Realized P&L:** {pnl_emoji} ${pnl:,.2f}" if pnl is not None else ""
            
            # Calculate return percentage
            return_text = ""
            if entry_price and entry_price > 0:
                return_pct = ((price - entry_price) / entry_price) * 100
                return_emoji = "📈" if return_pct > 0 else "📉"
                return_text = f"\n{return_emoji} **Return:** {return_pct:+.2f}% (${entry_price:.2f} → ${price:.2f})"
            
            # Add sell reason
            reason_text = ""
            if sell_reason:
                if target_hit:
                    reason_text = f"\n🎯 **Exit Reason:** Target achieved! {sell_reason}"
                else:
                    reason_text = f"\n📊 **Exit Reason:** {sell_reason}"
            
            # Performance assessment
            performance_text = ""
            if pnl is not None:
                if pnl > 1000:
                    performance_text = "\n🎉 **Excellent trade!** Major profit achieved"
                elif pnl > 100:
                    performance_text = "\n👍 **Good trade!** Solid profit"
                elif pnl > 0:
                    performance_text = "\n✅ **Profitable trade** completed"
                elif pnl > -100:
                    performance_text = "\n⚠️ **Small loss** - within risk tolerance"
                else:
                    performance_text = "\n🛑 **Loss contained** - risk management active"
            
            message = f"""
🔴 **SELL ORDER EXECUTED** 🔴

📉 **Symbol:** {symbol}
📊 **Quantity:** {quantity:,} shares
💰 **Exit Price:** ${price:.2f}
💵 **Total Proceeds:** ${quantity * price:,.2f}{return_text}{pnl_text}{reason_text}
🆔 **Order ID:** {order_id or 'N/A'}
⏰ **Executed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}{performance_text}

📊 This is a PAPER TRADE (no real money involved)
🤖 Executed by autonomous SignalFlow AI system
            """.strip()
            
            success = await self._send_message(message)
            if success:
                logger.info(f"Enhanced sell notification sent for {symbol}: {quantity} shares @ ${price}")
            return success
            
        except Exception as e:
            logger.error(f"Error sending sell notification: {e}")
            return False
    
    async def send_portfolio_update(self, total_value: float, cash: float, pnl_today: float = None) -> bool:
        """Send portfolio update notification."""
        try:
            pnl_emoji = "🟢" if pnl_today and pnl_today > 0 else "🔴" if pnl_today and pnl_today < 0 else "⚪"
            pnl_text = f"\n📈 **Today's P&L:** {pnl_emoji} ${pnl_today:,.2f}" if pnl_today is not None else ""
            
            message = f"""
📊 **PORTFOLIO UPDATE** 📊

💰 **Total Value:** ${total_value:,.2f}
💵 **Cash:** ${cash:,.2f}
📈 **Invested:** ${total_value - cash:,.2f}{pnl_text}
⏰ **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

📊 This is a PAPER TRADING account
🤖 Autonomous trading system active
            """.strip()
            
            success = await self._send_message(message)
            if success:
                logger.info(f"Portfolio update sent: ${total_value:,.2f} total value")
            return success
            
        except Exception as e:
            logger.error(f"Error sending portfolio update: {e}")
            return False
    
    async def send_exit_alert(self, ticker: str, exit_reason: str, 
                            current_price: float, entry_price: float, pnl: float) -> bool:
        """Send a trade exit alert."""
        try:
            message = self._format_exit_alert(ticker, exit_reason, current_price, entry_price, pnl)
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending exit alert: {e}")
            return False
    
    async def send_daily_summary(self, summary: Dict[str, Any]) -> bool:
        """Send daily trading summary."""
        try:
            message = self._format_daily_summary(summary)
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {e}")
            return False
    
    async def send_message(self, message: str) -> bool:
        """Send a custom message via Telegram."""
        try:
            return await self._send_message(message)
            
        except Exception as e:
            logger.error(f"Error sending custom message: {e}")
            return False
    
    async def send_system_alert(self, alert_type: str, message: str) -> bool:
        """Send system alerts (errors, warnings, etc.)."""
        try:
            formatted_message = self._format_system_alert(alert_type, message)
            return await self._send_message(formatted_message)
            
        except Exception as e:
            logger.error(f"Error sending system alert: {e}")
            return False
    
    async def send_trading_session_start(self, session_info: Dict[str, Any] = None) -> bool:
        """Send notification when trading session starts."""
        try:
            portfolio_value = session_info.get('portfolio_value', 0) if session_info else 0
            cash_available = session_info.get('cash_available', 0) if session_info else 0
            watchlist_size = session_info.get('watchlist_size', 0) if session_info else 0
            market_conditions = session_info.get('market_conditions', 'Unknown') if session_info else 'Analyzing...'
            
            message = f"""
🟢 **TRADING SESSION STARTED** 🟢

🤖 **SignalFlow AI Bot:** ONLINE
📊 **Market Status:** ACTIVE
⏰ **Started:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

💰 **Portfolio Value:** ${portfolio_value:,.2f}
💵 **Cash Available:** ${cash_available:,.2f}
📈 **Buying Power:** ${cash_available:,.2f}
🎯 **Watchlist:** {watchlist_size} symbols

🌡️ **Market Conditions:** {market_conditions}
🔍 **AI Scanning:** Real-time market analysis active
📱 **Notifications:** Full alert mode enabled

🛡️ **Safety Mode:** Paper trading (no real money at risk)
⚡ **Ready for autonomous trading signals**

Good luck trading! 🚀
            """.strip()
            
            success = await self._send_message(message)
            if success:
                logger.info("Trading session start notification sent")
            return success
            
        except Exception as e:
            logger.error(f"Error sending trading session start notification: {e}")
            return False
    
    async def send_market_close_notification(self, daily_summary: Dict[str, Any] = None) -> bool:
        """Send notification when market closes and bot shuts down."""
        try:
            # Extract daily performance data
            if daily_summary:
                total_trades = daily_summary.get('total_trades', 0)
                winning_trades = daily_summary.get('winning_trades', 0)
                daily_pnl = daily_summary.get('daily_pnl', 0)
                best_trade = daily_summary.get('best_trade', {})
                worst_trade = daily_summary.get('worst_trade', {})
                portfolio_value = daily_summary.get('final_portfolio_value', 0)
            else:
                total_trades = winning_trades = daily_pnl = portfolio_value = 0
                best_trade = worst_trade = {}
            
            # Calculate win rate
            win_rate = (winning_trades / max(1, total_trades)) * 100 if total_trades > 0 else 0
            
            # Performance emoji and message
            if daily_pnl > 500:
                perf_emoji = "🎉"
                perf_message = "Outstanding trading day!"
            elif daily_pnl > 100:
                perf_emoji = "💰"
                perf_message = "Profitable day achieved!"
            elif daily_pnl > 0:
                perf_emoji = "✅"
                perf_message = "Positive day completed"
            elif daily_pnl > -100:
                perf_emoji = "⚠️"
                perf_message = "Minor loss - within tolerance"
            else:
                perf_emoji = "🔴"
                perf_message = "Challenging day - learning for tomorrow"
            
            # Best trade info
            best_trade_text = ""
            if best_trade and 'symbol' in best_trade:
                best_pnl = best_trade.get('pnl', 0)
                best_trade_text = f"\n🏆 **Best Trade:** {best_trade['symbol']} (+${best_pnl:.2f})"
            
            message = f"""
🔴 **MARKET CLOSED - TRADING SESSION ENDED** 🔴

🤖 **SignalFlow AI Bot:** SHUTTING DOWN
📊 **Market Status:** CLOSED
⏰ **Session Ended:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

📈 **Daily Performance Summary:**
{perf_emoji} **Overall:** {perf_message}
💰 **P&L Today:** ${daily_pnl:+,.2f}
📊 **Total Trades:** {total_trades}
🎯 **Win Rate:** {win_rate:.1f}% ({winning_trades}/{total_trades})
💼 **Portfolio Value:** ${portfolio_value:,.2f}{best_trade_text}

🌙 **System Status:**
🔕 **Notifications:** Reduced to critical only
🛌 **AI Scanning:** Paused until market open
📱 **Bot Status:** Standby mode active

🌅 **Next Session:** Tomorrow at market open
🛡️ **Safety:** All trades were paper trades (no real money)

Rest well - see you tomorrow! 💤
            """.strip()
            
            success = await self._send_message(message)
            if success:
                logger.info("Market close notification sent")
            return success
            
        except Exception as e:
            logger.error(f"Error sending market close notification: {e}")
            return False
    
    def _format_trade_alert(self, recommendation: Dict[str, Any], explanation: Dict[str, Any]) -> str:
        """Format a trade alert message."""
        try:
            ticker = recommendation.get('ticker', 'Unknown')
            entry = recommendation.get('entry', 0)
            stop_loss = recommendation.get('stop_loss', 0)
            take_profit = recommendation.get('take_profit', 0)
            confidence = recommendation.get('confidence', 0)
            rr_ratio = recommendation.get('risk_reward_ratio', 0)
            setup_type = recommendation.get('setup_type', 'Setup')
            
            # Get technical signals
            technical_signals = recommendation.get('technical_signals', [])
            signals_text = ', '.join(technical_signals[:3]) if technical_signals else 'Multiple factors'
            
            # Main alert
            message = f"🚨 *TRADE ALERT* 🚨\n\n"
            message += f"📈 *{ticker}* - {setup_type}\n"
            message += f"💰 Entry: ${entry:.2f}\n"
            message += f"🎯 Target: ${take_profit:.2f}\n"
            message += f"🛑 Stop: ${stop_loss:.2f}\n"
            message += f"⚖️ R:R: {rr_ratio:.1f}:1\n"
            message += f"🎲 Confidence: {confidence:.1f}/10\n\n"
            
            # Technical analysis
            message += f"📊 *Signals:* {signals_text}\n\n"
            
            # Plain English explanation
            plain_english = explanation.get('plain_english', '')
            if plain_english:
                message += f"💡 *Analysis:* {plain_english}\n\n"
            
            # Risk info
            position_size = recommendation.get('position_size', {})
            risk_percent = position_size.get('max_risk_per_trade', 0) * 100
            
            message += f"⚠️ *Risk:* {risk_percent:.1f}% of account\n"
            message += f"⏰ *Valid until:* {self._format_time(recommendation.get('valid_until', ''))}\n\n"
            
            # Action buttons (text-based)
            message += "Reply with:\n"
            message += "✅ *APPROVE* to execute\n"
            message += "❌ *SKIP* to ignore\n"
            message += "❓ *INFO* for more details"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting trade alert: {e}")
            return f"Trade alert for {recommendation.get('ticker', 'Unknown')} - Check app for details"
    
    def _format_exit_alert(self, ticker: str, exit_reason: str, 
                          current_price: float, entry_price: float, pnl: float) -> str:
        """Format a trade exit alert."""
        try:
            pnl_percent = ((current_price - entry_price) / entry_price) * 100
            
            if exit_reason == 'take_profit':
                emoji = "🎯"
                reason_text = "Target Hit"
            elif exit_reason == 'stop_loss':
                emoji = "🛑"
                reason_text = "Stop Loss"
            elif exit_reason == 'time_exit':
                emoji = "⏰"
                reason_text = "Time Exit"
            else:
                emoji = "📤"
                reason_text = "Manual Exit"
            
            message = f"{emoji} *TRADE CLOSED* {emoji}\n\n"
            message += f"📈 *{ticker}*\n"
            message += f"🔄 Reason: {reason_text}\n"
            message += f"💰 Exit Price: ${current_price:.2f}\n"
            message += f"📊 Entry Price: ${entry_price:.2f}\n"
            
            if pnl_percent >= 0:
                message += f"💚 P&L: +{pnl_percent:.1f}% (${pnl:+.2f})\n"
            else:
                message += f"❤️ P&L: {pnl_percent:.1f}% (${pnl:.2f})\n"
            
            message += f"⏰ {datetime.now().strftime('%H:%M')}"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting exit alert: {e}")
            return f"Trade closed: {ticker} at ${current_price:.2f}"
    
    def _format_daily_summary(self, summary: Dict[str, Any]) -> str:
        """Format the daily trading summary."""
        try:
            date = datetime.now().strftime("%Y-%m-%d")
            
            trades_count = summary.get('total_trades', 0)
            wins = summary.get('wins', 0)
            losses = summary.get('losses', 0)
            win_rate = summary.get('win_rate', 0) * 100
            avg_rr = summary.get('avg_rr', 0)
            daily_pnl = summary.get('daily_pnl', 0)
            daily_pnl_percent = summary.get('daily_pnl_percent', 0)
            
            message = f"📊 *DAILY SUMMARY* 📊\n"
            message += f"📅 {date}\n\n"
            
            if trades_count == 0:
                message += "🔍 No trades executed today\n"
                message += "Market conditions didn't meet our criteria\n\n"
                message += "📈 Watchlist updated and ready for tomorrow"
            else:
                message += f"🎯 *Trades:* {trades_count}\n"
                message += f"✅ *Wins:* {wins}\n"
                message += f"❌ *Losses:* {losses}\n"
                message += f"📊 *Win Rate:* {win_rate:.0f}%\n"
                message += f"⚖️ *Avg R:R:* {avg_rr:.1f}:1\n\n"
                
                if daily_pnl >= 0:
                    message += f"💰 *Daily P&L:* +${daily_pnl:.2f} (+{daily_pnl_percent:.1f}%)\n"
                else:
                    message += f"💸 *Daily P&L:* ${daily_pnl:.2f} ({daily_pnl_percent:.1f}%)\n"
                
                # Performance commentary
                if win_rate >= 60:
                    message += "\n🎉 Excellent trading day!"
                elif win_rate >= 40:
                    message += "\n👍 Solid performance today"
                else:
                    message += "\n🔄 Room for improvement"
            
            # Best setup of the day
            best_setup = summary.get('best_setup')
            if best_setup:
                message += f"\n\n⭐ *Best Setup:* {best_setup}"
            
            # Tomorrow's watchlist size
            watchlist_size = summary.get('tomorrows_watchlist', 0)
            message += f"\n\n🎯 Tomorrow's watchlist: {watchlist_size} stocks"
            
            return message
            
        except Exception as e:
            logger.error(f"Error formatting daily summary: {e}")
            return "📊 Daily trading summary - Check app for details"
    
    def _format_system_alert(self, alert_type: str, message: str) -> str:
        """Format system alerts."""
        try:
            timestamp = datetime.now().strftime("%H:%M")
            
            if alert_type == 'error':
                emoji = "🚨"
                prefix = "SYSTEM ERROR"
            elif alert_type == 'warning':
                emoji = "⚠️"
                prefix = "WARNING"
            elif alert_type == 'info':
                emoji = "ℹ️"
                prefix = "INFO"
            else:
                emoji = "📢"
                prefix = "ALERT"
            
            formatted = f"{emoji} *{prefix}* {emoji}\n\n"
            formatted += f"{message}\n\n"
            formatted += f"⏰ {timestamp}"
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error formatting system alert: {e}")
            return f"System alert: {message}"
    
    def _format_time(self, iso_time: str) -> str:
        """Format ISO time string to readable format."""
        try:
            if not iso_time:
                return "30 min"
            
            dt = datetime.fromisoformat(iso_time.replace('Z', '+00:00'))
            return dt.strftime("%H:%M")
        except Exception:
            return "30 min"
    
    async def _send_message(self, message: str) -> bool:
        """Send a message via Telegram Bot API."""
        try:
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            url = f"https://api.telegram.org/bot{self.config.TELEGRAM_BOT_TOKEN}/sendMessage"
            
            payload = {
                'chat_id': self.config.TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'Markdown'
            }
            
            async with self.session.post(url, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    if result.get('ok'):
                        logger.info("Telegram message sent successfully")
                        return True
                    else:
                        logger.error(f"Telegram API error: {result.get('description')}")
                        return False
                else:
                    logger.error(f"HTTP error {response.status} sending Telegram message")
                    return False
            
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False
    
    async def test_connection(self) -> bool:
        """Test Telegram connection."""
        try:
            test_message = "🔬 Signal Flow Test Message\n\nConnection successful! ✅"
            return await self._send_message(test_message)
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
    
    def reset_daily_counter(self) -> None:
        """Reset daily alert counter."""
        self.daily_alert_count = 0
        logger.info("Daily Telegram alert counter reset")
    
    def get_remaining_alerts(self) -> int:
        """Get remaining alerts for today."""
        return max(0, self.max_daily_alerts - self.daily_alert_count)
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
