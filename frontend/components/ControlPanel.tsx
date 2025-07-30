'use client'

import { useState } from 'react'

interface ControlAction {
  id: string
  label: string
  action: string
  description: string
  type: 'button' | 'toggle'
  status?: boolean
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

  const handleAction = async (action: ControlAction) => {
    setLoading(action.id)
    
    try {
      // Mock API call - replace with actual API endpoint
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      if (action.type === 'toggle') {
        setActions(prev => prev.map(a => 
          a.id === action.id 
            ? { ...a, status: !a.status }
            : a
        ))
      }
      
      console.log(`Executed action: ${action.action}`)
    } catch (error) {
      console.error('Error executing action:', error)
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Control Panel</h2>
      
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
            <span className="text-green-400">Active</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">AI Analysis:</span>
            <span className="text-green-400">Running</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">Risk Management:</span>
            <span className="text-green-400">Enabled</span>
          </div>
          <div className="flex justify-between">
            <span className="text-gray-300">Data Feed:</span>
            <span className="text-green-400">Connected</span>
          </div>
        </div>
      </div>
    </div>
  )
}
