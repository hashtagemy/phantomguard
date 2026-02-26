import React, { useState, useEffect } from 'react';
import { Session } from '../types';
import { Shield, Zap, AlertOctagon, Activity, Github, ChevronRight, Trash2 } from 'lucide-react';
import { api } from '../services/api';

interface DashboardProps {
  sessions: Session[];
  onSelectSession: (id: string) => void;
  onSelectAgent?: (agentId: string) => void;
}

export const Dashboard: React.FC<DashboardProps> = ({ sessions, onSelectSession, onSelectAgent }) => {
  const [agents, setAgents] = useState<any[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(true);

  useEffect(() => {
    loadAgents();
  }, []);

  const loadAgents = async () => {
    try {
      const data = await api.getAgents();
      // Sort by added_at descending (newest first)
      const sorted = data.sort((a, b) => 
        new Date(b.added_at).getTime() - new Date(a.added_at).getTime()
      );
      setAgents(sorted);
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      setLoadingAgents(false);
    }
  };

  const handleDeleteAgent = async (agentId: string, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click
    
    if (!confirm('Are you sure you want to delete this agent?')) {
      return;
    }

    try {
      await api.deleteAgent(agentId);
      // Reload agents list
      await loadAgents();
    } catch (err) {
      console.error('Failed to delete agent:', err);
      alert('Failed to delete agent');
    }
  };

  // Calculate aggregates from real data — filter out sessions with null (unevaluated) scores
  const totalSessions = sessions.length;
  const totalAgents = agents.length;
  const evaluatedSessions = sessions.filter(s => s.securityScore != null);
  const evaluatedEfficiency = sessions.filter(s => s.efficiencyScore != null);
  const criticalThreats = evaluatedSessions.reduce((acc, s) => acc + ((s.securityScore ?? 100) < 70 ? 1 : 0), 0);
  const avgEfficiency = evaluatedEfficiency.length > 0
    ? Math.round(evaluatedEfficiency.reduce((acc, s) => acc + (s.efficiencyScore ?? 0), 0) / evaluatedEfficiency.length)
    : null;
  const securityPassRate = evaluatedSessions.length > 0
    ? Math.round((evaluatedSessions.filter(s => (s.securityScore ?? 0) >= 70).length / evaluatedSessions.length) * 1000) / 10
    : null;
  const avgSecurity = evaluatedSessions.length > 0
    ? Math.round(evaluatedSessions.reduce((acc, s) => acc + (s.securityScore ?? 0), 0) / evaluatedSessions.length * 10) / 10
    : null;

  const filteredAgents = agents;

  return (
    <div className="flex flex-col h-full space-y-4 animate-in fade-in duration-700">
      
      {/* Header Text & KPI */}
      <div className="flex-none space-y-4">
        <div>
          <h1 className="text-xl font-bold text-white tracking-tight">Monitoring Overview</h1>
          <p className="text-sm text-gray-400">Real-time insights across {totalSessions} session{totalSessions !== 1 ? 's' : ''} and {totalAgents} agent{totalAgents !== 1 ? 's' : ''}.</p>
        </div>

        {/* KPI Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          
          <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-phantom-900/30 rounded-lg text-phantom-400">
                  <Activity size={16} />
                </div>
                <span className="text-xs font-medium text-gray-400">Active Sessions</span>
              </div>
              {totalSessions > 0 && (
                <span className="text-[10px] text-phantom-400 font-medium bg-phantom-950/50 px-1.5 py-0.5 rounded">Live</span>
              )}
            </div>
            <div className="text-2xl font-bold text-white mb-0.5 pl-1">{totalSessions}</div>
          </div>

          <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-red-900/30 rounded-lg text-red-400">
                  <AlertOctagon size={16} />
                </div>
                <span className="text-xs font-medium text-gray-400">Critical Threats</span>
              </div>
              {criticalThreats > 0 && (
                <span className="text-[10px] text-red-400 font-medium bg-red-950/50 px-1.5 py-0.5 rounded animate-pulse">Action Req.</span>
              )}
            </div>
            <div className="text-2xl font-bold text-white mb-0.5 pl-1">{criticalThreats}</div>
          </div>

          <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-emerald-900/30 rounded-lg text-emerald-400">
                  <Shield size={16} />
                </div>
                <span className="text-xs font-medium text-gray-400">Security Pass Rate</span>
              </div>
            </div>
            <div className="text-2xl font-bold text-white mb-0.5 pl-1">{securityPassRate != null ? `${securityPassRate}%` : 'N/A'}</div>
          </div>

          <div className="bg-dark-surface border border-dark-border p-3 rounded-xl">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <div className="p-1.5 bg-blue-900/30 rounded-lg text-blue-400">
                  <Zap size={16} />
                </div>
                <span className="text-xs font-medium text-gray-400">Avg Efficiency</span>
              </div>
            </div>
            <div className="text-2xl font-bold text-white mb-0.5 pl-1">{avgEfficiency != null ? `${avgEfficiency}%` : 'N/A'}</div>
          </div>

        </div>
      </div>

      {/* Session List replacing the Chart */}
      <div className="flex-1 min-h-0 bg-dark-surface/30 border border-dark-border rounded-xl overflow-hidden flex flex-col p-3">
        <div className="flex items-center justify-between mb-3 px-2">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Monitoring Activity</h3>
          
          <span className="text-xs text-gray-600">
            {totalAgents} agent{totalAgents !== 1 ? 's' : ''} • {totalSessions} session{totalSessions !== 1 ? 's' : ''}
          </span>
        </div>

        {/* Combined List */}
        <div className="flex-1 min-h-0 overflow-y-auto space-y-2 pr-1">
          {/* Agents */}
          {filteredAgents.map((agent) => (
            <div 
              key={agent.id}
              onClick={() => onSelectAgent && onSelectAgent(agent.id)}
              className="px-4 py-4 bg-dark-surface/50 hover:bg-dark-surface rounded-lg border border-dark-border hover:border-phantom-900/50 cursor-pointer transition-all group"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 space-y-3">
                  {/* Header */}
                  <div className="flex items-center gap-3">
                    <Github size={18} className="text-phantom-400 shrink-0" />
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-semibold text-gray-100 group-hover:text-phantom-300 transition-colors">{agent.name}</span>
                        <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                          agent.status === 'analyzed' ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-900/50' :
                          agent.status === 'analyzing' ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-900/50' :
                          agent.status === 'completed' ? 'bg-blue-900/30 text-blue-400 border border-blue-900/50' :
                          agent.status === 'error' ? 'bg-red-900/30 text-red-400 border border-red-900/50' :
                          'bg-gray-800 text-gray-400 border border-gray-700'
                        }`}>
                          {agent.status === 'analyzed' ? '✓ Ready' : 
                           agent.status === 'analyzing' ? '⟳ Analyzing' :
                           agent.status === 'completed' ? '✓ Tested' :
                           agent.status}
                        </span>
                      </div>
                      <div className="text-xs text-gray-500">{agent.task_description}</div>
                    </div>
                  </div>
                  
                  {/* Analysis Results */}
                  {agent.discovery && (
                    <div className="grid grid-cols-2 gap-3">
                      {/* Left: Capabilities */}
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Capabilities</div>
                        <div className="flex flex-wrap gap-2">
                          <span className="text-xs px-2 py-1 rounded bg-phantom-950/30 text-phantom-400 border border-phantom-900/30">
                            {agent.discovery.tools?.length || 0} Tools
                          </span>
                          <span className="text-xs px-2 py-1 rounded bg-blue-950/30 text-blue-400 border border-blue-900/30">
                            {agent.discovery.functions?.length || 0} Functions
                          </span>
                          <span className="text-xs px-2 py-1 rounded bg-gray-800 text-gray-400 border border-gray-700">
                            {agent.discovery.agent_type || 'Unknown'}
                          </span>
                        </div>
                      </div>
                      
                      {/* Right: Health Status */}
                      <div className="space-y-1.5">
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider font-semibold">Health Status</div>
                        <div className="flex flex-wrap gap-2">
                          {(() => {
                            const issues = agent.discovery.potential_issues || [];
                            const highIssues = issues.filter(i => i.severity === 'HIGH').length;
                            const mediumIssues = issues.filter(i => i.severity === 'MEDIUM').length;
                            const lowIssues = issues.filter(i => i.severity === 'LOW').length;
                            
                            if (issues.length === 0) {
                              return (
                                <span className="text-xs px-2 py-1 rounded bg-emerald-950/30 text-emerald-400 border border-emerald-900/30">
                                  ✓ All Checks Passed
                                </span>
                              );
                            }
                            
                            return (
                              <>
                                {highIssues > 0 && (
                                  <span className="text-xs px-2 py-1 rounded bg-red-950/30 text-red-400 border border-red-900/30">
                                    {highIssues} Critical
                                  </span>
                                )}
                                {mediumIssues > 0 && (
                                  <span className="text-xs px-2 py-1 rounded bg-yellow-950/30 text-yellow-400 border border-yellow-900/30">
                                    {mediumIssues} Warning
                                  </span>
                                )}
                                {lowIssues > 0 && (
                                  <span className="text-xs px-2 py-1 rounded bg-blue-950/30 text-blue-400 border border-blue-900/30">
                                    {lowIssues} Info
                                  </span>
                                )}
                              </>
                            );
                          })()}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
                
                {/* Actions */}
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-xs text-gray-500">{new Date(agent.added_at).toLocaleDateString()}</span>
                  <button
                    onClick={(e) => handleDeleteAgent(agent.id, e)}
                    className="p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-900/20 rounded transition-colors opacity-0 group-hover:opacity-100"
                    title="Delete agent"
                  >
                    <Trash2 size={14} />
                  </button>
                  <ChevronRight size={14} className="text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </div>
            </div>
          ))}


          {/* Empty State */}
          {filteredAgents.length === 0 && (
            <div className="text-center py-12 text-gray-500">
              <div className="text-sm">No agents yet</div>
              <div className="text-xs mt-1">Import an agent to get started</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
