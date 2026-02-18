import { create } from 'zustand'
import { Alert } from '@/lib/api'

interface AlertStore {
  alerts: Alert[]
  unreadCount: number
  addAlert: (alert: Alert) => void
  setAlerts: (alerts: Alert[]) => void
  markAsRead: (alertId: string) => void
}

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],
  unreadCount: 0,
  
  addAlert: (alert: Alert) => set((state) => ({
    alerts: [alert, ...state.alerts],
    unreadCount: state.unreadCount + 1,
  })),
  
  setAlerts: (alerts: Alert[]) => set({
    alerts,
    unreadCount: alerts.filter((a) => !a.acknowledged_at).length,
  }),
  
  markAsRead: (alertId: string) => set((state) => ({
    alerts: state.alerts.map((a) => 
      a._id === alertId ? { ...a, acknowledged_at: new Date().toISOString() } : a
    ),
    unreadCount: Math.max(0, state.unreadCount - 1),
  })),
}))
