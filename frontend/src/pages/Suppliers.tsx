import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { MapPin, TrendingUp, Activity } from 'lucide-react'

export default function Suppliers() {
  const { data: suppliers, isLoading } = useQuery({
    queryKey: ['suppliers'],
    queryFn: api.getSuppliers,
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading suppliers...</div>
  }

  const getRiskBadge = (risk: number) => {
    if (risk >= 10) return { label: 'Critical', color: 'bg-red-600 text-white' }
    if (risk >= 6) return { label: 'High', color: 'bg-orange-500 text-white' }
    if (risk >= 3) return { label: 'Medium', color: 'bg-yellow-500 text-black' }
    return { label: 'Low', color: 'bg-green-600 text-white' }
  }

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      active: 'bg-green-100 text-green-800',
      pre_qualified: 'bg-blue-100 text-blue-800',
      alternate: 'bg-gray-100 text-gray-800',
    }
    return colors[status] || 'bg-gray-100 text-gray-800'
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Suppliers</h1>
        <p className="text-muted-foreground">
          Manage and monitor your supply chain suppliers
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {suppliers?.map((supplier) => {
          const riskBadge = getRiskBadge(supplier.risk_score_current)
          
          return (
            <Card key={supplier._id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{supplier.name}</CardTitle>
                    <div className="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                      <MapPin className="h-3 w-3" />
                      {supplier.country}
                    </div>
                  </div>
                  <span className={`px-2 py-1 rounded-md text-xs font-medium ${getStatusBadge(supplier.status)}`}>
                    {supplier.status}
                  </span>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                {/* Risk Score */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground">Risk Score</span>
                  <span className={`px-2 py-1 rounded-md text-xs font-medium ${riskBadge.color}`}>
                    {supplier.risk_score_current.toFixed(1)} - {riskBadge.label}
                  </span>
                </div>

                {/* ESG Score */}
                <div className="flex items-center justify-between">
                  <span className="text-sm text-muted-foreground flex items-center gap-1">
                    <Activity className="h-3 w-3" />
                    ESG Score
                  </span>
                  <span className="text-sm font-medium">{supplier.esg_score}/100</span>
                </div>

                {/* Supply Volume */}
                {supplier.supply_volume_pct > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground flex items-center gap-1">
                      <TrendingUp className="h-3 w-3" />
                      Supply Volume
                    </span>
                    <span className="text-sm font-medium">{supplier.supply_volume_pct.toFixed(1)}%</span>
                  </div>
                )}

                {/* Materials */}
                <div>
                  <span className="text-sm text-muted-foreground">Materials:</span>
                  <div className="flex flex-wrap gap-1 mt-1">
                    {supplier.supplies.map((material) => (
                      <span key={material} className="px-2 py-1 bg-secondary text-secondary-foreground rounded text-xs">
                        {material}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Tier */}
                <div className="flex items-center justify-between pt-2 border-t">
                  <span className="text-xs text-muted-foreground">Tier {supplier.tier}</span>
                  <span className="text-xs text-muted-foreground">{supplier.credit_rating}</span>
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
