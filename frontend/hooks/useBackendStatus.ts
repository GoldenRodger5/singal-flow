import { useState, useEffect } from 'react'

export function useBackendStatus() {
  const [isConnected, setIsConnected] = useState(false)
  const [lastCheck, setLastCheck] = useState<Date | null>(null)

  useEffect(() => {
    const checkBackendStatus = async () => {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), 5000)
        
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL || 'https://web-production-3e19d.up.railway.app'}/health`, {
          method: 'GET',
          signal: controller.signal,
        })
        
        clearTimeout(timeoutId)
        
        if (response.ok) {
          setIsConnected(true)
        } else {
          setIsConnected(false)
        }
      } catch (error) {
        console.error('Backend health check failed:', error)
        setIsConnected(false)
      } finally {
        setLastCheck(new Date())
      }
    }

    // Check immediately
    checkBackendStatus()

    // Check every 30 seconds
    const interval = setInterval(checkBackendStatus, 30000)

    return () => clearInterval(interval)
  }, [])

  return { isConnected, lastCheck }
}
