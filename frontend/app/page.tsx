'use client'

import { useState } from 'react'
import SystemOverview from '@/components/SystemOverview'
import TradingPerformance from '@/components/TradingPerformance'
import Holdings from '@/components/Holdings'
import EnhancedHoldings from '@/components/EnhancedHoldings'
import AIAnalysis from '@/components/AIAnalysis'
import AILearningDashboard from '@/components/AILearningDashboard'
import RealtimeCharts from '@/components/RealtimeCharts'
import ControlPanel from '@/components/ControlPanel'
import EnhancedControlPanel from '@/components/EnhancedControlPanel'

type DashboardView = 'overview' | 'trading' | 'ai' | 'control'

export default function Home() {
  const [activeView, setActiveView] = useState<DashboardView>('overview')
  const [enhancedMode, setEnhancedMode] = useState(false)

  const renderOverviewTab = () => (
    <div className="space-y-6">
      <SystemOverview />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <TradingPerformance />
        <RealtimeCharts />
      </div>
      {enhancedMode ? <EnhancedHoldings /> : <Holdings />}
    </div>
  )

  const renderTradingTab = () => (
    <div className="space-y-6">
      <TradingPerformance />
      <RealtimeCharts />
      {enhancedMode ? <EnhancedHoldings /> : <Holdings />}
    </div>
  )

  const renderAITab = () => (
    <div className="space-y-6">
      <AIAnalysis />
      <AILearningDashboard />
    </div>
  )

  const renderControlTab = () => (
    <div className="space-y-6">
      {enhancedMode ? <EnhancedControlPanel /> : <ControlPanel />}
    </div>
  )

  const renderContent = () => {
    switch (activeView) {
      case 'overview':
        return renderOverviewTab()
      case 'trading':
        return renderTradingTab()
      case 'ai':
        return renderAITab()
      case 'control':
        return renderControlTab()
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
            </div>
            
            <div className="flex items-center space-x-4">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={enhancedMode}
                  onChange={(e) => setEnhancedMode(e.target.checked)}
                  className="sr-only"
                />
                <div className={`w-11 h-6 rounded-full transition-colors ${
                  enhancedMode ? 'bg-blue-600' : 'bg-gray-600'
                } relative`}>
                  <div className={`w-5 h-5 bg-white rounded-full absolute top-0.5 transition-transform ${
                    enhancedMode ? 'translate-x-5' : 'translate-x-0.5'
                  }`}></div>
                </div>
                <span className="ml-2 text-sm">Enhanced Mode</span>
              </label>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation */}
      <nav className="bg-gray-800 border-b border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { key: 'overview', label: 'Overview' },
              { key: 'trading', label: 'Trading' },
              { key: 'ai', label: 'AI Analysis' },
              { key: 'control', label: 'Control Panel' }
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
              <span>Backend: Connected</span>
              <span>•</span>
              <span>Last Update: {new Date().toLocaleTimeString()}</span>
            </div>
          </div>
        </div>
      </footer>
    </main>
  )
}
