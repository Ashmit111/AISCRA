import { useEffect, useCallback } from 'react'
import { useAlertStore } from '@/stores/alertStore'
import { Alert } from '@/lib/api'

const WS_URL = (import.meta.env.VITE_WS_URL as string) || 'ws://localhost:8000/ws/alerts'

export const useWebSocket = () => {
  const addAlert = useAlertStore((state) => state.addAlert)

  const connect = useCallback(() => {
    const ws = new WebSocket(WS_URL)

    ws.onopen = () => {
      console.log('WebSocket connected')
    }

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        if (data.type === 'alert') {
          addAlert(data.alert as Alert)
          
          // Show browser notification if permission granted
          if ('Notification' in window && Notification.permission === 'granted') {
            new Notification('New Supply Chain Alert', {
              body: data.alert.title,
              icon: '/vite.svg',
            })
          }
        }
      } catch (error) {
        console.error('WebSocket message error:', error)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected, reconnecting in 5s...')
      setTimeout(connect, 5000)
    }

    return ws
  }, [addAlert])

  useEffect(() => {
    const ws = connect()

    // Request notification permission
    if ('Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission()
    }

    return () => {
      ws.close()
    }
  }, [connect])
}
