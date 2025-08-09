#!/usr/bin/env python3
"""
Test the minimal WebSocket server
"""
import asyncio
import websockets
import json

async def test_minimal_websocket():
    """Test the minimal WebSocket server"""
    try:
        print("🔌 Connecting to minimal WebSocket: ws://localhost:8001/ws/test")
        
        async with websockets.connect("ws://localhost:8001/ws/test") as websocket:
            print("✅ Connection established!")
            
            # Wait for initial message
            initial_message = await websocket.recv()
            data = json.loads(initial_message)
            print(f"📥 Initial: {data}")
            
            # Send test message
            await websocket.send("Hello WebSocket!")
            
            # Wait for echo
            echo_message = await websocket.recv()
            data = json.loads(echo_message)
            print(f"📥 Echo: {data}")
            
            return True
            
    except Exception as e:
        print(f"❌ Minimal WebSocket failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_minimal_websocket())
    print(f"Result: {'✅ Success' if result else '❌ Failed'}")
