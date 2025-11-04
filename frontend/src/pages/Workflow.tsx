import { useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { Play, Pause, CheckCircle, Clock, AlertCircle, Settings as SettingsIcon } from 'lucide-react'
import { workflowApi, opportunitiesApi } from '../lib/api'
import toast from 'react-hot-toast'

export default function Workflow() {
  const [searchParams] = useSearchParams()
  const opportunityId = searchParams.get('opportunity')

  const [selectedWorkflow, setSelectedWorkflow] = useState<string>('full')
  const [autoApprove, setAutoApprove] = useState(false)
  const [selectedOpportunity, setSelectedOpportunity] = useState<string>(opportunityId || '')

  const { data: opportunities = [] } = useQuery({
    queryKey: ['opportunities'],
    queryFn: () => opportunitiesApi.list({ limit: 100 }),
  })

  // Workflow status tracking - to be implemented
  const workflowStatus: any = null
  const refetchStatus = () => {}

  const executeMutation = useMutation({
    mutationFn: (data: { workflow: string; opportunityId?: string; autoApprove: boolean }) => {
      if (data.workflow === 'full' && data.opportunityId) {
        return workflowApi.execute({ opportunity_id: data.opportunityId, auto_approve: data.autoApprove })
      } else if (data.workflow === 'discovery') {
        return workflowApi.discover({ auto_approve: data.autoApprove })
      }
      throw new Error('Invalid workflow configuration')
    },
    onSuccess: () => {
      toast.success('Workflow started successfully')
      refetchStatus()
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || 'Failed to start workflow')
    },
  })

  const handleExecute = () => {
    if (selectedWorkflow === 'full' && !selectedOpportunity) {
      toast.error('Please select an opportunity')
      return
    }

    executeMutation.mutate({
      workflow: selectedWorkflow,
      opportunityId: selectedOpportunity || undefined,
      autoApprove,
    })
  }

  const getStageStatus = (stage: string) => {
    if (!workflowStatus?.current_stage) return 'pending'

    const stages = [
      'discovery', 'screening', 'pink_team', 'solicitation_review',
      'drafting', 'pricing', 'gold_team', 'submission'
    ]

    const currentIndex = stages.indexOf(workflowStatus.current_stage)
    const stageIndex = stages.indexOf(stage)

    if (stageIndex < currentIndex) return 'completed'
    if (stageIndex === currentIndex) return 'in_progress'
    return 'pending'
  }

  const getStageIcon = (status: string) => {
    if (status === 'completed') return <CheckCircle className="w-5 h-5 text-green-600" />
    if (status === 'in_progress') return <Clock className="w-5 h-5 text-blue-600 animate-pulse" />
    return <AlertCircle className="w-5 h-5 text-gray-400" />
  }

  const workflowStages = [
    { key: 'discovery', label: 'Discovery', description: 'Search SAM.gov for opportunities' },
    { key: 'screening', label: 'Screening', description: 'Bid/No-Bid analysis' },
    { key: 'pink_team', label: 'Pink Team', description: 'Initial review' },
    { key: 'solicitation_review', label: 'Solicitation Review', description: 'Compliance matrix' },
    { key: 'drafting', label: 'Drafting', description: 'Proposal generation' },
    { key: 'pricing', label: 'Pricing', description: 'Cost estimation' },
    { key: 'gold_team', label: 'Gold Team', description: 'Final review' },
    { key: 'submission', label: 'Submission', description: 'Ready to submit' },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Workflow Execution</h1>
        <p className="text-gray-600 mt-1">Run discovery or execute full proposal workflows</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration Panel */}
        <div className="lg:col-span-1 space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
              <SettingsIcon className="w-5 h-5" />
              Configuration
            </h2>

            <div className="space-y-4">
              {/* Workflow Type */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Workflow Type
                </label>
                <select
                  value={selectedWorkflow}
                  onChange={(e) => setSelectedWorkflow(e.target.value)}
                  className="input w-full"
                  disabled={executeMutation.isPending}
                >
                  <option value="discovery">Discovery Only</option>
                  <option value="full">Full Workflow</option>
                </select>
              </div>

              {/* Opportunity Selection */}
              {selectedWorkflow === 'full' && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Opportunity
                  </label>
                  <select
                    value={selectedOpportunity}
                    onChange={(e) => setSelectedOpportunity(e.target.value)}
                    className="input w-full"
                    disabled={executeMutation.isPending}
                  >
                    <option value="">Choose an opportunity...</option>
                    {opportunities.map((opp) => (
                      <option key={opp.id} value={opp.id}>
                        {opp.title}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Auto-approve */}
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="auto-approve"
                  checked={autoApprove}
                  onChange={(e) => setAutoApprove(e.target.checked)}
                  disabled={executeMutation.isPending}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                />
                <label htmlFor="auto-approve" className="text-sm text-gray-700">
                  Auto-approve stages
                </label>
              </div>

              {/* Execute Button */}
              <button
                onClick={handleExecute}
                disabled={executeMutation.isPending || workflowStatus?.is_running}
                className="btn-primary w-full h-10 gap-2"
              >
                {executeMutation.isPending ? (
                  <>
                    <Clock className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : workflowStatus?.is_running ? (
                  <>
                    <Pause className="w-4 h-4" />
                    Workflow Running
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Execute Workflow
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Current Status */}
          {workflowStatus?.is_running && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Status</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Current Stage</span>
                  <span className="badge badge-info capitalize">
                    {workflowStatus.current_stage?.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Progress</span>
                  <span className="text-sm font-medium text-gray-900">
                    {workflowStatus.progress_percentage?.toFixed(0)}%
                  </span>
                </div>
                {workflowStatus.estimated_completion && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Est. Completion</span>
                    <span className="text-sm font-medium text-gray-900">
                      {new Date(workflowStatus.estimated_completion).toLocaleTimeString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Workflow Stages */}
        <div className="lg:col-span-2">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-6">Workflow Stages</h2>

            <div className="space-y-4">
              {workflowStages.map((stage, index) => {
                const status = getStageStatus(stage.key)
                return (
                  <div
                    key={stage.key}
                    className={`flex items-start gap-4 p-4 rounded-lg border-2 transition-all ${
                      status === 'in_progress'
                        ? 'border-blue-200 bg-blue-50'
                        : status === 'completed'
                        ? 'border-green-200 bg-green-50'
                        : 'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex-shrink-0 mt-0.5">
                      {getStageIcon(status)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-900">
                          {index + 1}. {stage.label}
                        </h3>
                        {status === 'completed' && (
                          <span className="text-xs text-green-600 font-medium">Completed</span>
                        )}
                        {status === 'in_progress' && (
                          <span className="text-xs text-blue-600 font-medium">In Progress</span>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{stage.description}</p>

                      {status === 'in_progress' && workflowStatus?.current_message && (
                        <div className="mt-2 text-xs text-gray-500 italic">
                          {workflowStatus.current_message}
                        </div>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          {/* Recent Executions */}
          {workflowStatus?.recent_executions && workflowStatus.recent_executions.length > 0 && (
            <div className="card p-6 mt-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Executions</h2>
              <div className="space-y-3">
                {workflowStatus.recent_executions.map((execution: any) => (
                  <div key={execution.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {execution.workflow_type === 'full' ? 'Full Workflow' : 'Discovery'}
                      </p>
                      <p className="text-xs text-gray-500">
                        {new Date(execution.started_at).toLocaleString()}
                      </p>
                    </div>
                    <span className={`badge ${
                      execution.status === 'completed' ? 'badge-success' :
                      execution.status === 'failed' ? 'badge-danger' :
                      'badge-info'
                    }`}>
                      {execution.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
