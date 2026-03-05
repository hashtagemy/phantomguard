import React, { useState, useEffect, useCallback, useRef } from 'react';
import { api, AuditLogEvent } from '../services/api';
import {
  FileText,
  Play,
  Square,
  Terminal,
  AlertTriangle,
  Filter,
  RefreshCw,
  ChevronDown,
  ChevronRight,
  Shield,
  Clock,
  Trash2,
  X,
} from 'lucide-react';

const EVENT_CONFIG: Record<string, { icon: React.ElementType; label: string; color: string }> = {
  session_start: { icon: Play, label: 'Session Start', color: 'text-emerald-400' },
  session_end: { icon: Square, label: 'Session End', color: 'text-blue-400' },
  tool_call: { icon: Terminal, label: 'Tool Call', color: 'text-cyan-400' },
  issue: { icon: AlertTriangle, label: 'Issue', color: 'text-yellow-400' },
};

const SEVERITY_STYLES: Record<string, { bg: string; text: string; dot: string }> = {
  info: { bg: 'bg-blue-950/20', text: 'text-blue-400', dot: 'bg-blue-500' },
  warning: { bg: 'bg-yellow-950/20', text: 'text-yellow-400', dot: 'bg-yellow-500' },
  critical: { bg: 'bg-red-950/20', text: 'text-red-400', dot: 'bg-red-500' },
};

