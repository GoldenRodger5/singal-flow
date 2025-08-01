'use client'

import { useState, useEffect } from 'react'
import SystemOverview from '../components/SystemOverview'
import TradingDashboard from '../components/TradingDashboard'
import AIAnalysisDashboard from '../components/AIAnalysisDashboard'
import ControlPanel from '../components/ControlPanel'
import ConfigurationPanel from '../components/ConfigurationPanel'
import ClientTime from '../components/ClientTime'
import { useBackendStatus } from '../hooks/useBackendStatus'

type DashboardView = 'overview' | 'trading' | 'ai-analysis' | 'control' | 'config'

export default function Home() {
  const [activeView, setActiveView] = useState<DashboardView>('overview')
  const { isConnected: backendConnected } = useBackendStatus()
  const [marketStatus, setMarketStatus] = useState<'open' | 'closed' | 'unknown'>('unknown')

  // Check market hours (basic implementation)
  useEffect(() => {
    const checkMarketHours = () => {
      const now = new Date()
      const day = now.getDay() // 0 = Sunday, 6 = Saturday
      const hour = now.getHours()
      const minutes = now.getMinutes()
      const currentTime = hour * 60 + minutes
      
      // Market hours: Monday (1) to Friday (5), 9:30 AM to 4:00 PM ET
      if (day >= 1 && day <= 5 && currentTime >= 570 && currentTime <= 960) {
        setMarketStatus('open')
      } else {
        setMarketStatus('closed')
      }
    }
    
    checkMarketHours()
    const interval = setInterval(checkMarketHours, 60000) // Check every minute
    return () => clearInterval(interval)
  }, [])

  const renderOverviewTab = () => (
    <div className="space-y-6">
      <SystemOverview />
    </div>
  )

  const renderTradingTab = () => (
    <div className="space-y-6">
      <TradingDashboard />
    </div>
  )

  const renderAIAnalysisTab = () => (
    <div className="space-y-6">
      <AIAnalysisDashboard />
    </div>
  )

  const renderControlTab = () => (
    <div className="space-y-6">
      <ControlPanel />
    </div>
  )

  const renderConfigTab = () => (
    <div className="space-y-6">
      <ConfigurationPanel />
    </div>
  )

  const renderContent = () => {
    switch (activeView) {
      case 'overview':
        return renderOverviewTab()
      case 'trading':
        return renderTradingTab()
      case 'ai-analysis':
        return renderAIAnalysisTab()
      case 'control':
        return renderControlTab()
      case 'config':
        return renderConfigTab()
      default:
        return renderOverviewTab()
    }
  }

  return (
    <main className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-white">Signal Flow</h1>
              <span className="ml-3 px-2 py-1 bg-green-600 text-xs rounded-full">
                Live
              </span>
              <span className={`ml-2 px-2 py-1 text-xs rounded-full ${
                marketStatus === 'open' 
                  ? 'bg-green-600 text-white' 
                  : marketStatus === 'closed'
                  ? 'bg-red-600 text-white'
                  : 'bg-gray-600 text-white'
              }`}>
                Market {marketStatus === 'open' ? 'Open' : marketStatus === 'closed' ? 'Closed' : 'Unknown'}
              </span>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
                <span className={`text-sm ${backendConnected ? 'text-green-400' : 'text-red-400'}`}>
                  {backendConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { key: 'overview', label: 'System Overview' },
              { key: 'trading', label: 'Trading Dashboard' },
              { key: 'ai-analysis', label: 'AI Analysis' },
              { key: 'control', label: 'Control Panel' },
              { key: 'config', label: 'Configuration' }
            ].map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveView(tab.key as DashboardView)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeView === tab.key
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-gray-300 hover:text-white hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderContent()}
      </div>

      {/* Footer */}
      <footer className="bg-gray-800 border-t border-gray-700 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="flex justify-between items-center">
            <p className="text-gray-400 text-sm">
              Signal Flow AI Trading System © 2025
            </p>
            <div className="flex items-center space-x-4 text-sm text-gray-400">
              <span className="flex items-center">
                Backend: 
                <span className={`ml-1 ${backendConnected ? 'text-green-400' : 'text-red-400'}`}>
                  {backendConnected ? 'Connected' : 'Disconnected'}
                </span>
                <div className={`w-2 h-2 rounded-full ml-2 ${backendConnected ? 'bg-green-500' : 'bg-red-500'}`}></div>
              </span>
              <span>•</span>
              <span>Last Update: <ClientTime /></span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  )
}
