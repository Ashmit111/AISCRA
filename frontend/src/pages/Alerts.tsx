import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react'

export default function Alerts() {
  const queryClient = useQueryClient()

  const { data: alerts, isLoading } = useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.getAlerts(),
  })

  const acknowledgeMutation = useMutation({
    mutationFn: api.acknowledgeAlert,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['alerts'] })
    }
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading alerts...</div>
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return 'border-red-600 bg-red-50'
      case 'high': return 'border-orange-500 bg-orange-50'
      case 'medium': return 'border-yellow-500 bg-yellow-50'
      default: return 'border-blue-500 bg-blue-50'
    }
  }

  const getSeverityIcon = (severity: string) => {
    const colors = {
      critical: 'text-red-600',
      high: 'text-orange-500',
      medium: 'text-yellow-600',
      low: 'text-blue-500'
    }
    return <AlertTriangle className={`h-5 w-5 ${colors[severity as keyof typeof colors]}`} />
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Alerts</h1>
        <p className="text-muted-foreground">
          Active supply chain risk alerts requiring attention
        </p>
      </div>

      {!alerts || alerts.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <CheckCircle className="h-12 w-12 mx-auto mb-4 text-green-600" />
            <p className="text-lg font-medium">No active alerts</p>
            <p className="text-sm text-muted-foreground">Your supply chain is operating normally</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {alerts.map((alert) => (
            <Card key={alert._id} className={`border-l-4 ${getSeverityColor(alert.severity)}`}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-start gap-3">
                    {getSeverityIcon(alert.severity)}
                    <div>
                      <CardTitle className="text-lg">{alert.title}</CardTitle>
                      <div className="flex items-center gap-3 mt-2 text-sm text-muted-foreground">
                        <span className="font-medium uppercase">{alert.severity}</span>
                        <span>Score: {alert.risk_score.toFixed(1)}</span>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(alert.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>
                  {!alert.acknowledged_at && (
                    <Button
                      size="sm"
                      onClick={() => acknowledgeMutation.mutate(alert._id)}
                      disabled={acknowledgeMutation.isPending}
                    >
                      Acknowledge
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Affected Entities */}
                <div>
                  <h4 className="text-sm font-medium mb-2">Affected Suppliers</h4>
                  <div className="flex flex-wrap gap-2">
                    {alert.affected_suppliers.map((supplier) => (
                      <span key={supplier} className="px-2 py-1 bg-secondary rounded text-sm">
                        {supplier}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Materials */}
                {alert.affected_materials.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Affected Materials</h4>
                    <div className="flex flex-wrap gap-2">
                      {alert.affected_materials.map((material) => (
                        <span key={material} className="px-2 py-1 bg-secondary rounded text-sm">
                          {material}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recommendation */}
                {alert.recommendation && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Recommendation</h4>
                    <p className="text-sm text-muted-foreground">{alert.recommendation}</p>
                  </div>
                )}

                {/* Alternate Suppliers */}
                {alert.alternate_suppliers && alert.alternate_suppliers.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium mb-2">Alternate Suppliers</h4>
                    <div className="space-y-2">
                      {alert.alternate_suppliers.map((alt) => (
                        <div key={alt.supplier_id} className="flex items-center justify-between p-2 bg-background rounded border">
                          <div>
                            <span className="font-medium">{alt.name}</span>
                            <span className="text-sm text-muted-foreground ml-2">({alt.country})</span>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-medium">Score: {alt.score.toFixed(1)}/10</div>
                            {alt.lead_time_weeks && (
                              <div className="text-xs text-muted-foreground">{alt.lead_time_weeks}w lead time</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
