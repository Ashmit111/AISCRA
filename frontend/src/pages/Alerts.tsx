import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { AlertTriangle, CheckCircle, Clock, ShieldAlert, Building2, Package } from 'lucide-react'

const SEVERITY_CONFIG = {
  critical: { bg: 'bg-red-600',    border: 'border-l-red-600',   badge: 'bg-red-600 text-white',         soft: 'bg-red-50',     icon: 'text-red-600' },
  high:     { bg: 'bg-orange-500', border: 'border-l-orange-500', badge: 'bg-orange-500 text-white',      soft: 'bg-orange-50',  icon: 'text-orange-500' },
  medium:   { bg: 'bg-yellow-500', border: 'border-l-yellow-500', badge: 'bg-yellow-500 text-white',      soft: 'bg-yellow-50',  icon: 'text-yellow-500' },
  low:      { bg: 'bg-blue-500',   border: 'border-l-blue-500',   badge: 'bg-blue-500 text-white',        soft: 'bg-blue-50',    icon: 'text-blue-500' },
}

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

  const counts = { critical: 0, high: 0, medium: 0, low: 0 }
  ;(alerts || []).forEach(a => {
    const s = a.severity as keyof typeof counts
    if (s in counts) counts[s]++
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Alerts</h1>
          <p className="text-muted-foreground">Active supply chain risk alerts requiring attention</p>
        </div>
        <div className="flex items-center gap-2 text-sm">
          <ShieldAlert className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">{(alerts || []).length} total</span>
        </div>
      </div>

      {/* Severity summary pills */}
      <div className="grid grid-cols-4 gap-3">
        {(['critical','high','medium','low'] as const).map(sev => (
          <div key={sev} className={`rounded-lg p-3 ${SEVERITY_CONFIG[sev].soft} border border-opacity-20`}>
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold uppercase tracking-wide text-gray-500">{sev}</span>
              <AlertTriangle className={`h-4 w-4 ${SEVERITY_CONFIG[sev].icon}`} />
            </div>
            <div className={`text-2xl font-bold mt-1 ${SEVERITY_CONFIG[sev].icon}`}>{counts[sev]}</div>
          </div>
        ))}
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
          {alerts.map((alert) => {
            const sev = (alert.severity || 'low') as keyof typeof SEVERITY_CONFIG
            const cfg = SEVERITY_CONFIG[sev] || SEVERITY_CONFIG.low
            return (
            <Card key={alert._id} className={`border-l-4 ${cfg.border} shadow-sm hover:shadow-md transition-shadow`}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 flex-1 min-w-0">
                    <AlertTriangle className={`h-5 w-5 mt-0.5 flex-shrink-0 ${cfg.icon}`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`px-2 py-0.5 rounded-full text-xs font-bold uppercase tracking-wide ${cfg.badge}`}>
                          {sev}
                        </span>
                        <span className="text-xs font-semibold text-gray-700 bg-gray-100 px-2 py-0.5 rounded-full">
                          Risk Score: {alert.risk_score.toFixed(1)} / 10
                        </span>
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {new Date(alert.created_at).toLocaleString()}
                        </span>
                      </div>
                      <CardTitle className="text-base leading-snug">{alert.title}</CardTitle>
                    </div>
                  </div>
                  {!alert.acknowledged_at && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="flex-shrink-0"
                      onClick={() => acknowledgeMutation.mutate(alert._id)}
                      disabled={acknowledgeMutation.isPending}
                    >
                      Acknowledge
                    </Button>
                  )}
                  {alert.acknowledged_at && (
                    <span className="flex items-center gap-1 text-xs text-green-600 flex-shrink-0">
                      <CheckCircle className="h-3.5 w-3.5" /> Acknowledged
                    </span>
                  )}
                </div>
              </CardHeader>
              <CardContent className="space-y-4 pt-0">
                {/* Description */}
                {alert.description && (
                  <p className="text-sm text-muted-foreground leading-relaxed">{alert.description}</p>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Affected Suppliers */}
                  {(alert.affected_suppliers || []).length > 0 && (
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Building2 className="h-3.5 w-3.5 text-muted-foreground" />
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Affected Suppliers</h4>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(alert.affected_suppliers || []).map((supplier) => (
                          <span key={supplier} className="px-2 py-0.5 bg-secondary rounded-full text-xs font-medium">
                            {supplier}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Affected Materials */}
                  {(alert.affected_materials || []).length > 0 && (
                    <div className="rounded-lg border p-3">
                      <div className="flex items-center gap-1.5 mb-2">
                        <Package className="h-3.5 w-3.5 text-muted-foreground" />
                        <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Affected Materials</h4>
                      </div>
                      <div className="flex flex-wrap gap-1.5">
                        {(alert.affected_materials || []).map((material) => (
                          <span key={material} className="px-2 py-0.5 bg-secondary rounded-full text-xs font-medium">
                            {material}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* Recommendation */}
                {alert.recommendation && (
                  <div className="rounded-lg bg-muted/50 border p-3">
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-1">Recommendation</h4>
                    <p className="text-sm">{alert.recommendation}</p>
                  </div>
                )}

                {/* Alternate Suppliers */}
                {alert.alternate_suppliers && alert.alternate_suppliers.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground mb-2">Alternate Suppliers</h4>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {alert.alternate_suppliers.map((alt) => (
                        <div key={alt.supplier_id} className="flex items-center justify-between p-2.5 bg-background rounded-lg border">
                          <div>
                            <span className="text-sm font-semibold">{alt.name}</span>
                            <div className="text-xs text-muted-foreground mt-0.5">{alt.country}</div>
                          </div>
                          <div className="text-right">
                            <div className="text-sm font-bold text-green-600">{alt.score.toFixed(1)}<span className="text-xs font-normal text-muted-foreground">/10</span></div>
                            {alt.lead_time_weeks && (
                              <div className="text-xs text-muted-foreground">{alt.lead_time_weeks}w lead</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
          )}
        </div>
      )}
    </div>
  )
}
