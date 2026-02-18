import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import { AlertTriangle, Building2, TrendingUp, Shield } from 'lucide-react'
import SupplyChainGraph from '@/components/SupplyChainGraph'

export default function Dashboard() {
  const { data: summary, isLoading } = useQuery({
    queryKey: ['dashboard-summary'],
    queryFn: api.getDashboardSummary,
    refetchInterval: 30000, // Refresh every 30s
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-muted-foreground">Loading dashboard...</div>
      </div>
    )
  }

  const stats = summary?.summary

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Supply Chain Overview</h1>
        <p className="text-muted-foreground">
          Real-time monitoring of supply chain risks and alerts
        </p>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Alerts</CardTitle>
            <AlertTriangle className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.active_alerts || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              <span className="text-destructive font-medium">{stats?.critical_alerts || 0} critical</span>
              {' • '}
              <span className="text-orange-500 font-medium">{stats?.high_alerts || 0} high</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Suppliers</CardTitle>
            <Building2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total_suppliers || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              <span className="text-green-600 font-medium">{stats?.active_suppliers || 0} active</span>
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">At-Risk Suppliers</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.at_risk_suppliers || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Risk score ≥ 3.0
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Risk Level</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats && stats.critical_alerts > 0 ? 'Critical' :
               stats && stats.high_alerts > 0 ? 'High' :
               stats && stats.medium_alerts > 0 ? 'Medium' : 'Low'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Overall supply chain status
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Supply Chain Graph */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Supply Chain Network</CardTitle>
          <CardDescription>
            Interactive visualization of supplier relationships and risk levels
          </CardDescription>
        </CardHeader>
        <CardContent>
          <SupplyChainGraph />
        </CardContent>
      </Card>

      {/* Recent Alerts */}
      <Card className="col-span-4">
        <CardHeader>
          <CardTitle>Recent Alerts</CardTitle>
          <CardDescription>Latest supply chain risk alerts</CardDescription>
        </CardHeader>
        <CardContent>
          <RecentAlerts />
        </CardContent>
      </Card>
    </div>
  )
}

function RecentAlerts() {
  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts({ limit: 5 }),
  })

  if (!alerts || alerts.length === 0) {
    return (
      <div className="text-center text-muted-foreground py-8">
        No recent alerts
      </div>
    )
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'text-red-600'
      case 'high': return 'text-orange-500'
      case 'medium': return 'text-yellow-600'
      default: return 'text-blue-500'
    }
  }

  return (
    <div className="space-y-4">
      {alerts.map((alert) => (
        <div key={alert._id} className="flex items-start justify-between border-b pb-4 last:border-0">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className={`text-sm font-medium uppercase ${getSeverityColor(alert.severity)}`}>
                {alert.severity}
              </span>
              <span className="text-xs text-muted-foreground">
                Score: {alert.risk_score.toFixed(1)}
              </span>
            </div>
            <h4 className="font-medium mt-1">{alert.title}</h4>
            <p className="text-sm text-muted-foreground mt-1">
              Affected: {alert.affected_suppliers.join(', ')}
            </p>
          </div>
          <span className="text-xs text-muted-foreground">
            {new Date(alert.created_at).toLocaleDateString()}
          </span>
        </div>
      ))}
    </div>
  )
}
