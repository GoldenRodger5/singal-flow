# AI Decision Tracking System - Integration Guide

## 🎯 Overview

The AI Decision Tracking System automatically logs and analyzes all AI trading signals, regardless of whether they are executed. This system provides comprehensive performance tracking, post-decision analysis, and learning insights to improve your trading AI over time.

## ✨ What Was Implemented

### 1. Core Components

- **AI Decision Tracker** (`services/ai_decision_tracker.py`)
  - Logs all buy/sell signals with technical indicators
  - Tracks execution decisions (executed/rejected/partial)
  - Performs post-signal analysis to find optimal timing
  - Generates learning insights and performance metrics

- **Agent Integration Service** (`services/ai_agent_integration.py`)
  - Provides simple API for logging signals from any AI agent
  - Adds market context and confidence factor analysis
  - Handles execution logging with detailed reasoning

- **Enhanced Agent Wrapper** (`services/enhanced_agent_wrapper.py`)
  - Automatically wraps existing AI agents
  - Intercepts agent method calls to detect signals
  - Zero-code-change integration for existing agents

### 2. Database Collections

The system creates these MongoDB collections for comprehensive tracking:

- `ai_signals` - All AI buy/sell signals
- `ai_signal_analysis` - Post-signal analysis and performance
- `ai_signal_context` - Detailed context for each signal
- `ai_execution_context` - Execution decisions and reasoning

### 3. API Endpoints

Added to your production API (`production_api.py`):

- `GET /api/ai/signals/recent` - Get recent AI signals
- `GET /api/ai/signals/performance` - Performance summary
- `GET /api/ai/signals/analysis/{signal_id}` - Detailed signal analysis
- `POST /api/ai/signals/manual-log` - Manually log signals
- `POST /api/ai/signals/log-execution` - Log execution decisions
- `GET /api/ai/tracking/status` - Tracking system status

### 4. Dashboard Integration

Enhanced your Streamlit dashboard (`production_dashboard.py`) with:

- Real-time AI signal tracking display
- Signal performance metrics and charts
- Agent status monitoring
- Learning insights visualization

## 🚀 Quick Start

### 1. Setup AI Tracking

```bash
# Install and setup the tracking system
python setup_ai_tracking.py
```

This will:
- Initialize database collections
- Setup tracking for existing agents
- Start monitoring services
- Run integration tests

### 2. Test the System

```bash
# Run comprehensive tests
python test_ai_tracking_system.py
```

This verifies all components are working correctly.

### 3. Start Production System

```bash
# Launch with AI tracking enabled
python launch_production.py
```

## 📊 Using the System

### Automatic Integration (Recommended)

For existing AI agents, the system automatically wraps them:

```python
from services.enhanced_agent_wrapper import agent_tracking_manager

# Your existing agent
class MyTradingAgent:
    def analyze_stock(self, symbol):
        return {
            'symbol': symbol,
            'recommendation': 'buy',
            'confidence': 0.85,
            'rsi': 32.0,
            'reasoning': 'Strong buy signal based on technical analysis'
        }

# Wrap it for automatic tracking
my_agent = MyTradingAgent()
tracked_agent = agent_tracking_manager.wrap_agent(my_agent, "MyTradingAgent")

# Use normally - signals are automatically tracked
result = tracked_agent.analyze_stock("AAPL")
# Signal is now logged with ID in result['_tracking_signal_id']
```

### Manual Integration

For custom integration or new agents:

```python
from services.ai_agent_integration import ai_agent_integration

# Log a buy signal
signal_id = await ai_agent_integration.process_buy_signal(
    symbol="AAPL",
    confidence=0.85,
    technical_indicators={
        'rsi': 32.0,
        'macd': 0.05,
        'volume_ratio': 1.2
    },
    reasoning="Strong technical indicators suggest buy opportunity",
    risk_assessment={'overall_risk': 0.3},
    expected_return=0.08
)

# Later, log execution decision
await ai_agent_integration.log_execution_decision(
    signal_id=signal_id,
    decision="executed",  # or "rejected", "partial"
    reason="Strategy criteria met",
    execution_details={'price': 150.50, 'quantity': 10}
)
```

