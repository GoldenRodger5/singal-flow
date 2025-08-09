#!/usr/bin/env python3
"""
Minimal WebSocket Test Server
To isolate the WebSocket issue
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import asyncio

app = FastAPI()

# Enable CORS for WebSocket
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "WebSocket Test Server"}

@app.websocket("/ws/test")
async def websocket_test(websocket: WebSocket):
    """Simple WebSocket test endpoint"""
    await websocket.accept()
    print("✅ WebSocket connection accepted")
    
    try:
        # Send initial message
        await websocket.send_text(json.dumps({
            'type': 'connected',
            'message': 'WebSocket test connection successful'
        }))
        
        while True:
            try:
                message = await websocket.receive_text()
                print(f"📥 Received: {message}")
                
                # Echo back
                await websocket.send_text(json.dumps({
                    'type': 'echo',
                    'message': f'Echo: {message}'
                }))
                
            except WebSocketDisconnect:
                print("🔌 WebSocket disconnected")
                break
                
    except Exception as e:
        print(f"❌ WebSocket error: {e}")

if __name__ == "__main__":
    print("🧪 Starting minimal WebSocket test server...")
    uvicorn.run(app, host="0.0.0.0", port=8001)
