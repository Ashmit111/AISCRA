import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, PipelineRun } from '@/lib/api'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import {
  RefreshCw,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  FileText,
  Download,
  Activity,
  Zap,
} from 'lucide-react'
import { useState } from 'react'

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    idle: 'bg-slate-100 text-slate-700',
    running: 'bg-blue-100 text-blue-700',
    fetching: 'bg-cyan-100 text-cyan-700',
    extracting: 'bg-purple-100 text-purple-700',
    scoring: 'bg-amber-100 text-amber-700',
    alerting: 'bg-orange-100 text-orange-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
  }
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${
        styles[status] || styles.idle
      }`}
    >
      {status === 'running' || status === 'fetching' || status === 'extracting' || status === 'scoring' || status === 'alerting' ? (
        <Loader2 className="mr-1 h-3 w-3 animate-spin" />
      ) : status === 'completed' ? (
        <CheckCircle2 className="mr-1 h-3 w-3" />
      ) : status === 'failed' ? (
        <XCircle className="mr-1 h-3 w-3" />
      ) : (
        <Clock className="mr-1 h-3 w-3" />
      )}
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  )
}

function RunSummary({ run }: { run: PipelineRun }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div
      className="border rounded-lg p-3 cursor-pointer hover:bg-muted/30 transition-colors"
      onClick={() => setExpanded(!expanded)}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusBadge status={run.status} />
          <span className="text-xs text-muted-foreground font-mono">
            {run.run_id}
          </span>
        </div>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {run.duration_seconds != null && (
            <span>{run.duration_seconds.toFixed(1)}s</span>
          )}
          <span>{new Date(run.started_at).toLocaleString()}</span>
        </div>
      </div>

      {expanded && (
        <div className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          {run.fetch && (
            <div className="bg-cyan-50 rounded p-2">
              <div className="font-medium text-cyan-800 mb-1">Fetch</div>
              <div>NewsAPI: {run.fetch.newsapi_fetched}</div>
              <div>GDELT: {run.fetch.gdelt_fetched}</div>
              <div>Pushed: {run.fetch.pushed}</div>
              <div>Dupes: {run.fetch.duplicates}</div>
            </div>
          )}
          {run.extract && (
            <div className="bg-purple-50 rounded p-2">
              <div className="font-medium text-purple-800 mb-1">Extract</div>
              <div>Read: {run.extract.read}</div>
              <div>Relevant: {run.extract.relevant}</div>
              <div>Risks: {run.extract.risks_found}</div>
            </div>
          )}
          {run.score && (
            <div className="bg-amber-50 rounded p-2">
              <div className="font-medium text-amber-800 mb-1">Score</div>
              <div>Read: {run.score.read}</div>
              <div>Scored: {run.score.scored}</div>
            </div>
          )}
          {run.alert && (
            <div className="bg-orange-50 rounded p-2">
              <div className="font-medium text-orange-800 mb-1">Alert</div>
              <div>Created: {run.alert.alerts_created}</div>
              <div>Below threshold: {run.alert.below_threshold}</div>
            </div>
          )}
          {run.error && (
            <div className="col-span-full bg-red-50 rounded p-2 text-red-800">
              Error: {run.error}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default function Pipeline() {
  const queryClient = useQueryClient()

  const { data: pipelineData, isLoading } = useQuery({
    queryKey: ['pipeline-status'],
    queryFn: api.getPipelineStatus,
    refetchInterval: 5000,
  })

  const { data: streamData } = useQuery({
    queryKey: ['stream-stats'],
    queryFn: api.getStreamStats,
    refetchInterval: 5000,
  })

  const triggerMutation = useMutation({
    mutationFn: api.triggerPipeline,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
    },
  })

  const fetchOnlyMutation = useMutation({
    mutationFn: api.triggerFetchOnly,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['pipeline-status'] })
      queryClient.invalidateQueries({ queryKey: ['stream-stats'] })
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  const current = pipelineData?.current
  const runs = pipelineData?.recent_runs || []
  const schedule = pipelineData?.schedule
  const streams = streamData?.streams || {}
  const isRunning =
    current?.status === 'running' ||
    current?.status === 'fetching' ||
    current?.status === 'extracting' ||
    current?.status === 'scoring' ||
    current?.status === 'alerting'

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Automated Pipeline
          </h1>
          <p className="text-muted-foreground">
            News ingestion &rarr; Risk extraction &rarr; Scoring &rarr; Alert
            generation
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={isRunning || fetchOnlyMutation.isPending}
            onClick={() => fetchOnlyMutation.mutate()}
          >
            {fetchOnlyMutation.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Download className="mr-2 h-4 w-4" />
            )}
            Fetch Only
          </Button>
          <Button
            size="sm"
            disabled={isRunning || triggerMutation.isPending}
            onClick={() => triggerMutation.mutate()}
          >
            {triggerMutation.isPending || isRunning ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            Run Full Pipeline
          </Button>
        </div>
      </div>

      {/* Status + Schedule */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Current Status</CardTitle>
          </CardHeader>
          <CardContent>
            <StatusBadge status={current?.status || 'idle'} />
            {current?.detail && (
              <p className="text-xs text-muted-foreground mt-2">
                {current.detail}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Schedule</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm">
                Every {schedule?.interval_minutes || 15} minutes
              </span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Celery Beat automatic scheduling
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Stream Backlog
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Articles</span>
                <span className="font-mono">
                  {streams.normalized_events ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Risk Entities</span>
                <span className="font-mono">
                  {streams.risk_entities ?? 0}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Risk Scores</span>
                <span className="font-mono">{streams.risk_scores ?? 0}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">New Alerts</span>
                <span className="font-mono">{streams.new_alerts ?? 0}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Pipeline flow diagram (simple) */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Pipeline Flow</CardTitle>
          <CardDescription>
            Each stage processes data automatically and passes it downstream
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-2 overflow-x-auto py-2">
            {[
              { label: 'NewsAPI + GDELT', icon: FileText, color: 'bg-cyan-500' },
              { label: 'Normalize & Dedup', icon: RefreshCw, color: 'bg-teal-500' },
              { label: 'Relevance + AI Extract', icon: Zap, color: 'bg-purple-500' },
              { label: 'Risk Scoring', icon: Activity, color: 'bg-amber-500' },
              { label: 'Alerts & Notify', icon: CheckCircle2, color: 'bg-green-500' },
            ].map((step, i, arr) => (
              <div key={step.label} className="flex items-center gap-2 min-w-max">
                <div className="flex flex-col items-center gap-1">
                  <div
                    className={`${step.color} rounded-lg p-2 text-white`}
                  >
                    <step.icon className="h-5 w-5" />
                  </div>
                  <span className="text-[11px] text-muted-foreground text-center max-w-[100px]">
                    {step.label}
                  </span>
                </div>
                {i < arr.length - 1 && (
                  <div className="text-muted-foreground text-lg">&rarr;</div>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">
            Recent Pipeline Runs
          </CardTitle>
          <CardDescription>
            Click a run to expand stage-by-stage details
          </CardDescription>
        </CardHeader>
        <CardContent>
          {runs.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">
              No pipeline runs yet. Click "Run Full Pipeline" to start.
            </p>
          ) : (
            <div className="space-y-2">
              {runs.map((run: PipelineRun, idx: number) => (
                <RunSummary key={run.run_id || idx} run={run} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
