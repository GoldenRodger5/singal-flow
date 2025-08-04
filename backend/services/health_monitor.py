"""
Production Health Monitoring System for Signal Flow
Real-time system health, error tracking, and performance monitoring
"""
import os
import psutil
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from loguru import logger
import json
import threading
import time

from services.database_manager import get_db_manager
from services.alpaca_trading import AlpacaTradingService


class SystemHealthMonitor:
    """Comprehensive system health monitoring"""
    
    def __init__(self):
        # Initialize trading service with error handling
        try:
            self.trading_service = AlpacaTradingService()
            logger.info("✅ Trading service initialized successfully")
        except Exception as e:
            logger.error(f"❌ Trading service initialization failed: {e}")
            self.trading_service = None
            
        self.health_status = {
            'overall': 'healthy',
            'components': {},
            'last_check': None,
            'uptime_start': datetime.now(timezone.utc)
        }
        self.websocket_connections = set()
        self.monitoring_active = True
        self.start_monitoring()
    
    async def check_trading_api_health(self) -> Dict:
        """Check Alpaca API connectivity and account status"""
        try:
            if not self.trading_service:
                return {
                    'status': 'unhealthy',
                    'error': 'Trading service not initialized',
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
                
            account = await self.trading_service.get_account()
            positions = await self.trading_service.get_positions()
            
            return {
                'status': 'healthy',
                'account_status': account.status if account else 'unknown',
                'buying_power': float(account.buying_power) if account else 0,
                'positions_count': len(positions) if positions else 0,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Trading API health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    async def check_database_health(self) -> Dict:
        """Check MongoDB connectivity and performance"""
        try:
            db_manager = get_db_manager()
            
            # Test basic connectivity
            await db_manager.async_db.admin.command('ping')
            
            # Get database stats
            stats = await db_manager.async_db.command('dbStats')
            
            # Check recent activity
            recent_trades = await db_manager.get_active_trades()
            
            return {
                'status': 'healthy',
                'collections': stats.get('collections', 0),
                'data_size': stats.get('dataSize', 0),
                'active_trades': len(recent_trades),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    def check_system_resources(self) -> Dict:
        """Check system CPU, memory, and disk usage"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status = 'healthy'
            if cpu_percent > 80 or memory.percent > 85 or disk.percent > 90:
                status = 'warning'
            if cpu_percent > 95 or memory.percent > 95 or disk.percent > 95:
                status = 'critical'
            
            return {
                'status': status,
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available': memory.available,
                'disk_percent': disk.percent,
                'disk_free': disk.free,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"System resource check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    async def check_ai_agents_health(self) -> Dict:
        """Check if AI agents are running and responsive"""
        try:
            db_manager = get_db_manager()
            
            # Check recent AI decisions from database
            recent_decisions = await db_manager.get_recent_decisions(limit=10)
            
            # Check if we have recent activity (last 5 minutes)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)
            recent_activity = [
                d for d in recent_decisions 
                if d.get('timestamp', datetime.min.replace(tzinfo=timezone.utc)) > cutoff_time
            ]
            
            agent_status = 'healthy' if recent_activity else 'warning'
            
            return {
                'status': agent_status,
                'recent_decisions': len(recent_activity),
                'total_decisions_today': len(recent_decisions),
                'last_decision': recent_decisions[0].get('timestamp').isoformat() if recent_decisions else None,
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            logger.error(f"AI agents health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
    
    async def perform_full_health_check(self) -> Dict:
        """Perform comprehensive health check of all components"""
        try:
            # Run all health checks concurrently
            trading_health, db_health, ai_health = await asyncio.gather(
                self.check_trading_api_health(),
                self.check_database_health(),
                self.check_ai_agents_health(),
                return_exceptions=True
            )
            
            system_health = self.check_system_resources()
            
            # Determine overall health
            components = {
                'trading_api': trading_health,
                'database': db_health,
                'ai_agents': ai_health,
                'system_resources': system_health
            }
            
            # Calculate overall status
            statuses = [comp.get('status', 'unhealthy') for comp in components.values()]
            if 'unhealthy' in statuses:
                overall_status = 'unhealthy'
            elif 'warning' in statuses:
                overall_status = 'warning'
            else:
                overall_status = 'healthy'
            
            self.health_status = {
                'overall': overall_status,
                'components': components,
                'last_check': datetime.now(timezone.utc).isoformat(),
                'uptime': (datetime.now(timezone.utc) - self.health_status['uptime_start']).total_seconds()
            }
            
            # Log to database
            db_manager = get_db_manager()
            await db_manager.log_system_health(
                'overall_system', 
                overall_status,
                {'components': components}
            )
            
            return self.health_status
            
        except Exception as e:
            logger.error(f"Full health check failed: {e}")
            error_status = {
                'overall': 'unhealthy',
                'error': str(e),
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            self.health_status.update(error_status)
            return self.health_status
    
    async def broadcast_health_update(self):
        """Broadcast health updates to connected WebSocket clients"""
        if not self.websocket_connections:
            return
        
        health_data = await self.perform_full_health_check()
        message = json.dumps({
            'type': 'health_update',
            'data': health_data
        })
        
        # Send to all connected clients
        disconnected = set()
        for websocket in self.websocket_connections:
            try:
                await websocket.send_text(message)
            except WebSocketDisconnect:
                disconnected.add(websocket)
            except Exception as e:
                logger.warning(f"Failed to send health update to client: {e}")
                disconnected.add(websocket)
        
        # Remove disconnected clients
        self.websocket_connections -= disconnected
    
    def start_monitoring(self):
        """Start background health monitoring"""
        def monitor_loop():
            while self.monitoring_active:
                try:
                    # Run health check every 30 seconds
                    asyncio.run(self.broadcast_health_update())
                    time.sleep(30)
                except Exception as e:
                    logger.error(f"Health monitoring error: {e}")
                    time.sleep(10)  # Shorter retry interval on error
        
        monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        monitor_thread.start()
        logger.info("Health monitoring started")
    
    async def add_websocket_connection(self, websocket: WebSocket):
        """Add WebSocket connection for real-time updates"""
        self.websocket_connections.add(websocket)
        logger.info(f"WebSocket connected. Total connections: {len(self.websocket_connections)}")
    
    async def remove_websocket_connection(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        self.websocket_connections.discard(websocket)
        logger.info(f"WebSocket disconnected. Total connections: {len(self.websocket_connections)}")
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        logger.info("Health monitoring stopped")


# Global health monitor instance
health_monitor = SystemHealthMonitor()
