'use client'

import { useState, useEffect } from 'react'

interface AIAnalysis {
  market_sentiment: string
  sentiment_score: number
  key_insights: string[]
  recommendations: string[]
  risk_assessment: string
  confidence_level: number
}

export default function AIAnalysis() {
  const [analysis, setAnalysis] = useState<AIAnalysis | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchAIAnalysis()
    const interval = setInterval(fetchAIAnalysis, 300000) // Update every 5 minutes
    return () => clearInterval(interval)
  }, [])

  const fetchAIAnalysis = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/api/ai/analysis`)
      
      if (!response.ok) {
        throw new Error(`AI Analysis API returned ${response.status}`)
      }
      
      const data = await response.json()
      setAnalysis(data)
    } catch (error) {
      console.error('Error fetching AI analysis:', error)
      // Set fallback analysis on error
      setAnalysis({
        market_sentiment: 'Unknown',
        sentiment_score: 0,
        key_insights: ['AI analysis temporarily unavailable'],
        recommendations: ['Check connection and try again'],
        risk_assessment: 'Unknown',
        confidence_level: 0
      })
    } finally {
      setLoading(false)
    }
  }

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'bullish': return 'text-green-400'
      case 'bearish': return 'text-red-400'
      case 'neutral': return 'text-yellow-400'
      default: return 'text-gray-400'
    }
  }

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 8) return 'text-green-400'
    if (confidence >= 6) return 'text-yellow-400'
    return 'text-red-400'
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">AI Market Analysis</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (!analysis) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">AI Market Analysis</h2>
        <div className="text-center text-gray-400 py-8">
          Analysis not available
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">AI Market Analysis</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Market Sentiment</div>
          <div className={`text-xl font-bold ${getSentimentColor(analysis.market_sentiment)}`}>
            {analysis.market_sentiment}
          </div>
          <div className="text-sm text-gray-400">
            Score: {analysis.sentiment_score.toFixed(1)}/10
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Risk Assessment</div>
          <div className="text-xl font-bold">{analysis.risk_assessment}</div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Confidence Level</div>
          <div className={`text-xl font-bold ${getConfidenceColor(analysis.confidence_level)}`}>
            {analysis.confidence_level.toFixed(1)}/10
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-3">Key Insights</h3>
          <ul className="space-y-2">
            {analysis.key_insights.map((insight, index) => (
              <li key={index} className="flex items-start">
                <div className="w-2 h-2 bg-blue-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span className="text-sm text-gray-300">{insight}</span>
              </li>
            ))}
          </ul>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold mb-3">AI Recommendations</h3>
          <ul className="space-y-2">
            {analysis.recommendations.map((recommendation, index) => (
              <li key={index} className="flex items-start">
                <div className="w-2 h-2 bg-green-400 rounded-full mt-2 mr-3 flex-shrink-0"></div>
                <span className="text-sm text-gray-300">{recommendation}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
      
      <div className="mt-6 text-xs text-gray-400">
        Analysis generated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
