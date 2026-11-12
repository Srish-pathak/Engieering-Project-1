import { useEffect, useMemo, useState, type FormEvent } from 'react';
import {
  AlertCircle,
  ArrowUpRight,
  BookOpen,
  Check,
  ChevronRight,
  CircleHelp,
  Code2,
  ExternalLink,
  FileCode2,
  GitBranch,
  Github,
  LoaderCircle,
  RefreshCw,
  Shield,
  TriangleAlert,
} from 'lucide-react';

type Tab = 'overview' | 'review' | 'complexity' | 'security' | 'documentation' | 'architecture' | 'evaluation';
type Finding = { file?: string; line?: string | number; severity?: string; rule?: string; category?: string; description?: string; fix?: string; evidence?: string; deterministic?: boolean };
type Analysis = Record<string, any>;

const tabs: { id: Tab; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'review', label: 'Findings' },
  { id: 'complexity', label: 'Complexity' },
  { id: 'security', label: 'Security' },
  { id: 'documentation', label: 'Docs' },
  { id: 'architecture', label: 'Architecture' },
  { id: 'evaluation', label: 'Evaluation' },
];

function errorMessage(status: number, message?: string) {
  if (status === 403) return 'GitHub denied access or rate-limited this request. Check that the repository is public, or add a GitHub token in Render Environment settings.';
  if (status === 404) return 'Repository or branch not found. Check the URL and branch name, and confirm the repository is accessible.';
  if (status === 429) return 'GitHub rate limit reached. Wait a little before trying again, or configure a GitHub token.';
  return message || `Repository analysis failed (HTTP ${status}).`;
}

