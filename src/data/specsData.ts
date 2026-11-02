import { TechSpecDocument } from '../types/spec';
import { buildCapacityEnvelope } from '../utils/specAnalyzer';

export const INITIAL_SPECS: TechSpecDocument[] = [
  {
    id: 'spec-rfc-042',
    code: 'RFC-042',
    title: 'Multi-Region Event Mesh & Outbox Relay',
    domain: 'Distributed Messaging',
    author: 'K. Lindqvist',
    updatedAt: '2026-10-29',
    status: 'In Review',
    targetQps: 45000,
    p99TargetMs: 38,
    availabilityTargetPct: 99.99,
    monthlyStorageTb: 18.4,
    estimatedMonthlyCostUsd: 14200,
    rawMarkdown: `# 1. Context & Architecture
The Multi-Region Event Mesh decouples transactional order mutations from downstream fulfillment pipelines across three availability zones (us-east, eu-central, ap-northeast). Every producer service MUST write state changes and event envelopes atomically to a local transactional outbox table before WAL tailing relays publish to regional Kafka clusters. Cross-region replication should probably use asynchronous mirror connectors with deterministic conflict resolution.

# 2. Data Model & Storage
Outbox records MUST be partitioned by \`tenant_id\` and \`created_hour\` using 64-bit Snowflake identifiers. Retention in the hot PostgreSQL outbox table SHALL NOT exceed 72 hours, after which compacted segments are archived to immutable object storage. Payload sizes above 256 KB MUST be rejected at the ingress validator, though large payload handling is TBD for batch settlement attachments.

# 3. API & Wire Contracts
All event envelopes MUST conform to CloudEvents v1.0 over binary Protobuf encoding. Producers SHALL supply an \`idempotency_key\` header derived from \`sha256(tenant_id + entity_id + sequence_no)\`. Consumers might want to deduplicate incoming messages within a 24-hour sliding window in Redis.

# 4. Security & Access Control
Inter-cluster broker traffic MUST enforce mutual TLS (mTLS 1.3) with X.509 workload certificates rotated every 12 hours via SPIFFE/SPIRE. Topic-level ACLs REQUIRED per service principal; wildcard consumer group subscriptions SHALL NOT be permitted in production namespaces.

# 5. Failure Modes & SLA
When a regional broker partition leader becomes unreachable, the WAL relay SHOULD retry with exponential backoff after a few seconds and route poisoned frames to an isolated Dead Letter Queue (DLQ). End-to-end delivery must maintain low latency under regional failover. Circuit breakers MUST trip when downstream error rates exceed 2.5% over a 60-second rolling window.

# 6. Observability & Telemetry
Every relay worker MUST emit OpenTelemetry spans with \`traceparent\` propagation and expose Prometheus counters for \`outbox_wal_lag_bytes\`, \`relay_publish_latency_ms\`, and \`dlq_enqueue_total\`. Paging alerts SHALL trigger when replication lag exceeds 5,000 messages for more than 120 seconds.

# 7. Rollout & Backfill Plan
Deployment MUST proceed in four stages: shadow dual-write in staging, 1% canary tenant cohort for 48 hours, 25% regional traffic ramp, and 100% cutover. Instant rollback MUST be executable via runtime feature flag \`enable_wal_outbox_relay=false\` within 15 seconds.`,
    dependencies: [
      {
        id: 'dep-1',
        serviceName: 'Order Outbox Primary (PostgreSQL 16)',
        protocol: 'PostgreSQL',
        direction: 'Datastore',
        p99BudgetMs: 9,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Synchronous standby replica promotion via Patroni (< 8s cutover)',
      },
      {
        id: 'dep-2',
        serviceName: 'Debezium WAL Relay Fleet',
        protocol: 'gRPC',
        direction: 'Upstream',
        p99BudgetMs: 7,
        availabilitySla: 99.95,
        spofRisk: 'Moderate',
        fallbackStrategy: 'Active-passive worker lease handoff via etcd lock within 4s',
      },
      {
        id: 'dep-3',
        serviceName: 'Regional Kafka Broker Mesh',
        protocol: 'Kafka',
        direction: 'Downstream',
        p99BudgetMs: 11,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Rack-aware min.insync.replicas=2 with local NVMe disk spool',
      },
      {
        id: 'dep-4',
        serviceName: 'Idempotency Dedupe Cache',
        protocol: 'Redis',
        direction: 'Datastore',
        p99BudgetMs: 4,
        availabilitySla: 99.9,
        spofRisk: 'High',
        fallbackStrategy: 'Single-shard cluster without read replica failover configured',
      },
      {
        id: 'dep-5',
        serviceName: 'Schema Registry Validator',
        protocol: 'HTTPS/REST',
        direction: 'Upstream',
        p99BudgetMs: 5,
        availabilitySla: 99.95,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'In-memory LRU schema descriptor cache (TTL 6h)',
      },
    ],
    findings: [
      {
        id: 'find-101',
        section: '2. Data Model & Storage',
        title: 'Unresolved large-payload claim check pattern (> 256 KB)',
        severity: 'Critical',
        impact: 'Batch settlement events exceeding 256 KB will fail WAL ingestion without S3 claim-check pointer fallback.',
        remediation: 'Define mandatory S3 pre-signed URI claim-check specification with 30-day lifecycle policy.',
        owner: 'K. Lindqvist',
      },
      {
        id: 'find-102',
        section: '3. API & Wire Contracts',
        title: 'Redis idempotency cache is a single point of failure',
        severity: 'Critical',
        impact: 'Loss of Redis shard causes duplicate downstream fulfillment execution during broker rebalance.',
        remediation: 'Mandate Redis Cluster multi-AZ replication and fallback idempotency lookup on consumer PostgreSQL index.',
        owner: 'M. Vance',
      },
      {
        id: 'find-103',
        section: '5. Failure Modes & SLA',
        title: 'Ambiguous retry interval and unbounded failover latency phrasing',
        severity: 'Warning',
        impact: 'Non-deterministic retry timing risks retry storms across 120 concurrent WAL relay pods.',
        remediation: 'Replace vague retry phrasing with base=150ms, multiplier=2.0, max_backoff=3000ms, full jitter.',
        owner: 'K. Lindqvist',
      },
      {
        id: 'find-104',
        section: '4. Security & Access Control',
        title: 'SPIFFE/SPIRE certificate rotation grace window verified',
        severity: 'Resolved',
        impact: 'Zero-downtime TLS handshake continuity during 12-hour leaf certificate rotation.',
        remediation: 'Dual-trust bundle overlap window set to 90 minutes across all Envoy sidecars.',
        owner: 'S. Takahashi',
      },
    ],
    capacityEnvelope: buildCapacityEnvelope(45000, 38),
  },
  {
    id: 'spec-rfc-051',
    code: 'RFC-051',
    title: 'Zero-Trust KMS Envelope Key Rotation Engine',
    domain: 'Security & Cryptography',
    author: 'S. Takahashi',
    updatedAt: '2026-10-30',
    status: 'Approved',
    targetQps: 18500,
    p99TargetMs: 18,
    availabilityTargetPct: 99.995,
    monthlyStorageTb: 2.1,
    estimatedMonthlyCostUsd: 8900,
    rawMarkdown: `# 1. Context & Architecture
The Zero-Trust KMS Envelope Key Rotation Engine provides automated cryptographic key lifecycle management for tenant data encryption keys (DEKs) wrapped by hardware-backed Customer Master Keys (CMKs). All encryption operations MUST execute inside FIPS 140-3 Level 3 HSM enclaves. Services SHALL NOT persist plaintext DEKs to disk or swap memory at any point.

# 2. Data Model & Storage
Key metadata rows MUST store \`key_version_id\`, \`algorithm_suite\` (AES-256-GCM-HKDF), \`created_epoch_ms\`, and \`crypto_shred_ts\`. Every tenant namespace REQUIRED to maintain at most 2 active decrypt-capable versions and 1 primary encrypt-active version simultaneously.

# 3. API & Wire Contracts
The \`RotateTenantDek\` and \`UnwrapEnvelopeKey\` gRPC endpoints MUST enforce strict deadline propagation (\`grpc-timeout <= 15ms\`). Requests missing a valid hardware attestation quote header SHALL be rejected with \`PERMISSION_DENIED (HTTP 403)\`.

# 4. Security & Access Control
All administrative key destruction calls MUST require quorum M-of-N (3-of-5) YubiKey FIDO2 hardware signatures verified on the audit ledger. Memory buffers holding unwrapped DEKs MUST be zeroed immediately via \`explicit_bzero\` after cipher context initialization.

# 5. Failure Modes & SLA
End-to-end unwrap P99 latency MUST NOT exceed 18ms at 18,500 QPS. If the primary HSM partition exceeds 75% utilization, traffic MUST fail over to the warm standby HSM ring within 400ms. Local enclave DEK caching MAY hold read-only cipher contexts for up to 300 seconds with immediate revocation webhook support.

# 6. Observability & Telemetry
Every cryptographic operation MUST append an immutable hash-chained audit record to the security telemetry stream. Prometheus gauges MUST track \`hsm_enclave_saturation_ratio\`, \`dek_cache_hit_ratio\`, and \`quorum_signature_failures_total\`.

# 7. Rollout & Backfill Plan
Background re-wrapping of historical ciphertext blobs MUST run via rate-limited token bucket workers capped at 2,500 records/sec per shard. Canary validation MUST verify bit-exact roundtrip decryption across 100,000 synthetic tenant fixtures prior to production rollout.`,
    dependencies: [
      {
        id: 'dep-201',
        serviceName: 'CloudHSM FIPS 140-3 Ring',
        protocol: 'gRPC',
        direction: 'Downstream',
        p99BudgetMs: 8,
        availabilitySla: 99.995,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Multi-AZ active-active HSM cluster with automatic partition load balancing',
      },
      {
        id: 'dep-202',
        serviceName: 'Key Version Metadata Store',
        protocol: 'PostgreSQL',
        direction: 'Datastore',
        p99BudgetMs: 4,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Read-replica pool + local enclave signed metadata snapshot',
      },
      {
        id: 'dep-203',
        serviceName: 'SPIFFE Workload Attestor',
        protocol: 'gRPC',
        direction: 'Upstream',
        p99BudgetMs: 3,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Node-local Unix domain socket agent with 15m SVID cache',
      },
    ],
    findings: [
      {
        id: 'find-201',
        section: '5. Failure Modes & SLA',
        title: 'Revocation webhook propagation delay during network partition',
        severity: 'Warning',
        impact: 'Isolated worker nodes could use cached DEK for up to 300s TTL window if webhook push fails.',
        remediation: 'Reduce enclave DEK cache TTL to 60s when heartbeat stream misses 2 consecutive ticks.',
        owner: 'S. Takahashi',
      },
      {
        id: 'find-202',
        section: '4. Security & Access Control',
        title: 'M-of-N quorum signature verification audited',
        severity: 'Resolved',
        impact: 'Prevents unilateral crypto-shredding by any single compromised administrator account.',
        remediation: 'Ed25519 threshold verification contract deployed and fuzz-tested.',
        owner: 'S. Takahashi',
      },
    ],
    capacityEnvelope: buildCapacityEnvelope(18500, 18),
  },
  {
    id: 'spec-rfc-064',
    code: 'RFC-064',
    title: 'Real-Time HNSW Vector Indexing & Hybrid Search',
    domain: 'Search & Storage',
    author: 'A. Patel',
    updatedAt: '2026-10-27',
    status: 'Draft',
    targetQps: 12000,
    p99TargetMs: 65,
    availabilityTargetPct: 99.9,
    monthlyStorageTb: 64.0,
    estimatedMonthlyCostUsd: 29400,
    rawMarkdown: `# 1. Context & Architecture
The Real-Time HNSW Vector Indexing Engine combines dense 1536-dimensional embeddings with sparse BM25 lexical inverted lists for hybrid retrieval. Ingestion pipelines should probably buffer incoming document chunks in memory before flushing graph layers to NVMe segments.

# 2. Data Model & Storage
Each vector shard MUST store quantized INT8 HNSW adjacency lists in memory-mapped files while retaining FP16 raw vectors on NVMe SSDs. Compaction parameters are TBD and might want to run during off-peak hours to avoid several disk I/O spikes.

# 3. API & Wire Contracts
The \`HybridQuery\` gRPC method accepts a dense float32 vector, sparse token weights, metadata filter predicates, and \`top_k\` (MUST be <= 250). Reciprocal Rank Fusion (RRF) constant \`k=60\` SHALL be applied unless overridden by caller query profile.

# 4. Security & Access Control
Tenant document embeddings MUST be isolated via mandatory \`namespace_id\` pre-filtering inside the HNSW graph traversal predicate so cross-tenant nearest neighbors are never evaluated.

# 5. Failure Modes & SLA
Query execution should be very fast and maintain high availability even during segment merges. If a shard replica crashes during HNSW graph construction, the coordinator could potentially replay unindexed vectors from the upstream log after a few seconds.`,
    dependencies: [
      {
        id: 'dep-301',
        serviceName: 'HNSW Memory-Mapped Segment Nodes',
        protocol: 'gRPC',
        direction: 'Datastore',
        p99BudgetMs: 38,
        availabilitySla: 99.9,
        spofRisk: 'High',
        fallbackStrategy: 'Rebuild from WAL takes 14 minutes on cold boot without snapshot warm pool',
      },
      {
        id: 'dep-302',
        serviceName: 'BM25 Inverted Index Coordinator',
        protocol: 'gRPC',
        direction: 'Downstream',
        p99BudgetMs: 19,
        availabilitySla: 99.95,
        spofRisk: 'Moderate',
        fallbackStrategy: 'Degrade gracefully to dense-only retrieval when lexical shard times out',
      },
      {
        id: 'dep-303',
        serviceName: 'Segment Snapshot Object Store',
        protocol: 'S3/Object',
        direction: 'Datastore',
        p99BudgetMs: 22,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Multi-region object bucket with byte-range parallel download',
      },
    ],
    findings: [
      {
        id: 'find-301',
        section: '6. Observability & Telemetry',
        title: 'Missing Observability & Telemetry specification section',
        severity: 'Critical',
        impact: 'No defined metrics for recall@10 degradation, HNSW graph fragmentation, or segment merge stall duration.',
        remediation: 'Add Section 6 defining recall drift probes, mmap page-fault counters, and P99 merge pause alerts.',
        owner: 'A. Patel',
      },
      {
        id: 'find-302',
        section: '7. Rollout & Backfill Plan',
        title: 'Missing Rollout & Backfill migration plan for 400M existing vectors',
        severity: 'Critical',
        impact: 'Uncoordinated index rebuild will saturate NVMe IOPS and breach P99 <= 65ms query budget.',
        remediation: 'Add Section 7 specifying offline bulk graph builder on spot fleet + shadow traffic replay.',
        owner: 'A. Patel',
      },
      {
        id: 'find-303',
        section: '1. Context & Architecture',
        title: 'Cumulative dependency latency (79ms) exceeds spec P99 target (65ms)',
        severity: 'Critical',
        impact: 'Serial execution of HNSW (38ms) + BM25 (19ms) + S3 fetch (22ms) breaches 65ms SLA by 14ms.',
        remediation: 'Execute HNSW dense search and BM25 lexical search concurrently in parallel goroutines.',
        owner: 'D. Okafor',
      },
    ],
    capacityEnvelope: buildCapacityEnvelope(12000, 65),
  },
  {
    id: 'spec-rfc-078',
    code: 'RFC-078',
    title: 'Double-Entry Ledger Sharding & Settlement Engine',
    domain: 'Core FinTech Infrastructure',
    author: 'M. Vance',
    updatedAt: '2026-10-31',
    status: 'In Review',
    targetQps: 28000,
    p99TargetMs: 25,
    availabilityTargetPct: 99.995,
    monthlyStorageTb: 31.5,
    estimatedMonthlyCostUsd: 19800,
    rawMarkdown: `# 1. Context & Architecture
The Double-Entry Ledger Sharding Engine partitions high-volume merchant settlement journals across 64 deterministic CockroachDB/PostgreSQL logical shards. Every journal posting MUST enforce zero-sum balance invariants (\`SUM(debits) - SUM(credits) == 0\`) within a serializable transaction boundary.

# 2. Data Model & Storage
Ledger entries are immutable and append-only; UPDATE and DELETE statements MUST be revoked at the database role level. Corrections SHALL be executed exclusively via compensating reversal journal entries referencing \`original_journal_id\`. Hot account balances MUST use optimistic concurrency control with monotonic \`version_seq\`.

# 3. API & Wire Contracts
The \`PostJournalBatch\` gRPC service MUST require an RFC-8785 canonical JSON payload signature and a deterministic \`idempotency_key\`. Responses SHALL return the committed \`hlc_timestamp\` and cryptographic merkle leaf hash.

# 4. Security & Access Control
All ledger shard connections MUST authenticate via short-lived IAM database tokens (15-minute expiry) over TLS 1.3. Row-level security policies REQUIRED for multi-entity regulatory isolation.

# 5. Failure Modes & SLA
Cross-shard two-phase commit (2PC) coordinator locks MUST time out after 120ms and trigger automatic deterministic abort-and-compensate workers. Hot merchant accounts exceeding 500 writes/sec SHOULD automatically split into 16 sub-account virtual buckets to eliminate lock contention.

# 6. Observability & Telemetry
Continuous reconciliation daemons MUST verify merkle tree root hashes every 60 seconds and page on-call within 5 seconds if any shard exhibits a non-zero trial balance discrepancy.

# 7. Rollout & Backfill Plan
Migration from the monolithic ledger MUST run dual-read/dual-write shadow verification for 14 days with 100% automated parity diffing before shifting authoritative reads to the sharded cluster.`,
    dependencies: [
      {
        id: 'dep-401',
        serviceName: 'Sharded Ledger Cluster (64 Partitions)',
        protocol: 'PostgreSQL',
        direction: 'Datastore',
        p99BudgetMs: 11,
        availabilitySla: 99.995,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Raft consensus quorum (5 replicas per range) with automated leaseholder transfer',
      },
      {
        id: 'dep-402',
        serviceName: '2PC Distributed Lock Coordinator',
        protocol: 'gRPC',
        direction: 'Upstream',
        p99BudgetMs: 6,
        availabilitySla: 99.99,
        spofRisk: 'Moderate',
        fallbackStrategy: 'Stateless coordinator backed by replicated WAL intent log',
      },
      {
        id: 'dep-403',
        serviceName: 'Sub-Account Bucket Router',
        protocol: 'Redis',
        direction: 'Upstream',
        p99BudgetMs: 3,
        availabilitySla: 99.99,
        spofRisk: 'Mitigated',
        fallbackStrategy: 'Deterministic hash fallback when dynamic hot-key map is unreachable',
      },
    ],
    findings: [
      {
        id: 'find-401',
        section: '5. Failure Modes & SLA',
        title: 'Sub-account virtual bucket aggregation latency during EOD close',
        severity: 'Warning',
        impact: 'Summing 16 virtual sub-buckets adds 4.2ms read overhead during real-time balance checks.',
        remediation: 'Maintain materialized balance summary updated asynchronously within 50ms.',
        owner: 'M. Vance',
      },
      {
        id: 'find-402',
        section: '2. Data Model & Storage',
        title: 'Append-only DDL role revocation verified in migration script',
        severity: 'Resolved',
        impact: 'Guarantees SOC-2 and PCI-DSS immutable audit trail compliance.',
        remediation: 'Database trigger and REVOKE UPDATE/DELETE policy verified in CI.',
        owner: 'M. Vance',
      },
    ],
    capacityEnvelope: buildCapacityEnvelope(28000, 25),
  },
];
