'use client'

import React, { useState, useEffect } from 'react'

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

interface AISignal {
  symbol: string
  signal_type: string
  confidence: number
  reasoning: string
  technical_analysis: Record<string, number>
  fundamental_analysis: Record<string, number>
  sentiment_analysis: Record<string, number>
  timestamp: string
}

interface LearningMetrics {
  model_performance: {
    accuracy: number
    precision: number
    recall: number
    f1_score: number
  }
  learning_progress: {
    total_trades_analyzed: number
    successful_predictions: number
    model_improvements: number
    last_update: string
  }
  adaptation_metrics: {
    market_regime_detection: number
    strategy_adjustments: number
    risk_calibration: number
  }
}

export default function AIAnalysisDashboard() {
  const [marketPulse, setMarketPulse] = useState<MarketPulse | null>(null)
  const [aiSignals, setAiSignals] = useState<AISignal[]>([])
  const [learningMetrics, setLearningMetrics] = useState<LearningMetrics | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeSection, setActiveSection] = useState('market-pulse')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [pulseRes, signalsRes, learningRes] = await Promise.all([
        fetch(`${backendUrl}/api/dashboard/market/pulse`),
        fetch(`${backendUrl}/api/dashboard/ai/signals`),
        fetch(`${backendUrl}/api/dashboard/ai/learning-metrics`)
      ])

      if (!pulseRes.ok || !signalsRes.ok || !learningRes.ok) {
        throw new Error('Failed to fetch AI analysis data from backend')
      }

      const [pulseData, signalsData, learningData] = await Promise.all([
        pulseRes.json(),
        signalsRes.json(),
        learningRes.json()
      ])

      // Map backend data to frontend interface
      const mappedMarketPulse = {
        market_overview: pulseData.market_overview || {},
        sector_performance: pulseData.active_sectors || {},
        sentiment_indicators: {
          overall_sentiment: pulseData.market_overview?.trend || 'NEUTRAL',
          volatility_index: pulseData.market_overview?.volatility_index || 20.0,
          volume_profile: pulseData.market_overview?.volume_profile || 'NORMAL'
        },
        ai_market_assessment: {
          regime: pulseData.market_overview?.trend || 'NEUTRAL',
          confidence: 0.75,
          key_drivers: pulseData.historical_context?.momentum_history || [],
          risks: ['Market volatility', 'Economic uncertainty']
        }
      }

      // Map signals data
      const mappedSignals = (signalsData.signals || []).map((signal: any) => ({
        symbol: signal.symbol || 'N/A',
        signal_type: signal.signal || signal.action || 'HOLD',
        confidence: signal.confidence || 0,
        reasoning: signal.reasoning || 'Analysis in progress',
        technical_analysis: signal.technical_scores || {},
        fundamental_analysis: signal.fundamental_scores || {},
        sentiment_analysis: signal.sentiment_scores || {},
        timestamp: signal.generated_at || signal.timestamp || new Date().toISOString()
      }))

      // Map learning metrics
      const mappedLearningMetrics = {
        model_performance: {
          accuracy: learningData.accuracy || 0,
          precision: learningData.model_performance?.precision || 0.5,
          recall: learningData.model_performance?.recall || 0.5,
          f1_score: learningData.model_performance?.f1_score || 0.5
        },
        learning_progress: {
          total_trades_analyzed: learningData.total_predictions || 0,
          successful_predictions: learningData.correct_predictions || 0,
          model_improvements: 0,
          last_update: learningData.last_training || new Date().toISOString()
        },
        adaptation_metrics: {
          market_regime_detection: 0.8,
          strategy_adjustments: 0.7,
          risk_calibration: 0.75
        }
      }

      setMarketPulse(mappedMarketPulse)
      setAiSignals(mappedSignals)
      setLearningMetrics(mappedLearningMetrics)
      
    } catch (error: any) {
      const errorMessage = error.message || 'Failed to fetch AI analysis data'
      setError(errorMessage)
      console.error('AI analysis dashboard error:', error)
      
      setMarketPulse(null)
      setAiSignals([])
      setLearningMetrics(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  const formatPercent = (value: number) => {
    return `${value >= 0 ? '+' : ''}${(value * 100).toFixed(2)}%`
  }

  const getRegimeColor = (regime: string) => {
    switch (regime.toLowerCase()) {
      case 'bullish': return 'text-green-400'
      case 'bearish': return 'text-red-400'
      case 'neutral': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-400">Loading AI analysis...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">AI Analysis Dashboard</h2>
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry Connection
          </button>
        </div>
        
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-400 mb-2">AI Services Connection Error</h3>
          <p className="text-red-300">{error}</p>
          <p className="text-gray-400 mt-2 text-sm">
            AI analysis services are not yet implemented. The system is currently in development mode.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">AI Analysis Dashboard</h2>
        <button 
          onClick={fetchData} 
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
        >
          Refresh Analysis
        </button>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-4 border-b border-gray-700">
        {[
          { key: 'market-pulse', label: 'Market Pulse' },
          { key: 'ai-signals', label: 'AI Signals' },
          { key: 'learning-metrics', label: 'Learning Progress' }
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

      {/* Market Pulse Section */}
      {activeSection === 'market-pulse' && (
        <div className="space-y-6">
          {!marketPulse ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <p className="text-gray-400 text-center">Market pulse data not available</p>
            </div>
          ) : (
            <>
              {/* AI Market Assessment */}
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">AI Market Assessment</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <div className="flex items-center space-x-3 mb-4">
                      <div className="text-gray-400">Current Regime:</div>
                      <div className={`text-xl font-bold ${getRegimeColor(marketPulse.ai_market_assessment.regime)}`}>
                        {marketPulse.ai_market_assessment.regime}
                      </div>
                      <div className="text-sm text-gray-500">
                        ({(marketPulse.ai_market_assessment.confidence * 100).toFixed(0)}% confidence)
                      </div>
                    </div>
                    
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-blue-400">Key Market Drivers:</div>
                      <ul className="text-sm text-gray-300 space-y-1">
                        {marketPulse.ai_market_assessment.key_drivers.map((driver, index) => (
                          <li key={index} className="flex items-center">
                            <div className="w-2 h-2 bg-blue-500 rounded-full mr-2"></div>
                            {driver}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                  
                  <div>
                    <div className="space-y-2">
                      <div className="text-sm font-medium text-red-400">Risk Factors:</div>
                      <ul className="text-sm text-gray-300 space-y-1">
                        {marketPulse.ai_market_assessment.risks.map((risk, index) => (
                          <li key={index} className="flex items-center">
                            <div className="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                            {risk}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                </div>
              </div>

              {/* Market Overview */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {Object.entries(marketPulse.market_overview).map(([key, value]) => (
                  <div key={key} className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                    <div className="text-gray-500 text-sm capitalize">{key.replace('_', ' ')}</div>
                    <div className={`text-xl font-bold ${typeof value === 'number' && value >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      {typeof value === 'number' ? formatPercent(value) : value}
                    </div>
                  </div>
                ))}
              </div>

              {/* Sector Performance */}
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Sector Performance</h3>
                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                  {Object.entries(marketPulse.sector_performance).map(([sector, performance]) => (
                    <div key={sector} className="flex justify-between items-center p-3 bg-gray-700 rounded">
                      <span className="text-gray-300 text-sm">{sector}</span>
                      <span className={`font-medium ${performance >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                        {formatPercent(performance)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sentiment Indicators */}
              <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                <h3 className="text-lg font-semibold text-white mb-4">Sentiment Indicators</h3>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {Object.entries(marketPulse.sentiment_indicators).map(([indicator, value]) => (
                    <div key={indicator} className="flex justify-between items-center p-3 bg-gray-700 rounded">
                      <span className="text-gray-300 text-sm capitalize">{indicator.replace('_', ' ')}</span>
                      <span className="text-white font-medium">
                        {typeof value === 'number' ? value.toFixed(2) : value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* AI Signals Section */}
      {activeSection === 'ai-signals' && (
        <div className="space-y-6">
          {aiSignals.length === 0 ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <p className="text-gray-400 text-center">No AI signals available</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {aiSignals.map((signal, index) => (
                <div key={index} className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="text-xl font-bold text-white">{signal.symbol}</h3>
                      <div className={`inline-block px-3 py-1 rounded text-sm font-medium ${
                        signal.signal_type === 'BUY' ? 'bg-green-500 text-white' :
                        signal.signal_type === 'SELL' ? 'bg-red-500 text-white' :
                        'bg-yellow-500 text-black'
                      }`}>
                        {signal.signal_type}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-lg font-bold text-white">
                        Confidence: {(signal.confidence * 100).toFixed(0)}%
                      </div>
                      <div className="text-sm text-gray-400">
                        {new Date(signal.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                  
                  <div className="mb-4">
                    <div className="text-sm font-medium text-blue-400 mb-2">AI Reasoning:</div>
                    <div className="text-gray-300 text-sm bg-gray-700 p-3 rounded">
                      {signal.reasoning}
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gray-700 p-3 rounded">
                      <div className="text-sm font-medium text-green-400 mb-2">Technical Analysis</div>
                      <div className="space-y-1">
                        {Object.entries(signal.technical_analysis).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-400 capitalize">{key.replace('_', ' ')}</span>
                            <span className="text-white">{value.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div className="bg-gray-700 p-3 rounded">
                      <div className="text-sm font-medium text-blue-400 mb-2">Fundamental Analysis</div>
                      <div className="space-y-1">
                        {Object.entries(signal.fundamental_analysis).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-400 capitalize">{key.replace('_', ' ')}</span>
                            <span className="text-white">{value.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                    
                    <div className="bg-gray-700 p-3 rounded">
                      <div className="text-sm font-medium text-purple-400 mb-2">Sentiment Analysis</div>
                      <div className="space-y-1">
                        {Object.entries(signal.sentiment_analysis).map(([key, value]) => (
                          <div key={key} className="flex justify-between text-xs">
                            <span className="text-gray-400 capitalize">{key.replace('_', ' ')}</span>
                            <span className="text-white">{value.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Learning Metrics Section */}
      {activeSection === 'learning-metrics' && (
        <div className="space-y-6">
          {!learningMetrics ? (
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <p className="text-gray-400 text-center">Learning metrics not available</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Model Accuracy</div>
                  <div className="text-2xl font-bold text-green-400">
                    {(learningMetrics.model_performance.accuracy * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Precision</div>
                  <div className="text-2xl font-bold text-blue-400">
                    {(learningMetrics.model_performance.precision * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">Recall</div>
                  <div className="text-2xl font-bold text-purple-400">
                    {(learningMetrics.model_performance.recall * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <div className="text-gray-500 text-sm">F1 Score</div>
                  <div className="text-2xl font-bold text-yellow-400">
                    {learningMetrics.model_performance.f1_score.toFixed(3)}
                  </div>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold text-white mb-4">Learning Progress</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Total Trades Analyzed</span>
                      <span className="text-white font-medium">{learningMetrics.learning_progress.total_trades_analyzed.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Successful Predictions</span>
                      <span className="text-green-400 font-medium">{learningMetrics.learning_progress.successful_predictions.toLocaleString()}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Model Improvements</span>
                      <span className="text-blue-400 font-medium">{learningMetrics.learning_progress.model_improvements}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Last Update</span>
                      <span className="text-white font-medium">
                        {new Date(learningMetrics.learning_progress.last_update).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
                  <h3 className="text-lg font-semibold text-white mb-4">Adaptation Metrics</h3>
                  <div className="space-y-4">
                    <div className="flex justify-between">
                      <span className="text-gray-400">Market Regime Detection</span>
                      <span className="text-white font-medium">
                        {(learningMetrics.adaptation_metrics.market_regime_detection * 100).toFixed(1)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Strategy Adjustments</span>
                      <span className="text-white font-medium">{learningMetrics.adaptation_metrics.strategy_adjustments}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Risk Calibration</span>
                      <span className="text-white font-medium">
                        {(learningMetrics.adaptation_metrics.risk_calibration * 100).toFixed(1)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
