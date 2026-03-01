export enum QualityLevel {
  EXCELLENT = 'EXCELLENT',
  GOOD = 'GOOD',
  POOR = 'POOR',
  FAILED = 'FAILED',
  STUCK = 'STUCK',
  PENDING = 'PENDING',
}

export enum IssueType {
  INFINITE_LOOP = 'INFINITE_LOOP',
  TASK_DRIFT = 'TASK_DRIFT',
  INEFFICIENCY = 'INEFFICIENCY',
  INCOMPLETE = 'INCOMPLETE',
  TOOL_MISUSE = 'TOOL_MISUSE',
  ERROR_HANDLING = 'ERROR_HANDLING',
  DATA_EXFILTRATION = 'DATA_EXFILTRATION',
  PROMPT_INJECTION = 'PROMPT_INJECTION',
  UNAUTHORIZED_ACCESS = 'UNAUTHORIZED_ACCESS',
  SUSPICIOUS_BEHAVIOR = 'SUSPICIOUS_BEHAVIOR',
  CREDENTIAL_LEAK = 'CREDENTIAL_LEAK',
  NONE = 'NONE',
}

export interface SessionIssueDetail {
  issueId?: string;
  issueType: IssueType;
  severity: number;
  description: string;
  recommendation: string;
  affectedSteps?: string[];
}

export interface ShadowVerification {
  verified: boolean;
  verificationResult: 'VERIFIED' | 'SECURITY_CONCERN' | 'UNAVAILABLE';
  verificationMethod: string;
  securityScore: number | null;
  securityIssues: string[];
  details: string;
  url?: string;
}

export interface AgentStep {
  id: string;
  timestamp: string;
  type: 'user' | 'agent_thought' | 'tool_call' | 'tool_result' | 'norn_check';
  content: string;
  metadata?: {
    toolName?: string;
    duration?: string;
    riskScore?: number | null; // 0-100, null = not yet evaluated
    shadowVerification?: ShadowVerification;
  };
}

export interface Session {
  id: string;
  agentName: string;
  model: string;
  taskPreview: string;
  startTime: string;
  status: 'active' | 'completed' | 'terminated';
  overallQuality: QualityLevel;
  efficiencyScore: number | null;
  securityScore: number | null;
  issues: IssueType[];
  issueDetails: SessionIssueDetail[];
  steps: AgentStep[];
  aiEvaluation?: string;
  detailedAnalysis?: string;
  toolAnalysis?: { tool: string; usage: string; note: string }[];
  decisionObservations?: string[];
  efficiencyExplanation?: string;
  recommendations?: string[];
  taskCompletion?: boolean | null;
  loopDetected?: boolean;
  totalExecutionTimeMs?: number;
}

export interface StatMetric {
  label: string;
  value: string;
  change: string;
  trend: 'up' | 'down' | 'neutral';
}