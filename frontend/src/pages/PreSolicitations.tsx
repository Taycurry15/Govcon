import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { Search, Filter, FileText, Calendar, Building2 } from 'lucide-react'
import { opportunitiesApi } from '../lib/api'
import { format } from 'date-fns'

export default function PreSolicitations() {
  // Fetch opportunities that are in pre-solicitation phase (discovered/screening status)
  const { data: preSolicitations = [], isLoading } = useQuery({
    queryKey: ['pre-solicitations'],
    queryFn: () => opportunitiesApi.list({ limit: 100, status: 'discovered,screening' }),
  })

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Pre-Solicitations</h1>
          <p className="text-gray-600 mt-1">
            Track opportunities before formal solicitation release
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-right">
            <p className="text-2xl font-bold text-primary-600">{preSolicitations.length}</p>
            <p className="text-sm text-gray-500">Active Pre-Solicitations</p>
          </div>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-primary-100 rounded-apple-lg">
              <FileText className="w-6 h-6 text-primary-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {preSolicitations.filter(p => p.status === 'discovered').length}
              </p>
              <p className="text-sm text-gray-600">Newly Discovered</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-systemYellow/20 rounded-apple-lg">
              <Calendar className="w-6 h-6 text-amber-600" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {preSolicitations.filter(p => p.status === 'screening').length}
              </p>
              <p className="text-sm text-gray-600">Under Review</p>
            </div>
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-systemGreen/20 rounded-apple-lg">
              <Building2 className="w-6 h-6 text-systemGreen" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {new Set(preSolicitations.map(p => p.agency)).size}
              </p>
              <p className="text-sm text-gray-600">Agencies</p>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4">
        <div className="flex items-center gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search pre-solicitations..."
              className="input w-full pl-10"
            />
          </div>
          <button className="btn-secondary h-10 px-4 gap-2">
            <Filter className="w-4 h-4" />
            Filters
          </button>
        </div>
      </div>

      {/* Pre-Solicitations List */}
      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Title
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Agency
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Set-Aside
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  NAICS
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Posted Date
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="flex items-center justify-center gap-3">
                      <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
                      <span className="text-gray-500">Loading pre-solicitations...</span>
                    </div>
                  </td>
                </tr>
              ) : preSolicitations.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <div className="space-y-3">
                      <FileText className="w-12 h-12 text-gray-300 mx-auto" />
                      <p className="text-gray-500 font-medium">No pre-solicitations found</p>
                      <p className="text-sm text-gray-400">
                        New opportunities will appear here when discovered
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                preSolicitations.map((preSol) => (
                  <tr
                    key={preSol.id}
                    className="hover:bg-gray-50 transition-colors duration-150"
                  >
                    <td className="px-6 py-4">
                      <Link
                        to={`/opportunities/${preSol.id}`}
                        className="text-primary-600 hover:text-primary-700 font-medium transition-colors"
                      >
                        {preSol.title}
                      </Link>
                      <p className="text-sm text-gray-500 mt-1">
                        {preSol.solicitation_number}
                      </p>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm">
                        <div className="font-medium text-gray-900">{preSol.agency}</div>
                        {preSol.office && (
                          <div className="text-gray-500">{preSol.office}</div>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      {preSol.set_aside ? (
                        <span
                          className={`badge ${
                            preSol.set_aside === 'SDVOSB'
                              ? 'badge-sdvosb'
                              : preSol.set_aside === 'VOSB'
                              ? 'badge-vosb'
                              : preSol.set_aside === 'SB'
                              ? 'badge-sb'
                              : 'badge-info'
                          }`}
                        >
                          {preSol.set_aside}
                        </span>
                      ) : (
                        <span className="text-sm text-gray-400">-</span>
                      )}
                    </td>
                    <td className="px-6 py-4">
                      <span className="text-sm text-gray-900 font-mono">
                        {preSol.naics_code || '-'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="text-sm text-gray-900">
                        {format(new Date(preSol.posted_date), 'MMM d, yyyy')}
                      </div>
                      <div className="text-xs text-gray-500">
                        {format(new Date(preSol.posted_date), 'h:mm a')}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span
                        className={`badge ${
                          preSol.status === 'discovered'
                            ? 'badge-info'
                            : preSol.status === 'screening'
                            ? 'badge-warning'
                            : 'badge-success'
                        }`}
                      >
                        {preSol.status === 'discovered' && '🔍 Discovered'}
                        {preSol.status === 'screening' && '📋 Screening'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Info Card */}
      <div className="card-glass p-6">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-primary-100 rounded-apple">
            <FileText className="w-5 h-5 text-primary-600" />
          </div>
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">About Pre-Solicitations</h3>
            <p className="text-sm text-gray-600 mt-1">
              Pre-solicitations are opportunities in their early stages before formal solicitation
              release. These include sources sought notices, draft RFPs, and industry days that
              signal upcoming contracting opportunities. Early engagement can give you a competitive
              advantage.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
