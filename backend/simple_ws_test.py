#!/usr/bin/env python3
"""
Simple WebSocket Test using websocket-client
"""
import websocket
import json
import threading
import time

def on_message(ws, message):
    """Handle received messages"""
    print(f"📥 Received: {message}")

def on_error(ws, error):
    """Handle errors"""
    print(f"❌ WebSocket error: {error}")

def on_close(ws, close_status_code, close_msg):
    """Handle connection close"""
    print(f"🔌 WebSocket closed: {close_status_code} - {close_msg}")

def on_open(ws):
    """Handle connection open"""
    print("✅ WebSocket connection opened")
    
    def run():
        # Send initial message after connection
        time.sleep(1)
        print("📤 Sending: get_trades")
        ws.send("get_trades")
        time.sleep(2)
        ws.close()
    
    thread = threading.Thread(target=run)
    thread.start()

def test_websocket_client():
    """Test WebSocket using websocket-client library"""
    print("🧪 Testing WebSocket with websocket-client")
    print("=" * 50)
    
    # Enable debug for websocket-client
    websocket.enableTrace(True)
    
    ws = websocket.WebSocketApp(
        "ws://localhost:8000/ws/trades",
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
        on_open=on_open
    )
    
    print("🔌 Starting WebSocket connection...")
    ws.run_forever()
    print("🏁 WebSocket test completed")

if __name__ == "__main__":
    test_websocket_client()
