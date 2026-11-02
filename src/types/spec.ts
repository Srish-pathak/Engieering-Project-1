export type SpecStatus = 'Draft' | 'In Review' | 'Approved' | 'Blocked';
export type RiskSeverity = 'Critical' | 'Warning' | 'Resolved';

export interface AmbiguityIssue {
  id: string;
  lineNumber: number;
  phrase: string;
  contextLine: string;
  suggestion: string;
  replacementText: string;
  category: 'Ambiguous Quantifier' | 'Weak Modal (RFC-2119)' | 'Unbounded SLA' | 'Deferred Decision';
  resolved: boolean;
}

export interface DependencyNode {
  id: string;
  serviceName: string;
  protocol: 'gRPC' | 'Kafka' | 'PostgreSQL' | 'Redis' | 'HTTPS/REST' | 'S3/Object';
  direction: 'Upstream' | 'Downstream' | 'Datastore';
  p99BudgetMs: number;
  availabilitySla: number;
  spofRisk: 'High' | 'Moderate' | 'Mitigated';
  fallbackStrategy: string;
}

export interface AuditFinding {
  id: string;
  section: string;
  title: string;
  severity: RiskSeverity;
  impact: string;
  remediation: string;
  owner: string;
}

export interface SectionCoverage {
  section: string;
  present: boolean;
  completenessPct: number;
  wordCount: number;
  normativeCount: number;
  notes: string;
}

export interface CapacityProfile {
  loadMultiplier: string;
  qps: number;
  p50Ms: number;
  p99Ms: number;
  slaLimitMs: number;
  cpuUtilizationPct: number;
}

export interface TechSpecDocument {
  id: string;
  code: string;
  title: string;
  domain: string;
  author: string;
  updatedAt: string;
  status: SpecStatus;
  targetQps: number;
  p99TargetMs: number;
  availabilityTargetPct: number;
  monthlyStorageTb: number;
  estimatedMonthlyCostUsd: number;
  rawMarkdown: string;
  dependencies: DependencyNode[];
  findings: AuditFinding[];
  capacityEnvelope: CapacityProfile[];
}

export interface AnalyzedSpecMetrics {
  completenessScore: number;
  rfc2119MustCount: number;
  rfc2119ShouldCount: number;
  rfc2119MayCount: number;
  ambiguityIssues: AmbiguityIssue[];
  sectionCoverage: SectionCoverage[];
  spofCount: number;
  criticalFindingsCount: number;
  warningFindingsCount: number;
  resolvedFindingsCount: number;
  cumulativePathLatencyMs: number;
  latencyHeadroomMs: number;
  compositeSlaPct: number;
}
