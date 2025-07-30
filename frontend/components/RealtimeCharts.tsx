'use client'

import { useState, useEffect } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

interface RealtimeData {
  timestamp: string
  price: number
  volume: number
}

interface ChartProps {
  symbol?: string
}

export default function RealtimeCharts({ symbol = 'AAPL' }: ChartProps) {
  const [chartData, setChartData] = useState<RealtimeData[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedSymbol, setSelectedSymbol] = useState(symbol)

  const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']

  useEffect(() => {
    fetchRealtimeData()
    const interval = setInterval(fetchRealtimeData, 10000) // Update every 10 seconds
    return () => clearInterval(interval)
  }, [selectedSymbol])

  const fetchRealtimeData = async () => {
    try {
      // Get real market data from the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/market/realtime/${selectedSymbol}`)
      
      if (!response.ok) {
        throw new Error(`Market data API returned ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.chart_data && Array.isArray(data.chart_data)) {
        setChartData(data.chart_data)
      } else {
        throw new Error('Invalid market data format')
      }
    } catch (error) {
      console.error('Error fetching realtime data:', error)
      // Fallback to basic structure on error
      const fetchRealtimeData = async () => {
    try {
      // Get real market data from the backend
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/market/realtime/${selectedSymbol}`)
      
      if (!response.ok) {
        throw new Error(`Market API returned ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.chart_data && Array.isArray(data.chart_data)) {
        setChartData(data.chart_data)
      } else {
        throw new Error('Invalid market data format')
      }
    } catch (error) {
      console.error('Error fetching realtime data:', error)
      // Fallback to basic chart structure on error
      const basePrice = {
        'AAPL': 195.50,
        'GOOGL': 142.80,
        'MSFT': 415.30,
        'TSLA': 248.90,
        'AMZN': 145.20
      }[selectedSymbol] || 195.50

      const fallbackData = Array.from({ length: 50 }, (_, i) => ({
        timestamp: new Date(Date.now() - (49 - i) * 60 * 1000).toISOString(),
        price: basePrice,
        volume: 500000
      }))

      setChartData(fallbackData)
    } finally {
      setLoading(false)
    }
  }
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Realtime Charts</h2>
        <div className="animate-pulse">
          <div className="h-64 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  const currentPrice = chartData[chartData.length - 1]?.price || 0
  const previousPrice = chartData[chartData.length - 2]?.price || 0
  const priceChange = currentPrice - previousPrice
  const percentChange = (priceChange / previousPrice) * 100

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Realtime Charts</h2>
        <select 
          value={selectedSymbol} 
          onChange={(e) => setSelectedSymbol(e.target.value)}
          className="bg-gray-700 text-white rounded px-3 py-1 text-sm"
        >
          {symbols.map(sym => (
            <option key={sym} value={sym}>{sym}</option>
          ))}
        </select>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Current Price</div>
          <div className="text-2xl font-bold">
            ${currentPrice.toFixed(2)}
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Change</div>
          <div className={`text-2xl font-bold ${
            priceChange >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {priceChange >= 0 ? '+' : ''}${priceChange.toFixed(2)}
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Change %</div>
          <div className={`text-2xl font-bold ${
            percentChange >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {percentChange >= 0 ? '+' : ''}{percentChange.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="h-64 mb-4">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis 
              dataKey="timestamp" 
              stroke="#9CA3AF"
              tickFormatter={(value) => new Date(value).toLocaleTimeString()}
            />
            <YAxis 
              stroke="#9CA3AF"
              domain={['dataMin - 2', 'dataMax + 2']}
            />
            <Tooltip 
              contentStyle={{ 
                backgroundColor: '#374151', 
                border: 'none', 
                borderRadius: '8px',
                color: '#F9FAFB'
              }}
              labelFormatter={(value) => new Date(value).toLocaleString()}
              formatter={(value: number) => [`$${value.toFixed(2)}`, 'Price']}
            />
            <Line 
              type="monotone" 
              dataKey="price" 
              stroke="#3B82F6" 
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="text-xs text-gray-400">
        Live data • Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
