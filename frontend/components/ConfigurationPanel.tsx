'use client'

import React, { useState, useEffect } from 'react'

interface SystemConfiguration {
  trading_settings: {
    risk_level: string
    max_position_size: number
    stop_loss_percent: number
    take_profit_percent: number
    max_daily_trades: number
    portfolio_heat: number
  }
  ai_settings: {
    min_signal_confidence: number
    analysis_frequency: number
    auto_execution_enabled: boolean
    learning_rate: number
    model_retrain_frequency: number
  }
  risk_management: {
    max_drawdown_limit: number
    correlation_limit: number
    sector_concentration_limit: number
    volatility_threshold: number
  }
  market_data: {
    primary_data_source: string
    backup_data_source: string
    update_frequency: number
    extended_hours_trading: boolean
  }
  notifications: {
    email_enabled: boolean
    telegram_enabled: boolean
    push_notifications: boolean
    trade_confirmations: boolean
    daily_reports: boolean
  }
}

interface SystemStatus {
  trading_system: {
    status: string
    uptime: number
    last_trade: string
    active_positions: number
  }
  ai_engine: {
    status: string
    model_version: string
    last_update: string
    prediction_accuracy: number
  }
  data_feeds: {
    market_data: string
    news_feed: string
    social_sentiment: string
    economic_data: string
  }
  infrastructure: {
    database: string
    message_queue: string
    cache_system: string
    backup_status: string
  }
}

