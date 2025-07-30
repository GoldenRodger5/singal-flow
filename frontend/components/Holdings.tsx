'use client'

import { useState, useEffect } from 'react'

interface Holding {
  symbol: string
  quantity: number
  current_price: number
  market_value: number
  unrealized_pnl: number
  percentage_change: number
}

export default function Holdings() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchHoldings()
    const interval = setInterval(fetchHoldings, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchHoldings = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/holdings`)
      
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`)
      }
      
      const data = await response.json()
      
      if (data.holdings && Array.isArray(data.holdings)) {
        setHoldings(data.holdings)
      } else {
        // No holdings found - this is expected if MongoDB was purged or no positions exist
        setHoldings([])
      }
    } catch (error) {
      console.error('Error fetching holdings:', error)
      // Set empty holdings on error - don't show mock data
      // This is expected behavior when API is not available or no positions exist
      setHoldings([])
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">Current Holdings</h2>
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
      <h2 className="text-xl font-bold mb-4">Current Holdings</h2>
      
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
              </tr>
            </thead>
            <tbody>
              {holdings.map((holding) => (
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
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      <div className="mt-4 text-xs text-gray-400">
        Last updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
