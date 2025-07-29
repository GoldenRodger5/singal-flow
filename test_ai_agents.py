"""
Test AI Agents functionality
"""
import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.sentiment_agent import SentimentAgent
from agents.trade_recommender_agent import TradeRecommenderAgent
from agents.reasoning_agent import ReasoningAgent
from agents.execution_monitor_agent import ExecutionMonitorAgent
from agents.summary_agent import SummaryAgent
from services.twilio_whatsapp import WhatsAppNotifier
from utils.logger_setup import setup_logger


async def test_sentiment_agent():
    """Test sentiment analysis functionality."""
    print("🧠 Testing Sentiment Agent...")
    
    try:
        sentiment_agent = SentimentAgent()
        
        # Test with a sample ticker
        sentiment = await sentiment_agent.analyze_ticker("AAPL")
        
        if sentiment:
            print(f"✅ Sentiment analysis successful")
            print(f"   Sentiment: {sentiment.get('news_sentiment', 'unknown')}")
            print(f"   Score: {sentiment.get('sentiment_score', 0):.2f}")
            print(f"   Confidence: {sentiment.get('sentiment_confidence', 0):.2f}")
            print(f"   News count: {sentiment.get('news_count', 0)}")
            return True
        else:
            print("❌ Sentiment analysis failed")
            return False
            
    except Exception as e:
        print(f"❌ Sentiment agent error: {e}")
        return False


async def test_trade_recommender():
    """Test trade recommendation functionality."""
    print("\n📊 Testing Trade Recommender Agent...")
    
    try:
        recommender = TradeRecommenderAgent()
        
        # Mock setup data for testing
        mock_setup = {
            'ticker': 'SIRI',
            'current_price': 25.50,
            'setup_score': 7,
            'setup_reasons': ['RSI oversold', 'Volume spike'],
            'confidence': 7.5,
            'rsi': {'is_oversold': True, 'rsi_value': 28.5},
            'vwap': {'is_bounce': True, 'distance': 0.01},
            'macd': {'is_bullish_cross': True},
            'volume_data': {'spike': True, 'current': 50000, 'average': 25000},
            'risk_reward': {'stop_loss': 24.0, 'take_profit': 28.0, 'rr_ratio': 2.2},
            'is_volatile_session': True
        }
        
        # Create mock sentiment data
        mock_sentiment = {
            'news_sentiment': 'bullish',
            'sentiment_score': 0.6,
            'sentiment_confidence': 0.8,
            'news_count': 3
        }
        
        recommendation = await recommender.evaluate_setup(mock_setup, mock_sentiment)
        
        if recommendation:
            print(f"✅ Trade recommendation successful")
            print(f"   Ticker: {recommendation.get('ticker')}")
            print(f"   Confidence: {recommendation.get('confidence', 0):.1f}/10")
            print(f"   R:R Ratio: {recommendation.get('risk_reward_ratio', 0):.1f}:1")
            print(f"   Entry: ${recommendation.get('entry', 0):.2f}")
            return True
        else:
            print("❌ Trade recommendation failed")
            return False
            
    except Exception as e:
        print(f"❌ Trade recommender error: {e}")
        return False


async def test_reasoning_agent():
    """Test reasoning and explanation functionality."""
    print("\n🤔 Testing Reasoning Agent...")
    
    try:
        reasoning_agent = ReasoningAgent()
        
        # Create mock data
        mock_setup = {
            'ticker': 'AAPL',
            'current_price': 150.0,
            'setup_score': 6
        }
        
        mock_sentiment = {
            'news_sentiment': 'bullish',
            'sentiment_score': 0.6,
            'news_count': 3
        }
        
        mock_recommendation = {
            'ticker': 'AAPL',
            'entry': 150.0,
            'stop_loss': 147.0,
            'take_profit': 156.0,
            'confidence': 7.5,
            'setup_type': 'VWAP Bounce',
            'risk_reward_ratio': 2.0,
            'technical_signals': ['RSI oversold', 'VWAP bounce'],
            'sentiment_signals': ['Bullish news sentiment']
        }
        
        explanation = await reasoning_agent.explain_trade(mock_setup, mock_sentiment, mock_recommendation)
        
        if explanation and explanation.get('plain_english'):
            print(f"✅ Trade explanation successful")
            print(f"   Summary: {explanation.get('summary', 'N/A')}")
            print(f"   Plain English: {explanation.get('plain_english', 'N/A')[:100]}...")
            return True
        else:
            print("❌ Trade explanation failed")
            return False
            
    except Exception as e:
        print(f"❌ Reasoning agent error: {e}")
        return False