export const AuditLogView: React.FC = () => {
  const [events, setEvents] = useState<AuditLogEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterAgent, setFilterAgent] = useState<string>('all');
  const [filterSession, setFilterSession] = useState<string>('all');
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const prevDataRef = useRef<string>('');

  const loadLogs = useCallback(async () => {
    try {
      const data = await api.getAuditLogs();
      const serialized = JSON.stringify(data);
      // Skip re-render if data unchanged (preserves scroll, expanded state)
      if (serialized !== prevDataRef.current) {
        prevDataRef.current = serialized;
        setEvents(data);
      }
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit logs');
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteEvent = async (event: AuditLogEvent) => {
    const isSessionEvent = event.event_type === 'session_start' || event.event_type === 'session_end';
    const message = isSessionEvent
      ? `Delete entire session "${event.session_id}" and all its events?`
      : `Delete this ${event.event_type.replace(/_/g, ' ')} event?`;
    if (!confirm(message)) return;
    try {
      await api.deleteAuditEvent(event.id, event.session_id, event.event_type);
      prevDataRef.current = '';
      await loadLogs();
    } catch (err) {
      console.error('Failed to delete audit event:', err);
      alert('Failed to delete event');
    }
  };

  const handleClearAll = async () => {
    if (!confirm(`Delete ALL ${events.length} audit log events? This will remove all session data and cannot be undone.`)) return;
    try {
      await api.deleteAllAuditLogs();
      prevDataRef.current = '';
      await loadLogs();
    } catch (err) {
      console.error('Failed to clear audit logs:', err);
      alert('Failed to clear audit logs');
    }
  };

  const clearAllFilters = () => {
    setFilterType('all');
    setFilterSeverity('all');
    setFilterAgent('all');
    setFilterSession('all');
  };

  useEffect(() => {
    loadLogs();
    if (!autoRefresh) return;
    const interval = setInterval(loadLogs, 10000);
    return () => clearInterval(interval);
  }, [autoRefresh, loadLogs]);

  const filtered = events.filter(e => {
    if (filterType !== 'all' && e.event_type !== filterType) return false;
    if (filterSeverity !== 'all' && e.severity !== filterSeverity) return false;
    if (filterAgent !== 'all' && e.agent_name !== filterAgent) return false;
    if (filterSession !== 'all' && e.session_id !== filterSession) return false;
    return true;
  });

  const counts = {
    all: events.length,
    session_start: events.filter(e => e.event_type === 'session_start').length,
    session_end: events.filter(e => e.event_type === 'session_end').length,
    tool_call: events.filter(e => e.event_type === 'tool_call').length,
    issue: events.filter(e => e.event_type === 'issue').length,
    critical: events.filter(e => e.severity === 'critical').length,
    warning: events.filter(e => e.severity === 'warning').length,
  };

  const uniqueAgents = Array.from(new Set<string>(events.map(e => e.agent_name))).sort();
  const uniqueSessions = Array.from(new Set<string>(events.map(e => e.session_id))).sort();

  const hasActiveFilters = filterType !== 'all' || filterSeverity !== 'all' || filterAgent !== 'all' || filterSession !== 'all';

  if (loading && events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-400 flex items-center gap-2">
          <RefreshCw size={16} className="animate-spin" /> Loading audit logs...
        </div>
      </div>
    );
  }

  if (error && events.length === 0) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="bg-red-900/20 border border-red-900/30 rounded-xl p-6 text-center">
          <h3 className="text-lg font-medium text-red-400 mb-2">Error</h3>
          <p className="text-sm text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  const GRID = 'grid-cols-[130px_90px_1fr_110px_90px_70px_36px]';

  return (
    <div className="flex flex-col h-full space-y-4 animate-in fade-in duration-700">
      {/* Header */}
      <div className="flex-none">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <FileText size={20} className="text-norn-400" /> Audit Logs
            </h1>
            <p className="text-sm text-gray-400">{events.length} event{events.length !== 1 ? 's' : ''} across all sessions</p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors ${
                autoRefresh
                  ? 'bg-norn-950/30 border-norn-900/40 text-norn-300'
                  : 'bg-dark-surface border-dark-border text-gray-400 hover:text-gray-300'
              }`}
            >
              <RefreshCw size={12} className={autoRefresh ? 'animate-spin' : ''} />
              {autoRefresh ? 'Live' : 'Paused'}
            </button>
            {events.length > 0 && (
              <button
                onClick={handleClearAll}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-red-900/30 bg-red-950/20 text-red-400 hover:bg-red-900/30 hover:text-red-300 transition-colors"
              >
                <Trash2 size={12} /> Clear All
              </button>
            )}
            <button
              onClick={() => { prevDataRef.current = ''; loadLogs(); }}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-dark-border bg-dark-surface text-gray-400 hover:text-gray-300 transition-colors"
            >
              <RefreshCw size={12} /> Refresh
            </button>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="flex-none grid grid-cols-2 lg:grid-cols-4 gap-3">
        <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <Clock size={14} className="text-gray-500" />
            <span className="text-xs font-medium text-gray-400">Total Events</span>
          </div>
          <div className="text-2xl font-bold text-white pl-1">{counts.all}</div>
        </div>
        <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <Terminal size={14} className="text-cyan-500" />
            <span className="text-xs font-medium text-gray-400">Tool Calls</span>
          </div>
          <div className="text-2xl font-bold text-white pl-1">{counts.tool_call}</div>
        </div>
        <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <AlertTriangle size={14} className="text-yellow-500" />
            <span className="text-xs font-medium text-gray-400">Warnings</span>
          </div>
          <div className="text-2xl font-bold text-yellow-400 pl-1">{counts.warning}</div>
        </div>
        <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
          <div className="flex items-center gap-2 mb-1">
            <Shield size={14} className="text-red-500" />
            <span className="text-xs font-medium text-gray-400">Critical</span>
          </div>
          <div className="text-2xl font-bold text-red-400 pl-1">{counts.critical}</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex-none flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Filter size={12} /> Filter:
        </div>
        <div className="flex items-center gap-1 bg-dark-surface/50 rounded-lg p-1 border border-dark-border">
          {(['all', 'tool_call', 'issue', 'session_start', 'session_end'] as const).map(type => (
            <button
              key={type}
              onClick={() => setFilterType(type)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                filterType === type ? 'bg-norn-600 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              {type === 'all' ? 'All' : type.replace(/_/g, ' ')}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 bg-dark-surface/50 rounded-lg p-1 border border-dark-border">
          {(['all', 'critical', 'warning', 'info'] as const).map(sev => (
            <button
              key={sev}
              onClick={() => setFilterSeverity(sev)}
              className={`px-2.5 py-1 text-[11px] font-medium rounded transition-colors ${
                filterSeverity === sev ? 'bg-norn-600 text-white' : 'text-gray-400 hover:text-gray-300'
              }`}
            >
              {sev === 'all' ? 'All Severity' : sev}
            </button>
          ))}
        </div>
        {uniqueAgents.length > 1 && (
          <select
            value={filterAgent}
            onChange={(e) => setFilterAgent(e.target.value)}
            className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg bg-dark-surface/50 border border-dark-border text-gray-300 focus:outline-none focus:border-norn-500"
          >
            <option value="all">All Agents</option>
            {uniqueAgents.map(agent => (
              <option key={agent} value={agent}>{agent}</option>
            ))}
          </select>
        )}
        {uniqueSessions.length > 1 && (
          <select
            value={filterSession}
            onChange={(e) => setFilterSession(e.target.value)}
            className="px-2.5 py-1.5 text-[11px] font-medium rounded-lg bg-dark-surface/50 border border-dark-border text-gray-300 focus:outline-none focus:border-norn-500"
          >
            <option value="all">All Sessions</option>
            {uniqueSessions.map(sid => (
              <option key={sid} value={sid}>{sid.substring(0, 20)}...</option>
            ))}
          </select>
        )}
        <div className="flex items-center gap-2 ml-auto">
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="flex items-center gap-1 text-xs text-norn-400 hover:text-norn-300 transition-colors"
            >
              <X size={12} /> Clear filters
            </button>
          )}
          <span className="text-xs text-gray-500">{filtered.length} result{filtered.length !== 1 ? 's' : ''}</span>
        </div>
      </div>

      {/* Event List */}
      <div className="flex-1 min-h-0 bg-dark-surface/30 border border-dark-border rounded-xl overflow-hidden flex flex-col">
        {/* Table Header */}
        <div className={`flex-none grid ${GRID} gap-3 px-4 py-2 bg-dark-surface border-b border-dark-border text-[11px] font-semibold text-gray-500 uppercase tracking-wider`}>
          <span>Timestamp</span>
          <span>Type</span>
          <span>Event</span>
          <span>Agent</span>
          <span>Model</span>
          <span>Severity</span>
          <span></span>
        </div>

        {/* Rows */}
        <div className="flex-1 overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-gray-500 text-sm">No audit events found</div>
          ) : (
            filtered.map((event) => {
              const config = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.tool_call;
              const sevStyle = SEVERITY_STYLES[event.severity] || SEVERITY_STYLES.info;
              const isExpanded = expandedId === event.id;
              const Icon = config.icon;

              return (
                <div key={event.id}>
                  <div
                    onClick={() => event.detail ? setExpandedId(isExpanded ? null : event.id) : undefined}
                    className={`group grid ${GRID} gap-3 px-4 py-2.5 border-b border-dark-border/50 text-sm transition-colors ${
                      event.detail ? 'cursor-pointer hover:bg-dark-surface/50' : 'hover:bg-dark-surface/30'
                    } ${isExpanded ? 'bg-dark-surface/40' : ''}`}
                  >
                    {/* Timestamp */}
                    <span className="text-xs font-mono text-gray-500">
                      {new Date(event.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                    </span>

                    {/* Type */}
                    <span className={`flex items-center gap-1.5 text-xs font-medium ${config.color}`}>
                      <Icon size={12} />
                      {config.label}
                    </span>

                    {/* Summary */}
                    <span className="text-gray-300 text-xs truncate flex items-center gap-1.5">
                      {event.detail && (isExpanded ? <ChevronDown size={12} className="shrink-0 text-gray-500" /> : <ChevronRight size={12} className="shrink-0 text-gray-500" />)}
                      {event.summary}
                    </span>

                    {/* Agent */}
                    <span className="text-xs text-gray-400 truncate" title={event.agent_name}>{event.agent_name}</span>

                    {/* Model */}
                    <span className="text-xs text-gray-600 truncate font-mono" title={event.model || 'N/A'}>
                      {event.model || '\u2014'}
                    </span>

                    {/* Severity */}
                    <span className={`flex items-center gap-1.5 text-[11px] font-medium ${sevStyle.text}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${sevStyle.dot}`}></span>
                      {event.severity}
                    </span>

                    {/* Delete */}
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDeleteEvent(event); }}
                      title={event.event_type === 'session_start' || event.event_type === 'session_end' ? 'Delete session' : 'Delete event'}
                      className="p-1 text-gray-600 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>

                  {/* Expanded Detail */}
                  {isExpanded && event.detail && (
                    <div className="px-4 py-3 bg-dark-bg/50 border-b border-dark-border/50">
                      <div className="ml-[130px] pl-3 border-l-2 border-norn-900/30">
                        <div className="text-xs text-gray-500 uppercase tracking-wider mb-1 font-semibold">Detail</div>
                        <p className="text-xs text-gray-400 leading-relaxed whitespace-pre-wrap">{event.detail}</p>
                        <div className="mt-2 flex items-center gap-3 text-[10px] text-gray-600 font-mono">
                          <span>Session: {event.session_id}</span>
                          <button
                            onClick={(e) => { e.stopPropagation(); setFilterSession(event.session_id); }}
                            className="text-norn-500 hover:text-norn-400 underline"
                          >
                            Filter to this session
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
