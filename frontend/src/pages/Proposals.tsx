import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, Filter, FileCheck } from 'lucide-react'
import { proposalsApi } from '../lib/api'
import { format } from 'date-fns'

export default function Proposals() {
  const { data: proposals = [], isLoading } = useQuery({
    queryKey: ['proposals'],
    queryFn: () => proposalsApi.list({ limit: 100 }),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Proposals</h1>
          <p className="text-gray-600 mt-1">Manage proposal development and submissions</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search proposals..."
              className="input w-full pl-10"
            />
          </div>
          <button className="btn-secondary h-10 px-4 gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      {/* Proposals List */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Proposal</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Opportunity</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Stage</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    Loading proposals...
                  </td>
                </tr>
              ) : proposals.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    <FileCheck className="w-12 h-12 text-gray-400 mx-auto mb-3" />
                    <p>No proposals found. Execute a workflow to create a proposal.</p>
                  </td>
                </tr>
              ) : (
                proposals.map((proposal) => (
                  <tr key={proposal.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link to={`/proposals/${proposal.id}`} className="text-primary-600 hover:text-primary-700 font-medium">
                        {proposal.title || `Proposal ${proposal.id.substring(0, 8)}`}
                      </Link>
                      <p className="text-sm text-gray-500">
                        Version {proposal.version}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <Link to={`/opportunities/${proposal.opportunity_id}`} className="text-sm text-primary-600 hover:text-primary-700">
                        View Opportunity
                      </Link>
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-900 capitalize">
                        {proposal.stage?.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      {proposal.completion_percentage !== null && proposal.completion_percentage !== undefined && (
                        <div className="flex items-center gap-2">
                          <div className="flex-1 w-24 bg-gray-200 rounded-full h-2">
                            <div
                              className="bg-primary-600 h-2 rounded-full"
                              style={{ width: `${proposal.completion_percentage}%` }}
                            />
                          </div>
                          <span className="text-sm text-gray-600 w-12">
                            {proposal.completion_percentage.toFixed(0)}%
                          </span>
                        </div>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {proposal.due_date && format(new Date(proposal.due_date), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`badge ${
                        proposal.status === 'submitted' ? 'badge-success' :
                        proposal.status === 'ready_for_submission' ? 'badge-info' :
                        'badge-warning'
                      }`}>
                        {proposal.status.replace('_', ' ')}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
