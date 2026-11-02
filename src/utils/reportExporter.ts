export function buildMarkdownReport(result: any): string {
  const stamp = new Date().toLocaleString('en-GB');
  const bugs: any[] = result.bugs || [];
  const crit = bugs.filter((b) => b.severity === 'critical').length;
  const warn = bugs.filter((b) => b.severity === 'warning').length;
  const info = bugs.filter((b) => b.severity === 'info').length;
  const comp = result.complexity || {};
  const docs = result.documentation || {};
  const agents: any[] = result.agents || [];

  const lines: string[] = [
    `# TechSpecAnalyser — Multi-Agent Code Review & Documentation Report`,
    `*Project: ${result.project_name || 'CodeLens Workspace'} | Language: ${result.language || 'Python'} | Generated: ${stamp}*`,
    ``,
    `## 1. Executive Summary & Code Health Score: ${result.overall_score}/10`,
    `- **Rule-Based Deterministic Score:** ${result.score_details?.rule_score ?? result.overall_score}/10`,
    `- **AI Assessment Blend (40%):** ${result.score_details?.ai_score ?? 'N/A (Deterministic Mode)'}`,
    `- **Findings Breakdown:** Critical: **${crit}** | Warnings: **${warn}** | Info: **${info}**`,
    `- **Documentation Coverage:** ${docs.doc_coverage_before ?? 0}% existing → ${docs.doc_coverage_after ?? 100}% with proposed docstrings`,
    ``,
    result.summary || 'No summary.',
    ``,
    `## 2. Six-Agent Orchestrator Summary`,
    `| Agent | Status | Latency | Summary |`,
    `|---|---|---|---|`,
    ...agents.map(
      (a) => `| **${a.name}** | ${a.status} | ${a.latency_ms}ms | ${a.summary} |`
    ),
    ``,
    `## 3. Consolidated Review Findings (Synthesizer Output)`,
  ];

  if (bugs.length === 0) {
    lines.push('No issues detected.');
  } else {
    for (const b of bugs) {
      const origin = b.deterministic ? 'Deterministic Static Check' : `AI Suggestion (${b.source}) — Verify`;
      lines.push(
        `- **[${String(b.severity).toUpperCase()}]** \`${b.file || 'main.py'}:${b.line}\` (${origin}, rule: \`${b.rule || 'general'}\`): ${b.description}`
      );
      if (b.evidence) {
        lines.push(`  - Evidence: \`${b.evidence}\``);
      }
      if (b.fix) {
        lines.push(`  - Fix: ${b.fix}`);
      }
    }
  }

  lines.push(``, `## 4. Software Metrics & Cyclomatic Complexity`);
  lines.push(`- **Method:** ${comp.method || 'radon'} (${comp.analysis_type || 'measured'})`);
  lines.push(`- **Average Cyclomatic Complexity:** ${comp.average_complexity ?? 0} (Grade ${comp.rating || 'N/A'})`);
  lines.push(`- **Highest Function Complexity:** ${comp.max_complexity ?? 0}`);
  if (comp.maintainability_index != null) {
    lines.push(`- **Maintainability Index:** ${comp.maintainability_index} (${comp.mi_label})`);
  }

  if (comp.details?.length) {
    lines.push(``, `| Function | File | Line | Complexity | Grade |`);
    lines.push(`|---|---|---|---|---|`);
    for (const d of comp.details) {
      lines.push(`| \`${d.name}\` | ${d.file || 'main.py'} | ${d.line} | ${d.complexity} | ${d.rank} |`);
    }
  }

  if (docs.readme_markdown) {
    lines.push(``, `## 5. Generated Project Documentation`, ``, docs.readme_markdown);
  }

  if (result.improved_code) {
    const langTag = String(result.language || 'python').toLowerCase().replace('c++', 'cpp');
    lines.push(
      ``,
      `## 6. AI-Proposed Improved Code (Developer Verification Required)`,
      `\`\`\`${langTag}`,
      result.improved_code.trimEnd(),
      `\`\`\``
    );
  }

  return lines.join('\n') + '\n';
}

export function buildStandaloneHtmlReport(result: any): string {
  const esc = (s: any) =>
    String(s ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');

  const bugs: any[] = result.bugs || [];
  const comp = result.complexity || {};
  const agents: any[] = result.agents || [];
  const rows =
    bugs
      .map(
        (b) => `<tr>
          <td><code>${esc(b.file || 'main.py')}:${esc(b.line)}</code></td>
          <td class="${esc(b.severity)}">${esc(String(b.severity).toUpperCase())}</td>
          <td>${b.deterministic ? 'Deterministic Static' : esc(b.source)}</td>
          <td>${esc(b.description)}${b.fix ? `<br><em>Fix: ${esc(b.fix)}</em>` : ''}</td>
        </tr>`
      )
      .join('') || `<tr><td colspan="4">No issues detected.</td></tr>`;

  const agentRows = agents
    .map(
      (a) => `<tr>
        <td><strong>${esc(a.name)}</strong></td>
        <td>${esc(a.status)}</td>
        <td>${esc(a.latency_ms)}ms</td>
        <td>${esc(a.summary)}</td>
      </tr>`
    )
    .join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>TechSpecAnalyser Report — ${esc(result.project_name)}</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, sans-serif; max-width: 960px; margin: 2rem auto; padding: 0 1rem; color: #0f172a; line-height: 1.55; }
  h1, h2 { color: #0f172a; }
  .meta { color: #475569; font-size: 0.9rem; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: 0.9rem; }
  th, td { border: 1px solid #cbd5e1; padding: 0.5rem 0.7rem; text-align: left; vertical-align: top; }
  th { background: #f1f5f9; }
  pre { background: #0b1020; color: #e7ebfa; padding: 1rem; border-radius: 8px; overflow-x: auto; font-size: 0.85rem; }
  .critical { color: #dc2626; font-weight: 700; }
  .warning { color: #d97706; font-weight: 700; }
  .info { color: #2563eb; font-weight: 700; }
  .score { font-size: 2rem; font-weight: 800; color: #0284c7; }
</style>
</head>
<body>
  <h1>CodeLens AI — Multi-Agent Code Review &amp; Documentation Report</h1>
  <p class="meta">Project: ${esc(result.project_name)} | Language: ${esc(result.language)} | Score: <span class="score">${esc(result.overall_score)}/10</span></p>
  <h2>1. Summary</h2>
  <p>${esc(result.summary)}</p>
  <h2>2. Six-Agent Orchestrator Execution</h2>
  <table><tr><th>Agent</th><th>Status</th><th>Latency</th><th>Summary</th></tr>${agentRows}</table>
  <h2>3. Consolidated Findings</h2>
  <table><tr><th>Location</th><th>Severity</th><th>Source</th><th>Description &amp; Fix</th></tr>${rows}</table>
  <h2>4. Complexity &amp; Maintainability</h2>
  <p>Method: <strong>${esc(comp.method)}</strong> (${esc(comp.analysis_type)}) — Average Complexity: <strong>${esc(comp.average_complexity)}</strong> (Grade ${esc(comp.rating)}), Max: <strong>${esc(comp.max_complexity)}</strong>, Maintainability Index: <strong>${esc(comp.maintainability_index ?? 'N/A')}</strong></p>
  ${result.improved_code ? `<h2>5. AI-Proposed Improved Code</h2><pre>${esc(result.improved_code)}</pre>` : ''}
</body>
</html>`;
}

export function triggerFileDownload(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
