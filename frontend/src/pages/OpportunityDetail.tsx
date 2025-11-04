import { useQuery } from '@tanstack/react-query'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Play } from 'lucide-react'
import { opportunitiesApi } from '../lib/api'
import { format } from 'date-fns'

export default function OpportunityDetail() {
  const { id } = useParams<{ id: string }>()

  const { data: opportunity, isLoading } = useQuery({
    queryKey: ['opportunity', id],
    queryFn: () => opportunitiesApi.get(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return <div className="text-center py-12">Loading...</div>
  }

  if (!opportunity) {
    return <div className="text-center py-12">Opportunity not found</div>
  }

  return (
    <div className="space-y-6">
      <Link to="/opportunities" className="inline-flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900">
        <ArrowLeft className="w-4 h-4" />
        Back to Opportunities
      </Link>

      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">{opportunity.title}</h1>
          <p className="text-gray-600 mt-1">{opportunity.solicitation_number}</p>
        </div>
        <Link to={`/workflow?opportunity=${opportunity.id}`} className="btn-primary h-10 px-4 gap-2">
          <Play className="w-4 h-4" />
          Execute Workflow
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Details</h2>
            <dl className="grid grid-cols-2 gap-4">
              <div>
                <dt className="text-sm font-medium text-gray-500">Agency</dt>
                <dd className="mt-1 text-sm text-gray-900">{opportunity.agency}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Set-Aside</dt>
                <dd className="mt-1">
                  {opportunity.set_aside ? (
                    <span className={`badge badge-${opportunity.set_aside.toLowerCase()}`}>
                      {opportunity.set_aside}
                    </span>
                  ) : (
                    <span className="text-sm text-gray-500">None</span>
                  )}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">NAICS Code</dt>
                <dd className="mt-1 text-sm text-gray-900">{opportunity.naics_code || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">PSC Code</dt>
                <dd className="mt-1 text-sm text-gray-900">{opportunity.psc_code || 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Posted Date</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {format(new Date(opportunity.posted_date), 'MMM d, yyyy')}
                </dd>
              </div>
              <div>
                <dt className="text-sm font-medium text-gray-500">Response Deadline</dt>
                <dd className="mt-1 text-sm text-gray-900">
                  {opportunity.response_deadline ? format(new Date(opportunity.response_deadline), 'MMM d, yyyy') : 'N/A'}
                </dd>
              </div>
            </dl>
          </div>

          {opportunity.bid_score_total && (
            <div className="card p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Bid/No-Bid Analysis</h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-600">Total Score</span>
                  <span className="text-2xl font-bold text-primary-600">{opportunity.bid_score_total.toFixed(0)}</span>
                </div>
                {opportunity.bid_recommendation && (
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600">Recommendation</span>
                    <span className={`badge ${
                      opportunity.bid_recommendation === 'BID' ? 'badge-success' :
                      opportunity.bid_recommendation === 'NO_BID' ? 'badge-danger' :
                      'badge-warning'
                    }`}>
                      {opportunity.bid_recommendation}
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Status</h2>
            <span className={`badge badge-${
              opportunity.status === 'approved' ? 'success' :
              opportunity.status === 'rejected' ? 'danger' :
              'info'
            }`}>
              {opportunity.status}
            </span>
          </div>

          <div className="card p-6">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Match Scores</h2>
            <div className="space-y-3">
              {opportunity.naics_match !== null && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-600">NAICS Match</span>
                    <span className="text-sm font-medium">{(opportunity.naics_match * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${opportunity.naics_match * 100}%` }}
                    />
                  </div>
                </div>
              )}
              {opportunity.psc_match !== null && (
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-600">PSC Match</span>
                    <span className="text-sm font-medium">{(opportunity.psc_match * 100).toFixed(0)}%</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="bg-primary-600 h-2 rounded-full"
                      style={{ width: `${opportunity.psc_match * 100}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
