# Signal Flow API Documentation

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: `https://your-api-domain.com`

## Authentication
Currently no authentication required. All endpoints are open.

---

## AI Predictions Endpoints

### Get AI Predictions Dashboard Data
**GET** `/api/ai/predictions`

Returns complete AI predictions data for dashboard display.

**Response:**
```json
{
  "success": true,
  "predictions": [
    {
      "symbol": "AAPL",
      "confidence": 8.5,
      "direction": "bullish",
      "target_price": 185.50,
      "current_price": 175.25,
      "timeframe": "4h",
      "reasoning": "Strong momentum | High volume",
      "technical_score": 8.2,
      "momentum_score": 9.1,
      "volume_score": 7.8,
      "expected_move": 5.85,
      "timestamp": "2025-08-06T14:30:00Z"
    }
  ],
  "summary": {
    "total_predictions": 15,
    "high_confidence_count": 5,
    "high_confidence_percent": 33.3,
    "avg_confidence": 7.2,
    "bullish_count": 9,
    "bullish_percent": 60.0
  },
  "performance": {
    "accuracy": 76.5,
    "precision": 78.2,
    "total_predictions": 247,
    "correct_predictions": 189,
    "training_samples": 1247,
    "model_version": "v2.1",
    "learning_progress": 89.2,
    "status": "active"
  },
  "timestamp": "2025-08-06T14:30:00Z"
}
```

### Get Top Predictions
**GET** `/api/ai/predictions/top?limit=10`

Returns top AI predictions sorted by confidence score.

**Parameters:**
- `limit` (optional): Number of predictions to return (default: 10)

### Get Prediction by Symbol
**GET** `/api/ai/predictions/{symbol}`

Returns AI prediction for a specific symbol.

**Example:** `/api/ai/predictions/AAPL`

### Get High Confidence Signals
**GET** `/api/ai/predictions/signals/high-confidence?min_confidence=8.0`

Returns only high confidence trading signals.

**Parameters:**
- `min_confidence` (optional): Minimum confidence score (default: 8.0)

---

## Portfolio Holdings Endpoints

### Get Portfolio Holdings Dashboard Data
**GET** `/api/portfolio/holdings`

Returns complete portfolio holdings data for dashboard display.

**Response:**
```json
{
  "success": true,
  "holdings": [
    {
      "symbol": "AAPL",
      "quantity": 50,
      "avg_cost": 170.25,
      "current_price": 175.50,
      "market_value": 8775.00,
      "unrealized_pnl": 262.50,
      "unrealized_pnl_percent": 3.08,
      "cost_basis": 8512.50,
      "side": "long",
      "last_updated": "2025-08-06T14:30:00Z"
    }
  ],
  "summary": {
    "total_positions": 12,
    "long_positions": 11,
    "short_positions": 1,
    "total_market_value": 195250.75,
    "total_cost_basis": 187230.25,
    "total_unrealized_pnl": 8020.50,
    "total_unrealized_pnl_percent": 4.28,
    "best_performer": {
      "symbol": "NVDA",
      "pnl_percent": 12.5
    },
    "worst_performer": {
      "symbol": "META",
      "pnl_percent": -2.1
    }
  },
  "recent_trades": [
    {
      "symbol": "TSLA",
      "action": "BUY",
      "quantity": 25,
      "price": 245.67,
      "timestamp": "2025-08-06T13:45:00Z",
      "order_id": "abc123",
      "source": "ai_signal"
    }
  ],
  "timestamp": "2025-08-06T14:30:00Z"
}
```

### Get Portfolio Summary
**GET** `/api/portfolio/summary`

Returns portfolio summary metrics only.

### Get Portfolio Allocation
**GET** `/api/portfolio/allocation`

Returns portfolio allocation breakdown by position size.

### Get Position by Symbol
**GET** `/api/portfolio/position/{symbol}`

Returns specific position data for a symbol.

**Example:** `/api/portfolio/position/AAPL`

---

## Account Endpoints

### Get Account Summary
**GET** `/api/account/summary`

Returns detailed account information from Alpaca.

**Response:**
```json
{
  "success": true,
  "account": {
    "buying_power": 45670.25,
    "cash": 25430.50,
    "portfolio_value": 200000.75,
    "day_trade_buying_power": 91340.50,
    "unrealized_pl": 3250.25,
    "unrealized_plpc": 1.65,
    "day_trade_count": 2,
    "trading_blocked": false,
    "pattern_day_trader": false,
    "last_updated": "2025-08-06T14:30:00Z"
  },
  "timestamp": "2025-08-06T14:30:00Z"
}
```

