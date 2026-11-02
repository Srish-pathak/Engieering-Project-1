import {
  AmbiguityIssue,
  AnalyzedSpecMetrics,
  CapacityProfile,
  SectionCoverage,
  TechSpecDocument,
} from '../types/spec';

const AMBIGUITY_RULES: Array<{
  regex: RegExp;
  category: AmbiguityIssue['category'];
  suggestion: string;
  replacement: string;
}> = [
  {
    regex: /\b(should probably|might want to|could potentially|ideally should)\b/gi,
    category: 'Weak Modal (RFC-2119)',
    suggestion: 'Replace tentative phrasing with normative RFC-2119 keyword MUST or SHOULD.',
    replacement: 'MUST',
  },
  {
    regex: /\b(tbd|todo|to be determined|decide later|placeholder)\b/gi,
    category: 'Deferred Decision',
    suggestion: 'Resolve open architecture placeholder before moving spec to Approved status.',
    replacement: 'REQUIRED [Owner Assigned: Architecture Review]',
  },
  {
    regex: /\b(very fast|low latency|near real-time|as fast as possible|minimal delay)\b/gi,
    category: 'Unbounded SLA',
    suggestion: 'Specify explicit percentile bound (e.g., P99 <= 25ms under 10k QPS).',
    replacement: 'P99 <= 25ms at peak QPS',
  },
  {
    regex: /\b(high availability|almost always up|zero downtime|highly scalable)\b/gi,
    category: 'Unbounded SLA',
    suggestion: 'Define explicit availability tier (e.g., 99.95% monthly uptime, RTO <= 5m).',
    replacement: '99.95% availability (RTO <= 5m, RPO <= 30s)',
  },
  {
    regex: /\b(several|some retries|a few seconds|large payload|etc\.)\b/gi,
    category: 'Ambiguous Quantifier',
    suggestion: 'Replace vague quantifier with exact bounded integer, backoff ceiling, or byte limit.',
    replacement: '3 retries with exponential jitter (max 2000ms)',
  },
];

const REQUIRED_SECTIONS: Array<{
  name: string;
  keywords: RegExp;
  baselineNote: string;
}> = [
  {
    name: '1. Context & Architecture',
    keywords: /(architecture|overview|context|system design|topology)/i,
    baselineNote: 'Defines system boundaries, service topology, and data flow.',
  },
  {
    name: '2. Data Model & Storage',
    keywords: /(data model|schema|database|storage|persistence|index|partition)/i,
    baselineNote: 'Covers schema layout, partitioning keys, retention, and index bounds.',
  },
  {
    name: '3. API & Wire Contracts',
    keywords: /(api|endpoint|grpc|protobuf|payload|contract|interface|wire)/i,
    baselineNote: 'Specifies request/response schemas, idempotency keys, and error codes.',
  },
  {
    name: '4. Security & Access Control',
    keywords: /(security|auth|tls|mtls|encryption|rbac|token|kms|zero-trust)/i,
    baselineNote: 'Details authentication, encryption in transit/at rest, and RBAC scopes.',
  },
  {
    name: '5. Failure Modes & SLA',
    keywords: /(failure|fallback|sla|slo|retry|circuit breaker|degradation|outage|rto|rpo)/i,
    baselineNote: 'Documents circuit breakers, dead-letter queues, and blast radius containment.',
  },
  {
    name: '6. Observability & Telemetry',
    keywords: /(observability|metrics|tracing|logging|alerts|prometheus|opentelemetry)/i,
    baselineNote: 'Specifies golden signals, trace sampling rates, and paging thresholds.',
  },
  {
    name: '7. Rollout & Backfill Plan',
    keywords: /(rollout|migration|canary|feature flag|backfill|rollback)/i,
    baselineNote: 'Defines phased canary percentages, dual-write validation, and instant rollback.',
  },
];

