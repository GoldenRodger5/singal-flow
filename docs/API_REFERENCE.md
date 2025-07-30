# 📡 SignalFlow API Documentation

## 🌐 **API OVERVIEW**

The SignalFlow trading system exposes REST APIs for monitoring, control, and integration. All APIs return JSON responses and use standard HTTP status codes.

---

## 🔧 **BASE CONFIGURATION**

- **Base URL**: `http://localhost:8001` (default)
- **Authentication**: None (internal system APIs)
- **Content-Type**: `application/json`
- **Rate Limiting**: None (internal use)

---

## 📊 **LEARNING DASHBOARD API**

### **System Status**

#### `GET /api/learning/status`
Get current learning system status and configuration.

**Response:**
```json
{
  "status": "active",
  "learning_enabled": true,
  "total_decisions": 127,
  "total_predictions": 89,
  "model_version": "v2.1",
  "last_update": "2025-07-29T18:00:00Z",
  "system_health": "healthy"
}
```

#### `GET /api/learning/health`
System health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "database_connected": true,
  "models_loaded": true,
  "last_learning_cycle": "2025-07-29T17:30:00Z",
  "uptime_seconds": 3600,
  "memory_usage_mb": 245
}
```

#### `GET /api/learning/version`
API version and system information.

**Response:**
```json
{
  "api_version": "2.0",
  "system_version": "SignalFlow v2.0",
  "python_version": "3.12.0",
  "dependencies": {
    "scikit-learn": "1.3.0",
    "pandas": "2.0.3",
    "numpy": "1.24.3"
  }
}
```

### **Performance Metrics**

#### `GET /api/learning/metrics`
Detailed learning system metrics and performance data.

**Response:**
```json
{
  "learning_metrics": {
    "total_trades": 45,
    "successful_trades": 32,
    "win_rate": 0.711,
    "avg_return": 0.187,
    "sharpe_ratio": 1.42,
    "max_drawdown": 0.085
  },
  "model_performance": {
    "prediction_accuracy": 0.73,
    "confidence_calibration": 0.85,
    "learning_rate": 0.001,
    "epochs_completed": 150
  },
  "recent_performance": {
    "last_7_days": {
      "trades": 12,
      "wins": 9,
      "avg_return": 0.21
    },
    "last_30_days": {
      "trades": 45,
      "wins": 32,
      "avg_return": 0.187
    }
  }
}
```

#### `GET /api/learning/performance`
System performance analytics and statistics.

**Response:**
```json
{
  "performance_summary": {
    "total_return": 0.234,
    "annualized_return": 0.487,
    "volatility": 0.156,
    "information_ratio": 1.89,
    "calmar_ratio": 2.34
  },
  "regime_performance": {
    "trending_high_vol": {
      "trades": 15,
      "win_rate": 0.80,
      "avg_return": 0.25
    },
    "mean_reverting": {
      "trades": 20,
      "win_rate": 0.65,
      "avg_return": 0.15
    }
  },
  "position_sizing_effectiveness": {
    "kelly_criterion_usage": 0.85,
    "avg_position_size": 0.32,
    "size_accuracy": 0.78
  }
}
```

### **Insights and Analysis**

#### `GET /api/learning/insights`
Daily insights and trading recommendations.

**Response:**
```json
{
  "daily_insights": {
    "date": "2025-07-29",
    "market_regime": "trending_low_vol",
    "recommended_strategy": "momentum_following",
    "confidence_threshold": 7.2,
    "position_size_multiplier": 1.1
  },
  "pattern_insights": [
    {
      "pattern": "williams_r_oversold_bounce",
      "success_rate": 0.82,
      "avg_return": 0.18,
      "recommendation": "increase_weight"
    },
    {
      "pattern": "bollinger_squeeze_breakout",
      "success_rate": 0.75,
      "avg_return": 0.23,
      "recommendation": "maintain_weight"
    }
  ],
  "risk_insights": {
    "current_portfolio_risk": 0.12,
    "recommended_max_position": 0.45,
    "sector_concentration": {
      "technology": 0.35,
      "healthcare": 0.25,
      "energy": 0.20
    }
  }
}
```

#### `GET /api/learning/predictions`
Recent trading predictions and outcomes.

**Query Parameters:**
- `limit` (optional): Number of predictions to return (default: 20)
- `status` (optional): Filter by status (`pending`, `completed`, `failed`)

**Response:**
```json
{
  "predictions": [
    {
      "id": "pred_001",
      "ticker": "SIRI",
      "prediction_time": "2025-07-29T14:30:00Z",
      "entry_price": 4.25,
      "predicted_return": 0.15,
      "confidence": 8.2,
      "status": "completed",
      "actual_return": 0.18,
      "accuracy": 0.92
    },
    {
      "id": "pred_002", 
      "ticker": "NOK",
      "prediction_time": "2025-07-29T15:15:00Z",
      "entry_price": 3.85,
      "predicted_return": 0.12,
      "confidence": 7.8,
      "status": "pending",
      "actual_return": null,
      "accuracy": null
    }
  ],
  "summary": {
    "total_predictions": 89,
    "completed": 67,
    "pending": 22,
    "avg_accuracy": 0.73
  }
}
```

#### `GET /api/learning/decisions`
Decision history and reasoning analysis.

**Query Parameters:**
- `limit` (optional): Number of decisions to return (default: 20)
- `outcome` (optional): Filter by outcome (`success`, `failure`, `pending`)

**Response:**
```json
{
  "decisions": [
    {
      "id": "dec_001",
      "ticker": "PLUG",
      "decision_time": "2025-07-29T13:45:00Z",
      "decision": "buy",
      "confidence": 8.5,
      "reasoning": [
        "Williams %R oversold bounce signal",
        "Volume spike 3.2x average",
        "Momentum multiplier score 7.8/10"
      ],
      "risk_factors": [
        "Sub-$3 stock volatility",
        "Recent earnings uncertainty"
      ],
      "outcome": "success",
      "return": 0.22
    }
  ],
  "summary": {
    "total_decisions": 127,
    "successful": 89,
    "failed": 23,
    "pending": 15
  }
}
```

### **Control Endpoints**

#### `POST /api/learning/trigger-learning`
Manually trigger a learning cycle.

**Request Body:**
```json
{
  "learning_type": "full",  // "full" or "incremental"
  "force_retrain": false
}
```

**Response:**
```json
{
  "status": "started",
  "learning_id": "learn_001",
  "estimated_duration": "5 minutes",
  "message": "Learning cycle initiated successfully"
}
```

#### `POST /api/learning/trigger-backtest`
Start a backtesting run.

**Request Body:**
```json
{
  "start_date": "2025-07-01",
  "end_date": "2025-07-29",
  "strategy": "low_cap_momentum",
  "initial_capital": 10000
}
```

**Response:**
```json
{
  "status": "started",
  "backtest_id": "bt_001",
  "estimated_duration": "10 minutes",
  "message": "Backtest initiated successfully"
}
```

#### `POST /api/learning/reset`
Reset learning data (use with caution).

**Request Body:**
```json
{
  "reset_type": "soft",  // "soft" or "hard"
  "confirm": true
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Learning data reset successfully",
  "backup_created": "backup_2025-07-29_18-00-00"
}
```

---

## 📱 **TELEGRAM WEBHOOK API**

### **Message Handling**

#### `POST /webhook/telegram`
Main webhook endpoint for Telegram bot interactions.

**Headers:**
```
Content-Type: application/json
X-Telegram-Bot-Api-Secret-Token: your_secret_token
```

**Request Body (Example - Button Callback):**
```json
{
  "update_id": 123456789,
  "callback_query": {
    "id": "callback_001",
    "from": {
      "id": 987654321,
      "username": "trader_user"
    },
    "message": {
      "message_id": 1001,
      "date": 1690650000
    },
    "data": "execute_SIRI"
  }
}
```

**Response:**
```json
{
  "status": "processed",
  "action": "trade_executed",
  "message": "Buy order placed for SIRI"
}
```

### **Trade Execution Callbacks**

#### `POST /webhook/telegram/trade`
Handle trade execution callbacks from Telegram buttons.

**Request Body:**
```json
{
  "action": "execute",
  "ticker": "SIRI", 
  "chat_id": 987654321,
  "message_id": 1001,
  "user_id": 987654321
}
```

**Response:**
```json
{
  "status": "success",
  "order_id": "order_001",
  "execution_price": 4.27,
  "shares": 1250,
  "message": "✅ Trade executed: 1,250 shares of SIRI at $4.27"
}
```

---

## 🔧 **INTERNAL APIs**

### **System Health**

#### `GET /health`
Basic health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T18:00:00Z",
  "version": "2.0"
}
```