## 📈 Dashboard Features

### AI Signal Tracking Tab

The dashboard now includes a comprehensive AI tracking section:

1. **Signal Overview**
   - Total signals logged
   - Analysis completion status
   - Recent activity (24h)
   - Active agent count

2. **Performance Metrics**
   - Buy/sell signal accuracy
   - Timing accuracy
   - Learning insights

3. **Recent Signals Table**
   - Symbol, type, confidence
   - Reasoning and timing
   - Execution status

4. **Visualizations**
   - Signal type distribution
   - Confidence distribution
   - Timeline of signals

5. **Agent Status**
   - Active agents and methods
   - Tracking statistics

## 🎯 Key Benefits

### 1. Complete Signal History
- Every AI buy/sell signal is logged automatically
- Signals tracked regardless of execution
- Rich context and technical indicators stored

### 2. Performance Analysis
- Post-signal analysis to find optimal timing
- Accuracy tracking for buy/sell signals
- Learning insights to improve strategies

### 3. Zero-Code Integration
- Existing agents automatically wrapped
- No changes needed to current code
- Transparent signal tracking

### 4. Comprehensive Analytics
- Market regime analysis
- Confidence factor breakdown
- Risk assessment tracking
- Expected vs actual returns

## 🔧 Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# AI Tracking Configuration
AI_TRACKING_ENABLED=true
AI_ANALYSIS_DELAY_HOURS=24
AI_LEARNING_RETENTION_DAYS=365
```

### Database Configuration

The system automatically creates required indexes and collections. No manual setup needed.

## 📊 API Examples

### Get Recent Signals

```bash
curl "http://localhost:8000/api/ai/signals/recent?limit=10&signal_type=BUY"
```

### Get Performance Report

```bash
curl "http://localhost:8000/api/ai/signals/performance?days=30"
```

### Manual Signal Logging

```bash
curl -X POST "http://localhost:8000/api/ai/signals/manual-log" \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "signal_type": "BUY",
    "confidence": 0.85,
    "reasoning": "Strong technical indicators",
    "technical_indicators": {
      "rsi": 32.0,
      "macd": 0.05
    }
  }'
```

### Log Execution Decision

```bash
curl -X POST "http://localhost:8000/api/ai/signals/log-execution" \
  -H "Content-Type: application/json" \
  -d '{
    "signal_id": "signal_id_here",
    "decision": "executed",
    "reason": "Strategy criteria met",
    "execution_details": {
      "price": 150.50,
      "quantity": 10
    }
  }'
```

## 🔍 Monitoring

### Health Checks

The tracking system includes health monitoring:

```bash
curl "http://localhost:8000/api/ai/tracking/status"
```

### Log Monitoring

Watch logs for tracking activity:

```bash
tail -f logs/signal_flow.log | grep "AI_TRACKING"
```

## 🚨 Troubleshooting

### Common Issues

1. **Signals Not Being Tracked**
   - Check agent wrapper setup
   - Verify tracking is enabled
   - Check agent method naming conventions

2. **Database Connection Issues**
   - Verify MongoDB Atlas connection
   - Check network connectivity
   - Validate credentials

3. **Performance Analysis Not Working**
   - Ensure sufficient signal history
   - Check analysis delay settings
   - Verify market data availability

### Debug Mode

Enable debug logging:

```python
import logging
logging.getLogger("ai_tracking").setLevel(logging.DEBUG)
```

## 📝 Next Steps

1. **Run the setup script**: `python setup_ai_tracking.py`
2. **Test the system**: `python test_ai_tracking_system.py`
3. **Check the dashboard**: Look for the new AI tracking section
4. **Monitor performance**: Watch signals being logged in real-time
5. **Review insights**: Check learning insights for strategy improvements

## 🎉 Success Indicators

You'll know the system is working when:

- ✅ Agents are automatically wrapped and tracked
- ✅ Signals appear in the dashboard
- ✅ Performance metrics are calculated
- ✅ Learning insights are generated
- ✅ Database collections show signal data

The system is now ready to learn from every AI decision and help improve your trading performance over time!
