'use client'

import { useState, useEffect } from 'react'

export default function ClientTime() {
  const [time, setTime] = useState('')
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const updateTime = () => {
      setTime(new Date().toLocaleTimeString())
    }
    
    updateTime()
    const interval = setInterval(updateTime, 1000)
    
    return () => clearInterval(interval)
  }, [])

  if (!mounted) {
    return <span>--:--:--</span> // Server-side fallback
  }

  return <span>{time}</span>
}
