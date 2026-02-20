import React, { useState } from 'react';
import { Session, IssueType, SessionIssueDetail } from '../types';
import { StatusBadge } from './StatusBadge';
import { TestResultsPanel } from './panels/TestResultsPanel';
import { ExecutionStepsPanel } from './panels/ExecutionStepsPanel';
import { AIAnalysisPanel } from './panels/AIAnalysisPanel';
import {
  Terminal,
  Cpu,
  ArrowLeft,
  Bot,
  BarChart3
} from 'lucide-react';

interface SessionDetailProps {
  session: Session;
  onBack: () => void;
}

export const SessionDetail: React.FC<SessionDetailProps> = ({ session, onBack }) => {
  const [activeTab, setActiveTab] = useState<'overview' | 'steps' | 'analysis'>('overview');

  // Calculate pass rate for header badge
  const effScore = session.efficiencyScore;
  const secScore = session.securityScore;
  const isPending = session.overallQuality === 'PENDING';

  const allTests = [
    { passed: !session.loopDetected, pending: false },
    { passed: session.taskCompletion === true, pending: session.taskCompletion == null },
    { passed: effScore != null && effScore >= 70, pending: effScore == null },
    { passed: secScore != null && secScore >= 70, pending: secScore == null },
    { passed: ['EXCELLENT', 'GOOD'].includes(session.overallQuality), pending: isPending },
  ];
  const evaluatedTests = allTests.filter(t => !t.pending);
  const totalTests = evaluatedTests.length || 1;
  const passedTests = evaluatedTests.filter(t => t.passed).length;
  const passRate = Math.round((passedTests / totalTests) * 100);

  return (
    <div className="flex flex-col h-full animate-in fade-in slide-in-from-bottom-4 duration-500">
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
              <h2 className="text-xl font-semibold text-white tracking-tight">{session.agentName}</h2>
              <StatusBadge status={session.status} />
              <span className={`text-xs px-2 py-1 rounded-full font-medium ${
                passRate >= 80 ? 'bg-emerald-900/30 text-emerald-400 border border-emerald-900/50' :
                passRate >= 60 ? 'bg-yellow-900/30 text-yellow-400 border border-yellow-900/50' :
                'bg-red-900/30 text-red-400 border border-red-900/50'
              }`}>
                {passedTests}/{totalTests} Tests Passed
              </span>
            </div>
            <p className="text-gray-400 text-sm mt-1 flex items-center gap-2">
              <Bot size={14} /> {session.model} • {new Date(session.startTime).toLocaleString()}
            </p>
          </div>
        </div>
      </div>

      {/* Tabs */}
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
            Execution Steps ({session.steps.length})
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

      {/* Tab Content */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {activeTab === 'overview' && <TestResultsPanel session={session} />}
        {activeTab === 'steps' && <ExecutionStepsPanel session={session} />}
        {activeTab === 'analysis' && <AIAnalysisPanel session={session} />}
      </div>
    </div>
  );
};
