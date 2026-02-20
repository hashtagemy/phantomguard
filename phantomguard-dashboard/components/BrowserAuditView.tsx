import React, { useState } from 'react';
import { Globe, ChevronDown, ChevronRight, ShieldCheck, ShieldAlert, ShieldOff } from 'lucide-react';
import { Session, ShadowVerification } from '../types';

interface BrowserAuditViewProps {
  sessions: Session[];
}

interface UrlEntry {
  url: string;
  shadow: ShadowVerification;
  stepContent: string;
  stepTimestamp: string;
}

interface SessionAuditEntry {
  session: Session;
  urls: UrlEntry[];
  hasSecurityConcern: boolean;
}

function buildAuditEntries(sessions: Session[]): SessionAuditEntry[] {
  return sessions
    .map(session => {
      const urls: UrlEntry[] = [];

      for (const step of session.steps) {
        if (step.type !== 'phantom_check') continue;
        const sv = step.metadata?.shadowVerification;
        if (!sv) continue;

        urls.push({
          url: sv.url || '(unknown URL)',
          shadow: sv,
          stepContent: step.content,
          stepTimestamp: step.timestamp,
        });
      }

      return {
        session,
        urls,
        hasSecurityConcern: urls.some(u => u.shadow.verificationResult === 'SECURITY_CONCERN'),
      };
    })
    .filter(e => e.urls.length > 0);
}

function VerificationBadge({ result }: { result: ShadowVerification['verificationResult'] }) {
  if (result === 'VERIFIED') {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-emerald-950/30 text-emerald-400 border border-emerald-900/30">
        <ShieldCheck size={12} />
        VERIFIED
      </span>
    );
  }
  if (result === 'SECURITY_CONCERN') {
    return (
      <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-red-950/30 text-red-400 border border-red-900/30">
        <ShieldAlert size={12} />
        SECURITY CONCERN
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium bg-gray-800 text-gray-500 border border-gray-700">
      <ShieldOff size={12} />
      UNAVAILABLE
    </span>
  );
}

function ScorePill({ score }: { score: number | null }) {
  if (score == null) return <span className="text-xs text-gray-600">—</span>;
  const color = score >= 80 ? 'text-emerald-400' : score >= 50 ? 'text-yellow-400' : 'text-red-400';
  return <span className={`text-xs font-mono font-medium ${color}`}>{score}/100</span>;
}

