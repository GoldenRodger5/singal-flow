'use client'

import { useState, useEffect } from 'react'
import AIAnalysis from './AIAnalysis'

interface LearningMetric {
  model_accuracy: number
  prediction_success_rate: number
  total_trades_analyzed: number
  learning_iterations: number
  last_model_update: string
}

interface TrainingData {
  timestamp: string
  accuracy: number
  loss: number
}

export default function AILearningDashboard() {
  const [metrics, setMetrics] = useState<LearningMetric | null>(null)
  const [trainingData, setTrainingData] = useState<TrainingData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchLearningMetrics()
    const interval = setInterval(fetchLearningMetrics, 120000) // Update every 2 minutes
    return () => clearInterval(interval)
  }, [])

  const fetchLearningMetrics = async () => {
    try {
      // Mock learning data - replace with actual API call
      const mockMetrics = {
        model_accuracy: 87.5,
        prediction_success_rate: 72.3,
        total_trades_analyzed: 1247,
        learning_iterations: 18943,
        last_model_update: new Date(Date.now() - 30 * 60 * 1000).toISOString()
      }

      const mockTrainingData = Array.from({ length: 10 }, (_, i) => ({
        timestamp: new Date(Date.now() - (9 - i) * 60 * 60 * 1000).toISOString(),
        accuracy: 75 + Math.random() * 15,
        loss: Math.random() * 0.5
      }))

      setMetrics(mockMetrics)
      setTrainingData(mockTrainingData)
    } catch (error) {
      console.error('Error fetching learning metrics:', error)
    } finally {
      setLoading(false)
    }
  }

  const getAccuracyColor = (accuracy: number) => {
    if (accuracy >= 80) return 'text-green-400'
    if (accuracy >= 70) return 'text-yellow-400'
    return 'text-red-400'
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">AI Learning Dashboard</h2>
        <div className="animate-pulse">
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded mb-2"></div>
          <div className="h-4 bg-gray-700 rounded"></div>
        </div>
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4">AI Learning Dashboard</h2>
        <div className="text-center text-gray-400 py-8">
          Learning metrics not available
        </div>
      </div>
    )
  }

  return (
    <div className="bg-gray-800 rounded-lg p-6">
      <h2 className="text-xl font-bold mb-4">AI Learning Dashboard</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Model Accuracy</div>
          <div className={`text-2xl font-bold ${getAccuracyColor(metrics.model_accuracy)}`}>
            {metrics.model_accuracy.toFixed(1)}%
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Prediction Success</div>
          <div className={`text-2xl font-bold ${getAccuracyColor(metrics.prediction_success_rate)}`}>
            {metrics.prediction_success_rate.toFixed(1)}%
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Trades Analyzed</div>
          <div className="text-2xl font-bold text-blue-400">
            {metrics.total_trades_analyzed.toLocaleString()}
          </div>
        </div>
        
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="text-sm text-gray-300">Learning Iterations</div>
          <div className="text-2xl font-bold text-purple-400">
            {metrics.learning_iterations.toLocaleString()}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold mb-3">Recent Training Progress</h3>
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="space-y-3">
              {trainingData.slice(-5).map((data, index) => (
                <div key={index} className="flex justify-between items-center">
                  <span className="text-sm text-gray-300">
                    {new Date(data.timestamp).toLocaleTimeString()}
                  </span>
                  <div className="flex items-center space-x-4">
                    <span className={`text-sm ${getAccuracyColor(data.accuracy)}`}>
                      {data.accuracy.toFixed(1)}%
                    </span>
                    <span className="text-sm text-gray-400">
                      Loss: {data.loss.toFixed(3)}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        <div>
          <h3 className="text-lg font-semibold mb-3">Model Status</h3>
          <div className="bg-gray-700 rounded-lg p-4">
            <div className="space-y-3">
              <div className="flex justify-between">
                <span className="text-gray-300">Status</span>
                <span className="text-green-400 font-medium">Active Learning</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Last Update</span>
                <span className="text-gray-400">
                  {new Date(metrics.last_model_update).toLocaleString()}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Training Mode</span>
                <span className="text-blue-400 font-medium">Continuous</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-300">Performance Trend</span>
                <span className="text-green-400 font-medium">↗ Improving</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-6 text-xs text-gray-400">
        Learning metrics updated: {new Date().toLocaleTimeString()}
      </div>
    </div>
  )
}
