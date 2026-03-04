import React from 'react';
import { Session } from '../../types';
import {
  ShieldAlert,
  Clock,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Target,
  Zap,
  Shield,
  XCircle,
  AlertCircle,
  Info,
  TrendingUp,
  BarChart3,
  Hash
} from 'lucide-react';

interface TestResult {
  passed: boolean;
  pending?: boolean;
  name: string;
  description: string;
  score?: number | null;
}

interface TestResultsPanelProps {
  session: Session;
  allSessions?: Session[];
}

export const TestResultsPanel: React.FC<TestResultsPanelProps> = ({ session, allSessions }) => {
  const effScore = session.efficiencyScore;
  const secScore = session.securityScore;
  const isTerminated = session.status === 'terminated';
  const isActive = session.status === 'active';
  const isPending = session.overallQuality === 'PENDING' && !isTerminated;

  const testResults: Record<string, TestResult> = {
    loopDetection: {
      passed: !session.loopDetected,
      name: 'Loop Detection',
      description: session.loopDetected ? 'Agent got stuck in a loop' : 'No infinite loops detected'
    },
    taskCompletion: {
      passed: session.taskCompletion === true,
      pending: session.taskCompletion == null,
      name: 'Task Completion',
      description: session.taskCompletion === true ? 'Task completed successfully' :
                   session.taskCompletion === false ? 'Task not completed' :
                   'Not yet determined'
    },
    efficiency: {
      passed: effScore != null && effScore >= 70,
      pending: effScore == null,
      name: 'Efficiency',
      description: effScore != null ? `${effScore}% efficiency score` : 'Evaluating...',
      score: effScore
    },
    security: {
      passed: secScore != null && secScore >= 70,
      pending: secScore == null,
      name: 'Security',
      description: secScore != null ? `${secScore}% security score` : 'Evaluating...',
      score: secScore
    },
    qualityLevel: {
      passed: ['EXCELLENT', 'GOOD'].includes(session.overallQuality),
      pending: isPending,
      name: 'Overall Quality',
      description: isPending ? 'Evaluation pending...' :
                   (isTerminated && session.overallQuality === 'PENDING') ? 'Execution terminated — quality not evaluated' :
                   `Quality level: ${session.overallQuality}`
    }
  };

  const allTests = Object.values(testResults);
  const evaluatedTests = allTests.filter(t => !t.pending);
  const totalTests = evaluatedTests.length || 1;
  const passedTests = evaluatedTests.filter(t => t.passed).length;
  const passRate = Math.round((passedTests / totalTests) * 100);

  // Aggregate stats across all sessions
  const sessions = allSessions && allSessions.length > 1 ? allSessions : null;
  const aggregate = sessions ? (() => {
    const completed = sessions.filter(s => s.status === 'completed');
    const effScores = completed.map(s => s.efficiencyScore).filter((v): v is number => v != null);
    const secScores = completed.map(s => s.securityScore).filter((v): v is number => v != null);
    const qualityCounts: Record<string, number> = {};
    completed.forEach(s => {
      const q = s.overallQuality || 'PENDING';
      qualityCounts[q] = (qualityCounts[q] || 0) + 1;
    });
    const allIssues = sessions.flatMap(s => s.issueDetails || []);
    return {
      totalSessions: sessions.length,
      completedSessions: completed.length,
      avgEfficiency: effScores.length > 0 ? Math.round(effScores.reduce((a, b) => a + b, 0) / effScores.length) : null,
      avgSecurity: secScores.length > 0 ? Math.round(secScores.reduce((a, b) => a + b, 0) / secScores.length) : null,
      qualityCounts,
      totalIssues: allIssues.length,
      totalSteps: sessions.reduce((sum, s) => sum + s.steps.length, 0),
    };
  })() : null;

  return (
    <div className="space-y-4">
      {/* Latest Session — Current State */}
      <div>
        <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Activity size={14} className="text-norn-500" />
          Latest Session
          <span className="text-[10px] text-gray-600 font-mono font-normal">{session.id}</span>
        </h3>

        {/* Test Results Summary */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-3 mb-3">
          {/* Pass Rate Card */}
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Test Pass Rate</h3>
              <TrendingUp size={12} className={passRate >= 80 ? 'text-emerald-400' : passRate >= 60 ? 'text-yellow-400' : 'text-red-400'} />
            </div>
            <div className="flex items-end gap-2">
              <span className={`text-sm font-bold ${
                passRate >= 80 ? 'text-emerald-400' : passRate >= 60 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {passRate}%
              </span>
              <span className="text-gray-500 text-xs mb-0.5">{passedTests} / {totalTests}</span>
            </div>
            <div className="mt-2 h-1 bg-dark-bg rounded-full overflow-hidden">
              <div
                className={`h-full transition-all ${
                  passRate >= 80 ? 'bg-emerald-500' : passRate >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${passRate}%` }}
              />
            </div>
          </div>

          {/* Quality Badge */}
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Overall Quality</h3>
              <Target size={12} className="text-norn-400" />
            </div>
            <div className={`text-sm font-bold mb-0.5 ${
              session.overallQuality === 'EXCELLENT' ? 'text-emerald-400' :
              session.overallQuality === 'GOOD' ? 'text-blue-400' :
              (session.overallQuality === 'PENDING' && isTerminated) ? 'text-red-400' :
              session.overallQuality === 'PENDING' ? 'text-gray-500' :
              session.overallQuality === 'POOR' ? 'text-yellow-400' :
              'text-red-400'
            }`}>
              {isPending ? '⏳ PENDING' :
               (isTerminated && session.overallQuality === 'PENDING') ? '✕ TERMINATED' :
               session.overallQuality}
            </div>
            <p className="text-xs text-gray-500">
              {session.overallQuality === 'EXCELLENT' ? 'Agent performed exceptionally well' :
               session.overallQuality === 'GOOD' ? 'Agent completed task with minor issues' :
               isPending ? 'AI evaluation in progress...' :
               isTerminated && session.overallQuality === 'PENDING' ? 'Execution terminated before evaluation' :
               session.overallQuality === 'POOR' ? 'Agent had significant issues' :
               'Agent failed to complete task'}
            </p>
          </div>
        </div>

        {/* Detailed Test Results */}
        <div className="bg-dark-surface/50 rounded-lg border border-dark-border overflow-hidden mb-3">
          <div className="p-3 bg-dark-surface border-b border-dark-border">
            <h3 className="text-xs font-semibold text-gray-200 flex items-center gap-2">
              <CheckCircle2 size={13} className="text-emerald-400" />
              Test Results Breakdown
            </h3>
          </div>
          <div className="p-3 space-y-2">
            {Object.entries(testResults).map(([key, test]) => {
              const testPending = test.pending;
              return (
                <div key={key} className={`flex items-center justify-between p-2 rounded border ${
                  testPending ? 'bg-gray-900/10 border-gray-800/30' :
                  test.passed ? 'bg-emerald-950/10 border-emerald-900/30' :
                  'bg-red-950/10 border-red-900/30'
                }`}>
                  <div className="flex items-center gap-2">
                    {testPending ? (
                      <Clock size={14} className="text-gray-500 shrink-0 animate-pulse" />
                    ) : test.passed ? (
                      <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
                    ) : (
                      <XCircle size={14} className="text-red-400 shrink-0" />
                    )}
                    <div>
                      <div className={`text-xs font-medium ${
                        testPending ? 'text-gray-400' :
                        test.passed ? 'text-emerald-300' : 'text-red-300'
                      }`}>
                        {test.name}
                      </div>
                      <div className="text-[10px] text-gray-500 mt-0.5">{test.description}</div>
                    </div>
                  </div>
                  {test.score !== undefined && test.score !== null ? (
                    <div className={`text-base font-bold ${
                      test.score >= 80 ? 'text-emerald-400' :
                      test.score >= 60 ? 'text-yellow-400' :
                      'text-red-400'
                    }`}>
                      {test.score}
                    </div>
                  ) : testPending ? (
                    <div className="text-xs font-medium text-gray-600">&mdash;</div>
                  ) : null}
                </div>
              );
            })}
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center gap-1.5 text-gray-400 text-[10px] font-medium uppercase mb-1.5">
              <Activity size={12} /> Total Steps
            </div>
            <div className="text-base font-bold text-white">{session.steps.length}</div>
          </div>
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center gap-1.5 text-gray-400 text-[10px] font-medium uppercase mb-1.5">
              <Zap size={12} /> Efficiency
            </div>
            {effScore != null ? (
              <div className={`text-base font-bold ${
                effScore >= 80 ? 'text-emerald-400' : effScore >= 60 ? 'text-yellow-400' : 'text-red-400'
              }`}>{effScore}%</div>
            ) : isTerminated ? (
              <div className="text-base font-medium text-gray-600">N/A</div>
            ) : (
              <div className="text-base font-medium text-gray-600 animate-pulse">–</div>
            )}
          </div>
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center gap-1.5 text-gray-400 text-[10px] font-medium uppercase mb-1.5">
              <Shield size={12} /> Security
            </div>
            {secScore != null ? (
              <div className={`text-base font-bold ${
                secScore >= 80 ? 'text-emerald-400' : secScore >= 70 ? 'text-yellow-400' : 'text-red-400'
              }`}>{secScore}%</div>
            ) : isTerminated ? (
              <div className="text-base font-medium text-gray-600">N/A</div>
            ) : (
              <div className="text-base font-medium text-gray-600 animate-pulse">–</div>
            )}
          </div>
          <div className="bg-dark-surface/50 p-3 rounded-lg border border-dark-border">
            <div className="flex items-center gap-1.5 text-gray-400 text-[10px] font-medium uppercase mb-1.5">
              <AlertTriangle size={12} /> Issues
            </div>
            <div className={`text-base font-bold ${
              session.issueDetails.length === 0 ? 'text-emerald-400' :
              session.issueDetails.length <= 2 ? 'text-yellow-400' : 'text-red-400'
            }`}>{session.issueDetails.length}</div>
          </div>
        </div>
      </div>

      {/* Issues from latest session */}
      {session.issueDetails.length > 0 && (
        <div className="bg-dark-surface/50 rounded-lg border border-dark-border overflow-hidden">
          <div className="p-3 bg-dark-surface border-b border-dark-border">
            <h3 className="text-xs font-semibold text-gray-200 flex items-center gap-2">
              <ShieldAlert size={13} className="text-red-400" />
              Detected Issues ({session.issueDetails.length})
            </h3>
          </div>
          <div className="p-3 space-y-2">
            {session.issueDetails.map((issue, idx) => (
              <div key={issue.issueId || idx} className={`p-3 rounded-lg border ${
                issue.severity >= 8 ? 'bg-red-950/20 border-red-900/30' :
                issue.severity >= 5 ? 'bg-yellow-950/20 border-yellow-900/30' :
                'bg-blue-950/20 border-blue-900/30'
              }`}>
                <div className="flex items-start gap-2">
                  {issue.severity >= 8 ? (
                    <AlertCircle size={14} className="text-red-400 shrink-0 mt-0.5" />
                  ) : issue.severity >= 5 ? (
                    <AlertTriangle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
                  ) : (
                    <Info size={14} className="text-blue-400 shrink-0 mt-0.5" />
                  )}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-xs font-semibold ${
                        issue.severity >= 8 ? 'text-red-300' :
                        issue.severity >= 5 ? 'text-yellow-300' : 'text-blue-300'
                      }`}>{issue.issueType.replace(/_/g, ' ')}</span>
                      <span className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${
                        issue.severity >= 8 ? 'bg-red-900/30 text-red-300' :
                        issue.severity >= 5 ? 'bg-yellow-900/30 text-yellow-300' : 'bg-blue-900/30 text-blue-300'
                      }`}>{issue.severity}/10</span>
                    </div>
                    <p className="text-xs text-gray-400 mb-1">{issue.description}</p>
                    {issue.recommendation && (
                      <div className="text-[10px] text-gray-500 bg-dark-bg/50 p-1.5 rounded border border-dark-border/50">
                        <span className="font-medium text-gray-400">Rec:</span> {issue.recommendation}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Aggregate Summary — only when multiple sessions exist */}
      {aggregate && (
        <div className="bg-dark-surface/50 rounded-lg border border-dark-border overflow-hidden">
          <div className="p-3 bg-dark-surface border-b border-dark-border">
            <h3 className="text-xs font-semibold text-gray-200 flex items-center gap-2">
              <BarChart3 size={13} className="text-norn-400" />
              All Sessions Summary
              <span className="text-[10px] text-gray-500 font-normal">({aggregate.totalSessions} sessions)</span>
            </h3>
          </div>
          <div className="p-3">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              <div className="bg-dark-bg/50 p-2.5 rounded-lg border border-dark-border/50 text-center">
                <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">Sessions</div>
                <div className="text-sm font-bold text-white">{aggregate.totalSessions}</div>
              </div>
              <div className="bg-dark-bg/50 p-2.5 rounded-lg border border-dark-border/50 text-center">
                <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">Total Steps</div>
                <div className="text-sm font-bold text-white">{aggregate.totalSteps}</div>
              </div>
              <div className="bg-dark-bg/50 p-2.5 rounded-lg border border-dark-border/50 text-center">
                <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">Avg Efficiency</div>
                <div className={`text-sm font-bold ${
                  aggregate.avgEfficiency == null ? 'text-gray-600' :
                  aggregate.avgEfficiency >= 80 ? 'text-emerald-400' :
                  aggregate.avgEfficiency >= 60 ? 'text-yellow-400' : 'text-red-400'
                }`}>{aggregate.avgEfficiency != null ? `${aggregate.avgEfficiency}%` : '–'}</div>
              </div>
              <div className="bg-dark-bg/50 p-2.5 rounded-lg border border-dark-border/50 text-center">
                <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">Avg Security</div>
                <div className={`text-sm font-bold ${
                  aggregate.avgSecurity == null ? 'text-gray-600' :
                  aggregate.avgSecurity >= 80 ? 'text-emerald-400' :
                  aggregate.avgSecurity >= 70 ? 'text-yellow-400' : 'text-red-400'
                }`}>{aggregate.avgSecurity != null ? `${aggregate.avgSecurity}%` : '–'}</div>
              </div>
              <div className="bg-dark-bg/50 p-2.5 rounded-lg border border-dark-border/50 text-center">
                <div className="text-[10px] text-gray-500 uppercase font-medium mb-1">Total Issues</div>
                <div className={`text-sm font-bold ${
                  aggregate.totalIssues === 0 ? 'text-emerald-400' :
                  aggregate.totalIssues <= 3 ? 'text-yellow-400' : 'text-red-400'
                }`}>{aggregate.totalIssues}</div>
              </div>
            </div>

            {/* Quality Distribution */}
            {Object.keys(aggregate.qualityCounts).length > 0 && (
              <div className="mt-3 flex items-center gap-2 flex-wrap">
                <span className="text-[10px] text-gray-500 uppercase font-medium">Quality:</span>
                {Object.entries(aggregate.qualityCounts).map(([quality, count]) => (
                  <span key={quality} className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                    quality === 'EXCELLENT' ? 'bg-emerald-900/30 text-emerald-400' :
                    quality === 'GOOD' ? 'bg-blue-900/30 text-blue-400' :
                    quality === 'POOR' ? 'bg-yellow-900/30 text-yellow-400' :
                    quality === 'FAILED' ? 'bg-red-900/30 text-red-400' :
                    'bg-gray-800 text-gray-400'
                  }`}>{quality} ×{count}</span>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
