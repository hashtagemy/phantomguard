import React, { useState, useEffect } from 'react';
import { ArrowLeft, Github, AlertCircle, CheckCircle2, Code, Terminal, Activity, ShieldAlert, Cpu, Microscope, Lightbulb, AlertTriangle, Play, Loader2, Pencil, BarChart3, LayoutDashboard } from 'lucide-react';
import { api } from '../services/api';
import { Session } from '../types';
import { StatusBadge } from './StatusBadge';
import { TestResultsPanel } from './panels/TestResultsPanel';
import { ExecutionStepsPanel } from './panels/ExecutionStepsPanel';
import { AIAnalysisPanel } from './panels/AIAnalysisPanel';

interface AgentDetailProps {
  agent: any;
  onBack: () => void;
  currentSession?: Session;
  onSessionStart?: (sessionId: string) => void;
}

export const AgentDetail: React.FC<AgentDetailProps> = ({ agent, onBack, currentSession, onSessionStart }) => {
  const [isRunning, setIsRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const [taskText, setTaskText] = useState<string>(agent.task_description || '');
  const [isEditingTask, setIsEditingTask] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'results' | 'steps' | 'analysis'>('overview');
  // For non-hook agents: auto-switch to steps tab when Run Agent creates a session
  const didAutoSwitch = React.useRef(false);
  useEffect(() => {
    if (agent.source !== 'hook' && currentSession?.id && !didAutoSwitch.current) {
      didAutoSwitch.current = true;
      setActiveTab('steps');
    }
  }, [currentSession?.id]);

  const handleRunAgent = async () => {
    setIsRunning(true);
    setRunError(null);

    const minDelay = new Promise(r => setTimeout(r, 800));
    try {
      const [result] = await Promise.all([api.runAgent(agent.id, taskText), minDelay]);
      onSessionStart?.(result.session_id);
    } catch (err) {
      await minDelay;
      setRunError(err instanceof Error ? err.message : 'Failed to run agent');
      setTimeout(() => setRunError(null), 4000);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="flex items-center justify-between mb-6 pb-6 border-b border-dark-border">
        <div className="flex items-center gap-4">
          <button
            onClick={onBack}
            className="p-2 rounded-lg hover:bg-dark-surface text-gray-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={20} />
          </button>
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-xl font-semibold text-white tracking-tight">{agent.name}</h2>
              <span className={`text-xs px-3 py-1 rounded-full ${
                agent.status === 'analyzed' ? 'bg-emerald-900/30 text-emerald-400' :
                agent.status === 'analyzing' ? 'bg-yellow-900/30 text-yellow-400' :
                agent.status === 'error' ? 'bg-red-900/30 text-red-400' :
                'bg-gray-800 text-gray-400'
              }`}>
                {agent.status}
              </span>
              <span className="text-xs text-gray-500 font-mono">{agent.id}</span>
            </div>
            <p className="text-gray-400 text-sm mt-1 flex items-center gap-2">
              <Github size={14} /> {agent.source === 'git' ? 'GitHub Repository' : 'ZIP Upload'}
            </p>
          </div>
        </div>
        <div className="flex gap-4">
          {agent.status === 'analyzed' && agent.source !== 'hook' && (
            <button
              onClick={handleRunAgent}
              disabled={isRunning}
              className="px-4 py-2 bg-phantom-600 hover:bg-phantom-500 text-white rounded-lg flex items-center gap-2 font-medium text-sm transition-colors disabled:cursor-not-allowed"
            >
              {isRunning
                ? <Loader2 size={15} className="animate-spin shrink-0" />
                : <Play size={15} className="shrink-0" />
              }
              Run Agent
            </button>
          )}
          <div className="text-right">
            <div className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Added</div>
            <div className="text-sm text-gray-300 font-mono">{new Date(agent.added_at).toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* Hook agent — live monitoring note */}
      {agent.source === 'hook' && (
        <div className="mb-4 p-3 bg-dark-surface/50 rounded-xl border border-dark-border flex items-center gap-2">
          <Activity size={12} className="text-phantom-500 shrink-0" />
          <p className="text-xs text-gray-500">
            Live monitoring active. Steps and reports are tracked automatically as the agent runs.
          </p>
        </div>
      )}

      {/* Test Task — only for non-hook agents */}
      {agent.status === 'analyzed' && agent.source !== 'hook' && (
        <div className="mb-4 bg-dark-surface/50 rounded-xl border border-dark-border p-4">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <Terminal size={14} className="text-phantom-500" /> Test Task
            </h3>
            <button
              onClick={() => setIsEditingTask(!isEditingTask)}
              className="text-xs text-gray-500 hover:text-phantom-400 flex items-center gap-1 transition-colors"
            >
              <Pencil size={12} /> {isEditingTask ? 'Done' : 'Edit'}
            </button>
          </div>
          {isEditingTask ? (
            <textarea
              value={taskText}
              onChange={(e) => setTaskText(e.target.value)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg p-3 text-sm text-gray-200 focus:outline-none focus:border-phantom-500 resize-none"
              rows={3}
              placeholder="Enter a test task for this agent..."
            />
          ) : (
            <p className="text-sm text-gray-300 leading-relaxed">{taskText}</p>
          )}
          <p className="text-[10px] text-gray-600 mt-2">Auto-generated based on agent capabilities. Click Edit to customize.</p>
        </div>
      )}

      {/* Error toast */}
      {runError && (
        <div className="mb-4 p-3 bg-red-900/20 border border-red-900/30 rounded-lg text-red-300 text-sm flex items-center gap-2 animate-in fade-in slide-in-from-top-2">
          <AlertCircle size={14} className="shrink-0" />
          {runError}
        </div>
      )}

      {/* Tab Bar — always visible */}
      <div className="flex gap-2 mb-6 border-b border-dark-border">
        <button
          onClick={() => setActiveTab('overview')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'overview'
              ? 'border-phantom-500 text-phantom-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <LayoutDashboard size={16} />
            Agent Overview
          </div>
        </button>
        <button
          onClick={() => setActiveTab('results')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'results'
              ? 'border-phantom-500 text-phantom-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <BarChart3 size={16} />
            Test Results
          </div>
        </button>
        <button
          onClick={() => setActiveTab('steps')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'steps'
              ? 'border-phantom-500 text-phantom-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <Terminal size={16} />
            Execution Steps{currentSession ? ` (${currentSession.steps.length})` : ''}
          </div>
        </button>
        <button
          onClick={() => setActiveTab('analysis')}
          className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 ${
            activeTab === 'analysis'
              ? 'border-phantom-500 text-phantom-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          }`}
        >
          <div className="flex items-center gap-2">
            <Cpu size={16} />
            AI Analysis
          </div>
        </button>
      </div>

      {/* Agent Overview Tab */}
      {activeTab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Code Analysis */}
          <div className="lg:col-span-2 flex flex-col bg-dark-surface/50 rounded-xl border border-dark-border overflow-hidden">
            <div className="p-4 border-b border-dark-border flex items-center justify-between bg-dark-surface">
              <h3 className="text-sm font-medium text-gray-200 flex items-center gap-2">
                <Terminal size={16} className="text-phantom-500" />
                Code Analysis
              </h3>
              <span className="text-xs text-gray-500 bg-dark-bg px-2 py-1 rounded border border-dark-border">
                {agent.discovery?.agent_type || 'Unknown Type'}
              </span>
            </div>

            <div className="p-4 space-y-6">
              {!agent.discovery ? (
                <div className="text-center py-12 text-gray-500">
                  <div className="text-lg mb-2">Analysis Pending</div>
                  <div className="text-sm">Agent analysis has not been completed yet</div>
                </div>
              ) : (
                <>
                  {/* Repository Info */}
                  <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                    <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">Repository Information</h4>
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-500">Main File:</span>
                        <span className="text-phantom-400 font-mono">{agent.main_file}</span>
                      </div>
                      {agent.source === 'git' && (
                        <>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Branch:</span>
                            <span className="text-gray-300">{agent.branch || 'main'}</span>
                          </div>
                          <div className="text-xs text-gray-500 break-all mt-2">
                            {agent.repo_url}
                          </div>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Tools */}
                  {agent.discovery.tools && agent.discovery.tools.length > 0 && (
                    <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">
                        Discovered Tools ({agent.discovery.tools.length})
                      </h4>
                      <div className="space-y-3">
                        {agent.discovery.tools.map((tool: any, idx: number) => (
                          <div key={idx} className="bg-dark-surface border border-dark-border rounded-lg p-3">
                            <div className="text-sm font-semibold text-phantom-400 mb-1">{tool.name}</div>
                            <div className="text-xs text-gray-400 mb-2">{tool.description}</div>
                            {tool.parameters && tool.parameters.length > 0 && (
                              <div className="flex flex-wrap gap-1">
                                {tool.parameters.map((param: string, pidx: number) => (
                                  <span key={pidx} className="text-xs px-2 py-0.5 bg-dark-bg rounded font-mono text-gray-500">
                                    {param}
                                  </span>
                                ))}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Dependencies */}
                  {agent.discovery.dependencies && agent.discovery.dependencies.length > 0 && (
                    <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">Dependencies</h4>
                      <div className="grid grid-cols-2 gap-2">
                        {agent.discovery.dependencies.map((dep: any, idx: number) => (
                          <div key={idx} className="flex items-center gap-2 text-xs">
                            {dep.status === 'installed' ? (
                              <CheckCircle2 size={12} className="text-emerald-400" />
                            ) : (
                              <AlertCircle size={12} className="text-red-400" />
                            )}
                            <span className={`font-mono ${
                              dep.status === 'installed' ? 'text-gray-400' : 'text-red-400'
                            }`}>
                              {dep.name}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Imports */}
                  {agent.discovery.imports && agent.discovery.imports.length > 0 && (
                    <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">
                        Imports ({agent.discovery.imports.length})
                      </h4>
                      <div className="flex flex-wrap gap-2">
                        {agent.discovery.imports.map((imp: string, idx: number) => (
                          <span key={idx} className="text-xs px-2 py-1 bg-dark-surface rounded font-mono text-gray-400">
                            {imp}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Entry Points */}
                  {agent.discovery.entry_points && agent.discovery.entry_points.length > 0 && (
                    <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
                      <h4 className="text-xs font-semibold text-gray-400 uppercase mb-3">Entry Points</h4>
                      <div className="flex flex-wrap gap-2">
                        {agent.discovery.entry_points.map((entry: string, idx: number) => (
                          <span key={idx} className="text-xs px-2 py-1 bg-emerald-900/20 text-emerald-300 rounded font-mono">
                            {entry}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Right Column: Metrics & Issues */}
          <div className="flex flex-col gap-6">
            {/* Score Cards */}
            <div className="grid grid-cols-2 gap-4">
              <div className="bg-dark-surface/50 p-4 rounded-xl border border-dark-border">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium uppercase mb-2">
                  <Code size={14} /> Tools
                </div>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-phantom-500">
                    {agent.discovery?.tools?.length || 0}
                  </span>
                </div>
              </div>
              <div className="bg-dark-surface/50 p-4 rounded-xl border border-dark-border">
                <div className="flex items-center gap-2 text-gray-400 text-xs font-medium uppercase mb-2">
                  <Activity size={14} /> Functions
                </div>
                <div className="flex items-end gap-2">
                  <span className="text-3xl font-bold text-blue-500">
                    {agent.discovery?.functions?.length || 0}
                  </span>
                </div>
              </div>
            </div>

            {/* Issues Detected */}
            <div className="bg-dark-surface/50 rounded-xl border border-dark-border overflow-hidden">
              <div className="p-3 bg-dark-surface border-b border-dark-border">
                <h3 className="text-sm font-medium text-gray-200 flex items-center gap-2">
                  <ShieldAlert size={16} /> Potential Issues
                </h3>
              </div>
              <div className="p-4">
                {!agent.discovery?.potential_issues || agent.discovery.potential_issues.length === 0 ? (
                  <div className="text-center py-4 text-gray-500 flex flex-col items-center">
                    <CheckCircle2 size={32} className="text-emerald-900 mb-2" />
                    <span className="text-sm">No issues detected</span>
                  </div>
                ) : (
                  <div className="space-y-2">
                    {agent.discovery.potential_issues.map((issue: any, idx: number) => (
                      <div key={idx} className={`flex items-start gap-3 p-2 rounded border text-sm ${
                        issue.severity === 'HIGH' ? 'bg-red-950/20 border-red-900/30 text-red-300' :
                        issue.severity === 'MEDIUM' ? 'bg-yellow-950/20 border-yellow-900/30 text-yellow-300' :
                        'bg-blue-950/20 border-blue-900/30 text-blue-300'
                      }`}>
                        <AlertTriangle size={16} className="shrink-0 mt-0.5" />
                        <div>
                          <div className="font-medium">{issue.type}</div>
                          <div className="text-xs opacity-80 mt-0.5">{issue.description}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* AI Analysis Summary */}
            <div className="bg-gradient-to-b from-phantom-900/20 to-dark-surface rounded-xl border border-phantom-900/30 overflow-hidden flex-1 flex flex-col">
              <div className="p-3 border-b border-phantom-900/30 bg-phantom-900/10 flex items-center justify-between">
                <h3 className="text-sm font-medium text-phantom-300 flex items-center gap-2">
                  <Cpu size={16} /> Analysis Summary
                </h3>
                <span className="text-[10px] uppercase tracking-wider text-phantom-400/70 border border-phantom-500/20 px-2 py-0.5 rounded">Auto Generated</span>
              </div>

              <div className="p-5 space-y-6 overflow-y-auto">
                <div>
                  <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                    <Microscope size={14} className="text-blue-400" /> Code Analysis
                  </h4>
                  <p className="text-sm text-gray-300 leading-relaxed mb-3">
                    {agent.task_description}
                  </p>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between p-2 bg-dark-bg/50 rounded">
                      <span className="text-gray-400">Agent Type:</span>
                      <span className="text-gray-300 font-medium">{agent.discovery?.agent_type || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between p-2 bg-dark-bg/50 rounded">
                      <span className="text-gray-400">Status:</span>
                      <span className={`font-medium ${
                        agent.status === 'analyzed' ? 'text-emerald-400' :
                        agent.status === 'analyzing' ? 'text-yellow-400' :
                        'text-gray-400'
                      }`}>{agent.status}</span>
                    </div>
                    {agent.discovery?.imports && (
                      <div className="flex justify-between p-2 bg-dark-bg/50 rounded">
                        <span className="text-gray-400">Imports:</span>
                        <span className="text-gray-300 font-medium">{agent.discovery.imports.length} modules</span>
                      </div>
                    )}
                  </div>
                </div>

                {agent.discovery?.potential_issues && agent.discovery.potential_issues.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                      <Lightbulb size={14} className="text-yellow-400" /> Recommendations
                    </h4>
                    <ul className="space-y-2">
                      {agent.discovery.potential_issues.map((issue: any, idx: number) => (
                        <li key={idx} className="flex gap-2 text-sm text-gray-300 bg-dark-bg/50 p-2 rounded border border-dark-border/50">
                          <span className="text-phantom-500">•</span>
                          Fix {issue.type}: {issue.description}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Monitoring Tabs — session required */}
      {activeTab !== 'overview' && (
        <div>
          {!currentSession ? (
            <div className="py-16 text-center text-gray-500">
              <Activity size={32} className="mx-auto mb-3 opacity-30" />
              <p className="text-sm">No session yet. Run the agent to see results here.</p>
            </div>
          ) : (
            <>
              {/* Session header */}
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <StatusBadge status={currentSession.status} />
                  {currentSession.status === 'completed' && (
                    <span className="text-xs text-gray-500">
                      Completed: {new Date(currentSession.startTime).toLocaleString()}
                    </span>
                  )}
                </div>
                <span className="text-xs text-gray-600 font-mono">{currentSession.id}</span>
              </div>

              {activeTab === 'results' && <TestResultsPanel session={currentSession} />}
              {activeTab === 'steps' && <ExecutionStepsPanel session={currentSession} />}
              {activeTab === 'analysis' && <AIAnalysisPanel session={currentSession} />}
            </>
          )}
        </div>
      )}
    </div>
  );
};
