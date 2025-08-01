'use client'

import React, { useState, useEffect } from 'react'

interface DetailedHolding {
  symbol: string
  qty: number
  market_value: number
  entry_price: number
  current_price: number
  unrealized_pl: number
  unrealized_pnl_percent: number
  position_size_percent: number
  risk_metrics: {
    beta: number
    volatility: number
    sharpe_ratio: number
  }
  ai_signals: {
    current_signal: string
    confidence: number
    next_review: string
  }
}

interface PerformanceAnalytics {
  daily_performance: {
    return_pct: number
    alpha: number
    beta: number
    sharpe_ratio: number
    sortino_ratio: number
    max_drawdown: number
    volatility: number
  }
  attribution: {
    sector_allocation: Record<string, number>
    factor_exposure: Record<string, number>
  }
  risk_metrics: {
    var_95: number
    cvar_95: number
    beta_spy: number
    correlation_spy: number
    tracking_error: number
  }
  trade_analytics: {
    win_rate: number
    avg_win: number
    avg_loss: number
    profit_factor: number
    avg_holding_period: number
  }
}

interface MarketPulse {
  market_overview: Record<string, number>
  sector_performance: Record<string, number>
  sentiment_indicators: Record<string, number | string>
  ai_market_assessment: {
    regime: string
    confidence: number
    key_drivers: string[]
    risks: string[]
  }
}

interface WatchlistSignal {
  symbol: string
  signal_type: string
  confidence: number
  current_price: number
  target_price: number
  stop_loss: number
  technical_score: number
  fundamental_score: number
  sentiment_score: number
  last_updated: string
}

