#!/usr/bin/env python3
"""
Interactive response system for trading bot
"""
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List

class TradingResponseSystem:
    def __init__(self):
        self.pending_signals_file = "data/pending_signals.json"
        self.commands_file = "data/bot_commands.json"
        self.ensure_data_dir()
    
    def ensure_data_dir(self):
        """Create data directory if it doesn't exist."""
        os.makedirs("data", exist_ok=True)
    
    def save_pending_signal(self, signal_data: Dict) -> str:
        """Save a signal waiting for user response."""
        signal_id = f"signal_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Load existing signals
        pending_signals = self.load_pending_signals()
        
        # Add new signal
        pending_signals[signal_id] = {
            **signal_data,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending',
            'expires': (datetime.now() + timedelta(minutes=30)).isoformat()
        }
        
        # Save to file
        with open(self.pending_signals_file, 'w') as f:
            json.dump(pending_signals, f, indent=2)
        
        return signal_id
    
    def load_pending_signals(self) -> Dict:
        """Load pending signals from file."""
        try:
            with open(self.pending_signals_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def check_for_commands(self) -> List[Dict]:
        """Check for user commands."""
        try:
            with open(self.commands_file, 'r') as f:
                commands = json.load(f)
            
            # Clear processed commands
            with open(self.commands_file, 'w') as f:
                json.dump([], f)
            
            return commands
        except FileNotFoundError:
            return []
    
    def execute_command(self, command: str, signal_id: str = None) -> str:
        """Execute user command."""
        command = command.upper().strip()
        
        if command == "YES" and signal_id:
            return self.approve_signal(signal_id)
        elif command == "NO" and signal_id:
            return self.reject_signal(signal_id)
        elif command == "STATUS":
            return self.get_status()
        elif command == "STOP":
            return self.stop_bot()
        elif command == "START":
            return self.start_bot()
        elif command == "PORTFOLIO":
            return self.get_portfolio_status()
        else:
            return f"Unknown command: {command}"
    
    def approve_signal(self, signal_id: str) -> str:
        """Approve a trading signal."""
        pending_signals = self.load_pending_signals()
        
        if signal_id in pending_signals:
            signal = pending_signals[signal_id]
            signal['status'] = 'approved'
            signal['approved_at'] = datetime.now().isoformat()
            
            with open(self.pending_signals_file, 'w') as f:
                json.dump(pending_signals, f, indent=2)
            
            return f"✅ Approved: {signal['ticker']} {signal['signal']} at ${signal['price']}"
        else:
            return "❌ Signal not found or expired"
    
    def reject_signal(self, signal_id: str) -> str:
        """Reject a trading signal."""
        pending_signals = self.load_pending_signals()
        
        if signal_id in pending_signals:
            signal = pending_signals[signal_id]
            signal['status'] = 'rejected'
            signal['rejected_at'] = datetime.now().isoformat()
            
            with open(self.pending_signals_file, 'w') as f:
                json.dump(pending_signals, f, indent=2)
            
            return f"❌ Rejected: {signal['ticker']} {signal['signal']}"
        else:
            return "❌ Signal not found"
    
    def get_status(self) -> str:
        """Get current bot status."""
        pending_signals = self.load_pending_signals()
        pending_count = len([s for s in pending_signals.values() if s['status'] == 'pending'])
        
        return f"""📊 Bot Status:
• Pending signals: {pending_count}
• Last update: {datetime.now().strftime('%H:%M:%S')}
• Mode: Paper Trading
• Status: Active

Commands:
• YES/NO - Approve/reject signals
• STATUS - This status
• PORTFOLIO - Show positions
• STOP/START - Control bot"""
    
    def stop_bot(self) -> str:
        """Stop the trading bot."""
        with open("data/bot_control.json", 'w') as f:
            json.dump({"status": "stopped", "timestamp": datetime.now().isoformat()}, f)
        return "⏸️ Trading bot stopped"
    
    def start_bot(self) -> str:
        """Start the trading bot."""
        with open("data/bot_control.json", 'w') as f:
            json.dump({"status": "running", "timestamp": datetime.now().isoformat()}, f)
        return "▶️ Trading bot started"
    
    def get_portfolio_status(self) -> str:
        """Get portfolio status."""
        return """📈 Portfolio Status:
• Account Value: $105,247
• Day P&L: +$1,247 (+1.2%)
• Open Positions: 3
• Buying Power: $45,230
• Win Rate: 75% (6/8 trades today)

Recent Trades:
• AAPL: +$445 (closed)
• TSLA: +$320 (open)
• NVDA: -$125 (closed)"""

def demo_response_system():
    """Demo the response system."""
    response_system = TradingResponseSystem()
    
    # Simulate a new signal
    sample_signal = {
        'ticker': 'AAPL',
        'signal': 'BUY',
        'price': 150.25,
        'confidence': 8.5,
        'position_size': 15000,
        'stop_loss': 147.25,
        'take_profit': 156.25,
        'reasoning': 'RSI oversold + VWAP bounce'
    }
    
    # Save signal
    signal_id = response_system.save_pending_signal(sample_signal)
    print(f"📱 New signal saved: {signal_id}")
    
    # Demo commands
    commands = ["STATUS", "YES", "PORTFOLIO", "STOP"]
    
    for command in commands:
        result = response_system.execute_command(command, signal_id)
        print(f"Command '{command}': {result}")
        print()

if __name__ == "__main__":
    demo_response_system()
