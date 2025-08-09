#!/usr/bin/env python3
"""
WebSocket Endpoint Test Script
Tests the fixed /ws/trades endpoint
"""
import asyncio
import websockets
import json
import sys

async def test_websocket_trades():
    """Test the /ws/trades WebSocket endpoint"""
    try:
        print("🔌 Connecting to WebSocket endpoint: ws://localhost:8000/ws/trades")
        
        async with websockets.connect("ws://localhost:8000/ws/trades") as websocket:
            print("✅ WebSocket connection established!")
            
            # Wait for initial message
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(initial_message)
                print(f"📥 Received initial message: {data['type']}")
                print(f"   Data: {len(data.get('data', []))} trades")
                
            except asyncio.TimeoutError:
                print("⚠️ No initial message received (timeout)")
            
            # Send a test message
            print("📤 Sending test message: get_trades")
            await websocket.send("get_trades")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(response)
                print(f"📥 Received response: {data['type']}")
                print(f"   Data: {len(data.get('data', []))} trades")
                
                return True
                
            except asyncio.TimeoutError:
                print("⚠️ No response received (timeout)")
                return False
                
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")
        return False

async def test_websocket_health():
    """Test the /ws/health WebSocket endpoint for comparison"""
    try:
        print("🔌 Testing health WebSocket for comparison: ws://localhost:8000/ws/health")
        
        async with websockets.connect("ws://localhost:8000/ws/health") as websocket:
            print("✅ Health WebSocket connection established!")
            
            # Wait for initial message
            try:
                initial_message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                data = json.loads(initial_message)
                print(f"📥 Health WebSocket working: {data['type']}")
                return True
                
            except asyncio.TimeoutError:
                print("⚠️ No health message received")
                return False
                
    except Exception as e:
        print(f"❌ Health WebSocket failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Testing WebSocket Endpoints")
    print("=" * 50)
    
    # Test health WebSocket first
    health_result = await test_websocket_health()
    print()
    
    # Test trades WebSocket (the one we fixed)
    trades_result = await test_websocket_trades()
    print()
    
    # Summary
    print("📊 Test Results:")
    print(f"   Health WebSocket: {'✅ Working' if health_result else '❌ Failed'}")
    print(f"   Trades WebSocket: {'✅ Working' if trades_result else '❌ Failed'}")
    
    if trades_result:
        print("🎉 WebSocket fix is working!")
        return True
    else:
        print("❌ WebSocket fix needs more work")
        return False

if __name__ == "__main__":
    try:
        result = asyncio.run(main())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("🛑 Test interrupted")
        sys.exit(1)
