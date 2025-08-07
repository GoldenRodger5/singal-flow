"""
Real-Time WebSocket Trading Engine
Non-blocking real-time data processing for day trading
Based on Polygon.io WebSocket best practices
"""

import asyncio
import json
import websockets
from typing import Dict, List, Callable, Optional
from datetime import datetime
from loguru import logger
from dataclasses import dataclass, asdict
import os

@dataclass
class RealTimeQuote:
    """Real-time quote from WebSocket."""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    exchange: str
    conditions: List[str]

@dataclass  
class RealTimeTrade:
    """Real-time trade from WebSocket."""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    exchange: str
    conditions: List[str]

class RealTimeWebSocketEngine:
    """
    High-performance WebSocket engine for day trading.
    Implements non-blocking pattern from Polygon.io tutorials.
    """
    
    def __init__(self):
        self.api_key = os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        self.websocket = None
        self.is_connected = False
        self.subscriptions = set()
        self.message_queue = asyncio.Queue()
        self.quote_handlers = []
        self.trade_handlers = []
        self.anomaly_handlers = []
        
        # Performance metrics
        self.messages_received = 0
        self.last_message_time = None
        
        logger.info("⚡ Real-Time WebSocket Engine initialized")
    
    async def connect(self):
        """Connect to Polygon.io WebSocket."""
        try:
            ws_url = f"wss://socket.polygon.io/stocks"
            
            self.websocket = await websockets.connect(ws_url)
            self.is_connected = True
            
            # Authenticate
            auth_message = {
                "action": "auth",
                "params": self.api_key
            }
            await self.websocket.send(json.dumps(auth_message))
            
            # Start message processing
            asyncio.create_task(self._message_handler())
            asyncio.create_task(self._process_messages())
            
            logger.info("🔗 WebSocket connected to Polygon.io")
            return True
            
        except Exception as e:
            logger.error(f"WebSocket connection failed: {e}")
            return False
    
    async def subscribe_quotes(self, symbols: List[str]):
        """Subscribe to real-time quotes."""
        if not self.is_connected:
            await self.connect()
        
        # Subscribe to quotes
        subscribe_message = {
            "action": "subscribe",
            "params": f"Q.{',Q.'.join(symbols)}"
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscriptions.update([f"Q.{symbol}" for symbol in symbols])
        
        logger.info(f"📡 Subscribed to real-time quotes: {symbols}")
    
    async def subscribe_trades(self, symbols: List[str]):
        """Subscribe to real-time trades."""
        if not self.is_connected:
            await self.connect()
        
        # Subscribe to trades
        subscribe_message = {
            "action": "subscribe", 
            "params": f"T.{',T.'.join(symbols)}"
        }
        
        await self.websocket.send(json.dumps(subscribe_message))
        self.subscriptions.update([f"T.{symbol}" for symbol in symbols])
        
        logger.info(f"📊 Subscribed to real-time trades: {symbols}")
    
    async def _message_handler(self):
        """Handle incoming WebSocket messages (non-blocking)."""
        try:
            async for message in self.websocket:
                # Add to queue for processing (non-blocking)
                await self.message_queue.put(message)
                self.messages_received += 1
                self.last_message_time = datetime.now()
                
        except websockets.exceptions.ConnectionClosed:
            logger.warning("WebSocket connection closed")
            self.is_connected = False
        except Exception as e:
            logger.error(f"WebSocket message handler error: {e}")
    
    async def _process_messages(self):
        """Process queued messages asynchronously."""
        while True:
            try:
                # Get message from queue (non-blocking)
                message = await self.message_queue.get()
                
                # Process message
                await self._handle_message(message)
                self.message_queue.task_done()
                
            except Exception as e:
                logger.error(f"Message processing error: {e}")
                await asyncio.sleep(0.01)  # Brief pause on error
    
    async def _handle_message(self, message: str):
        """Handle individual WebSocket message."""
        try:
            data = json.loads(message)
            
            # Handle different message types
            for item in data:
                if item.get('ev') == 'Q':  # Quote
                    await self._handle_quote(item)
                elif item.get('ev') == 'T':  # Trade
                    await self._handle_trade(item)
                elif item.get('ev') == 'status':
                    logger.info(f"WebSocket status: {item.get('message')}")
                    
        except json.JSONDecodeError:
            logger.debug(f"Non-JSON message: {message[:100]}")
        except Exception as e:
            logger.error(f"Message handling error: {e}")
    
    async def _handle_quote(self, quote_data: Dict):
        """Handle real-time quote."""
        try:
            quote = RealTimeQuote(
                symbol=quote_data.get('sym', ''),
                price=float(quote_data.get('ap', 0)),  # Ask price
                size=int(quote_data.get('as', 0)),     # Ask size
                timestamp=datetime.fromtimestamp(quote_data.get('t', 0) / 1000),
                exchange=str(quote_data.get('x', '')),
                conditions=quote_data.get('c', [])
            )
            
            # Notify quote handlers
            for handler in self.quote_handlers:
                asyncio.create_task(handler(quote))
            
            # Check for anomalies (non-blocking)
            asyncio.create_task(self._check_quote_anomaly(quote))
            
        except Exception as e:
            logger.error(f"Quote handling error: {e}")
    
    async def _handle_trade(self, trade_data: Dict):
        """Handle real-time trade."""
        try:
            trade = RealTimeTrade(
                symbol=trade_data.get('sym', ''),
                price=float(trade_data.get('p', 0)),
                size=int(trade_data.get('s', 0)),
                timestamp=datetime.fromtimestamp(trade_data.get('t', 0) / 1000),
                exchange=str(trade_data.get('x', '')),
                conditions=trade_data.get('c', [])
            )
            
            # Notify trade handlers
            for handler in self.trade_handlers:
                asyncio.create_task(handler(trade))
            
            # Check for anomalies (non-blocking) 
            asyncio.create_task(self._check_trade_anomaly(trade))
            
        except Exception as e:
            logger.error(f"Trade handling error: {e}")
    
    async def _check_quote_anomaly(self, quote: RealTimeQuote):
        """Check quote for anomalies (non-blocking)."""
        try:
            # Quick anomaly check based on price movement
            # More sophisticated checks can be added here
            
            # Example: Large price gap detection
            # This is a simplified example - real implementation would be more complex
            pass
            
        except Exception as e:
            logger.error(f"Quote anomaly check error: {e}")
    
    async def _check_trade_anomaly(self, trade: RealTimeTrade):
        """Check trade for anomalies (non-blocking)."""
        try:
            # Check for unusual trade size
            if trade.size > 100000:  # Large block trade
                anomaly = {
                    'type': 'large_block_trade',
                    'symbol': trade.symbol,
                    'price': trade.price,
                    'size': trade.size,
                    'timestamp': trade.timestamp,
                    'confidence': 85
                }
                
                # Notify anomaly handlers
                for handler in self.anomaly_handlers:
                    asyncio.create_task(handler(anomaly))
            
        except Exception as e:
            logger.error(f"Trade anomaly check error: {e}")
    
    def add_quote_handler(self, handler: Callable):
        """Add handler for real-time quotes."""
        self.quote_handlers.append(handler)
    
    def add_trade_handler(self, handler: Callable):
        """Add handler for real-time trades."""
        self.trade_handlers.append(handler)
    
    def add_anomaly_handler(self, handler: Callable):
        """Add handler for detected anomalies."""
        self.anomaly_handlers.append(handler)
    
    async def get_connection_stats(self) -> Dict:
        """Get WebSocket connection statistics."""
        return {
            'connected': self.is_connected,
            'messages_received': self.messages_received,
            'subscriptions': len(self.subscriptions),
            'last_message_ago': (datetime.now() - self.last_message_time).total_seconds() if self.last_message_time else None,
            'queue_size': self.message_queue.qsize()
        }
    
    async def disconnect(self):
        """Disconnect WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("📴 WebSocket disconnected")

# Example usage handlers
async def handle_real_time_quote(quote: RealTimeQuote):
    """Example quote handler."""
    logger.debug(f"📈 {quote.symbol}: ${quote.price:.2f} @ {quote.timestamp}")

async def handle_real_time_trade(trade: RealTimeTrade):
    """Example trade handler."""
    logger.debug(f"💰 {trade.symbol}: {trade.size} shares @ ${trade.price:.2f}")

async def handle_anomaly(anomaly: Dict):
    """Example anomaly handler."""
    logger.info(f"🚨 ANOMALY: {anomaly['type']} in {anomaly['symbol']} - Confidence: {anomaly['confidence']}%")

# Global instance - will be created when needed
websocket_engine = None

def get_websocket_engine():
    """Get or create the websocket engine instance."""
    global websocket_engine
    if websocket_engine is None:
        websocket_engine = RealTimeWebSocketEngine()
    return websocket_engine

# Export
__all__ = ['get_websocket_engine', 'websocket_engine', 'RealTimeWebSocketEngine', 'RealTimeQuote', 'RealTimeTrade']
