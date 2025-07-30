'use client'

import { useState, useEffect } from 'react'
import ControlPanel from './ControlPanel'

interface EnhancedControl {
  id: string
  category: string
  label: string
  action: string
  description: string
  type: 'button' | 'toggle' | 'slider' | 'select'
  status?: boolean
  value?: number
  options?: string[]
  min?: number
  max?: number
}

export default function EnhancedControlPanel() {
  const [controls, setControls] = useState<EnhancedControl[]>([
    {
      id: 'auto_trading',
      category: 'Trading',
      label: 'Auto Trading',
      action: 'toggle_auto_trading',
      description: 'Enable/disable automated trading',
      type: 'toggle',
      status: true
    },
    {
      id: 'risk_level',
      category: 'Risk Management',
      label: 'Risk Level',
      action: 'set_risk_level',
      description: 'Adjust overall risk tolerance (1-10)',
      type: 'slider',
      value: 5,
      min: 1,
      max: 10
    },
    {
      id: 'position_size',
      category: 'Trading',
      label: 'Max Position Size',
      action: 'set_position_size',
      description: 'Maximum position size as % of portfolio',
      type: 'slider',
      value: 25,
      min: 5,
      max: 50
    },
    {
      id: 'trading_strategy',
      category: 'Strategy',
      label: 'Trading Strategy',
      action: 'set_strategy',
      description: 'Select active trading strategy',
      type: 'select',
      options: ['Momentum', 'Mean Reversion', 'Trend Following', 'AI Adaptive']
    },
    {
      id: 'ai_learning',
      category: 'AI',
      label: 'AI Learning',
      action: 'toggle_ai_learning',
      description: 'Enable continuous AI model learning',
      type: 'toggle',
      status: true
    },
    {
      id: 'notification_level',
      category: 'Notifications',
      label: 'Alert Level',
      action: 'set_alert_level',
      description: 'Notification threshold sensitivity',
      type: 'select',
      options: ['Low', 'Medium', 'High', 'Critical Only']
    }
  ])

  const [loading, setLoading] = useState<string | null>(null)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  const handleControlChange = async (control: EnhancedControl, newValue?: any) => {
    setLoading(control.id)
    
    try {
      // Mock API call - replace with actual API endpoint
      await new Promise(resolve => setTimeout(resolve, 1000))
      
      setControls(prev => prev.map(c => {
        if (c.id === control.id) {
          if (control.type === 'toggle') {
            return { ...c, status: !c.status }
          } else if (control.type === 'slider') {
            return { ...c, value: newValue }
          } else if (control.type === 'select') {
            return { ...c, value: newValue }
          }
        }
        return c
      }))
      
      setLastUpdate(new Date())
      console.log(`Updated control: ${control.action}`, newValue)
    } catch (error) {
      console.error('Error updating control:', error)
    } finally {
      setLoading(null)
    }
  }

  const categories = Array.from(new Set(controls.map(c => c.category)))

  const renderControl = (control: EnhancedControl) => {
    switch (control.type) {
      case 'toggle':
        return (
          <div className={`w-12 h-6 rounded-full transition-colors ${
            control.status ? 'bg-green-500' : 'bg-gray-500'
          } relative cursor-pointer`}
          onClick={() => handleControlChange(control)}>
            <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform ${
              control.status ? 'translate-x-6' : 'translate-x-0.5'
            }`}></div>
          </div>
        )

      case 'slider':
        return (
          <div className="w-full">
            <input
              type="range"
              min={control.min}
              max={control.max}
              value={control.value}
              onChange={(e) => handleControlChange(control, parseInt(e.target.value))}
              className="w-full h-2 bg-gray-600 rounded-lg appearance-none cursor-pointer slider"
              disabled={loading === control.id}
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>{control.min}</span>
              <span className="font-semibold text-blue-400">{control.value}</span>
              <span>{control.max}</span>
            </div>
          </div>
        )

      case 'select':
        return (
          <select 
            onChange={(e) => handleControlChange(control, e.target.value)}
            disabled={loading === control.id}
            className="w-full bg-gray-600 text-white rounded px-3 py-2 text-sm"
          >
            {control.options?.map(option => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
        )

      case 'button':
        return (
          <button
            onClick={() => handleControlChange(control)}
            disabled={loading === control.id}
            className="w-full py-2 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-800 rounded transition-colors disabled:opacity-50"
          >
            {loading === control.id ? 'Processing...' : control.label}
          </button>
        )

      default:
        return null
    }
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-xl font-bold">Enhanced Control Panel</h2>
        <div className="text-xs text-gray-400">
          Last updated: {lastUpdate.toLocaleTimeString()}
        </div>
      </div>
      
      {categories.map(category => (
        <div key={category} className="mb-6">
          <h3 className="text-lg font-semibold mb-3 text-blue-400">{category}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {controls
              .filter(control => control.category === category)
              .map((control) => (
                <div key={control.id} className="bg-gray-700 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div className="flex-1">
                      <h4 className="font-semibold">{control.label}</h4>
                      <p className="text-sm text-gray-300 mt-1">{control.description}</p>
                    </div>
                    {control.type === 'toggle' && (
                      <div className="ml-4 flex-shrink-0">
                        {renderControl(control)}
                      </div>
                    )}
                  </div>
                  
                  {control.type !== 'toggle' && (
                    <div className="mt-3">
                      {renderControl(control)}
                    </div>
                  )}
                  
                  {control.type === 'toggle' && (
                    <div className="text-sm mt-2">
                      Status: <span className={control.status ? 'text-green-400' : 'text-red-400'}>
                        {control.status ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  )}
                  
                  {loading === control.id && (
                    <div className="text-sm text-blue-400 mt-2">Updating...</div>
                  )}
                </div>
              ))}
          </div>
        </div>
      ))}
      
      <div className="mt-6 bg-gray-700 rounded-lg p-4">
        <h3 className="font-semibold mb-3">Quick Actions</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          <button className="py-2 px-3 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors">
            Emergency Stop
          </button>
          <button className="py-2 px-3 bg-blue-600 hover:bg-blue-700 rounded text-sm transition-colors">
            Sync Data
          </button>
          <button className="py-2 px-3 bg-green-600 hover:bg-green-700 rounded text-sm transition-colors">
            Backup Settings
          </button>
          <button className="py-2 px-3 bg-yellow-600 hover:bg-yellow-700 rounded text-sm transition-colors">
            Reset to Default
          </button>
        </div>
      </div>
    </div>
  )
}
