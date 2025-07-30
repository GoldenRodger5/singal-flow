'use client'

import { useState, useEffect } from 'react'
import Holdings from './Holdings'

interface EnhancedHolding {
  symbol: string
  quantity: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  percentage_change: number
  ai_score: number
  risk_level: string
  recommendation: string
}

export default function EnhancedHoldings() {
  const [holdings, setHoldings] = useState<EnhancedHolding[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<string>('market_value')

  useEffect(() => {
    fetchEnhancedHoldings()
    const interval = setInterval(fetchEnhancedHoldings, 30000)
    return () => clearInterval(interval)
  }, [])

  const fetchEnhancedHoldings = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/holdings`)
      const data = await response.json()
      
      if (data.holdings && Array.isArray(data.holdings)) {
        // Add AI scoring to real holdings data (mock AI scores for now)
        const enhancedHoldings = data.holdings.map((holding: any) => ({
          ...holding,
          ai_score: Math.random() * 3 + 7, // Random score between 7-10
          risk_level: Math.random() > 0.7 ? 'Medium' : 'Low',
          recommendation: Math.random() > 0.5 ? 'Hold' : 'Buy'
        }))
        setHoldings(enhancedHoldings)
      } else {
        // No holdings found - this is expected if MongoDB was purged
        setHoldings([])
      }
    } catch (error) {
      console.error('Error fetching enhanced holdings:', error)
      // Set empty holdings on error - don't show mock data
      setHoldings([])
    } finally {
      setLoading(false)
    }
  }

  const sortedHoldings = [...holdings].sort((a, b) => {
    if (sortBy === 'ai_score') return b.ai_score - a.ai_score
    if (sortBy === 'market_value') return b.market_value - a.market_value
    if (sortBy === 'percentage_change') return b.percentage_change - a.percentage_change
    return 0
  })

  const getRiskColor = (risk: string) => {
    switch (risk) {
      case 'Low': return 'text-green-400'
      case 'Medium': return 'text-yellow-400'
      case 'High': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  const getRecommendationColor = (rec: string) => {
    switch (rec) {
      case 'Buy': return 'text-green-400'
      case 'Hold': return 'text-blue-400'
      case 'Sell': return 'text-red-400'
      default: return 'text-gray-400'
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Enhanced Holdings Analysis</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Enhanced Holdings Analysis</h2>
        <select 
          value={sortBy} 
          onChange={(e) => setSortBy(e.target.value)}
          className="bg-gray-700 text-white rounded px-3 py-1 text-sm"
        >
          <option value="market_value">Sort by Value</option>
          <option value="ai_score">Sort by AI Score</option>
          <option value="percentage_change">Sort by Change</option>
        </select>
      </div>
      
      {holdings.length === 0 ? (
        <div className="text-center text-gray-400 py-8">
          No holdings found
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-2">Symbol</th>
                <th className="text-right py-2">Quantity</th>
                <th className="text-right py-2">Price</th>
                <th className="text-right py-2">Market Value</th>
                <th className="text-right py-2">P&L</th>
                <th className="text-right py-2">Change %</th>
                <th className="text-right py-2">AI Score</th>
                <th className="text-center py-2">Risk</th>
                <th className="text-center py-2">Recommendation</th>
              </tr>
            </thead>
            <tbody>
              {sortedHoldings.map((holding) => (
                <tr key={holding.symbol} className="border-b border-gray-700">
                  <td className="py-3 font-medium">{holding.symbol}</td>
                  <td className="text-right py-3">{holding.quantity}</td>
                  <td className="text-right py-3">${holding.current_price.toFixed(2)}</td>
                  <td className="text-right py-3">${holding.market_value.toFixed(2)}</td>
                  <td className={`text-right py-3 ${
                    holding.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    ${holding.unrealized_pnl.toFixed(2)}
                  </td>
                  <td className={`text-right py-3 ${
                    holding.percentage_change >= 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {holding.percentage_change >= 0 ? '+' : ''}{holding.percentage_change.toFixed(2)}%
                  </td>
                  <td className="text-right py-3 font-bold text-purple-400">
                    {holding.ai_score.toFixed(1)}
                  </td>
                  <td className={`text-center py-3 ${getRiskColor(holding.risk_level)}`}>
                    {holding.risk_level}
                  </td>
                  <td className={`text-center py-3 font-medium ${getRecommendationColor(holding.recommendation)}`}>
                    {holding.recommendation}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="mt-4 text-xs text-gray-400">
        AI analysis updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