---

## Trading Control Endpoints

### Execute Buy Order
**POST** `/api/trading/buy`

Executes a manual buy order.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "shares": 10,      // Optional: specify shares
  "amount": 1000     // Optional: specify dollar amount
}
```

**Response:**
```json
{
  "success": true,
  "order_id": "abc123",
  "shares": 10,
  "price": 175.50,
  "message": "Buy order executed: 10 shares of AAPL at $175.50"
}
```

### Execute Sell Order
**POST** `/api/trading/sell`

Executes a manual sell order.

**Request Body:**
```json
{
  "ticker": "AAPL",
  "shares": 10       // Optional: specify shares (default: all shares)
}
```

### Pause Auto Trading
**POST** `/api/trading/pause`

Pauses automatic trading system.

### Resume Auto Trading
**POST** `/api/trading/resume`

Resumes automatic trading system.

### Trigger Market Scan
**POST** `/api/trading/scan`

Triggers immediate market scan.

### Send Test Notification
**POST** `/api/notifications/test`

Sends test notification via Telegram.

---

## Real-Time WebSocket Endpoints

### Trading Updates
**WebSocket** `/ws/trading`

Real-time updates for:
- New AI predictions
- Trade executions
- Portfolio changes
- Account updates

**Message Format:**
```json
{
  "type": "trade_executed",
  "data": {
    "symbol": "AAPL",
    "action": "BUY",
    "shares": 10,
    "price": 175.50,
    "timestamp": "2025-08-06T14:30:00Z"
  }
}
```

**Message Types:**
- `trade_executed`: New trade executed
- `ai_prediction`: New AI prediction
- `portfolio_update`: Portfolio value changed
- `account_update`: Account status changed
- `system_status`: System status changed

---

## Health & Status Endpoints

### Basic Health Check
**GET** `/health`

Returns basic system health status.

### Detailed Health Check
**GET** `/health/detailed`

Returns comprehensive system health and component status.

---

## Error Responses

All endpoints return consistent error responses:

```json
{
  "success": false,
  "error": "Error message description",
  "timestamp": "2025-08-06T14:30:00Z"
}
```

**HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `500`: Internal Server Error

---

## Frontend Integration Examples

### React Hook for AI Predictions
```javascript
import { useState, useEffect } from 'react';

export const useAIPredictions = () => {
  const [predictions, setPredictions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchPredictions = async () => {
      try {
        const response = await fetch('/api/ai/predictions');
        const data = await response.json();
        
        if (data.success) {
          setPredictions(data);
        } else {
          setError(data.error);
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPredictions();
    
    // Refresh every 30 seconds
    const interval = setInterval(fetchPredictions, 30000);
    
    return () => clearInterval(interval);
  }, []);

  return { predictions, loading, error };
};
```

### Execute Buy Order
```javascript
const executeBuyOrder = async (ticker, amount) => {
  try {
    const response = await fetch('/api/trading/buy', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ticker: ticker.toUpperCase(),
        amount: amount
      })
    });
    
    const result = await response.json();
    
    if (result.success) {
      console.log('Order executed:', result.message);
      // Update UI with success
    } else {
      console.error('Order failed:', result.error);
      // Show error to user
    }
  } catch (error) {
    console.error('Network error:', error);
  }
};
```

### WebSocket Connection
```javascript
const connectWebSocket = () => {
  const ws = new WebSocket('ws://localhost:8000/ws/trading');
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch (message.type) {
      case 'trade_executed':
        // Update portfolio display
        updatePortfolio(message.data);
        break;
      case 'ai_prediction':
        // Show new prediction
        showNewPrediction(message.data);
        break;
      case 'portfolio_update':
        // Refresh portfolio data
        refreshPortfolio();
        break;
    }
  };
  
  ws.onopen = () => console.log('WebSocket connected');
  ws.onclose = () => console.log('WebSocket disconnected');
  
  return ws;
};
```

---

## Notes

- All timestamps are in ISO 8601 format (UTC)
- Prices are in USD with 2-4 decimal places
- Confidence scores are on a scale of 0-10
- Percentage values are already converted (e.g., 5.25 = 5.25%)
- All API responses include a `timestamp` field
- WebSocket connections automatically reconnect on disconnect