export default function EnhancedDashboard() {
  const [detailedHoldings, setDetailedHoldings] = useState<DetailedHolding[]>([])
  const [performanceAnalytics, setPerformanceAnalytics] = useState<PerformanceAnalytics | null>(null)
  const [marketPulse, setMarketPulse] = useState<MarketPulse | null>(null)
  const [watchlistSignals, setWatchlistSignals] = useState<WatchlistSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('holdings')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'

  const fetchData = async () => {
    try {
      setLoading(true)
      
      const [holdingsRes, analyticsRes, pulseRes, signalsRes] = await Promise.all([
        fetch(`${backendUrl}/api/dashboard/holdings/detailed`),
        fetch(`${backendUrl}/api/dashboard/analytics/performance`),
        fetch(`${backendUrl}/api/dashboard/market/pulse`),
        fetch(`${backendUrl}/api/dashboard/watchlist/signals`)
      ])

      const [holdingsData, analyticsData, pulseData, signalsData] = await Promise.all([
        holdingsRes.json(),
        analyticsRes.json(),
        pulseRes.json(),
        signalsRes.json()
      ])

      setDetailedHoldings(holdingsData.holdings || [])
      setPerformanceAnalytics(analyticsData.analytics)
      setMarketPulse(pulseData.market_pulse)
      setWatchlistSignals(signalsData.signals || [])
      
    } catch (error) {
      console.error('Failed to fetch enhanced dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'bg-green-500 text-white'
      case 'SELL': return 'bg-red-500 text-white'
      case 'HOLD': return 'bg-yellow-500 text-black'
      default: return 'bg-gray-500 text-white'
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Enhanced Trading Dashboard</h2>
        <button 
          onClick={fetchData} 
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Refresh Data
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-700">
        <nav className="flex space-x-8">
          {[
            { id: 'holdings', label: 'Advanced Holdings' },
            { id: 'analytics', label: 'Performance Analytics' },
            { id: 'market', label: 'Market Pulse' },
            { id: 'watchlist', label: 'AI Watchlist' }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-400'
                  : 'border-transparent text-gray-400 hover:text-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Holdings Tab */}
      {activeTab === 'holdings' && (
        <div className="space-y-4">
          {detailedHoldings.map((holding) => (
            <div key={holding.symbol} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  <h3 className="text-lg font-semibold text-white">{holding.symbol}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(holding.ai_signals.current_signal)}`}>
                    {holding.ai_signals.current_signal}
                  </span>
                  <span className="text-sm text-gray-400">
                    {(holding.ai_signals.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-white">{formatCurrency(holding.market_value)}</div>
                  <div className={`text-sm ${holding.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPercent(holding.unrealized_pnl_percent)}
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-300">
                <div>
                  <div className="text-gray-500">Qty</div>
                  <div className="font-medium text-white">{holding.qty}</div>
                </div>
                <div>
                  <div className="text-gray-500">Entry Price</div>
                  <div className="font-medium text-white">{formatCurrency(holding.entry_price)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Current Price</div>
                  <div className="font-medium text-white">{formatCurrency(holding.current_price)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Position Size</div>
                  <div className="font-medium text-white">{holding.position_size_percent.toFixed(1)}%</div>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-3 gap-4 text-sm text-gray-300">
                <div>
                  <div className="text-gray-500">Beta</div>
                  <div className="font-medium text-white">{holding.risk_metrics.beta}</div>
                </div>
                <div>
                  <div className="text-gray-500">Volatility</div>
                  <div className="font-medium text-white">{holding.risk_metrics.volatility}%</div>
                </div>
                <div>
                  <div className="text-gray-500">Sharpe Ratio</div>
                  <div className="font-medium text-white">{holding.risk_metrics.sharpe_ratio}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Analytics Tab */}
      {activeTab === 'analytics' && performanceAnalytics && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Daily Performance</h3>
            <div className="space-y-3 text-gray-300">
              <div className="flex justify-between">
                <span>Return</span>
                <span className="font-semibold text-white">{formatPercent(performanceAnalytics.daily_performance.return_pct)}</span>
              </div>
              <div className="flex justify-between">
                <span>Sharpe Ratio</span>
                <span className="font-semibold text-white">{performanceAnalytics.daily_performance.sharpe_ratio}</span>
              </div>
              <div className="flex justify-between">
                <span>Max Drawdown</span>
                <span className="font-semibold text-red-400">{formatPercent(performanceAnalytics.daily_performance.max_drawdown)}</span>
              </div>
              <div className="flex justify-between">
                <span>Volatility</span>
                <span className="font-semibold text-white">{performanceAnalytics.daily_performance.volatility.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Risk Metrics</h3>
            <div className="space-y-3 text-gray-300">
              <div className="flex justify-between">
                <span>VaR (95%)</span>
                <span className="font-semibold text-white">{formatPercent(performanceAnalytics.risk_metrics.var_95)}</span>
              </div>
              <div className="flex justify-between">
                <span>Beta (SPY)</span>
                <span className="font-semibold text-white">{performanceAnalytics.risk_metrics.beta_spy}</span>
              </div>
              <div className="flex justify-between">
                <span>Correlation (SPY)</span>
                <span className="font-semibold text-white">{performanceAnalytics.risk_metrics.correlation_spy}</span>
              </div>
              <div className="flex justify-between">
                <span>Tracking Error</span>
                <span className="font-semibold text-white">{performanceAnalytics.risk_metrics.tracking_error.toFixed(1)}%</span>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Sector Allocation</h3>
            <div className="space-y-3">
              {Object.entries(performanceAnalytics.attribution.sector_allocation).map(([sector, allocation]) => (
                <div key={sector} className="space-y-1">
                  <div className="flex justify-between text-sm text-gray-300">
                    <span>{sector}</span>
                    <span className="text-white">{allocation.toFixed(1)}%</span>
                  </div>
                  <div className="w-full bg-gray-700 rounded-full h-2">
                    <div 
                      className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${allocation}%` }}
                    ></div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Trade Analytics</h3>
            <div className="space-y-3 text-gray-300">
              <div className="flex justify-between">
                <span>Win Rate</span>
                <span className="font-semibold text-white">{(performanceAnalytics.trade_analytics.win_rate * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span>Profit Factor</span>
                <span className="font-semibold text-white">{performanceAnalytics.trade_analytics.profit_factor.toFixed(2)}</span>
              </div>
              <div className="flex justify-between">
                <span>Avg Win</span>
                <span className="font-semibold text-green-400">{formatPercent(performanceAnalytics.trade_analytics.avg_win)}</span>
              </div>
              <div className="flex justify-between">
                <span>Avg Loss</span>
                <span className="font-semibold text-red-400">{formatPercent(performanceAnalytics.trade_analytics.avg_loss)}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Market Pulse Tab */}
      {activeTab === 'market' && marketPulse && (
        <div className="grid gap-6 md:grid-cols-2">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Market Overview</h3>
            <div className="space-y-3 text-gray-300">
              {Object.entries(marketPulse.market_overview).map(([key, value]) => (
                <div key={key} className="flex justify-between">
                  <span className="capitalize">{key.replace('_', ' ')}</span>
                  <span className={`font-semibold ${value >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {typeof value === 'number' ? (key.includes('yield') ? `${value.toFixed(2)}%` : formatPercent(value)) : value}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">AI Market Assessment</h3>
            <div className="space-y-3 text-gray-300">
              <div className="flex justify-between">
                <span>Regime</span>
                <span className="px-2 py-1 bg-blue-600 text-white rounded text-sm">
                  {marketPulse.ai_market_assessment.regime}
                </span>
              </div>
              <div className="flex justify-between">
                <span>Confidence</span>
                <span className="font-semibold text-white">{(marketPulse.ai_market_assessment.confidence * 100).toFixed(0)}%</span>
              </div>
              <div>
                <h4 className="font-medium mb-2 text-white">Key Drivers</h4>
                <ul className="text-sm space-y-1">
                  {marketPulse.ai_market_assessment.key_drivers.map((driver, idx) => (
                    <li key={idx} className="text-green-400">• {driver}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4 className="font-medium mb-2 text-white">Risks</h4>
                <ul className="text-sm space-y-1">
                  {marketPulse.ai_market_assessment.risks.map((risk, idx) => (
                    <li key={idx} className="text-red-400">• {risk}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>

          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 md:col-span-2">
            <h3 className="text-lg font-semibold text-white mb-4">Sector Performance</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              {Object.entries(marketPulse.sector_performance).map(([sector, performance]) => (
                <div key={sector} className="text-center">
                  <div className="text-sm font-medium text-gray-300">{sector}</div>
                  <div className={`text-lg font-bold ${performance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPercent(performance)}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Watchlist Tab */}
      {activeTab === 'watchlist' && (
        <div className="space-y-4">
          {watchlistSignals.map((signal) => (
            <div key={signal.symbol} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center space-x-3">
                  <h3 className="text-lg font-semibold text-white">{signal.symbol}</h3>
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(signal.signal_type)}`}>
                    {signal.signal_type}
                  </span>
                  <span className="text-sm text-gray-400">
                    {(signal.confidence * 100).toFixed(0)}% confidence
                  </span>
                </div>
                <div className="text-right">
                  <div className="text-lg font-semibold text-white">{formatCurrency(signal.current_price)}</div>
                  <div className="text-sm text-gray-400">Current Price</div>
                </div>
              </div>
              
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm text-gray-300">
                <div>
                  <div className="text-gray-500">Target</div>
                  <div className="font-medium text-green-400">{formatCurrency(signal.target_price)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Stop Loss</div>
                  <div className="font-medium text-red-400">{formatCurrency(signal.stop_loss)}</div>
                </div>
                <div>
                  <div className="text-gray-500">Technical</div>
                  <div className="font-medium text-white">{(signal.technical_score * 100).toFixed(0)}%</div>
                </div>
                <div>
                  <div className="text-gray-500">Sentiment</div>
                  <div className="font-medium text-white">{(signal.sentiment_score * 100).toFixed(0)}%</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
