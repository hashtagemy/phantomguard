import React from 'react';
import { Session } from '../../types';
import { Cpu, Microscope, Lightbulb, AlertCircle, AlertTriangle, Info, XCircle, Wrench, Brain, Zap } from 'lucide-react';

interface AIAnalysisPanelProps {
  session: Session;
}

export const AIAnalysisPanel: React.FC<AIAnalysisPanelProps> = ({ session }) => {
  const isTerminated = session.status === 'terminated';
  const isActive = session.status === 'active';
  const hasAiEval = !!(session.detailedAnalysis || session.aiEvaluation);
  const hasIssues = session.issueDetails && session.issueDetails.length > 0;

  const renderAnalysisContent = () => {
    if (hasAiEval) {
      return (
        <p className="text-xs text-gray-300 leading-relaxed bg-dark-bg/50 p-3 rounded-lg border border-dark-border/50">
          {session.detailedAnalysis || session.aiEvaluation}
        </p>
      );
    }
    if (isActive) {
      return (
        <p className="text-xs text-gray-500 leading-relaxed bg-dark-bg/50 p-3 rounded-lg border border-dark-border/50 animate-pulse">
          AI analysis is being generated...
        </p>
      );
    }
    if (isTerminated) {
      return (
        <div className="bg-red-950/20 border border-red-900/30 rounded-lg p-3 flex items-start gap-2">
          <XCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
          <p className="text-xs text-red-300 leading-relaxed">
            AI evaluation could not be completed — execution was terminated before analysis ran.
            {hasIssues && ' See the issues below for details.'}
          </p>
        </div>
      );
    }
    return (
      <p className="text-xs text-gray-500 leading-relaxed bg-dark-bg/50 p-3 rounded-lg border border-dark-border/50">
        No AI evaluation available for this session.
      </p>
    );
  };

  return (
    <div className="space-y-3">
      <div className="bg-gradient-to-b from-phantom-900/20 to-dark-surface rounded-lg border border-phantom-900/30 overflow-hidden">
        <div className="p-3 border-b border-phantom-900/30 bg-phantom-900/10 flex items-center justify-between">
          <h3 className="text-xs font-semibold text-phantom-300 flex items-center gap-2">
            <Cpu size={13} /> Amazon Nova AI Evaluation
          </h3>
          <span className={`text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border ${
            isTerminated && !hasAiEval
              ? 'text-red-400/70 border-red-500/20'
              : 'text-phantom-400/70 border-phantom-500/20'
          }`}>
            {isTerminated && !hasAiEval ? 'Terminated' : 'AI Generated'}
          </span>
        </div>

        <div className="p-4 space-y-4">
          {/* Analysis */}
          <div>
            <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Microscope size={12} className="text-blue-400"/> Detailed Analysis
            </h4>
            {renderAnalysisContent()}
          </div>

          {/* Issues — show when terminated with no AI eval */}
          {isTerminated && hasIssues && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertCircle size={12} className="text-red-400"/> Execution Issues
              </h4>
              <ul className="space-y-1.5">
                {session.issueDetails.map((issue, idx) => (
                  <li key={issue.issueId || idx} className={`flex gap-2 p-2 rounded-lg border ${
                    issue.severity >= 8 ? 'bg-red-950/20 border-red-900/30' :
                    issue.severity >= 5 ? 'bg-yellow-950/20 border-yellow-900/30' :
                    'bg-blue-950/20 border-blue-900/30'
                  }`}>
                    {issue.severity >= 8 ? (
                      <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
                    ) : issue.severity >= 5 ? (
                      <AlertTriangle size={13} className="text-yellow-400 shrink-0 mt-0.5" />
                    ) : (
                      <Info size={13} className="text-blue-400 shrink-0 mt-0.5" />
                    )}
                    <div>
                      <div className={`text-xs font-medium ${
                        issue.severity >= 8 ? 'text-red-300' :
                        issue.severity >= 5 ? 'text-yellow-300' :
                        'text-blue-300'
                      }`}>
                        {issue.issueType.replace(/_/g, ' ')}
                      </div>
                      <div className="text-[10px] text-gray-400 mt-0.5">{issue.description}</div>
                      {issue.recommendation && (
                        <div className="text-[10px] text-gray-500 mt-0.5 italic">{issue.recommendation}</div>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Tool Analysis */}
          {session.toolAnalysis && session.toolAnalysis.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Wrench size={12} className="text-cyan-400"/> Tool Usage Analysis
              </h4>
              <ul className="space-y-1.5">
                {session.toolAnalysis.map((t, idx) => {
                  const usageColor =
                    t.usage === 'correct' ? 'text-green-400' :
                    t.usage === 'incorrect' ? 'text-red-400' :
                    'text-yellow-400';
                  const usageBg =
                    t.usage === 'correct' ? 'bg-green-950/20 border-green-900/30' :
                    t.usage === 'incorrect' ? 'bg-red-950/20 border-red-900/30' :
                    'bg-yellow-950/20 border-yellow-900/30';
                  return (
                    <li key={idx} className={`p-2 rounded-lg border ${usageBg}`}>
                      <div className="flex items-center gap-2 mb-0.5">
                        <code className="text-[10px] font-mono text-gray-200">{t.tool}</code>
                        <span className={`text-[9px] uppercase font-semibold tracking-wider ${usageColor}`}>{t.usage}</span>
                      </div>
                      <p className="text-[10px] text-gray-400 leading-relaxed">{t.note}</p>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}

          {/* Decision Observations */}
          {session.decisionObservations && session.decisionObservations.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Brain size={12} className="text-purple-400"/> Decision Making
              </h4>
              <ul className="space-y-1.5">
                {session.decisionObservations.map((obs, idx) => (
                  <li key={idx} className="flex gap-2 text-[10px] text-gray-300 bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50 leading-relaxed">
                    <span className="text-purple-500 shrink-0 mt-0.5">&bull;</span>
                    <span>{obs}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Efficiency Explanation */}
          {session.efficiencyExplanation && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Zap size={12} className="text-orange-400"/> Efficiency
              </h4>
              <p className="text-[10px] text-gray-300 leading-relaxed bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50">
                {session.efficiencyExplanation}
              </p>
            </div>
          )}

          {/* Recommendations */}
          {session.recommendations && session.recommendations.length > 0 && (
            <div>
              <h4 className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <Lightbulb size={12} className="text-yellow-400"/> Recommended Actions
              </h4>
              <ul className="space-y-1.5">
                {session.recommendations.map((rec, idx) => (
                  <li key={idx} className="flex gap-2 text-xs text-gray-300 bg-dark-bg/50 p-2 rounded-lg border border-dark-border/50">
                    <span className="text-phantom-500 shrink-0">&bull;</span>
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
