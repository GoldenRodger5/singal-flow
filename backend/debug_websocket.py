#!/usr/bin/env python3
"""
Detailed WebSocket Debug Test
"""
import asyncio
import websockets
import json
import traceback

async def test_websocket_detailed():
    """Test WebSocket with detailed debugging"""
    uri = "ws://localhost:8000/ws/trades"
    
    print(f"🔌 Attempting to connect to: {uri}")
    
    try:
        print("📡 Creating WebSocket connection...")
        websocket = await websockets.connect(
            uri,
            timeout=10,
            ping_interval=None,  # Disable ping to avoid interference
            close_timeout=5
        )
        
        print("✅ WebSocket connection established!")
        
        try:
            # Wait for initial message
            print("⏳ Waiting for initial message...")
            initial_message = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f"📥 Initial message received: {initial_message}")
            
            # Send test message
            print("📤 Sending test message: get_trades")
            await websocket.send("get_trades")
            
            # Wait for response
            print("⏳ Waiting for response...")
            response = await asyncio.wait_for(websocket.recv(), timeout=10)
            print(f"📥 Response received: {response}")
            
            print("🎉 WebSocket test successful!")
            return True
            
        except asyncio.TimeoutError:
            print("⏰ Timeout waiting for message")
            return False
            
        finally:
            await websocket.close()
            print("🔌 WebSocket connection closed")
            
    except websockets.exceptions.InvalidStatusCode as e:
        print(f"❌ Invalid status code: {e.status_code}")
        print(f"   Headers: {e.headers}")
        return False
        
    except websockets.exceptions.WebSocketException as e:
        print(f"❌ WebSocket exception: {e}")
        return False
        
    except Exception as e:
        print(f"❌ General exception: {e}")
        print(f"   Type: {type(e)}")
        traceback.print_exc()
        return False

async def test_regular_endpoint():
    """Test regular HTTP endpoint for comparison"""
    import aiohttp
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:8000/health") as response:
                print(f"🌐 HTTP health check: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"   Status: {data.get('status')}")
                    return True
                return False
                
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("🧪 Detailed WebSocket Debugging")
    print("=" * 50)
    
    # Test HTTP first
    http_ok = await test_regular_endpoint()
    print()
    
    # Test WebSocket
    ws_ok = await test_websocket_detailed()
    
    print("\n📊 Test Results:")
    print(f"   HTTP endpoint: {'✅ Working' if http_ok else '❌ Failed'}")
    print(f"   WebSocket endpoint: {'✅ Working' if ws_ok else '❌ Failed'}")

if __name__ == "__main__":
    asyncio.run(main())
