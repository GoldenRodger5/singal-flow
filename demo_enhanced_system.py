#!/usr/bin/env python3
"""
Enhanced Trading System Demo
Demonstrates the LLM routing, time-window trading, and automation features.
"""
import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path

# Add the project root to the path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.config import Config
from services.system_orchestrator import (
    TradingSystemOrchestrator, 
    SystemConfiguration,
    SystemMode
)
from services.automated_trading_manager import AutomationMode
from services.llm_router import LLMRouter, TaskType
from services.trading_window_config import TradingWindowManager
from loguru import logger


async def demo_llm_routing():
    """Demonstrate LLM routing for different tasks."""
    print("\n🧠 LLM Routing Demo")
    print("=" * 50)
    
    config = Config()
    router = LLMRouter(config)
    
    # Test different task types
    tasks = [
        (TaskType.TRADE_EXPLANATION, "Explain why we should buy AAPL at current levels"),
        (TaskType.SENTIMENT_CLASSIFICATION, "AAPL to the moon! 🚀 Best stock ever!!!"),
        (TaskType.STRATEGY_GENERATION, "Generate a new momentum strategy for tech stocks"),
        (TaskType.LIGHTWEIGHT_TASKS, "Tag this as: bullish, bearish, or neutral: Stock up 5%")
    ]
    
    for task_type, prompt in tasks:
        print(f"\n📋 Task: {task_type.value}")
        print(f"Prompt: {prompt}")
        
        try:
            result = router.route_task(task_type, prompt)
            print(f"✅ LLM Used: {result['llm_used']}")
            print(f"Response: {result['response'][:200]}...")
            print(f"Cost: ${result['cost_estimate']:.4f}")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Show usage statistics
    usage = router.get_usage_report()
    print(f"\n📊 Usage Report: {usage['total_calls']} total calls")


def demo_trading_windows():
    """Demonstrate time-window based trading."""
    print("\n⏰ Trading Windows Demo")
    print("=" * 50)
    
    window_manager = TradingWindowManager()
    
    # Show current window
    current_window = window_manager.get_current_window()
    print(f"Current Trading Window: {current_window.value}")
    
    if current_window.value != "closed":
        config = window_manager.get_window_config(current_window)
        print(f"Risk Level: {config.risk_level}")
        print(f"Allowed Strategies: {[s.value for s in config.allowed_strategies]}")
        print(f"Position Size Multiplier: {config.position_size_multiplier}")
        print(f"Min Confidence Threshold: {config.min_confidence_threshold}")
    
    # Show next window change
    next_change = window_manager.get_next_window_change()
    print(f"\nNext window: {next_change['next_window']}")
    print(f"Time until change: {next_change['minutes_until_change']:.1f} minutes")
    
    # Show full schedule
    print("\n📅 Today's Trading Schedule:")
    schedule = window_manager.get_window_schedule()
    for window_name, window_info in schedule.items():
        print(f"  {window_name}: {window_info['start'].strftime('%H:%M')} - {window_info['end'].strftime('%H:%M')}")
        print(f"    Risk: {window_info['risk_level']}, Strategies: {len(window_info['strategies'])}")


async def demo_system_integration():
    """Demonstrate full system integration."""
    print("\n🚀 System Integration Demo")
    print("=" * 50)
    
    try:
        # Create system configuration
        config = Config()
        system_config = SystemConfiguration(
            mode=SystemMode.PAPER_TRADING,
            automation_mode=AutomationMode.ANALYSIS_ONLY,  # Safe mode for demo
            enable_ai_explanations=True,
            max_daily_trades=5
        )
        
        # Create orchestrator
        orchestrator = TradingSystemOrchestrator(config, system_config)
        
        print("✅ System orchestrator created")
        print(f"Mode: {system_config.mode.value}")
        print(f"Automation: {system_config.automation_mode.value}")
        
        # Show system status before start
        status = orchestrator.get_system_status()
        print(f"\nSystem Status: {status['orchestrator']['running']}")
        print(f"Current Window: {status['trading_window']['current']}")
        
        # For demo purposes, we'll just show the configuration
        # In a real scenario, you would call:
        # await orchestrator.start_system()
        
        print("\n💡 System Ready - In production, call await orchestrator.start_system()")
        
    except Exception as e:
        print(f"❌ Error in system integration: {e}")