export const BrowserAuditView: React.FC<BrowserAuditViewProps> = ({ sessions }) => {
  const entries = buildAuditEntries(sessions);

  // Sessions with security concern start expanded; others start collapsed
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    for (const e of entries) {
      init[e.session.id] = e.hasSecurityConcern;
    }
    return init;
  });

  const [showDetails, setShowDetails] = useState<Record<string, boolean>>({});

  const toggle = (id: string) =>
    setExpanded(prev => ({ ...prev, [id]: !prev[id] }));

  const toggleDetail = (key: string) =>
    setShowDetails(prev => ({ ...prev, [key]: !prev[key] }));

  // Summary counts — skip UNAVAILABLE
  const totalVerified = entries.flatMap(e => e.urls).filter(u => u.shadow.verificationResult === 'VERIFIED').length;
  const totalConcern = entries.flatMap(e => e.urls).filter(u => u.shadow.verificationResult === 'SECURITY_CONCERN').length;
  const totalChecked = totalVerified + totalConcern;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-3 mb-1">
          <Globe size={22} className="text-phantom-400" />
          <h1 className="text-xl font-bold text-white">Browser Audit</h1>
        </div>
        <p className="text-sm text-gray-500 ml-9">Nova Act shadow verification results</p>
      </div>

      {/* Summary cards */}
      {entries.length > 0 && (
        <div className="flex gap-4">
          <div className="flex-1 bg-dark-surface border border-dark-border rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-white">{totalChecked}</div>
            <div className="text-xs text-gray-500 mt-0.5">Total Checked</div>
          </div>
          <div className="flex-1 bg-dark-surface border border-emerald-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-emerald-400">{totalVerified}</div>
            <div className="text-xs text-gray-500 mt-0.5">Verified</div>
          </div>
          <div className="flex-1 bg-dark-surface border border-red-900/30 rounded-xl p-4 text-center">
            <div className="text-2xl font-bold text-red-400">{totalConcern}</div>
            <div className="text-xs text-gray-500 mt-0.5">Security Concerns</div>
          </div>
        </div>
      )}

      {/* Empty state */}
      {entries.length === 0 && (
        <div className="bg-dark-surface border border-dark-border rounded-xl p-12 text-center">
          <Globe size={32} className="text-gray-700 mx-auto mb-3" />
          <h3 className="text-base font-medium text-gray-400 mb-1">No browser activity recorded</h3>
          <p className="text-sm text-gray-600 max-w-sm mx-auto">
            Nova Act shadow verification runs automatically when agents visit URLs.
            Enable <code className="text-gray-500">enable_shadow_browser=True</code> in your
            PhantomGuard hook configuration and set <code className="text-gray-500">NOVA_ACT_API_KEY</code>.
          </p>
        </div>
      )}

      {/* Session accordion list */}
      <div className="space-y-3">
        {entries.map(entry => {
          const isOpen = expanded[entry.session.id] ?? false;

          return (
            <div
              key={entry.session.id}
              className={`bg-dark-surface border rounded-xl overflow-hidden transition-all ${
                entry.hasSecurityConcern
                  ? 'border-red-900/40'
                  : 'border-dark-border'
              }`}
            >
              {/* Accordion header */}
              <button
                onClick={() => toggle(entry.session.id)}
                className="w-full flex items-center gap-3 px-5 py-4 text-left hover:bg-white/5 transition-colors"
              >
                <span className="text-gray-500">
                  {isOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                </span>
                <span className="text-sm font-medium text-gray-300 flex-1 truncate">
                  <span className="text-gray-500 mr-1">[{entry.session.agentName}]</span>
                  {entry.session.taskPreview || '(no task)'}
                </span>
                <span className="text-xs text-gray-600 shrink-0">
                  {new Date(entry.session.startTime).toLocaleString(undefined, {
                    month: 'short', day: 'numeric',
                    hour: '2-digit', minute: '2-digit',
                  })}
                </span>
                {entry.hasSecurityConcern && (
                  <span className="text-xs px-2 py-0.5 rounded-full bg-red-950/30 text-red-400 border border-red-900/30 shrink-0">
                    ⚠ Security Concern
                  </span>
                )}
                <span className="text-xs text-gray-600 shrink-0">
                  {entry.urls.length} URL{entry.urls.length !== 1 ? 's' : ''}
                </span>
              </button>

              {/* Accordion body */}
              {isOpen && (
                <div className="border-t border-dark-border divide-y divide-dark-border/50">
                  {entry.urls.length === 0 ? (
                    <div className="px-6 py-4 text-sm text-gray-600">
                      No browser activity recorded in this session.
                    </div>
                  ) : (
                    entry.urls.map((urlEntry, idx) => {
                      const detailKey = `${entry.session.id}-${idx}`;
                      const detailOpen = showDetails[detailKey];

                      return (
                        <div key={idx} className="px-6 py-3">
                          <div className="flex items-center gap-3 flex-wrap">
                            {/* URL */}
                            <span className="text-sm font-mono text-gray-400 flex-1 truncate min-w-0">
                              {urlEntry.url}
                            </span>

                            {/* Verification badge */}
                            <VerificationBadge result={urlEntry.shadow.verificationResult} />

                            {/* Score */}
                            <ScorePill score={urlEntry.shadow.securityScore} />
                          </div>

                          {/* Security issues */}
                          {urlEntry.shadow.securityIssues.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-2">
                              {urlEntry.shadow.securityIssues.map((issue, i) => (
                                <span key={i} className="text-xs text-red-400 flex items-center gap-1">
                                  <span>⚠</span> {issue}
                                </span>
                              ))}
                            </div>
                          )}

                          {/* Details toggle */}
                          {urlEntry.shadow.details && (
                            <div className="mt-2">
                              <button
                                onClick={() => toggleDetail(detailKey)}
                                className="text-xs text-gray-600 hover:text-gray-400 transition-colors flex items-center gap-1"
                              >
                                {detailOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                                {detailOpen ? 'Hide' : 'Show'} Nova Act report
                              </button>
                              {detailOpen && (
                                <p className="mt-1.5 text-xs text-gray-500 bg-dark-bg rounded-lg p-3 leading-relaxed border border-dark-border">
                                  {urlEntry.shadow.details}
                                </p>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};
