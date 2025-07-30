#!/usr/bin/env python3
"""
Production Startup Script for Signal Flow Trading System
Starts all components with proper error handling and monitoring
"""
import os
import sys
import asyncio
import threading
import time
import subprocess
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

class ProductionLauncher:
    """Production launcher with health monitoring and auto-restart"""
    
    def __init__(self):
        self.processes = {}
        self.monitoring = True
        self.restart_attempts = {}
        self.max_restarts = 3
        
        # Configure logging
        logger.add(
            "logs/production.log",
            rotation="100 MB",
            retention="30 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
        )
    
    def check_requirements(self):
        """Check if all required environment variables and dependencies are available"""
        required_env_vars = [
            'ALPACA_API_KEY',
            'ALPACA_SECRET_KEY',
            'TELEGRAM_BOT_TOKEN',
            'OPENAI_API_KEY'
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing required environment variables: {missing_vars}")
            print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
            print("Please check your .env file and ensure all required variables are set.")
            return False
        
        # Check Python dependencies
        try:
            import fastapi
            import uvicorn
            import streamlit
            import pymongo
            import motor
            import alpaca
            logger.info("All required dependencies available")
        except ImportError as e:
            logger.error(f"Missing Python dependency: {e}")
            print(f"❌ Missing Python dependency: {e}")
            print("Please run: pip install -r requirements.txt")
            return False
        
        return True
    
    def start_mongodb(self):
        """Start MongoDB if not running (for local development)"""
        try:
            # Check if MongoDB is already running
            import pymongo
            client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=1000)
            client.admin.command('ping')
            logger.info("MongoDB is already running")
            return True
        except Exception:
            logger.info("Starting local MongoDB...")
            try:
                # Try to start MongoDB (macOS/Linux)
                subprocess.run(['brew', 'services', 'start', 'mongodb-community'], 
                             check=False, capture_output=True)
                time.sleep(3)  # Give MongoDB time to start
                
                # Verify it started
                client = pymongo.MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
                client.admin.command('ping')
                logger.info("MongoDB started successfully")
                return True
            except Exception as e:
                logger.warning(f"Could not start local MongoDB: {e}")
                logger.info("Assuming MongoDB is available via MONGODB_URL environment variable")
                return True
    
    def start_fastapi_server(self):
        """Start the FastAPI production server"""
        def run_server():
            try:
                port = int(os.getenv('PORT', 8000))
                logger.info(f"Starting FastAPI server on port {port}")
                
                process = subprocess.Popen([
                    sys.executable, '-m', 'uvicorn',
                    'production_api:app',
                    '--host', '0.0.0.0',
                    '--port', str(port),
                    '--workers', '1',
                    '--log-level', 'info'
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                self.processes['fastapi'] = process
                logger.info(f"FastAPI server started with PID {process.pid}")
                
                # Monitor process
                while self.monitoring and process.poll() is None:
                    time.sleep(5)
                
                if process.poll() is not None and self.monitoring:
                    logger.error(f"FastAPI server crashed with exit code {process.returncode}")
                    self.restart_process('fastapi', self.start_fastapi_server)
                    
            except Exception as e:
                logger.error(f"FastAPI server startup failed: {e}")
                if self.monitoring:
                    self.restart_process('fastapi', self.start_fastapi_server)
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        return thread
    
    def start_trading_system(self):
        """Start the main trading system"""
        def run_trading():
            try:
                logger.info("Starting main trading system...")
                
                process = subprocess.Popen([
                    sys.executable, 'run_production.py'
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                self.processes['trading'] = process
                logger.info(f"Trading system started with PID {process.pid}")
                
                # Monitor process
                while self.monitoring and process.poll() is None:
                    time.sleep(5)
                
                if process.poll() is not None and self.monitoring:
                    logger.error(f"Trading system crashed with exit code {process.returncode}")
                    self.restart_process('trading', self.start_trading_system)
                    
            except Exception as e:
                logger.error(f"Trading system startup failed: {e}")
                if self.monitoring:
                    self.restart_process('trading', self.start_trading_system)
        
        thread = threading.Thread(target=run_trading, daemon=True)
        thread.start()
        return thread
    
    def start_dashboard(self):
        """Start the Streamlit dashboard"""
        def run_dashboard():
            try:
                dashboard_port = int(os.getenv('DASHBOARD_PORT', 8501))
                logger.info(f"Starting Streamlit dashboard on port {dashboard_port}")
                
                process = subprocess.Popen([
                    sys.executable, '-m', 'streamlit', 'run',
                    'production_dashboard.py',
                    '--server.port', str(dashboard_port),
                    '--server.address', '0.0.0.0',
                    '--server.headless', 'true'
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                self.processes['dashboard'] = process
                logger.info(f"Dashboard started with PID {process.pid}")
                
                # Monitor process
                while self.monitoring and process.poll() is None:
                    time.sleep(5)
                
                if process.poll() is not None and self.monitoring:
                    logger.error(f"Dashboard crashed with exit code {process.returncode}")
                    self.restart_process('dashboard', self.start_dashboard)
                    
            except Exception as e:
                logger.error(f"Dashboard startup failed: {e}")
                if self.monitoring:
                    self.restart_process('dashboard', self.start_dashboard)
        
        thread = threading.Thread(target=run_dashboard, daemon=True)
        thread.start()
        return thread
    
    def restart_process(self, process_name: str, start_function):
        """Restart a crashed process with exponential backoff"""
        if process_name not in self.restart_attempts:
            self.restart_attempts[process_name] = 0
        
        self.restart_attempts[process_name] += 1
        
        if self.restart_attempts[process_name] > self.max_restarts:
            logger.error(f"Max restart attempts reached for {process_name}. Giving up.")
            return
        
        wait_time = min(30, 2 ** self.restart_attempts[process_name])
        logger.info(f"Restarting {process_name} in {wait_time} seconds (attempt {self.restart_attempts[process_name]})")
        
        time.sleep(wait_time)
        
        if self.monitoring:
            start_function()
    
    def monitor_health(self):
        """Monitor system health and log status"""
        while self.monitoring:
            try:
                import requests
                
                # Check API health
                try:
                    response = requests.get('http://localhost:8000/health', timeout=5)
                    if response.status_code == 200:
                        logger.debug("API health check passed")
                    else:
                        logger.warning(f"API health check failed: {response.status_code}")
                except requests.exceptions.RequestException:
                    logger.warning("API health check failed: Connection error")
                
                # Log process status
                alive_processes = []
                for name, process in self.processes.items():
                    if process and process.poll() is None:
                        alive_processes.append(name)
                
                logger.info(f"Active processes: {', '.join(alive_processes) if alive_processes else 'None'}")
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health monitoring error: {e}")
                time.sleep(30)
    
    def cleanup(self):
        """Clean shutdown of all processes"""
        logger.info("Shutting down all processes...")
        self.monitoring = False
        
        for name, process in self.processes.items():
            if process and process.poll() is None:
                logger.info(f"Terminating {name} (PID {process.pid})")
                try:
                    process.terminate()
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {name}")
                    process.kill()
                except Exception as e:
                    logger.error(f"Error terminating {name}: {e}")
        
        logger.info("Shutdown complete")
    
    def run(self):
        """Main execution function"""
        print("🚀 Signal Flow Trading System - Production Launcher")
        print("=" * 50)
        
        # Check requirements
        if not self.check_requirements():
            return False
        
        print("✅ Requirements check passed")
        
        # Start MongoDB
        if not self.start_mongodb():
            print("❌ MongoDB startup failed")
            return False
        
        print("✅ Database ready")
        
        try:
            # Start all components
            print("🔧 Starting FastAPI server...")
            self.start_fastapi_server()
            time.sleep(3)
            
            print("🤖 Starting trading system...")
            self.start_trading_system()
            time.sleep(3)
            
            print("📊 Starting dashboard...")
            self.start_dashboard()
            time.sleep(3)
            
            # Start health monitoring
            health_thread = threading.Thread(target=self.monitor_health, daemon=True)
            health_thread.start()
            
            print("\n🎉 All systems started successfully!")
            print("=" * 50)
            print("📈 Dashboard: http://localhost:8501")
            print("🔧 API: http://localhost:8000")
            print("📊 Health: http://localhost:8000/health/detailed")
            print("=" * 50)
            print("Press Ctrl+C to stop all services")
            
            # Keep main thread alive
            while True:
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n⚠️  Shutdown signal received...")
            self.cleanup()
            return True
        except Exception as e:
            logger.error(f"Production launcher error: {e}")
            print(f"❌ Critical error: {e}")
            self.cleanup()
            return False


def main():
    launcher = ProductionLauncher()
    success = launcher.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