export default function ConfigurationPanel() {
  const [config, setConfig] = useState<SystemConfiguration | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [activeSection, setActiveSection] = useState('trading')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'

  const fetchData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [configRes, statusRes] = await Promise.all([
        fetch(`${backendUrl}/api/config/system`),
        fetch(`${backendUrl}/api/config/status`)
      ])

      const errors = []
      if (!configRes.ok) {
        const configError = await configRes.json().catch(() => ({ detail: 'Configuration service not implemented' }))
        errors.push(`Config: ${configError.detail}`)
      }
      if (!statusRes.ok) {
        const statusError = await statusRes.json().catch(() => ({ detail: 'Status service not implemented' }))
        errors.push(`Status: ${statusError.detail}`)
      }

      if (errors.length > 0) {
        throw new Error(errors.join('; '))
      }

      const [configData, statusData] = await Promise.all([
        configRes.json(),
        statusRes.json()
      ])

      setConfig(configData.config || null)
      setSystemStatus(statusData.status || null)
      
    } catch (error: any) {
      const errorMessage = error.message || 'Failed to fetch configuration data'
      setError(errorMessage)
      console.error('Configuration panel error:', error)
      
      setConfig(null)
      setSystemStatus(null)
    } finally {
      setLoading(false)
    }
  }

  const saveConfiguration = async (updatedConfig: SystemConfiguration) => {
    try {
      setSaving(true)
      const response = await fetch(`${backendUrl}/api/config/system`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ config: updatedConfig }),
      })

      if (!response.ok) {
        throw new Error('Failed to save configuration')
      }

      setConfig(updatedConfig)
      // Show success message (could be a toast notification)
      
    } catch (error: any) {
      console.error('Failed to save configuration:', error)
      setError('Failed to save configuration: ' + error.message)
    } finally {
      setSaving(false)
    }
  }

  const resetToDefaults = () => {
    if (confirm('Are you sure you want to reset all settings to defaults? This cannot be undone.')) {
      // Reset to default configuration
      const defaultConfig: SystemConfiguration = {
        trading_settings: {
          risk_level: 'moderate',
          max_position_size: 5,
          stop_loss_percent: 3,
          take_profit_percent: 8,
          max_daily_trades: 10,
          portfolio_heat: 25
        },
        ai_settings: {
          min_signal_confidence: 0.7,
          analysis_frequency: 15,
          auto_execution_enabled: false,
          learning_rate: 0.01,
          model_retrain_frequency: 168
        },
        risk_management: {
          max_drawdown_limit: 10,
          correlation_limit: 0.6,
          sector_concentration_limit: 30,
          volatility_threshold: 25
        },
        market_data: {
          primary_data_source: 'alpaca',
          backup_data_source: 'polygon',
          update_frequency: 1,
          extended_hours_trading: false
        },
        notifications: {
          email_enabled: true,
          telegram_enabled: false,
          push_notifications: true,
          trade_confirmations: true,
          daily_reports: true
        }
      }
      setConfig(defaultConfig)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'active':
      case 'connected':
      case 'online':
      case 'healthy':
        return 'text-green-400'
      case 'warning':
      case 'limited':
      case 'degraded':
        return 'text-yellow-400'
      case 'error':
      case 'offline':
      case 'failed':
        return 'text-red-400'
      default:
        return 'text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-400">Loading configuration...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-white">System Configuration</h2>
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
          >
            Retry Connection
          </button>
        </div>
        
        <div className="bg-red-900/20 border border-red-500/50 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-400 mb-2">Configuration Service Error</h3>
          <p className="text-red-300">{error}</p>
          <p className="text-gray-400 mt-2 text-sm">
            Configuration services are not yet implemented. The system is currently in development mode.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">System Configuration</h2>
        <div className="flex space-x-3">
          <button 
            onClick={fetchData} 
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
            disabled={saving}
          >
            Refresh
          </button>
          {config && (
            <>
              <button 
                onClick={() => saveConfiguration(config)} 
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition-colors"
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
              <button 
                onClick={resetToDefaults} 
                className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700 transition-colors"
                disabled={saving}
              >
                Reset to Defaults
              </button>
            </>
          )}
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex space-x-4 border-b border-gray-700">
        {[
          { key: 'trading', label: 'Trading Settings' },
          { key: 'ai', label: 'AI Configuration' },
          { key: 'risk', label: 'Risk Management' },
          { key: 'data', label: 'Data Sources' },
          { key: 'status', label: 'System Status' }
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

      {/* Trading Settings */}
      {activeSection === 'trading' && config && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Trading Parameters</h3>
            
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Risk Level</label>
                  <select 
                    value={config.trading_settings.risk_level}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, risk_level: e.target.value }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value="conservative">Conservative</option>
                    <option value="moderate">Moderate</option>
                    <option value="aggressive">Aggressive</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Max Position Size ({config.trading_settings.max_position_size}%)
                  </label>
                  <input 
                    type="range" 
                    min="1" 
                    max="25" 
                    value={config.trading_settings.max_position_size}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, max_position_size: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Stop Loss ({config.trading_settings.stop_loss_percent}%)
                  </label>
                  <input 
                    type="range" 
                    min="1" 
                    max="10" 
                    value={config.trading_settings.stop_loss_percent}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, stop_loss_percent: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Take Profit ({config.trading_settings.take_profit_percent}%)
                  </label>
                  <input 
                    type="range" 
                    min="5" 
                    max="20" 
                    value={config.trading_settings.take_profit_percent}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, take_profit_percent: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Max Daily Trades</label>
                  <input 
                    type="number" 
                    min="1" 
                    max="50" 
                    value={config.trading_settings.max_daily_trades}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, max_daily_trades: Number(e.target.value) }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Portfolio Heat ({config.trading_settings.portfolio_heat}%)
                  </label>
                  <input 
                    type="range" 
                    min="10" 
                    max="50" 
                    value={config.trading_settings.portfolio_heat}
                    onChange={(e) => setConfig({
                      ...config,
                      trading_settings: { ...config.trading_settings, portfolio_heat: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Settings */}
      {activeSection === 'ai' && config && (
        <div className="space-y-6">
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">AI Engine Configuration</h3>
            
            <div className="grid gap-6 md:grid-cols-2">
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Min Signal Confidence ({(config.ai_settings.min_signal_confidence * 100).toFixed(0)}%)
                  </label>
                  <input 
                    type="range" 
                    min="0.5" 
                    max="0.95" 
                    step="0.05"
                    value={config.ai_settings.min_signal_confidence}
                    onChange={(e) => setConfig({
                      ...config,
                      ai_settings: { ...config.ai_settings, min_signal_confidence: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Analysis Frequency (minutes)</label>
                  <select 
                    value={config.ai_settings.analysis_frequency}
                    onChange={(e) => setConfig({
                      ...config,
                      ai_settings: { ...config.ai_settings, analysis_frequency: Number(e.target.value) }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value={1}>Every 1 minute</option>
                    <option value={5}>Every 5 minutes</option>
                    <option value={15}>Every 15 minutes</option>
                    <option value={30}>Every 30 minutes</option>
                    <option value={60}>Every hour</option>
                  </select>
                </div>
                
                <div className="flex items-center space-x-2">
                  <input 
                    type="checkbox" 
                    id="autoExecute" 
                    checked={config.ai_settings.auto_execution_enabled}
                    onChange={(e) => setConfig({
                      ...config,
                      ai_settings: { ...config.ai_settings, auto_execution_enabled: e.target.checked }
                    })}
                    className="rounded"
                  />
                  <label htmlFor="autoExecute" className="text-sm text-gray-300">Enable Auto Execution</label>
                </div>
              </div>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Learning Rate ({config.ai_settings.learning_rate})
                  </label>
                  <input 
                    type="range" 
                    min="0.001" 
                    max="0.1" 
                    step="0.001"
                    value={config.ai_settings.learning_rate}
                    onChange={(e) => setConfig({
                      ...config,
                      ai_settings: { ...config.ai_settings, learning_rate: Number(e.target.value) }
                    })}
                    className="w-full"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Model Retrain Frequency (hours)</label>
                  <select 
                    value={config.ai_settings.model_retrain_frequency}
                    onChange={(e) => setConfig({
                      ...config,
                      ai_settings: { ...config.ai_settings, model_retrain_frequency: Number(e.target.value) }
                    })}
                    className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white"
                  >
                    <option value={24}>Daily</option>
                    <option value={72}>Every 3 days</option>
                    <option value={168}>Weekly</option>
                    <option value={336}>Bi-weekly</option>
                  </select>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* System Status */}
      {activeSection === 'status' && systemStatus && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Trading System Status */}
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">Trading System</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Status</span>
                  <span className={`font-medium ${getStatusColor(systemStatus.trading_system.status)}`}>
                    {systemStatus.trading_system.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Uptime</span>
                  <span className="text-white">{systemStatus.trading_system.uptime}h</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Active Positions</span>
                  <span className="text-white">{systemStatus.trading_system.active_positions}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Last Trade</span>
                  <span className="text-white">{systemStatus.trading_system.last_trade}</span>
                </div>
              </div>
            </div>

            {/* AI Engine Status */}
            <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
              <h3 className="text-lg font-semibold text-white mb-4">AI Engine</h3>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <span className="text-gray-400">Status</span>
                  <span className={`font-medium ${getStatusColor(systemStatus.ai_engine.status)}`}>
                    {systemStatus.ai_engine.status}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Model Version</span>
                  <span className="text-white">{systemStatus.ai_engine.model_version}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Last Update</span>
                  <span className="text-white">{systemStatus.ai_engine.last_update}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Accuracy</span>
                  <span className="text-green-400">{(systemStatus.ai_engine.prediction_accuracy * 100).toFixed(1)}%</span>
                </div>
              </div>
            </div>
          </div>

          {/* Data Feeds Status */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Data Feed Status</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(systemStatus.data_feeds).map(([feed, status]) => (
                <div key={feed} className="text-center p-3 bg-gray-700 rounded">
                  <div className="text-gray-300 text-sm capitalize mb-1">{feed.replace('_', ' ')}</div>
                  <div className={`font-medium ${getStatusColor(status)}`}>{status}</div>
                </div>
              ))}
            </div>
          </div>

          {/* Infrastructure Status */}
          <div className="bg-gray-800 rounded-lg p-6 border border-gray-700">
            <h3 className="text-lg font-semibold text-white mb-4">Infrastructure Status</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(systemStatus.infrastructure).map(([component, status]) => (
                <div key={component} className="text-center p-3 bg-gray-700 rounded">
                  <div className="text-gray-300 text-sm capitalize mb-1">{component.replace('_', ' ')}</div>
                  <div className={`font-medium ${getStatusColor(status)}`}>{status}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