### **Configuration**

#### `GET /config`
Get current system configuration (sanitized).

**Response:**
```json
{
  "trading_params": {
    "price_range": [0.75, 10.0],
    "position_size_range": [0.25, 0.50],
    "min_confidence": 6.0,
    "paper_trading": true
  },
  "technical_indicators": {
    "williams_r_enabled": true,
    "bollinger_squeeze_enabled": true,
    "momentum_multiplier_enabled": true
  },
  "risk_management": {
    "max_daily_loss": 0.15,
    "max_position_size": 0.50,
    "max_sub_3_exposure": 0.60
  }
}
```

---

## 🚨 **ERROR RESPONSES**

### **Standard Error Format**
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request parameters are invalid",
    "details": "confidence_score must be between 0 and 10",
    "timestamp": "2025-07-29T18:00:00Z"
  }
}
```

### **Common Error Codes**
- **400 Bad Request**: `INVALID_REQUEST`, `MISSING_PARAMETER`
- **404 Not Found**: `ENDPOINT_NOT_FOUND`, `RESOURCE_NOT_FOUND`
- **500 Internal Error**: `SYSTEM_ERROR`, `DATABASE_ERROR`, `MODEL_ERROR`
- **503 Service Unavailable**: `SYSTEM_MAINTENANCE`, `OVERLOADED`

---

## 📋 **USAGE EXAMPLES**

### **Python Client Example**
```python
import requests

# Get learning metrics
response = requests.get('http://localhost:8001/api/learning/metrics')
metrics = response.json()
print(f"Win Rate: {metrics['learning_metrics']['win_rate']:.2%}")

# Trigger learning cycle
learning_request = {
    "learning_type": "incremental",
    "force_retrain": False
}
response = requests.post(
    'http://localhost:8001/api/learning/trigger-learning',
    json=learning_request
)
print(f"Learning Status: {response.json()['status']}")
```

### **JavaScript Client Example**
```javascript
// Get daily insights
fetch('http://localhost:8001/api/learning/insights')
  .then(response => response.json())
  .then(data => {
    console.log('Market Regime:', data.daily_insights.market_regime);
    console.log('Confidence Threshold:', data.daily_insights.confidence_threshold);
  });

// Start backtest
const backtestConfig = {
  start_date: '2025-07-01',
  end_date: '2025-07-29',
  strategy: 'low_cap_momentum',
  initial_capital: 10000
};

fetch('http://localhost:8001/api/learning/trigger-backtest', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(backtestConfig)
})
.then(response => response.json())
.then(data => console.log('Backtest ID:', data.backtest_id));
```

---

*API Documentation v2.0 - Updated July 29, 2025*
