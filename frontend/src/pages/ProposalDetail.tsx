import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Download, FileText, CheckCircle } from 'lucide-react'
import { proposalsApi } from '../lib/api'
import { format } from 'date-fns'

export default function ProposalDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: proposal, isLoading } = useQuery({
    queryKey: ['proposal', id],
    queryFn: () => proposalsApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!proposal) {
    return <div className="text-center py-12">Proposal not found</div>
  }

  const stages = [
    { key: 'discovery', label: 'Discovery', completed: true },
    { key: 'screening', label: 'Screening', completed: true },
    { key: 'pink_team', label: 'Pink Team', completed: proposal.stage !== 'discovery' && proposal.stage !== 'screening' },
    { key: 'solicitation_review', label: 'Solicitation Review', completed: proposal.stage !== 'discovery' && proposal.stage !== 'screening' && proposal.stage !== 'pink_team' },
    { key: 'drafting', label: 'Drafting', completed: proposal.stage === 'drafting' || proposal.stage === 'pricing' || proposal.stage === 'gold_team' || proposal.stage === 'submission' },
    { key: 'pricing', label: 'Pricing', completed: proposal.stage === 'pricing' || proposal.stage === 'gold_team' || proposal.stage === 'submission' },
    { key: 'gold_team', label: 'Gold Team', completed: proposal.stage === 'gold_team' || proposal.stage === 'submission' },
    { key: 'submission', label: 'Submission', completed: proposal.stage === 'submission' },
  ]

  return (
    <div className="space-y-6">
      <Link to="/proposals" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft className="w-4 h-4" />
        Back to Proposals
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            {proposal.title || `Proposal ${proposal.id.substring(0, 8)}`}
          </h1>
          <p className="text-gray-600 mt-1">Version {proposal.version}</p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary h-10 px-4 gap-2">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* Progress Timeline */}
      <div className="card p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Workflow Progress</h2>
        <div className="relative">
          <div className="absolute top-5 left-0 right-0 h-0.5 bg-gray-200" />
          <div
            className="absolute top-5 left-0 h-0.5 bg-primary-600 transition-all"
            style={{ width: `${(proposal.completion_percentage || 0)}%` }}
          />
          <div className="relative flex justify-between">
            {stages.map((stage, index) => (
              <div key={stage.key} className="flex flex-col items-center">
                <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                  stage.completed ? 'bg-primary-600 text-white' : 'bg-gray-200 text-gray-400'
                }`}>
                  {stage.completed ? (
                    <CheckCircle className="w-5 h-5" />
                  ) : (
                    <span className="text-sm font-medium">{index + 1}</span>
                  )}
                </div>
                <span className="text-xs text-gray-600 mt-2 text-center max-w-20">
                  {stage.label}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Proposal Details */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Details</h2>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Status</dt>
                <dd className="mt-1">
                  <span className={`badge ${
                    proposal.status === 'submitted' ? 'badge-success' :
                    proposal.status === 'ready_for_submission' ? 'badge-info' :
                    'badge-warning'
                  }`}>
                    {proposal.status.replace('_', ' ')}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Stage</dt>
                <dd className="mt-1 text-sm text-gray-900 capitalize">
                  {proposal.stage?.replace('_', ' ')}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Due Date</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {proposal.due_date ? format(new Date(proposal.due_date), 'MMM d, yyyy') : 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Completion</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {proposal.completion_percentage?.toFixed(0)}%
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Created</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {format(new Date(proposal.created_at), 'MMM d, yyyy')}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Last Updated</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {format(new Date(proposal.updated_at), 'MMM d, yyyy')}
                </dd>
              </div>
            </dl>
          </div>

          {/* Proposal Volumes */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Proposal Volumes</h2>
            {proposal.volumes && proposal.volumes.length > 0 ? (
              <div className="space-y-3">
                {proposal.volumes.map((volume: any) => (
                  <div key={volume.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <div>
                        <p className="font-medium text-gray-900">{volume.name}</p>
                        <p className="text-sm text-gray-500">{volume.section_count || 0} sections</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`badge ${
                        volume.status === 'completed' ? 'badge-success' :
                        volume.status === 'in_progress' ? 'badge-info' :
                        'badge-warning'
                      }`}>
                        {volume.status}
                      </span>
                      <button className="text-sm text-primary-600 hover:text-primary-700">
                        View
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-500">No volumes created yet</p>
            )}
          </div>
        </div>

        <div className="space-y-6">
          {/* Opportunity Link */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Related Opportunity</h2>
            <Link
              to={`/opportunities/${proposal.opportunity_id}`}
              className="text-primary-600 hover:text-primary-700 text-sm font-medium"
            >
              View Opportunity Details →
            </Link>
          </div>

          {/* Pricing Summary */}
          {proposal.total_price && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Pricing</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total Price</span>
                  <span className="text-2xl font-bold text-gray-900">
                    ${proposal.total_price.toLocaleString()}
                  </span>
                </div>
                {proposal.labor_cost && (
                  <div className="flex items-center justify-between pt-3 border-t">
                    <span className="text-sm text-gray-600">Labor Cost</span>
                    <span className="text-sm font-medium text-gray-900">
                      ${proposal.labor_cost.toLocaleString()}
                    </span>
                  </div>
                )}
                {proposal.materials_cost && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Materials Cost</span>
                    <span className="text-sm font-medium text-gray-900">
                      ${proposal.materials_cost.toLocaleString()}
                    </span>
                  </div>
                )}
                {proposal.indirect_cost && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Indirect Cost</span>
                    <span className="text-sm font-medium text-gray-900">
                      ${proposal.indirect_cost.toLocaleString()}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Team Members */}
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Team</h2>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center">
                  <span className="text-sm font-medium text-primary-700">CM</span>
                </div>
                <div>
                  <p className="text-sm font-medium text-gray-900">Capture Manager</p>
                  <p className="text-xs text-gray-500">Owner</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
