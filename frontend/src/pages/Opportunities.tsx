import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, Filter, Plus } from 'lucide-react'
import { opportunitiesApi } from '../lib/api'
import { format } from 'date-fns'

export default function Opportunities() {
  const { data: opportunities = [], isLoading } = useQuery({
    queryKey: ['opportunities'],
    queryFn: () => opportunitiesApi.list({ limit: 100 }),
  })

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Opportunities</h1>
          <p className="text-gray-600 mt-1">Manage federal contracting opportunities</p>
        </div>
        <Link to="/workflow" className="btn-primary h-10 px-4 gap-2">
          <Plus className="w-4 h-4" />
          Run Discovery
        </Link>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search opportunities..."
              className="input w-full pl-10"
            />
          </div>
          <button className="btn-secondary h-10 px-4 gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      {/* Opportunities List */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Title</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agency</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Set-Aside</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Score</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Deadline</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    Loading opportunities...
                  </td>
                </tr>
              ) : opportunities.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    No opportunities found. Run discovery to find new opportunities.
                  </td>
                </tr>
              ) : (
                opportunities.map((opp) => (
                  <tr key={opp.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <Link to={`/opportunities/${opp.id}`} className="text-primary-600 hover:text-primary-700 font-medium">
                        {opp.title}
                      </Link>
                      <p className="text-sm text-gray-500">{opp.solicitation_number}</p>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">{opp.agency}</td>
                    <td className="px-6 py-4">
                      {opp.set_aside && (
                        <span className={`badge badge-${opp.set_aside.toLowerCase()}`}>
                          {opp.set_aside}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      {opp.bid_score_total && (
                        <span className="text-sm font-medium text-gray-900">
                          {opp.bid_score_total.toFixed(0)}
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-900">
                      {opp.response_deadline && format(new Date(opp.response_deadline), 'MMM d, yyyy')}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`badge ${
                        opp.status === 'approved' ? 'badge-success' :
                        opp.status === 'rejected' ? 'badge-danger' :
                        'badge-info'
                      }`}>
                        {opp.status}
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
