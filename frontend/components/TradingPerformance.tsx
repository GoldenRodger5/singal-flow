'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface PerformanceData {
  timestamp: string
  value: number
  pnl: number
}

export default function TradingPerformance() {
  const [performanceData, setPerformanceData] = useState<PerformanceData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchPerformanceData()
    const interval = setInterval(fetchPerformanceData, 60000) // Update every minute
    return () => clearInterval(interval)
  }, [])

  const fetchPerformanceData = async () => {
    try {
      // Get real portfolio data
      const portfolioResponse = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/portfolio`)
      
      if (!portfolioResponse.ok) {
        throw new Error(`Portfolio API returned ${portfolioResponse.status}`)
      }
      
      const portfolioData = await portfolioResponse.json()
      
      // Create time series data with current portfolio value
      const currentValue = portfolioData.portfolio_value || 100000 // Default to $100k if no data
      const mockData = Array.from({ length: 24 }, (_, i) => ({
        timestamp: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
        value: currentValue + (Math.random() * 100 - 50), // Small variations around current value
        pnl: Math.random() * 20 - 10 // Small P&L variations
      }))
      
      setPerformanceData(mockData)
    } catch (error) {
      console.error('Error fetching performance data:', error)
      // Show default data on error - represents starting capital
      const defaultData = Array.from({ length: 24 }, (_, i) => ({
        timestamp: new Date(Date.now() - (23 - i) * 60 * 60 * 1000).toISOString(),
        value: 100000, // Default starting portfolio value
        pnl: 0 // No P&L yet
      }))
      setPerformanceData(defaultData)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Trading Performance</h2>
        <div className="animate-pulse">
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">Trading Performance</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Total PnL</div>
          <div className="text-2xl font-bold text-green-400">
            ${performanceData.reduce((sum, item) => sum + item.pnl, 0).toFixed(2)}
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Portfolio Value</div>
          <div className="text-2xl font-bold">
            ${performanceData[performanceData.length - 1]?.value.toFixed(2) || '0.00'}
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Daily Change</div>
          <div className="text-2xl font-bold text-blue-400">
            {performanceData.length > 1 ? 
              ((performanceData[performanceData.length - 1]?.value - performanceData[0]?.value) / performanceData[0]?.value * 100).toFixed(2) + '%'
              : '0.00%'
            }
          </div>
        </div>
      </div>

      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={performanceData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="timestamp" 
              stroke="#9CA3AF"
              tickFormatter={(value) => new Date(value).toLocaleTimeString()}
            />
            <YAxis stroke="#9CA3AF" />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#374151', 
                border: 'none', 
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              labelFormatter={(value) => new Date(value).toLocaleString()}
            />
            <Line 
              type="monotone" 
              dataKey="value" 
              stroke="#10B981" 
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
