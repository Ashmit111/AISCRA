import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '@/lib/api'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { FileText, Calendar, Download } from 'lucide-react'

export default function Reports() {
  const [reportType, setReportType] = useState<'all' | 'daily' | 'weekly' | 'custom'>('all')
  const queryClient = useQueryClient()

  const { data: reports, isLoading } = useQuery({
    queryKey: ['reports', reportType],
    queryFn: () => api.getReports({ 
      report_type: reportType === 'all' ? undefined : reportType,
      limit: 20 
    }),
  })

  const generateMutation = useMutation({
    mutationFn: (type: 'daily' | 'weekly') => api.generateReport(type),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['reports'] })
    }
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading reports...</div>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Reports</h1>
          <p className="text-muted-foreground">
            AI-generated supply chain risk analysis reports
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={() => generateMutation.mutate('daily')}
            disabled={generateMutation.isPending}
          >
            Generate Daily Report
          </Button>
          <Button
            variant="outline"
            onClick={() => generateMutation.mutate('weekly')}
            disabled={generateMutation.isPending}
          >
            Generate Weekly Report
          </Button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2">
        {['all', 'daily', 'weekly', 'custom'].map((type) => (
          <Button
            key={type}
            variant={reportType === type ? 'default' : 'outline'}
            size="sm"
            onClick={() => setReportType(type as any)}
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </Button>
        ))}
      </div>

      {/* Reports List */}
      {!reports || reports.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <FileText className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
            <p className="text-lg font-medium">No reports found</p>
            <p className="text-sm text-muted-foreground">Generate a report to get started</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {reports.map((report) => (
            <Card key={report._id} className="hover:shadow-md transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <FileText className="h-5 w-5 text-primary" />
                  <span className="px-2 py-1 bg-secondary text-secondary-foreground rounded text-xs font-medium">
                    {report.report_type}
                  </span>
                </div>
                <CardTitle className="text-base mt-2">{report.title}</CardTitle>
                <div className="flex items-center gap-1 text-xs text-muted-foreground mt-1">
                  <Calendar className="h-3 w-3" />
                  {new Date(report.generated_at).toLocaleDateString()}
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <p className="text-sm text-muted-foreground">
                    {report.sections.length} sections
                  </p>
                  <div className="flex gap-2">
                    <Button size="sm" variant="outline" className="flex-1">
                      View Report
                    </Button>
                    <Button size="sm" variant="ghost">
                      <Download className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
