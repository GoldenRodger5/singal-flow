import { useState, useEffect } from 'react'

export const useBackendConnection = () => {
  const [isConnected, setIsConnected] = useState(false)
  const [lastChecked, setLastChecked] = useState<Date | null>(null)

  useEffect(() => {
    const checkConnection = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 5000)
        
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/health`, {
          method: 'GET',
          signal: controller.signal
        })
        
        clearTimeout(timeoutId)
        setIsConnected(response.ok)
        setLastChecked(new Date())
      } catch (error) {
        setIsConnected(false)
        setLastChecked(new Date())
      }
    }

    checkConnection()
    const interval = setInterval(checkConnection, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  return { isConnected, lastChecked }
}
