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

export default function TradingDashboard() {
  const [detailedHoldings, setDetailedHoldings] = useState<DetailedHolding[]>([])
  const [performanceAnalytics, setPerformanceAnalytics] = useState<PerformanceAnalytics | null>(null)
  const [watchlistSignals, setWatchlistSignals] = useState<WatchlistSignal[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState('holdings')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      // Use working endpoints instead of unimplemented dashboard endpoints
      const [holdingsRes, accountRes] = await Promise.all([
        fetch(`${backendUrl}/api/holdings`),
        fetch(`${backendUrl}/api/account`)
      ])

      if (!holdingsRes.ok || !accountRes.ok) {
        throw new Error('Failed to fetch trading data from backend')
      }

      const [holdingsData, accountData] = await Promise.all([
        holdingsRes.json(),
        accountRes.json()
      ])

      // Map basic holdings data to detailed format
      const mappedHoldings = (holdingsData.holdings || []).map((holding: any) => ({
        symbol: holding.symbol,
        qty: holding.quantity,
        market_value: holding.market_value,
        entry_price: holding.current_price, // Approximation - actual entry price not available
        current_price: holding.current_price,
        unrealized_pl: holding.unrealized_pnl,
        unrealized_pnl_percent: holding.percentage_change,
        position_size_percent: accountData.portfolio_value > 0 ? (holding.market_value / accountData.portfolio_value) * 100 : 0,
        risk_metrics: {
          beta: null, // Not available without external data
          volatility: null,
          sharpe_ratio: null
        },
        ai_signals: {
          current_signal: 'DATA_UNAVAILABLE',
          confidence: 0,
          next_review: null
        }
      }))

      setDetailedHoldings(mappedHoldings)
      // Clear unavailable data instead of showing mock data
      setPerformanceAnalytics(null)
      setWatchlistSignals([])
      
    } catch (error: any) {
      const errorMessage = error.message || 'Failed to fetch trading data'
      setError(errorMessage)
      console.error('Trading dashboard error:', error)
      
      setDetailedHoldings([])
      setPerformanceAnalytics(null)
      setWatchlistSignals([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    // More frequent updates during market hours
    const interval = setInterval(fetchData, 15000) // Every 15 seconds for live trading
    return () => clearInterval(interval)
  }, [])

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(value)
  }

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${value.toFixed(2)}%`
  }

  const getSignalColor = (signal: string) => {
    switch (signal) {
      case 'BUY': return 'bg-green-500 text-white'
      case 'SELL': return 'bg-red-500 text-white'
      case 'HOLD': return 'bg-yellow-500 text-black'
      default: return 'bg-gray-500 text-white'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-400">Loading trading data...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">Trading Dashboard</h2>
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry Connection
          </button>
        </div>
        
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-400 mb-2">Backend Connection Error</h3>
          <p className="text-red-300">{error}</p>
          <p className="text-gray-400 mt-2 text-sm">
            Using available endpoints. Advanced analytics and AI features are in development.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">Trading Dashboard</h2>
        <button 
          onClick={fetchData} 
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Refresh Data
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-4 border-b border-gray-700">
        {[
          { key: 'holdings', label: 'Portfolio Holdings' },
          { key: 'performance', label: 'Performance Analytics' },
          { key: 'watchlist', label: 'Trading Signals' }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveSection(tab.key)}
            className={`py-2 px-4 font-medium text-sm transition-colors border-b-2 ${
              activeSection === tab.key
                ? 'border-blue-500 text-blue-400'
                : 'border-transparent text-gray-300 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Holdings Section */}
      {activeSection === 'holdings' && (
        <div className="space-y-6">
          {detailedHoldings.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <p className="text-gray-400 text-center">No portfolio positions found</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {detailedHoldings.map((holding) => (
                <div key={holding.symbol} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white">{holding.symbol}</h3>
                      <p className="text-gray-400">{holding.qty} shares</p>
                    </div>
                    <div className="text-right">
                      <div className="text-2xl font-bold text-white">
                        {formatCurrency(holding.market_value)}
                      </div>
                      <div className={`text-sm ${holding.unrealized_pl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatCurrency(holding.unrealized_pl)} ({formatPercent(holding.unrealized_pnl_percent)})
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-gray-500 text-sm">Entry Price</div>
                      <div className="text-white font-medium">{formatCurrency(holding.entry_price)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">Current Price</div>
                      <div className="text-white font-medium">{formatCurrency(holding.current_price)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">Position Size</div>
                      <div className="text-white font-medium">{holding.position_size_percent.toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">AI Signal</div>
                      <div className={`px-2 py-1 rounded text-xs font-medium ${getSignalColor(holding.ai_signals.current_signal)}`}>
                        {holding.ai_signals.current_signal}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500">Beta</div>
                      <div className="text-white">{holding.risk_metrics.beta.toFixed(2)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Volatility</div>
                      <div className="text-white">{(holding.risk_metrics.volatility * 100).toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Sharpe Ratio</div>
                      <div className="text-white">{holding.risk_metrics.sharpe_ratio.toFixed(2)}</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Performance Section */}
      {activeSection === 'performance' && (
        <div className="space-y-6">
          {!performanceAnalytics ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="text-center py-8">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">Performance Analytics</h3>
                <p className="text-gray-400 mb-4">Advanced performance analytics are in development</p>
                <div className="text-sm text-gray-500">
                  <p>Coming soon:</p>
                  <ul className="list-disc list-inside mt-2 space-y-1 text-left max-w-md mx-auto">
                    <li>Risk metrics (VaR, Beta, Sharpe ratio)</li>
                    <li>Performance attribution analysis</li>
                    <li>Drawdown and volatility calculations</li>
                    <li>Trade analytics and win rates</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Daily Return</div>
                  <div className={`text-2xl font-bold ${performanceAnalytics.daily_performance.return_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    {formatPercent(performanceAnalytics.daily_performance.return_pct)}
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Sharpe Ratio</div>
                  <div className="text-2xl font-bold text-white">
                    {performanceAnalytics.daily_performance.sharpe_ratio.toFixed(2)}
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Max Drawdown</div>
                  <div className="text-2xl font-bold text-red-400">
                    {formatPercent(performanceAnalytics.daily_performance.max_drawdown)}
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Win Rate</div>
                  <div className="text-2xl font-bold text-green-400">
                    {(performanceAnalytics.trade_analytics.win_rate * 100).toFixed(1)}%
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold text-white mb-4">Risk Metrics</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Value at Risk (95%)</span>
                      <span className="text-white">{formatCurrency(performanceAnalytics.risk_metrics.var_95)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Beta vs SPY</span>
                      <span className="text-white">{performanceAnalytics.risk_metrics.beta_spy.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Correlation vs SPY</span>
                      <span className="text-white">{performanceAnalytics.risk_metrics.correlation_spy.toFixed(2)}</span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold text-white mb-4">Trade Analytics</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Average Win</span>
                      <span className="text-green-400">{formatCurrency(performanceAnalytics.trade_analytics.avg_win)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Average Loss</span>
                      <span className="text-red-400">{formatCurrency(performanceAnalytics.trade_analytics.avg_loss)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Profit Factor</span>
                      <span className="text-white">{performanceAnalytics.trade_analytics.profit_factor.toFixed(2)}</span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Watchlist Signals Section */}
      {activeSection === 'watchlist' && (
        <div className="space-y-6">
          {watchlistSignals.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <div className="text-center py-8">
                <h3 className="text-lg font-semibold text-gray-300 mb-2">AI Trading Signals</h3>
                <p className="text-gray-400 mb-4">AI signal generation is in development</p>
                <div className="text-sm text-gray-500">
                  <p>Coming soon:</p>
                  <ul className="list-disc list-inside mt-2 space-y-1 text-left max-w-md mx-auto">
                    <li>Technical analysis signals</li>
                    <li>Sentiment-based recommendations</li>
                    <li>Risk-adjusted position sizing</li>
                    <li>Real-time confidence scoring</li>
                  </ul>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid gap-4">
              {watchlistSignals.map((signal) => (
                <div key={signal.symbol} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white">{signal.symbol}</h3>
                      <div className={`inline-block px-3 py-1 rounded text-sm font-medium ${getSignalColor(signal.signal_type)}`}>
                        {signal.signal_type}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-white">
                        {formatCurrency(signal.current_price)}
                      </div>
                      <div className="text-sm text-gray-400">
                        Confidence: {(signal.confidence * 100).toFixed(0)}%
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div>
                      <div className="text-gray-500 text-sm">Target Price</div>
                      <div className="text-green-400 font-medium">{formatCurrency(signal.target_price)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">Stop Loss</div>
                      <div className="text-red-400 font-medium">{formatCurrency(signal.stop_loss)}</div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">Upside Potential</div>
                      <div className="text-white font-medium">
                        {formatPercent(((signal.target_price - signal.current_price) / signal.current_price) * 100)}
                      </div>
                    </div>
                    <div>
                      <div className="text-gray-500 text-sm">Risk</div>
                      <div className="text-white font-medium">
                        {formatPercent(((signal.stop_loss - signal.current_price) / signal.current_price) * 100)}
                      </div>
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <div className="text-gray-500">Technical</div>
                      <div className="text-white">{(signal.technical_score * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Fundamental</div>
                      <div className="text-white">{(signal.fundamental_score * 100).toFixed(0)}%</div>
                    </div>
                    <div>
                      <div className="text-gray-500">Sentiment</div>
                      <div className="text-white">{(signal.sentiment_score * 100).toFixed(0)}%</div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
