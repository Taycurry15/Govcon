import { useQuery } from '@tanstack/react-query'
import { FileText, FileCheck, DollarSign, Target, AlertCircle } from 'lucide-react'
import { opportunitiesApi, proposalsApi } from '../lib/api'
import { Link } from 'react-router-dom'

export default function Dashboard() {
  const { data: opportunities = [], isLoading: loadingOpps } = useQuery({
    queryKey: ['opportunities'],
    queryFn: () => opportunitiesApi.list({ limit: 100 }),
  })

  const { data: proposals = [], isLoading: loadingProps } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => proposalsApi.list({ limit: 100 }),
  })

  // Calculate stats
  const stats = {
    totalOpportunities: opportunities.length,
    sdvosbOpportunities: opportunities.filter(o => o.set_aside === 'SDVOSB').length,
    activeProposals: proposals.filter(p => p.status !== 'submitted').length,
    submittedProposals: proposals.filter(p => p.status === 'submitted').length,
    pipelineValue: opportunities.reduce((sum, o) => sum + (o.estimated_value || 0), 0),
    avgBidScore: opportunities.filter(o => o.bid_score_total).reduce((sum, o) => sum + (o.bid_score_total || 0), 0) / (opportunities.filter(o => o.bid_score_total).length || 1),
  }

  const statCards = [
    {
      name: 'Total Opportunities',
      value: stats.totalOpportunities,
      icon: FileText,
      color: 'blue',
      trend: '+12%',
    },
    {
      name: 'SDVOSB Opportunities',
      value: stats.sdvosbOpportunities,
      icon: Target,
      color: 'purple',
      trend: `${Math.round((stats.sdvosbOpportunities / stats.totalOpportunities) * 100)}%`,
    },
    {
      name: 'Active Proposals',
      value: stats.activeProposals,
      icon: FileCheck,
      color: 'green',
      trend: '+3 this week',
    },
    {
      name: 'Pipeline Value',
      value: `$${(stats.pipelineValue / 1000000).toFixed(1)}M`,
      icon: DollarSign,
      color: 'emerald',
      trend: '+18%',
    },
  ]

  const recentOpportunities = opportunities.slice(0, 5)
  const pendingApprovals = opportunities.filter(o => o.status === 'awaiting_pink_team' || o.status === 'awaiting_gold_team')

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Welcome to The Bronze Shield GovCon AI Pipeline</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat) => (
          <div key={stat.name} className="card p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="text-3xl font-bold text-gray-900 mt-2">{stat.value}</p>
                <p className="text-sm text-green-600 mt-1">{stat.trend}</p>
              </div>
              <div className={`w-12 h-12 bg-${stat.color}-100 rounded-lg flex items-center justify-center`}>
                <stat.icon className={`w-6 h-6 text-${stat.color}-600`} />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Pending Approvals */}
      {pendingApprovals.length > 0 && (
        <div className="card p-6">
          <div className="flex items-center gap-2 mb-4">
            <AlertCircle className="w-5 h-5 text-yellow-600" />
            <h2 className="text-lg font-semibold text-gray-900">Pending Approvals</h2>
            <span className="badge badge-warning">{pendingApprovals.length}</span>
          </div>
          <div className="space-y-3">
            {pendingApprovals.map((opp) => (
              <Link
                key={opp.id}
                to={`/opportunities/${opp.id}`}
                className="block p-4 bg-yellow-50 border border-yellow-200 rounded-lg hover:bg-yellow-100 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900">{opp.title}</p>
                    <p className="text-sm text-gray-600">{opp.agency} • {opp.solicitation_number}</p>
                  </div>
                  <div className="text-right">
                    <span className={`badge ${opp.status === 'awaiting_pink_team' ? 'badge-warning' : 'badge-info'}`}>
                      {opp.status.replace('awaiting_', '').replace('_', ' ')}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {/* Recent Opportunities */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Recent Opportunities</h2>
          {loadingOpps ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : recentOpportunities.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No opportunities yet</div>
          ) : (
            <div className="space-y-3">
              {recentOpportunities.map((opp) => (
                <Link
                  key={opp.id}
                  to={`/opportunities/${opp.id}`}
                  className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 line-clamp-1">{opp.title}</p>
                      <p className="text-sm text-gray-600 mt-1">{opp.agency}</p>
                      <div className="flex items-center gap-2 mt-2">
                        {opp.set_aside && (
                          <span className={`badge badge-${opp.set_aside.toLowerCase()}`}>
                            {opp.set_aside}
                          </span>
                        )}
                        {opp.bid_score_total && (
                          <span className="text-xs text-gray-500">
                            Score: {opp.bid_score_total.toFixed(0)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
          <Link to="/opportunities" className="block mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium">
            View all opportunities →
          </Link>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Active Proposals</h2>
          {loadingProps ? (
            <div className="text-center py-8 text-gray-500">Loading...</div>
          ) : proposals.length === 0 ? (
            <div className="text-center py-8 text-gray-500">No proposals yet</div>
          ) : (
            <div className="space-y-3">
              {proposals.slice(0, 5).map((proposal) => (
                <Link
                  key={proposal.id}
                  to={`/proposals/${proposal.id}`}
                  className="block p-4 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <p className="font-medium text-gray-900 line-clamp-1">{proposal.title}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500">v{proposal.version}</span>
                    <span className={`badge ${
                      proposal.status === 'submitted' ? 'badge-success' :
                      proposal.status === 'ready_for_submission' ? 'badge-info' :
                      'badge-warning'
                    }`}>
                      {proposal.status.replace('_', ' ')}
                    </span>
                  </div>
                </Link>
              ))}
            </div>
          )}
          <Link to="/proposals" className="block mt-4 text-sm text-primary-600 hover:text-primary-700 font-medium">
            View all proposals →
          </Link>
        </div>
      </div>
    </div>
  )
}