def demo_automation_modes():
    """Demonstrate different automation modes."""
    print("\n🤖 Automation Modes Demo")
    print("=" * 50)
    
    modes = [
        (AutomationMode.FULLY_AUTOMATED, "System runs 24/7 without human intervention"),
        (AutomationMode.MARKET_HOURS_ONLY, "System runs only during market hours"),
        (AutomationMode.SUPERVISED, "Human approval required for trades"),
        (AutomationMode.PAPER_TRADING, "Simulated trades only"),
        (AutomationMode.ANALYSIS_ONLY, "No trading, analysis and alerts only")
    ]
    
    for mode, description in modes:
        print(f"🔧 {mode.value}: {description}")
    
    print("\n💡 Recommended Progression:")
    print("1. Start with ANALYSIS_ONLY to validate signals")
    print("2. Move to PAPER_TRADING to test execution")
    print("3. Use SUPERVISED mode for initial live trading")
    print("4. Graduate to MARKET_HOURS_ONLY for partial automation")
    print("5. Consider FULLY_AUTOMATED for 24/7 operation")


def show_system_architecture():
    """Show the system architecture overview."""
    print("\n🏗️ System Architecture Overview")
    print("=" * 50)
    
    architecture = """
    ┌─────────────────────────────────────────────────────────────┐
    │                    System Orchestrator                      │
    │                   (Main Controller)                         │
    └─────────────────────┬───────────────────────────────────────┘
                          │
    ┌─────────────────────┼───────────────────────────────────────┐
    │                     │                                       │
    ▼                     ▼                                       ▼
┌─────────────┐  ┌─────────────────┐                    ┌──────────────┐
│LLM Router   │  │Trading Window   │                    │Automated     │
│             │  │Manager          │                    │Trading Mgr   │
│• GPT-4o     │  │                 │                    │              │
│• Claude-4   │  │• Pre-market     │                    │• Safety      │
│• Task       │  │• Opening range  │                    │• Monitoring  │
│  Routing    │  │• Morning        │                    │• Execution   │
└─────────────┘  │• Afternoon      │                    └──────────────┘
                 │• Closing        │
                 │• Post-market    │
                 └─────────────────┘
                          │
    ┌─────────────────────┼───────────────────────────────────────┐
    │                     │                                       │
    ▼                     ▼                                       ▼
┌─────────────┐  ┌─────────────────┐                    ┌──────────────┐
│Enhanced     │  │Market Regime    │                    │Technical     │
│Indicators   │  │Detector         │                    │Indicators    │
│             │  │                 │                    │              │
│• RSI Z-Score│  │• Volatility     │                    │• Traditional │
│• Order Flow │  │• Trend          │                    │• Enhanced    │
│• Sector     │  │• Mean Reversion │                    │• AI-Powered  │
│  Strength   │  │• Uncertainty    │                    │• Window-Aware│
└─────────────┘  └─────────────────┘                    └──────────────┘
    """
    
    print(architecture)
    
    print("\n🔄 Data Flow:")
    print("1. Market data flows in continuously")
    print("2. Regime detector analyzes market conditions")
    print("3. Window manager determines appropriate strategies")
    print("4. Enhanced indicators generate signals")
    print("5. LLM router provides AI analysis and explanations")
    print("6. Automated manager executes approved trades")
    print("7. System orchestrator coordinates everything")


async def main():
    """Run the complete demo."""
    print("🎯 Enhanced Trading System Demo")
    print("=" * 60)
    print("Demonstrating LLM routing, time windows, and automation")
    print("=" * 60)
    
    # Check for required environment variables
    required_vars = ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {missing_vars}")
        print("Demo will run with limited functionality")
    
    # Run demonstrations
    show_system_architecture()
    
    demo_trading_windows()
    
    demo_automation_modes()
    
    if not missing_vars:
        await demo_llm_routing()
        await demo_system_integration()
    else:
        print("\n🚫 Skipping LLM and integration demos due to missing API keys")
    
    print("\n" + "=" * 60)
    print("✅ Demo completed!")
    print("\n💡 Next Steps:")
    print("1. Set up API keys for OpenAI and Anthropic")
    print("2. Configure your broker API integration")
    print("3. Start with ANALYSIS_ONLY mode to validate signals")
    print("4. Gradually move to more automated modes")
    print("5. Monitor and iterate based on performance")
    print("\n🚀 Ready to revolutionize your trading!")


if __name__ == "__main__":
    asyncio.run(main())
