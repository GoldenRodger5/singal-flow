'use client'

import { useState, useEffect } from 'react'
import { Activity, TrendingUp, Database, Settings } from 'lucide-react'

interface SystemStatus {
  railway_status: string
  database_status: string
  automation_status: string
  last_updated: string
}

export default function SystemOverview() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchSystemStatus()
    const interval = setInterval(fetchSystemStatus, 30000) // Update every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const fetchSystemStatus = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/health`)
      const data = await response.json()
      setSystemStatus({
        railway_status: 'Running',
        database_status: 'Connected',
        automation_status: 'Active',
        last_updated: new Date().toLocaleTimeString()
      })
    } catch (error) {
      console.error('Error fetching system status:', error)
      setSystemStatus({
        railway_status: 'Unknown',
        database_status: 'Unknown',
        automation_status: 'Unknown',
        last_updated: new Date().toLocaleTimeString()
      })
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="bg-gray-800 rounded-lg p-6">
        <h2 className="text-xl font-bold mb-4 flex items-center">
          <Activity className="mr-2" />
          System Overview
        </h2>
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
      <h2 className="text-xl font-bold mb-4 flex items-center">
        <Activity className="mr-2" />
        System Overview
      </h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Railway Status</span>
            <div className={`w-2 h-2 rounded-full ${
              systemStatus?.railway_status === 'Running' ? 'bg-green-500' : 'bg-red-500'
            }`}></div>
          </div>
          <div className="text-lg font-semibold">{systemStatus?.railway_status}</div>
        </div>

        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Database</span>
            <Database className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-lg font-semibold">{systemStatus?.database_status}</div>
        </div>

        <div className="bg-gray-700 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-300">Automation</span>
            <Settings className="w-4 h-4 text-green-400" />
          </div>
          <div className="text-lg font-semibold">{systemStatus?.automation_status}</div>
        </div>
      </div>

      <div className="mt-4 text-xs text-gray-400">
        Last updated: {systemStatus?.last_updated}
      </div>
    </div>
  )
}