function Card({ children, className = '' }: { children: React.ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-slate-800 bg-slate-900/70 ${className}`}>{children}</section>;
}

function Metric({ label, value, tone = 'text-slate-100' }: { label: string; value: React.ReactNode; tone?: string }) {
  return <div className="rounded-lg border border-slate-800 bg-slate-950/70 p-4"><div className="text-xs text-slate-400">{label}</div><div className={`mt-2 text-2xl font-semibold tabular-nums ${tone}`}>{value}</div></div>;
}

function FindingsList({ findings, empty = 'No findings in this category.' }: { findings: Finding[]; empty?: string }) {
  if (!findings.length) return <div className="rounded-lg border border-dashed border-slate-700 p-8 text-center text-sm text-slate-400">{empty}</div>;
  return <div className="space-y-3">{findings.map((item, index) => {
    const severity = (item.severity || 'info').toLowerCase();
    const color = severity === 'critical' || severity === 'high' ? 'text-rose-300 bg-rose-400/10 border-rose-400/25' : severity === 'warning' || severity === 'medium' ? 'text-amber-200 bg-amber-400/10 border-amber-400/25' : 'text-cyan-200 bg-cyan-400/10 border-cyan-400/25';
    return <article key={`${item.file}-${item.line}-${item.rule}-${index}`} className="rounded-lg border border-slate-800 bg-slate-950/60 p-4">
      <div className="flex flex-wrap items-center gap-2 text-xs"><span className={`rounded-full border px-2 py-1 font-semibold uppercase ${color}`}>{severity}</span><span className="font-mono text-slate-400">{item.file || 'source'}{item.line ? `:${item.line}` : ''}</span>{item.rule && <span className="rounded bg-slate-800 px-2 py-1 font-mono text-slate-300">{item.rule}</span>}</div>
      <p className="mt-3 text-sm leading-6 text-slate-100">{item.description || 'Review this finding.'}</p>
      {item.evidence && <pre className="mt-3 overflow-x-auto rounded-md bg-black/40 p-3 text-xs text-slate-300">{item.evidence}</pre>}
      {item.fix && <p className="mt-3 text-sm text-emerald-300"><span className="font-medium">Suggested fix:</span> {item.fix}</p>}
    </article>;
  })}</div>;
}

export default function GitHubWorkspace() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [result, setResult] = useState<Analysis | null>(null);
  const [repoName, setRepoName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [apiReady, setApiReady] = useState<boolean | null>(null);
  const [apiConfigured, setApiConfigured] = useState(false);
  const [evaluation, setEvaluation] = useState<Analysis | null>(null);
  const [showSecondary, setShowSecondary] = useState(false);
  const [secondaryCode, setSecondaryCode] = useState('');

  useEffect(() => {
    fetch('/api/status').then((r) => r.json()).then((data) => {
      setApiReady(data.status === 'ok');
      setApiConfigured(Boolean(data.api_key_configured));
    }).catch(() => setApiReady(false));
  }, []);

  const findings: Finding[] = result?.bugs || result?.deterministic_bugs || [];
  const securityFindings = useMemo(() => findings.filter((f) => f.category === 'security' || /security|secret|injection|unsafe/i.test(`${f.rule || ''} ${f.source || ''}`)), [findings]);
  const critical = findings.filter((f) => f.severity === 'critical' || f.severity === 'high').length;
  const warnings = findings.filter((f) => f.severity === 'warning' || f.severity === 'medium').length;
  const inventory: any[] = result?.files_inventory || [];

  async function connectRepository(event: FormEvent) {
    event.preventDefault();
    setError('');
    const raw = repoUrl.trim().replace(/\.git$/i, '').replace(/\/+$/, '');
    const valid = /^(?:https?:\/\/github\.com\/)?[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(raw);
    if (!valid) {
      setError('Enter a GitHub repository URL like https://github.com/owner/repository.');
      return;
    }
    setBusy(true);
    setResult(null);
    try {
      const response = await fetch('/api/import-github', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_url: raw, branch: branch.trim(), use_ai: apiConfigured }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.valid) throw new Error(errorMessage(response.status, data.error));
      setRepoName(data.repo || raw.replace(/^https?:\/\/github\.com\//, ''));
      setResult(data.result);
      setActiveTab('overview');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not connect to GitHub.');
    } finally { setBusy(false); }
  }

  async function analyzePasted(event: FormEvent) {
    event.preventDefault();
    if (!secondaryCode.trim()) return;
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: secondaryCode, language: 'Python', project_name: 'Pasted source', input_mode: 'paste', use_ai: apiConfigured }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error(data.summary || `Analysis failed (HTTP ${response.status}).`);
      setRepoName('Pasted source'); setResult(data); setActiveTab('overview'); setShowSecondary(false);
    } catch (e) { setError(e instanceof Error ? e.message : 'Analysis failed.'); }
    finally { setBusy(false); }
  }

  async function loadEvaluation() {
    setActiveTab('evaluation');
    if (evaluation) return;
    try { const response = await fetch('/api/evaluate'); const data = await response.json(); if (response.ok) setEvaluation(data); }
    catch { setError('Could not load evaluation data.'); }
  }

  function selectTab(tab: Tab) { if (tab === 'evaluation') void loadEvaluation(); else setActiveTab(tab); }

  const complexity = result?.complexity || {};
  const docs = result?.documentation || {};
  const facts = (result?.ast_facts || []).flatMap((f: any) => f.functions || []);

  return <div className="min-h-screen bg-[#070b14] text-slate-100">
    <header className="sticky top-0 z-20 border-b border-slate-800 bg-[#090e19]/95 backdrop-blur">
      <div className="mx-auto flex max-w-[1440px] items-center justify-between gap-4 px-4 py-3 sm:px-7">
        <a href="#home" onClick={(e) => { e.preventDefault(); setActiveTab('overview'); }} className="flex shrink-0 items-center gap-2.5 font-semibold tracking-tight"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-400 text-slate-950"><Code2 size={18}/></span><span>TechSpec<span className="text-cyan-300">Analyser</span></span></a>
        <nav className="flex min-w-0 items-center gap-1 overflow-x-auto" aria-label="Analysis sections">{tabs.map((tab) => <button key={tab.id} onClick={() => selectTab(tab.id)} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs transition ${activeTab === tab.id ? 'bg-slate-800 text-cyan-200' : 'text-slate-400 hover:bg-slate-800/70 hover:text-white'}`}>{tab.id === 'review' && result ? `Findings (${findings.length})` : tab.id === 'security' && result ? `Security (${securityFindings.length})` : tab.label}</button>)}</nav>
        <div className="hidden shrink-0 items-center gap-2 text-xs sm:flex"><span className={`h-2 w-2 rounded-full ${apiReady ? 'bg-emerald-400' : apiReady === false ? 'bg-rose-400' : 'bg-slate-500'}`}/><span className="text-slate-400">{apiReady ? 'Service online' : apiReady === false ? 'Service unavailable' : 'Checking service'}</span></div>
      </div>
    </header>

    <main className="mx-auto max-w-[1440px] space-y-6 px-4 py-6 sm:px-7 sm:py-8">
      {!result && <div className="mx-auto max-w-4xl pt-4 sm:pt-12">
        <div className="mb-7 flex items-center gap-2 text-xs font-medium uppercase tracking-[0.18em] text-cyan-300"><Github size={16}/> Repository intelligence</div>
        <h1 className="max-w-3xl text-3xl font-semibold tracking-tight sm:text-5xl">Review the code behind your next push.</h1>
        <p className="mt-4 max-w-2xl text-sm leading-6 text-slate-400 sm:text-base">Connect a GitHub repository to inspect source, security risks, complexity, and documentation in one pass.</p>
        <Card className="mt-8 p-5 sm:p-7">
          <form onSubmit={connectRepository} className="space-y-4">
            <label className="block"><span className="mb-2 block text-sm font-medium">GitHub repository</span><span className="flex items-center gap-3 rounded-lg border border-slate-700 bg-[#070b14] px-3.5 focus-within:border-cyan-400"><Github size={18} className="shrink-0 text-slate-400"/><input value={repoUrl} onChange={(e) => setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repository" className="min-w-0 flex-1 bg-transparent py-3.5 font-mono text-sm outline-none placeholder:text-slate-600" autoComplete="url" required/><a title="Open GitHub" href="https://github.com" target="_blank" rel="noreferrer" className="text-slate-500 hover:text-cyan-300"><ExternalLink size={16}/></a></span></label>
            <div className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end"><label className="block"><span className="mb-2 flex items-center gap-2 text-sm font-medium"><GitBranch size={15} className="text-slate-400"/>Branch <span className="font-normal text-slate-500">(optional)</span></span><input value={branch} onChange={(e) => setBranch(e.target.value)} placeholder="Default branch" className="w-full rounded-lg border border-slate-700 bg-[#070b14] px-3.5 py-3 font-mono text-sm outline-none placeholder:text-slate-600 focus:border-cyan-400"/></label><button disabled={busy || apiReady === false} className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-cyan-400 px-5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-60">{busy ? <LoaderCircle className="animate-spin" size={17}/> : <ArrowUpRight size={17}/>} {busy ? 'Analyzing repository…' : 'Connect & analyze'}</button></div>
          </form>
          {error && <div role="alert" className="mt-4 flex gap-2 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200"><AlertCircle size={17} className="mt-0.5 shrink-0"/><span>{error}</span></div>}
          <div className="mt-5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-4 text-xs text-slate-500"><span className="flex items-center gap-1.5"><Shield size={14} className="text-emerald-300"/>Source is analyzed, not executed.</span><span>Public repositories work without a token.</span></div>
        </Card>
        <div className="mt-5 flex items-center justify-between rounded-lg border border-slate-800/80 bg-slate-900/40 px-4 py-3"><span className="text-sm text-slate-400">Need a quick check instead?</span><button onClick={() => setShowSecondary((v) => !v)} className="text-sm font-medium text-cyan-300 hover:text-cyan-200">{showSecondary ? 'Hide manual analysis' : 'Paste source'} <ChevronRight className={`inline transition ${showSecondary ? 'rotate-90' : ''}`} size={15}/></button></div>
        {showSecondary && <Card className="mt-3 p-4"><form onSubmit={analyzePasted} className="space-y-3"><textarea value={secondaryCode} onChange={(e) => setSecondaryCode(e.target.value)} rows={7} placeholder="Paste a small source snippet…" className="w-full rounded-lg border border-slate-700 bg-[#070b14] p-3 font-mono text-xs leading-5 outline-none focus:border-cyan-400"/><button disabled={busy || !secondaryCode.trim()} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-cyan-400 disabled:opacity-50">Analyze snippet</button></form></Card>}
        <div className="mt-8 grid gap-3 sm:grid-cols-3"><div className="rounded-lg border border-slate-800/80 p-4"><FileCode2 size={18} className="text-cyan-300"/><div className="mt-3 text-sm font-medium">Repository scan</div><div className="mt-1 text-xs text-slate-500">Find source files and inspect the selected branch.</div></div><div className="rounded-lg border border-slate-800/80 p-4"><TriangleAlert size={18} className="text-amber-300"/><div className="mt-3 text-sm font-medium">Actionable findings</div><div className="mt-1 text-xs text-slate-500">Prioritize security risks and critical issues.</div></div><div className="rounded-lg border border-slate-800/80 p-4"><BookOpen size={18} className="text-blue-300"/><div className="mt-3 text-sm font-medium">Codebase context</div><div className="mt-1 text-xs text-slate-500">Review structure, complexity, and docs.</div></div></div>
      </div>}

      {result && <>
        <div className="flex flex-wrap items-start justify-between gap-4"><div><button onClick={() => { setResult(null); setError(''); }} className="mb-3 text-xs text-slate-500 hover:text-cyan-300">← Analyze another repository</button><div className="flex flex-wrap items-center gap-2"><Github size={20} className="text-cyan-300"/><h1 className="text-xl font-semibold sm:text-2xl">{repoName}</h1>{result.valid_syntax ? <span className="rounded-full border border-emerald-400/25 bg-emerald-400/10 px-2.5 py-1 text-xs text-emerald-300">Scan complete</span> : <span className="rounded-full border border-rose-400/25 bg-rose-400/10 px-2.5 py-1 text-xs text-rose-200">Syntax issues</span>}</div><p className="mt-2 text-sm text-slate-400">{inventory.length} source files scanned <span className="mx-1 text-slate-700">·</span>{result.execution_ms || '—'} ms</p></div><div className="flex gap-2"><a href={`https://github.com/${repoName}`} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-cyan-400"><ExternalLink size={14}/>Open repo</a><button onClick={() => void connectRepository({ preventDefault() {} } as FormEvent)} disabled={busy} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-cyan-400 disabled:opacity-50"><RefreshCw size={14} className={busy ? 'animate-spin' : ''}/>Rescan</button></div></div>
        {error && <div role="alert" className="rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</div>}
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-5"><Metric label="Health score" value={`${result.overall_score ?? '—'}/10`} tone="text-cyan-200"/><Metric label="Critical" value={critical} tone={critical ? 'text-rose-300' : 'text-emerald-300'}/><Metric label="Warnings" value={warnings} tone={warnings ? 'text-amber-200' : 'text-emerald-300'}/><Metric label="Security" value={securityFindings.length} tone={securityFindings.length ? 'text-rose-300' : 'text-emerald-300'}/><Metric label="Complexity" value={complexity.rating || '—'} tone="text-blue-200"/></div>
        <div className="flex gap-1 overflow-x-auto border-b border-slate-800">{tabs.map((tab) => <button key={tab.id} onClick={() => selectTab(tab.id)} className={`whitespace-nowrap border-b-2 px-4 py-3 text-sm ${activeTab === tab.id ? 'border-cyan-300 text-cyan-200' : 'border-transparent text-slate-400 hover:text-white'}`}>{tab.id === 'review' ? `Findings (${findings.length})` : tab.id === 'security' ? `Security (${securityFindings.length})` : tab.label}</button>)}</div>
        {activeTab === 'overview' && <div className="grid gap-4 lg:grid-cols-[1.4fr_1fr]"><Card className="p-5"><h2 className="text-base font-semibold">Review summary</h2><p className="mt-3 text-sm leading-6 text-slate-300">{result.summary || 'Repository scan completed.'}</p><div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Files" value={result.files_count ?? inventory.length}/><Metric label="Functions" value={complexity.function_count ?? facts.length}/><Metric label="Doc coverage" value={`${result.documentation?.doc_coverage_before ?? complexity.doc_coverage_pct ?? 0}%`}/><Metric label="AI review" value={result.ai_status === 'ok' ? 'Enabled' : 'Static'} tone={result.ai_status === 'ok' ? 'text-emerald-300' : 'text-slate-300'}/></div></Card><Card className="p-5"><h2 className="text-base font-semibold">Top findings</h2><div className="mt-4"><FindingsList findings={[...findings].sort((a,b) => (a.severity === 'critical' ? -1 : 0) - (b.severity === 'critical' ? -1 : 0)).slice(0,4)} empty="No issues detected in scanned files."/></div></Card></div>}
        {activeTab === 'review' && <Card className="p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-semibold">Code findings</h2><span className="text-xs text-slate-500">{findings.length} total</span></div><FindingsList findings={findings} empty="No findings for this repository."/></Card>}
        {activeTab === 'security' && <Card className="p-5"><div className="mb-4 flex items-center gap-2"><Shield size={18} className="text-cyan-300"/><h2 className="font-semibold">Security findings</h2></div><FindingsList findings={securityFindings} empty="No security-related patterns were flagged."/></Card>}
        {activeTab === 'complexity' && <Card className="overflow-hidden"><div className="grid grid-cols-2 gap-px bg-slate-800 sm:grid-cols-4"><Metric label="Average CC" value={complexity.average_complexity ?? '—'}/><Metric label="Maximum CC" value={complexity.max_complexity ?? '—'}/><Metric label="Maintainability" value={complexity.maintainability_index ?? 'N/A'}/><Metric label="High complexity" value={complexity.high_complexity_count ?? 0}/></div><div className="overflow-x-auto p-5"><h2 className="mb-4 font-semibold">Functions</h2><table className="w-full min-w-[600px] text-left text-sm"><thead className="text-xs text-slate-500"><tr><th className="pb-3">Function</th><th className="pb-3">File</th><th className="pb-3">Line</th><th className="pb-3 text-right">CC</th><th className="pb-3 text-right">Grade</th></tr></thead><tbody className="divide-y divide-slate-800">{(complexity.details || []).map((fn: any, i: number) => <tr key={`${fn.name}-${i}`}><td className="py-3 font-mono text-cyan-100">{fn.name}()</td><td className="py-3 font-mono text-xs text-slate-400">{fn.file}</td><td className="py-3 text-slate-400">{fn.line}</td><td className="py-3 text-right">{fn.complexity}</td><td className="py-3 text-right">{fn.rank}</td></tr>)}</tbody></table>{!(complexity.details || []).length && <p className="text-sm text-slate-400">No function-level metrics available.</p>}</div></Card>}
        {activeTab === 'documentation' && <div className="grid gap-4 lg:grid-cols-2"><Card className="p-5"><h2 className="font-semibold">Documentation coverage</h2><div className="mt-5 text-4xl font-semibold text-cyan-200">{docs.doc_coverage_before ?? complexity.doc_coverage_pct ?? 0}%</div><div className="mt-4 h-2 overflow-hidden rounded-full bg-slate-800"><div className="h-full rounded-full bg-cyan-300" style={{ width: `${Math.min(100, docs.doc_coverage_before ?? complexity.doc_coverage_pct ?? 0)}%` }}/></div><p className="mt-3 text-xs text-slate-500">Existing documented symbols</p></Card><Card className="p-5"><h2 className="font-semibold">Missing documentation</h2><div className="mt-4 space-y-2">{(docs.suggested_docstrings || []).slice(0,15).map((item: any, i: number) => <div key={i} className="flex justify-between gap-3 rounded-md bg-slate-950/70 px-3 py-2 text-sm"><span className="font-mono text-slate-200">{item.name}</span><span className="text-xs text-slate-500">{item.file}:{item.line}</span></div>)}</div>{!(docs.suggested_docstrings || []).length && <p className="mt-3 text-sm text-slate-400">No documentation gaps reported.</p>}</Card></div>}
        {activeTab === 'architecture' && <div className="grid gap-4 lg:grid-cols-2"><Card className="p-5"><h2 className="font-semibold">Source files</h2><div className="mt-4 max-h-96 space-y-1 overflow-auto">{inventory.map((file, i) => <div key={`${file.path}-${i}`} className="flex items-center gap-2 rounded-md px-2 py-2 text-sm hover:bg-slate-800/60"><FileCode2 size={15} className="shrink-0 text-cyan-300"/><span className="truncate font-mono text-slate-300">{file.path}</span><span className="ml-auto text-xs text-slate-500">{file.language}</span></div>)}</div></Card><Card className="p-5"><h2 className="font-semibold">Architecture summary</h2><p className="mt-3 text-sm leading-6 text-slate-300">{docs.architecture_summary || 'No architecture summary available.'}</p><h3 className="mt-6 text-sm font-medium">Repository structure</h3><pre className="mt-3 max-h-72 overflow-auto rounded-lg bg-slate-950 p-4 text-xs leading-5 text-cyan-100">{docs.directory_structure || `${repoName}/\n${inventory.map((f) => `├── ${f.path}`).join('\n')}`}</pre></Card></div>}
        {activeTab === 'evaluation' && <Card className="p-5"><div className="flex items-center gap-2"><CircleHelp size={18} className="text-cyan-300"/><h2 className="font-semibold">Analysis evaluation</h2></div>{evaluation?.approaches ? <div className="mt-4 overflow-x-auto"><table className="w-full min-w-[600px] text-left text-sm"><thead className="text-xs text-slate-500"><tr><th className="pb-3">Approach</th><th className="pb-3 text-right">Precision</th><th className="pb-3 text-right">Recall</th><th className="pb-3 text-right">F1</th><th className="pb-3 text-right">Time</th></tr></thead><tbody className="divide-y divide-slate-800">{evaluation.approaches.map((item: any) => <tr key={item.id}><td className="py-3">{item.name}</td><td className="py-3 text-right">{item.precision}</td><td className="py-3 text-right">{item.recall}</td><td className="py-3 text-right text-cyan-200">{item.f1_score}</td><td className="py-3 text-right">{item.execution_time_ms} ms</td></tr>)}</tbody></table></div> : <p className="mt-3 text-sm text-slate-400">{evaluation ? 'Evaluation data is unavailable.' : 'Loading evaluation…'}</p>}</Card>}
        <footer className="flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-4 text-xs text-slate-500"><span>Repository analysis complete</span><span className="flex items-center gap-1.5"><Check size={14} className="text-emerald-300"/>Source code is not executed</span></footer>
      </>}
    </main>
  </div>;
}