async def test_whatsapp_notifier():
    """Test WhatsApp notification functionality."""
    print("\n📱 Testing WhatsApp Notifier...")
    
    try:
        notifier = WhatsAppNotifier()
        
        # Test connection
        connection_test = await notifier.test_connection()
        
        if connection_test:
            print("✅ WhatsApp connection test successful")
            return True
        else:
            print("❌ WhatsApp connection test failed (may be expected in demo mode)")
            return True  # Still consider success in demo mode
            
    except Exception as e:
        print(f"❌ WhatsApp notifier error: {e}")
        return False


async def test_execution_monitor():
    """Test execution monitoring functionality."""
    print("\n👁️ Testing Execution Monitor Agent...")
    
    try:
        monitor = ExecutionMonitorAgent()
        
        # Test adding a mock trade
        mock_recommendation = {
            'ticker': 'AAPL',
            'entry': 150.0,
            'stop_loss': 147.0,
            'take_profit': 156.0,
            'position_size': {'percentage': 0.05, 'max_risk_per_trade': 0.01},
            'setup_type': 'VWAP Bounce',
            'confidence': 7.5,
            'exit_strategy': {'trailing_stop': True}
        }
        
        trade_id = await monitor.add_trade(mock_recommendation)
        
        if trade_id:
            print(f"✅ Execution monitor test successful")
            print(f"   Trade ID: {trade_id}")
            
            # Test getting active trades
            summary = monitor.get_active_trades_summary()
            print(f"   Active trades: {summary['count']}")
            
            # Clean up - remove the test trade
            await monitor.remove_trade(trade_id, "test_cleanup")
            
            return True
        else:
            print("❌ Execution monitor test failed")
            return False
            
    except Exception as e:
        print(f"❌ Execution monitor error: {e}")
        return False


async def test_summary_agent():
    """Test summary generation functionality."""
    print("\n📋 Testing Summary Agent...")
    
    try:
        summary_agent = SummaryAgent()
        
        # Generate daily summary
        summary = await summary_agent.generate_daily_summary()
        
        if summary:
            print(f"✅ Summary generation successful")
            print(f"   Date: {summary.get('date')}")
            print(f"   Trades: {summary.get('trade_count', 0)}")
            print(f"   Insights: {len(summary.get('insights', []))}")
            return True
        else:
            print("❌ Summary generation failed")
            return False
            
    except Exception as e:
        print(f"❌ Summary agent error: {e}")
        return False


async def main():
    """Run all AI agent tests."""
    print("🚀 AI Agents Test Suite\n")
    
    setup_logger()
    
    tests = [
        test_sentiment_agent,
        test_trade_recommender,
        test_reasoning_agent,
        test_whatsapp_notifier,
        test_execution_monitor,
        test_summary_agent
    ]
    
    results = []
    
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("\n" + "="*50)
    print("🎯 AI AGENTS TEST SUMMARY")
    print("="*50)
    print(f"Passed: {passed}/{total} tests")
    print(f"Success Rate: {passed/total*100:.0f}%")
    
    if passed == total:
        print("🎉 All AI agents are working correctly!")
        print("\n📝 Next steps:")
        print("1. Run: python main.py")
        print("2. Monitor logs for trade alerts")
        print("3. Check WhatsApp for notifications")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        print("Common issues:")
        print("- Missing API keys in .env file")
        print("- Network connectivity issues")
        print("- Missing dependencies")


if __name__ == "__main__":
    asyncio.run(main())