export function analyzeTechSpec(spec: TechSpecDocument, resolvedIssueIds: Set<string> = new Set()): AnalyzedSpecMetrics {
  const lines = spec.rawMarkdown.split('\n');

  // Count RFC-2119 normative keywords (case-sensitive uppercase standard + case-insensitive)
  const fullText = spec.rawMarkdown;
  const mustMatches = fullText.match(/\b(MUST|REQUIRED|SHALL|MUST NOT|SHALL NOT)\b/g);
  const shouldMatches = fullText.match(/\b(SHOULD|RECOMMENDED|SHOULD NOT)\b/g);
  const mayMatches = fullText.match(/\b(MAY|OPTIONAL)\b/g);

  const rfc2119MustCount = mustMatches ? mustMatches.length : 0;
  const rfc2119ShouldCount = shouldMatches ? shouldMatches.length : 0;
  const rfc2119MayCount = mayMatches ? mayMatches.length : 0;

  // Detect ambiguity issues line-by-line
  const ambiguityIssues: AmbiguityIssue[] = [];
  lines.forEach((line, idx) => {
    AMBIGUITY_RULES.forEach((rule, ruleIdx) => {
      const regex = new RegExp(rule.regex.source, 'gi');
      let match: RegExpExecArray | null;
      while ((match = regex.exec(line)) !== null) {
        const issueId = `${spec.id}-L${idx + 1}-R${ruleIdx}-${match.index}`;
        ambiguityIssues.push({
          id: issueId,
          lineNumber: idx + 1,
          phrase: match[0],
          contextLine: line.trim(),
          suggestion: rule.suggestion,
          replacementText: rule.replacement,
          category: rule.category,
          resolved: resolvedIssueIds.has(issueId),
        });
      }
    });
  });

  // Evaluate section coverage by splitting markdown headers
  const blocks = spec.rawMarkdown.split(/^#{1,3}\s+/m);
  const sectionCoverage: SectionCoverage[] = REQUIRED_SECTIONS.map((req) => {
    const matchingBlocks = blocks.filter((b) => req.keywords.test(b));
    const combinedText = matchingBlocks.join(' ');
    const words = combinedText.trim() ? combinedText.trim().split(/\s+/).length : 0;
    const normative = (combinedText.match(/\b(MUST|SHALL|REQUIRED|SHOULD|MAY)\b/g) || []).length;
    const present = matchingBlocks.length > 0 && words >= 12;

    let completenessPct = 0;
    if (present) {
      const wordFactor = Math.min(65, Math.round((words / 45) * 65));
      const normativeFactor = Math.min(35, normative * 12);
      completenessPct = Math.min(100, Math.max(35, wordFactor + normativeFactor));
    }

    return {
      section: req.name,
      present,
      completenessPct,
      wordCount: words,
      normativeCount: normative,
      notes: present
        ? `${words} words · ${normative} normative rules verified`
        : `Missing or underspecified (${words} words) — ${req.baselineNote}`,
    };
  });

  const avgSectionScore =
    sectionCoverage.reduce((acc, item) => acc + item.completenessPct, 0) / sectionCoverage.length;

  const unresolvedAmbiguities = ambiguityIssues.filter((i) => !i.resolved).length;
  const spofCount = spec.dependencies.filter((d) => d.spofRisk === 'High').length;
  const criticalFindingsCount = spec.findings.filter((f) => f.severity === 'Critical').length;
  const warningFindingsCount = spec.findings.filter((f) => f.severity === 'Warning').length;
  const resolvedFindingsCount = spec.findings.filter((f) => f.severity === 'Resolved').length;

  // Calculate composite readiness score (deterministic formula)
  const penalty = unresolvedAmbiguities * 4 + criticalFindingsCount * 8 + spofCount * 5;
  const normativeBonus = Math.min(12, (rfc2119MustCount + rfc2119ShouldCount) * 1.5);
  const completenessScore = Math.max(
    18,
    Math.min(100, Math.round(avgSectionScore + normativeBonus - penalty))
  );

  // Critical path P99 latency sum across synchronous upstream/downstream/datastore hops
  const cumulativePathLatencyMs = spec.dependencies.reduce((sum, dep) => sum + dep.p99BudgetMs, 0);
  const latencyHeadroomMs = spec.p99TargetMs - cumulativePathLatencyMs;

  // Serial availability product for High/Moderate dependencies
  const compositeSlaFraction = spec.dependencies.reduce((acc, dep) => {
    const depFraction = dep.availabilitySla / 100;
    // Mitigated dependencies have active failover so effective availability impact is squared
    const effective = dep.spofRisk === 'Mitigated' ? 1 - Math.pow(1 - depFraction, 2) : depFraction;
    return acc * effective;
  }, 1);
  const compositeSlaPct = Number((compositeSlaFraction * 100).toFixed(3));

  return {
    completenessScore,
    rfc2119MustCount,
    rfc2119ShouldCount,
    rfc2119MayCount,
    ambiguityIssues,
    sectionCoverage,
    spofCount,
    criticalFindingsCount,
    warningFindingsCount,
    resolvedFindingsCount,
    cumulativePathLatencyMs,
    latencyHeadroomMs,
    compositeSlaPct,
  };
}

export function buildCapacityEnvelope(targetQps: number, p99TargetMs: number): CapacityProfile[] {
  const multipliers = [
    { label: '0.5x Baseline', factor: 0.5, latFactor: 0.58, cpu: 32 },
    { label: '1.0x Nominal', factor: 1.0, latFactor: 0.78, cpu: 58 },
    { label: '1.5x Peak Burst', factor: 1.5, latFactor: 0.96, cpu: 76 },
    { label: '2.0x Failover Surge', factor: 2.0, latFactor: 1.28, cpu: 89 },
    { label: '3.0x Stress Limit', factor: 3.0, latFactor: 1.85, cpu: 98 },
  ];

  return multipliers.map((m) => {
    const qps = Math.round(targetQps * m.factor);
    const p99Ms = Math.round(p99TargetMs * m.latFactor);
    const p50Ms = Math.max(2, Math.round(p99Ms * 0.38));
    return {
      loadMultiplier: m.label,
      qps,
      p50Ms,
      p99Ms,
      slaLimitMs: p99TargetMs,
      cpuUtilizationPct: m.cpu,
    };
  });
}
