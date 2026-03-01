import React, { useEffect, useState } from 'react';
import { Network, ChevronDown, ChevronRight, AlertTriangle, CheckCircle, Clock, ArrowDown, MessageSquare, Cpu, Microscope, Brain, Lightbulb, GitMerge, Zap } from 'lucide-react';
import { api } from '../services/api';

interface SwarmAgent {
  session_id: string;
  agent_name: string;
  swarm_order: number | null;
  overall_quality: string;
  efficiency_score: number | null;
  security_score: number | null;
  task: string;
  status: string;
  total_steps: number;
  handoff_input?: string | null;
}

interface Swarm {
  swarm_id: string;
  agent_count: number;
  overall_quality: string;
  started_at: string;
  ended_at: string;
  agents: SwarmAgent[];
}

interface SwarmAnalysis {
  swarm_id: string;
  summary: string;
  agent_assessments: { agent_name: string; order: number; note: string }[];
  handoff_quality: string;
  pipeline_coherence: string;
  recommendations: string[];
}

const qualityColor = (q: string) => {
  switch (q) {
    case 'EXCELLENT': return 'text-emerald-400 bg-emerald-950/40 border-emerald-900/50';
    case 'GOOD':      return 'text-blue-400 bg-blue-950/40 border-blue-900/50';
    case 'POOR':      return 'text-yellow-400 bg-yellow-950/40 border-yellow-900/50';
    case 'FAILED':    return 'text-red-400 bg-red-950/40 border-red-900/50';
    case 'STUCK':     return 'text-orange-400 bg-orange-950/40 border-orange-900/50';
    default:          return 'text-gray-400 bg-gray-900/40 border-gray-800/50';
  }
};

// Collapsible handoff data bubble shown between two agents
const HandoffConnector: React.FC<{ data: string }> = ({ data }) => {
  const [expanded, setExpanded] = useState(false);
  const isLong = data.length > 160;

  return (
    <div className="flex flex-col items-center w-full">
      <div className="w-px h-3 bg-phantom-900/40" />
      <div className="w-full pl-9 pr-0">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full text-left bg-phantom-950/20 border border-phantom-900/30 rounded-lg px-3 py-2.5 hover:bg-phantom-950/30 transition-colors group"
        >
          <div className="flex items-center gap-2 mb-1.5">
            <MessageSquare size={11} className="text-phantom-400 flex-shrink-0" />
            <span className="text-[10px] font-semibold text-phantom-400 uppercase tracking-wider">
              Handoff
            </span>
            {isLong && (
              <span className="ml-auto text-[10px] text-gray-600 group-hover:text-gray-400 transition-colors">
                {expanded ? 'collapse ▲' : 'expand ▼'}
              </span>
            )}
          </div>
          <p className={`text-xs text-gray-400 leading-relaxed whitespace-pre-wrap break-words ${!expanded && isLong ? 'line-clamp-3' : ''}`}>
            {data}
          </p>
        </button>
      </div>
      <div className="w-px h-3 bg-phantom-900/40" />
      <ArrowDown size={10} className="text-phantom-700" />
    </div>
  );
};

const SimpleConnector: React.FC = () => (
  <div className="flex flex-col items-center">
    <div className="w-px h-3 bg-phantom-900/40" />
    <ArrowDown size={10} className="text-phantom-700" />
  </div>
);

