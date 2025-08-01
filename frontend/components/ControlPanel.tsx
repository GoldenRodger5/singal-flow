'use client'

import { useState, useEffect } from 'react'

interface ControlAction {
  id: string
  label: string
  action: string
  description: string
  type: 'button' | 'toggle'
  status?: boolean
}

interface SystemStatus {
  trading_engine: boolean
  ai_analysis: boolean
  risk_management: boolean
  data_feed: boolean
}

export default function ControlPanel() {
  const [actions, setActions] = useState<ControlAction[]>([
    {
      id: 'auto_trading',
      label: 'Auto Trading',
      action: 'toggle_auto_trading',
      description: 'Enable/disable automated trading',
      type: 'toggle',
      status: true
    },
    {
      id: 'paper_trading',
      label: 'Paper Trading',
      action: 'toggle_paper_trading',
      description: 'Switch between paper and live trading',
      type: 'toggle',
      status: true
    },
    {
      id: 'stop_all',
      label: 'Emergency Stop',
      action: 'emergency_stop',
      description: 'Immediately stop all trading activities',
      type: 'button'
    },
    {
      id: 'sync_data',
      label: 'Sync Data',
      action: 'sync_data',
      description: 'Synchronize data with trading platform',
      type: 'button'
    }
  ])

  const [loading, setLoading] = useState<string | null>(null)
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    trading_engine: false,
    ai_analysis: false,
    risk_management: false,
    data_feed: false
  })
  const [lastMessage, setLastMessage] = useState<string>('')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'

  // Fetch current system status
  const fetchStatus = async () => {
    try {
      const response = await fetch(`${backendUrl}/api/control/status`)
      if (response.ok) {
        const data = await response.json()
        setSystemStatus(data.system_health || systemStatus)
        
        // Update toggle states from backend
        if (data.control_state) {
          setActions(prev => prev.map(action => {
            if (action.id === 'auto_trading') {
              return { ...action, status: data.control_state.auto_trading }
            }
            if (action.id === 'paper_trading') {
              return { ...action, status: data.control_state.paper_trading }
            }
            return action
          }))
        }
      }
    } catch (error) {
      console.error('Failed to fetch system status:', error)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 10000) // Update every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const handleAction = async (action: ControlAction) => {
    setLoading(action.id)
    setLastMessage('')
    
    try {
      // Call actual backend API endpoint
      const response = await fetch(`${backendUrl}/api/control/${action.action}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action: action.action })
      })
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `Action failed: ${response.statusText}`)
      }
      
      const result = await response.json()
      setLastMessage(result.message || 'Action completed successfully')
      
      if (action.type === 'toggle') {
        setActions(prev => prev.map(a => 
          a.id === action.id 
            ? { ...a, status: result.new_status ?? !a.status }
            : a
        ))
      }
      
      // Refresh system status after action
      setTimeout(fetchStatus, 1000)
      
      console.log(`Executed action: ${action.action}`, result)
    } catch (error) {
      console.error('Error executing action:', error)
      setLastMessage(`Failed to execute ${action.label}: ${error}`)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Control Panel</h2>
      
      {/* Status Messages */}
      {lastMessage && (
        <div className={`mb-4 p-3 rounded-lg ${
          lastMessage.includes('Failed') || lastMessage.includes('error') 
            ? 'bg-red-900/20 border border-red-500/50 text-red-300' 
            : 'bg-green-900/20 border border-green-500/50 text-green-300'
        }`}>
          {lastMessage}
        </div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {actions.map((action) => (
          <div key={action.id} className="bg-gray-700 rounded-lg p-4">
            <div className="flex justify-between items-center mb-2">
              <h3 className="font-semibold">{action.label}</h3>
              {action.type === 'toggle' && (
                <div className={`w-12 h-6 rounded-full transition-colors ${
                  action.status ? 'bg-green-500' : 'bg-gray-500'
                } relative cursor-pointer`}
                onClick={() => handleAction(action)}>
                  <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform ${
                    action.status ? 'translate-x-6' : 'translate-x-0.5'
                  }`}></div>
                </div>
              )}
            </div>
            
            <p className="text-sm text-gray-300 mb-3">{action.description}</p>
            
            {action.type === 'button' && (
              <button
                onClick={() => handleAction(action)}
                disabled={loading === action.id}
                className={`w-full py-2 px-4 rounded transition-colors ${
                  action.id === 'stop_all' 
                    ? 'bg-red-600 hover:bg-red-700 disabled:bg-red-800' 
                    : 'bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800'
                } disabled:opacity-50`}
              >
                {loading === action.id ? 'Processing...' : action.label}
              </button>
            )}
            
            {action.type === 'toggle' && (
              <div className="text-sm">
                Status: <span className={action.status ? 'text-green-400' : 'text-red-400'}>
                  {action.status ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            )}
          </div>
        ))}
      </div>
      
      <div className="mt-6 bg-gray-700 rounded-lg p-4">
        <h3 className="font-semibold mb-2">System Status</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex justify-between">
            <span className="text-gray-300">Trading Engine:</span>
            <span className={systemStatus.trading_engine ? 'text-green-400' : 'text-red-400'}>
              {systemStatus.trading_engine ? 'Active' : 'Inactive'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">AI Analysis:</span>
            <span className={systemStatus.ai_analysis ? 'text-green-400' : 'text-yellow-400'}>
              {systemStatus.ai_analysis ? 'Running' : 'Limited'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">Risk Management:</span>
            <span className={systemStatus.risk_management ? 'text-green-400' : 'text-red-400'}>
              {systemStatus.risk_management ? 'Enabled' : 'Disabled'}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">Data Feed:</span>
            <span className={systemStatus.data_feed ? 'text-green-400' : 'text-red-400'}>
              {systemStatus.data_feed ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
        
        <div className="mt-3 text-xs text-gray-400">
          Last updated: {new Date().toLocaleTimeString()}
        </div>
      </div>
    </div>
  )
}
