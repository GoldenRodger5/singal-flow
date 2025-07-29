"""
Test the complete Signal Flow system with simulated live data
"""
import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.market_watcher_agent import MarketWatcherAgent
from agents.sentiment_agent import SentimentAgent
from agents.trade_recommender_agent import TradeRecommenderAgent
from agents.reasoning_agent import ReasoningAgent
from services.twilio_whatsapp import WhatsAppNotifier

async def simulate_live_trading():
    """Simulate live trading with real data during market hours."""
    print("🚀 Signal Flow Live System Test")
    print("=" * 50)
    
    # Initialize agents
    market_watcher = MarketWatcherAgent()
    sentiment_agent = SentimentAgent()
    trade_recommender = TradeRecommenderAgent()
    reasoning_agent = ReasoningAgent()
    whatsapp = WhatsAppNotifier()
    
    # Test with a few popular low-priced stocks
    test_tickers = ['SIRI', 'SOFI', 'PLTR', 'NIO', 'SNAP']
    
    # Manually add tickers to watchlist for testing
    import json
    watchlist_path = 'data/watchlist.json'
    with open(watchlist_path, 'w') as f:
        json.dump(test_tickers, f, indent=2)
    
    print(f"� Added {len(test_tickers)} tickers to watchlist for testing...")
    
    # Scan for setups using the market watcher
    setups = await market_watcher.scan_for_setups()
    
    print(f"📊 Found {len(setups)} potential setups")
    
    found_trades = []
    
    for setup in setups:
        ticker = setup['ticker']
        try:
            print(f"\n📊 Processing setup for {ticker}...")
            print(f"   Setup score: {setup['setup_score']}/10")
            
            # Get sentiment
            sentiment = await sentiment_agent.analyze_ticker(ticker)
            print(f"   📰 Sentiment: {sentiment['news_sentiment']} ({sentiment['sentiment_score']:.2f})")
            
            # Get recommendation
            recommendation = await trade_recommender.evaluate_setup(setup, sentiment)
            
            if recommendation:
                print(f"   🎯 Trade recommended: {recommendation['confidence']}/10 confidence")
                
                # Generate explanation
                explanation = await reasoning_agent.explain_trade(recommendation, setup, sentiment)
                
                # Send WhatsApp alert
                await whatsapp.send_trade_alert(recommendation, explanation)
                
                found_trades.append({
                    'ticker': ticker,
                    'setup': setup,
                    'sentiment': sentiment,
                    'recommendation': recommendation,
                    'explanation': explanation
                })
            else:
                print(f"   ❌ Setup did not meet recommendation criteria")
                
        except Exception as e:
            print(f"   ❌ Error processing {ticker}: {e}")
    
    print(f"\n🎯 RESULTS: Found {len(found_trades)} tradeable setups")
    
    for trade in found_trades:
        rec = trade['recommendation']
        print(f"   • {trade['ticker']}: {rec['confidence']}/10 confidence, "
              f"{rec['risk_reward_ratio']}:1 R:R, ${rec['entry']} entry")
    
    if found_trades:
        print(f"\n📱 WhatsApp alerts sent for all recommendations")
    else:
        print(f"\n💭 No setups met trading criteria (this is normal during off-hours)")

if __name__ == "__main__":
    asyncio.run(simulate_live_trading())