// AI Analysis panel for a swarm — mirrors the style of AIAnalysisPanel.tsx
const SwarmAnalysisPanel: React.FC<{ swarmId: string }> = ({ swarmId }) => {
  const [analysis, setAnalysis] = useState<SwarmAnalysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getSwarmAnalysis(swarmId)
      .then(setAnalysis)
      .catch(e => setError(e instanceof Error ? e.message : 'Analysis failed'))
      .finally(() => setLoading(false));
  }, [swarmId]);

  if (loading) {
    return (
      <div className="bg-gradient-to-b from-phantom-900/20 to-dark-surface rounded-lg border border-phantom-900/30 p-4">
        <p className="text-xs text-gray-500 animate-pulse">Analyzing pipeline...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-4">
        <p className="text-xs text-red-400">{error}</p>
      </div>
    );
  }

  if (!analysis) return null;

  const coherenceColor =
    analysis.pipeline_coherence === 'EXCELLENT' ? 'text-emerald-400' :
    analysis.pipeline_coherence === 'GOOD' ? 'text-blue-400' :
    'text-yellow-400';

  return (
    <div className="space-y-3">
      <div className="bg-gradient-to-b from-phantom-900/20 to-dark-surface rounded-lg border border-phantom-900/30 overflow-hidden">
        <div className="p-3 border-b border-phantom-900/30 bg-phantom-900/10 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-phantom-300 flex items-center gap-2">
            <Cpu size={13} /> Amazon Nova AI Evaluation
          </h3>
          <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border text-phantom-400/70 border-phantom-500/20">
            AI Generated
          </span>
        </div>

        <div className="p-4 space-y-4">

          {/* Summary */}
          <div>
            <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Microscope size={12} className="text-blue-400" /> Pipeline Analysis
            </h4>
            <p className="text-xs text-gray-300 leading-relaxed bg-dark-bg/50 p-3 rounded-lg border border-dark-border/50">
              {analysis.summary}
            </p>
          </div>

          {/* Per-agent assessments */}
          {analysis.agent_assessments && analysis.agent_assessments.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Brain size={12} className="text-purple-400" /> Agent Assessments
              </h4>
              <ul className="space-y-1.5">
                {analysis.agent_assessments.map((a, idx) => (
                  <li key={idx} className="p-2 rounded-lg border bg-dark-bg/50 border-dark-border/50">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span className="w-4 h-4 rounded-full bg-phantom-950/60 border border-phantom-900/50 flex items-center justify-center flex-shrink-0">
                        <span className="text-[9px] font-bold text-phantom-300">{a.order}</span>
                      </span>
                      <span className="text-xs font-medium text-gray-200">{a.agent_name}</span>
                    </div>
                    <p className="text-[10px] text-gray-400 leading-relaxed pl-6">{a.note}</p>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Handoff quality */}
          {analysis.handoff_quality && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <GitMerge size={12} className="text-cyan-400" /> Handoff Quality
              </h4>
              <p className="text-[10px] text-gray-300 leading-relaxed bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50">
                {analysis.handoff_quality}
              </p>
            </div>
          )}

          {/* Pipeline coherence */}
          {analysis.pipeline_coherence && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Zap size={12} className="text-orange-400" /> Pipeline Coherence
              </h4>
              <p className={`text-xs font-semibold bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50 ${coherenceColor}`}>
                {analysis.pipeline_coherence}
              </p>
            </div>
          )}

          {/* Recommendations */}
          {analysis.recommendations && analysis.recommendations.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Lightbulb size={12} className="text-yellow-400" /> Recommended Actions
              </h4>
              <ul className="space-y-1.5">
                {analysis.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex gap-2 text-xs text-gray-300 bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50">
                    <span className="text-phantom-500 flex-shrink-0">&bull;</span>
                    <span>{rec}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

        </div>
      </div>
    </div>
  );
};

const SwarmCard: React.FC<{ swarm: Swarm; onSelectSession?: (id: string) => void }> = ({ swarm, onSelectSession }) => {
  const [expanded, setExpanded] = useState(false);
  const [activeTab, setActiveTab] = useState<'pipeline' | 'analysis'>('pipeline');

  return (
    <div className="bg-dark-surface border border-dark-border rounded-xl overflow-hidden">
      {/* Header */}
      <button
        className="w-full flex items-center gap-4 px-5 py-4 hover:bg-dark-hover transition-colors text-left"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="w-9 h-9 rounded-lg bg-phantom-950/40 border border-phantom-900/40 flex items-center justify-center flex-shrink-0">
          <Network size={18} className="text-phantom-400" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-semibold text-gray-100 truncate">{swarm.swarm_id}</span>
            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${qualityColor(swarm.overall_quality)}`}>
              {swarm.overall_quality}
            </span>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500">
            <span>{swarm.agent_count} agents</span>
            {swarm.started_at && (
              <>
                <span>·</span>
                <span>{new Date(swarm.started_at).toLocaleString()}</span>
              </>
            )}
          </div>
        </div>

        {expanded
          ? <ChevronDown size={16} className="text-gray-500 flex-shrink-0" />
          : <ChevronRight size={16} className="text-gray-500 flex-shrink-0" />
        }
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="border-t border-dark-border">

          {/* Tab bar */}
          <div className="flex border-b border-dark-border px-5">
            <button
              onClick={() => setActiveTab('pipeline')}
              className={`py-2.5 px-1 mr-6 text-xs font-medium border-b-2 transition-colors ${
                activeTab === 'pipeline'
                  ? 'border-phantom-400 text-phantom-300'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              Agent Pipeline
            </button>
            <button
              onClick={() => setActiveTab('analysis')}
              className={`py-2.5 px-1 text-xs font-medium border-b-2 transition-colors flex items-center gap-1.5 ${
                activeTab === 'analysis'
                  ? 'border-phantom-400 text-phantom-300'
                  : 'border-transparent text-gray-500 hover:text-gray-300'
              }`}
            >
              <Cpu size={11} />
              AI Analysis
            </button>
          </div>

          {/* Agent Pipeline tab */}
          {activeTab === 'pipeline' && (
            <div className="px-5 py-4">
              <div className="flex flex-col">
                {swarm.agents.map((agent, idx) => (
                  <React.Fragment key={agent.session_id}>
                    <div className="flex items-start gap-3">
                      <div className="flex flex-col items-center flex-shrink-0 pt-1 w-6">
                        <div className="w-6 h-6 rounded-full bg-phantom-950/60 border border-phantom-900/50 flex items-center justify-center">
                          <span className="text-xs font-bold text-phantom-300">{agent.swarm_order ?? idx + 1}</span>
                        </div>
                      </div>

                      <div
                        className={`flex-1 bg-dark-bg border border-dark-border rounded-lg px-4 py-3 ${onSelectSession && agent.session_id ? 'cursor-pointer hover:border-phantom-700 hover:bg-dark-surface transition-colors' : ''}`}
                        onClick={() => onSelectSession && agent.session_id && onSelectSession(agent.session_id)}
                      >
                        <div className="flex items-center justify-between gap-3 mb-1">
                          <span className="text-sm font-medium text-gray-200">{agent.agent_name}</span>
                          <div className="flex items-center gap-2 flex-shrink-0">
                            <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ${qualityColor(agent.overall_quality)}`}>
                              {agent.overall_quality}
                            </span>
                            {agent.status === 'running' && (
                              <span className="flex items-center gap-1 text-xs text-phantom-400">
                                <span className="animate-ping w-1.5 h-1.5 rounded-full bg-phantom-400 inline-block" />
                                Running
                              </span>
                            )}
                          </div>
                        </div>

                        {agent.task && (
                          <p className="text-xs text-gray-400 mb-2 line-clamp-2">{agent.task}</p>
                        )}

                        <div className="flex items-center gap-4 text-xs text-gray-500">
                          <span>{agent.total_steps} steps</span>
                          {agent.efficiency_score != null && (
                            <span className="flex items-center gap-1">
                              <CheckCircle size={11} className="text-blue-400" />
                              Eff {agent.efficiency_score}%
                            </span>
                          )}
                          {agent.security_score != null && (
                            <span className={`flex items-center gap-1 ${agent.security_score < 70 ? 'text-red-400' : 'text-gray-500'}`}>
                              {agent.security_score < 70 && <AlertTriangle size={11} />}
                              Sec {agent.security_score}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>

                    {idx < swarm.agents.length - 1 && (
                      <div className="flex items-start gap-3 py-0.5">
                        <div className="w-6 flex-shrink-0 flex justify-center">
                          <div className="w-px bg-phantom-900/40 h-full min-h-[8px]" />
                        </div>
                        <div className="flex-1 -mt-0.5">
                          {swarm.agents[idx + 1].handoff_input
                            ? <HandoffConnector data={swarm.agents[idx + 1].handoff_input!} />
                            : <SimpleConnector />
                          }
                        </div>
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}

          {/* AI Analysis tab */}
          {activeTab === 'analysis' && (
            <div className="px-5 py-4">
              <SwarmAnalysisPanel swarmId={swarm.swarm_id} />
            </div>
          )}

        </div>
      )}
    </div>
  );
};

export const SwarmView: React.FC<{ onSelectSession?: (id: string) => void }> = ({ onSelectSession }) => {
  const [swarms, setSwarms] = useState<Swarm[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadSwarms = async () => {
    try {
      const data = await api.getSwarms();
      setSwarms(data);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load swarms');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSwarms();
    const interval = setInterval(loadSwarms, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-gray-100">Swarm Monitor</h1>
          <p className="text-sm text-gray-500 mt-1">
            Multi-agent pipelines — inter-agent collaboration and pipeline analysis
          </p>
        </div>
        <button
          onClick={loadSwarms}
          className="flex items-center gap-2 px-3 py-1.5 text-xs text-gray-400 hover:text-gray-200 bg-dark-surface border border-dark-border rounded-lg transition-colors"
        >
          <Clock size={13} />
          Refresh
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16 text-gray-500 text-sm">
          Loading swarms...
        </div>
      ) : error ? (
        <div className="bg-red-950/20 border border-red-900/30 rounded-xl p-6 text-center">
          <p className="text-red-400 text-sm">{error}</p>
        </div>
      ) : swarms.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-dark-surface border border-dark-border flex items-center justify-center mb-4">
            <Network size={28} className="text-gray-600" />
          </div>
          <h3 className="text-base font-medium text-gray-400 mb-2">No swarms yet</h3>
          <p className="text-sm text-gray-600 max-w-sm">
            Use <code className="bg-dark-surface px-1.5 py-0.5 rounded text-phantom-300">swarm_id</code> in{' '}
            <code className="bg-dark-surface px-1.5 py-0.5 rounded text-phantom-300">NornHook</code> to group
            multiple agents into a monitored pipeline.
          </p>
          <pre className="mt-4 text-left text-xs bg-dark-surface border border-dark-border rounded-lg p-4 text-gray-400 max-w-sm">
{`hook_a = NornHook(
  swarm_id="my-pipeline",
  swarm_order=1,
  agent_name="Researcher"
)
result = agent_a("Research AI trends")

hook_b = NornHook(
  swarm_id="my-pipeline",
  swarm_order=2,
  agent_name="Writer",
  handoff_input=str(result)[:500]
)`}
          </pre>
        </div>
      ) : (
        <div className="space-y-3">
          {swarms.map(swarm => (
            <SwarmCard key={swarm.swarm_id} swarm={swarm} onSelectSession={onSelectSession} />
          ))}
        </div>
      )}
    </div>
  );
};
