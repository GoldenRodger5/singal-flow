#!/usr/bin/env python3
"""
Desktop Notification Service for Trading Signals
Runs in background and sends system notifications for high-confidence signals
"""

import time
import subprocess
import platform
import json
from datetime import datetime
from pathlib import Path
import threading
import queue

class DesktopNotifier:
    """Cross-platform desktop notification system."""
    
    def __init__(self):
        self.system = platform.system()
        self.notification_queue = queue.Queue()
        self.running = False
    
    def send_notification(self, title: str, message: str, urgency: str = 'normal'):
        """Send desktop notification based on OS."""
        if self.system == "Darwin":  # macOS
            self._send_macos_notification(title, message, urgency)
        elif self.system == "Linux":
            self._send_linux_notification(title, message, urgency)
        elif self.system == "Windows":
            self._send_windows_notification(title, message, urgency)
    
    def _send_macos_notification(self, title: str, message: str, urgency: str):
        """Send macOS notification using osascript."""
        sound = "Glass" if urgency == 'high' else "default"
        script = f'''
        display notification "{message}" with title "{title}" sound name "{sound}"
        '''
        try:
            subprocess.run(["osascript", "-e", script], check=True)
        except subprocess.CalledProcessError:
            print(f"Failed to send notification: {title}")
    
    def _send_linux_notification(self, title: str, message: str, urgency: str):
        """Send Linux notification using notify-send."""
        urgency_flag = "--urgency=critical" if urgency == 'high' else "--urgency=normal"
        try:
            subprocess.run([
                "notify-send", urgency_flag, title, message
            ], check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"Failed to send notification: {title}")
    
    def _send_windows_notification(self, title: str, message: str, urgency: str):
        """Send Windows notification using toast."""
        try:
            import win10toast
            toaster = win10toast.ToastNotifier()
            duration = 10 if urgency == 'high' else 5
            toaster.show_toast(title, message, duration=duration)
        except ImportError:
            print("Install win10toast for Windows notifications: pip install win10toast")
            print(f"Notification: {title} - {message}")

class TradingNotificationService:
    """Background service for trading signal notifications."""
    
    def __init__(self):
        self.notifier = DesktopNotifier()
        self.running = False
        self.notification_history = []
        self.config = {
            'min_confidence': 8.5,
            'notify_high_confidence': True,
            'notify_executions': True,
            'notify_pnl_milestones': True,
            'sound_enabled': True
        }
    
    def start(self):
        """Start the notification service."""
        self.running = True
        print("🔔 Trading Notification Service Started")
        print(f"⚡ Monitoring signals with confidence > {self.config['min_confidence']}")
        
        # Start background thread
        notification_thread = threading.Thread(target=self._monitor_signals, daemon=True)
        notification_thread.start()
        
        return notification_thread
    
    def stop(self):
        """Stop the notification service."""
        self.running = False
        print("🔕 Trading Notification Service Stopped")
    
    def _monitor_signals(self):
        """Monitor for trading signals and send notifications."""
        while self.running:
            try:
                # Check for new high-confidence signals
                self._check_signal_notifications()
                
                # Check for P&L milestones
                self._check_pnl_notifications()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                print(f"Notification service error: {e}")
                time.sleep(10)
    
    def _check_signal_notifications(self):
        """Check for new trading signals to notify about."""
        # This would integrate with your trading engine
        # For now, simulate signal checking
        
        # In real implementation, this would read from your trading session
        # or database to check for new high-confidence signals
        pass
    
    def _check_pnl_notifications(self):
        """Check for P&L milestones and send notifications."""
        # This would check current P&L and send notifications for:
        # - Daily P&L milestones ($500, $1000, etc.)
        # - Major wins/losses
        # - Portfolio value milestones
        pass
    
    def notify_signal(self, signal_data: dict):
        """Send notification for a trading signal."""
        confidence = signal_data.get('confidence', 0)
        
        if confidence >= self.config['min_confidence']:
            ticker = signal_data.get('ticker', 'UNKNOWN')
            action = signal_data.get('signal', 'UNKNOWN')
            price = signal_data.get('price', 0)
            
            title = f"🚨 HIGH CONFIDENCE SIGNAL"
            message = f"{action} {ticker} @ ${price:.2f} | Confidence: {confidence}/10"
            
            urgency = 'high' if confidence >= 9.0 else 'normal'
            
            self.notifier.send_notification(title, message, urgency)
            
            # Log notification
            self.notification_history.append({
                'type': 'signal',
                'data': signal_data,
                'timestamp': datetime.now()
            })
    
    def notify_execution(self, trade_data: dict):
        """Send notification for trade execution."""
        if not self.config['notify_executions']:
            return
        
        ticker = trade_data.get('ticker', 'UNKNOWN')
        action = trade_data.get('action', 'UNKNOWN')
        price = trade_data.get('price', 0)
        pnl = trade_data.get('pnl', 0)
        
        emoji = "🚀" if action == 'BUY' else "📉"
        pnl_emoji = "💰" if pnl >= 0 else "📉"
        
        title = f"{emoji} Trade Executed"
        message = f"{action} {ticker} @ ${price:.2f} | {pnl_emoji} P&L: ${pnl:+,.0f}"
        
        urgency = 'high' if abs(pnl) >= 200 else 'normal'
        
        self.notifier.send_notification(title, message, urgency)
        
        # Log notification
        self.notification_history.append({
            'type': 'execution',
            'data': trade_data,
            'timestamp': datetime.now()
        })
    
    def notify_pnl_milestone(self, pnl_data: dict):
        """Send notification for P&L milestones."""
        if not self.config['notify_pnl_milestones']:
            return
        
        daily_pnl = pnl_data.get('daily_pnl', 0)
        total_pnl = pnl_data.get('total_pnl', 0)
        
        # Check for daily milestones
        milestones = [500, 1000, 2000, 5000, 10000]
        
        for milestone in milestones:
            if abs(daily_pnl) >= milestone:
                emoji = "🎉" if daily_pnl >= 0 else "⚠️"
                title = f"{emoji} Daily P&L Milestone"
                message = f"Daily P&L: ${daily_pnl:+,.0f} | Total: ${total_pnl:+,.0f}"
                
                urgency = 'high' if milestone >= 1000 else 'normal'
                
                self.notifier.send_notification(title, message, urgency)
                break
    
    def get_notification_stats(self) -> dict:
        """Get notification service statistics."""
        total_notifications = len(self.notification_history)
        signal_notifications = len([n for n in self.notification_history if n['type'] == 'signal'])
        execution_notifications = len([n for n in self.notification_history if n['type'] == 'execution'])
        
        return {
            'total_notifications': total_notifications,
            'signal_notifications': signal_notifications,
            'execution_notifications': execution_notifications,
            'service_running': self.running,
            'last_notification': self.notification_history[-1] if self.notification_history else None
        }

def main():
    """Run the notification service as a standalone application."""
    service = TradingNotificationService()
    
    try:
        # Start service
        service.start()
        
        print("\n" + "="*50)
        print("🔔 TRADING NOTIFICATION SERVICE ACTIVE")
        print("="*50)
        print("⚡ Monitoring for high-confidence signals...")
        print("💰 Tracking P&L milestones...")
        print("🔊 Desktop notifications enabled")
        print("\nPress Ctrl+C to stop service")
        print("="*50)
        
        # Keep service running
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping notification service...")
        service.stop()
        print("✅ Service stopped. Goodbye!")

if __name__ == "__main__":
    main()
