import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  Code2,
  Download,
  FileArchive,
  FileCode2,
  Github,
  GitBranch,
  LoaderCircle,
  ShieldCheck,
  Upload,
} from 'lucide-react';

type Section = 'dashboard' | 'results' | 'security' | 'reports';
type InputMode = 'zip' | 'file' | 'paste' | null;
type Finding = {
  file?: string; line?: number | string; severity?: string; rule?: string;
  category?: string; description?: string; fix?: string; evidence?: string;
  deterministic?: boolean; source?: string;
};
type Analysis = Record<string, any>;

const navigation: { id: Section; label: string }[] = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'results', label: 'Analysis Results' },
  { id: 'security', label: 'Security' },
  { id: 'reports', label: 'Reports' },
];

// Keep provider error bodies out of the interface. GitHub intentionally returns
// 404 for some inaccessible private repositories as well as missing repositories.
function friendlyError(status: number) {
  if (status === 403) return 'GitHub refused the request. This public repository is available, so the service may have reached GitHub’s unauthenticated API limit. Try again later or configure GITHUB_TOKEN in the service environment.';
  if (status === 404) return 'Repository or selected branch was not found or is not accessible. Check the URL and branch name.';
  if (status === 429) return 'GitHub request limit reached. Wait a little and try again, or configure a GitHub access token.';
  if (status === 401) return 'GitHub could not authenticate this request. Check the service’s GitHub token configuration.';
  if (status >= 500) return 'The analysis service had a temporary problem. Please try again shortly.';
  return 'We could not analyze that repository. Check the URL and try again.';
}

function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-xl border border-slate-800 bg-[#101827] ${className}`}>{children}</section>;
}

function healthStatus(score: number) {
  if (score >= 90) return 'Excellent';
  if (score >= 75) return 'Good';
  if (score >= 50) return 'Needs Improvement';
  return 'Poor';
}

function severityOf(finding: Finding) {
  const severity = (finding.severity || '').toLowerCase();
  if (['critical', 'high', 'error'].includes(severity)) return 'Critical';
  if (['warning', 'medium', 'moderate'].includes(severity)) return 'Warning';
  return 'Suggestion';
}

function titleOf(finding: Finding) {
  return finding.rule
    ? finding.rule.replace(/[-_]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase())
    : finding.category === 'security' ? 'Security concern' : 'Code improvement';
}

function downloadFile(filename: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

export default function GitHubWorkspace() {
  const [repoUrl, setRepoUrl] = useState('');
  const [branch, setBranch] = useState('');
  const [branchOpen, setBranchOpen] = useState(false);
  const [section, setSection] = useState<Section>('dashboard');
  const [inputMode, setInputMode] = useState<InputMode>(null);
  const [pasteCode, setPasteCode] = useState('');
  const [result, setResult] = useState<Analysis | null>(null);
  const [repoName, setRepoName] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [aiConfigured, setAiConfigured] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const zipRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('/api/status')
      .then((response) => response.json())
      .then((data) => setAiConfigured(Boolean(data.api_key_configured)))
      .catch(() => setAiConfigured(false));
  }, []);

  const findings: Finding[] = result?.bugs || result?.deterministic_bugs || [];
  const criticalFindings = useMemo(() => findings.filter((item) => severityOf(item) === 'Critical'), [findings]);
  const warningFindings = useMemo(() => findings.filter((item) => severityOf(item) === 'Warning'), [findings]);
  const suggestionFindings = useMemo(() => findings.filter((item) => severityOf(item) === 'Suggestion'), [findings]);
  const securityFindings = useMemo(() => findings.filter((item) => item.category === 'security' || /security|secret|injection|unsafe/i.test(`${item.rule || ''} ${item.source || ''}`)), [findings]);
  const aiFindings = useMemo(() => findings.filter((item) => item.deterministic === false || String(item.source || '').startsWith('agent:')), [findings]);
  const score = typeof result?.overall_score === 'number' ? Math.round(result.overall_score * 10) : null;
  const complexity = result?.complexity || {};
  const docs = result?.documentation || {};
  const repoFiles: any[] = result?.files_inventory || [];

  function setCurrentResult(data: Analysis, name: string) {
    setResult(data);
    setRepoName(name);
    setSection('results');
    setError('');
  }

  async function analyzeRepository(event: FormEvent) {
    event.preventDefault();
    const normalized = repoUrl.trim().replace(/\.git$/i, '').replace(/\/+$/, '');
    if (!/^(?:https?:\/\/github\.com\/)?[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(normalized)) {
      setError('Enter a GitHub repository URL, for example https://github.com/owner/repository.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await fetch('/api/import-github', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        // An omitted ref tells GitHub to use the repository's own default branch.
        body: JSON.stringify({ repo_url: normalized, ...(branch.trim() ? { branch: branch.trim() } : {}), use_ai: aiConfigured }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.valid) throw new Error(friendlyError(response.status));
      setCurrentResult(data.result, data.repo || normalized.replace(/^https?:\/\/github\.com\//, ''));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Could not connect to GitHub.');
    } finally { setBusy(false); }
  }

  async function analyzeFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setBusy(true); setError('');
    try {
      const extension = file.name.split('.').pop()?.toLowerCase();
      const language = ['cpp', 'cc', 'cxx', 'h', 'hpp'].includes(extension || '') ? 'C++' : extension === 'java' ? 'Java' : 'Python';
      const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: await file.text(), language, file_name: file.name, project_name: file.name, input_mode: 'file', use_ai: aiConfigured }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error('The file could not be analyzed.');
      setCurrentResult(data, file.name);
    } catch { setError('The file could not be analyzed. Please try again.'); }
    finally { setBusy(false); }
  }

  async function analyzeZip(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    setBusy(true); setError('');
    try {
      const bytes = new Uint8Array(await file.arrayBuffer());
      let binary = '';
      for (let offset = 0; offset < bytes.length; offset += 0x8000) binary += String.fromCharCode(...bytes.subarray(offset, Math.min(offset + 0x8000, bytes.length)));
      const response = await fetch('/api/upload-zip', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ zip_base64: btoa(binary), project_name: file.name.replace(/\.zip$/i, ''), use_ai: aiConfigured }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || !data.valid) throw new Error('This ZIP could not be analyzed. Check that it contains supported source files.');
      setCurrentResult(data.result, file.name.replace(/\.zip$/i, ''));
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'The ZIP could not be analyzed.'); }
    finally { setBusy(false); }
  }

  async function analyzePasted(event: FormEvent) {
    event.preventDefault();
    if (!pasteCode.trim()) return;
    setBusy(true); setError('');
    try {
      const response = await fetch('/api/analyze', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: pasteCode, language: 'Python', project_name: 'Pasted code', input_mode: 'paste', use_ai: aiConfigured }) });
      const data = await response.json().catch(() => ({}));
      if (!response.ok || data.error) throw new Error('Code could not be analyzed.');
      setCurrentResult(data, 'Pasted code');
    } catch { setError('Code could not be analyzed. Please try again.'); }
    finally { setBusy(false); }
  }

  function renderFindingGroup(title: string, items: Finding[], color: string) {
    return <section className="space-y-3" key={title}>
      <div className="flex items-center justify-between"><h3 className={`font-semibold ${color}`}>{title}</h3><span className="text-xs text-slate-500">{items.length}</span></div>
      {!items.length ? <p className="rounded-lg border border-dashed border-slate-800 px-4 py-5 text-sm text-slate-500">No {title.toLowerCase()} found.</p> : items.map((item, index) => <article key={`${item.file}-${item.line}-${item.rule}-${index}`} className="rounded-lg border border-slate-800 bg-[#0b1220] p-4">
        <div className="flex flex-wrap items-start justify-between gap-2"><h4 className="font-medium text-slate-100">{titleOf(item)}</h4><span className="font-mono text-xs text-slate-400">{item.file || 'Source file'}{item.line ? `:${item.line}` : ''}</span></div>
        <p className="mt-2 text-sm leading-6 text-slate-300"><span className="text-slate-500">Why it matters: </span>{item.description || 'Review this code for a possible issue.'}</p>
        {item.fix && <p className="mt-2 text-sm leading-6 text-emerald-200"><span className="text-emerald-400">How to fix it: </span>{item.fix}</p>}
        {item.evidence && <details className="mt-3"><summary className="cursor-pointer text-xs text-slate-500">Show code location</summary><pre className="mt-2 overflow-x-auto rounded-md bg-black/30 p-3 font-mono text-xs text-slate-300">{item.evidence}</pre></details>}
      </article>)}
    </section>;
  }

  function renderDashboard() {
    if (result) return <div className="mx-auto max-w-5xl"><div className="mb-6 flex items-center justify-between gap-4"><div><p className="text-sm text-cyan-300">Repository</p><h1 className="mt-1 text-2xl font-semibold">{repoName}</h1></div><button onClick={() => { setResult(null); setSection('dashboard'); }} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-cyan-400"><ArrowLeft size={16}/>New analysis</button></div><Panel className="p-5 sm:p-7"><div className="flex items-center gap-2"><CheckCircle2 className="text-emerald-300" size={20}/><h2 className="text-lg font-semibold">Your repository is ready</h2></div><p className="mt-2 text-sm text-slate-400">{repoFiles.length} source files checked. Open Analysis Results to see issues and suggested fixes.</p><button onClick={() => setSection('results')} className="mt-5 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300">View analysis results</button></Panel></div>;

    return <div className="mx-auto max-w-3xl pt-4 sm:pt-12">
      <div className="mb-8 flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-cyan-400 text-slate-950"><Code2 size={23}/></span><span className="text-xl font-semibold tracking-tight">TechSpec<span className="text-cyan-300">Analyser</span></span></div>
      <h1 className="text-3xl font-semibold tracking-tight sm:text-5xl">Analyze Your GitHub Repository</h1>
      <p className="mt-4 text-base leading-7 text-slate-400">Find bugs, security issues and code quality problems in seconds.</p>
      <Panel className="mt-8 p-5 sm:p-7"><form onSubmit={analyzeRepository} className="space-y-5">
        <label className="block"><span className="mb-2 block text-sm font-medium text-slate-200">GitHub Repository URL</span><span className="flex items-center gap-3 rounded-lg border border-slate-700 bg-[#080e18] px-3.5 focus-within:border-cyan-400"><Github size={18} className="shrink-0 text-slate-400"/><input value={repoUrl} onChange={(event) => setRepoUrl(event.target.value)} placeholder="https://github.com/owner/repository" className="min-w-0 flex-1 bg-transparent py-3.5 font-mono text-sm outline-none placeholder:text-slate-600" autoComplete="url" required/></span></label>
        <details className="rounded-lg border border-slate-800 bg-[#0b1220] px-3.5 py-3" open={branchOpen} onToggle={(event) => setBranchOpen((event.currentTarget as HTMLDetailsElement).open)}><summary className="flex cursor-pointer list-none items-center gap-2 text-sm text-slate-400 hover:text-slate-200"><ChevronDown size={15}/>Choose Branch <span className="text-xs text-slate-600">(optional)</span></summary><label className="mt-3 block"><span className="mb-2 flex items-center gap-2 text-xs text-slate-500"><GitBranch size={14}/>Leave empty to use this repository’s default branch</span><input value={branch} onChange={(event) => setBranch(event.target.value)} placeholder="Branch or tag" className="w-full rounded-lg border border-slate-700 bg-[#080e18] px-3 py-2.5 font-mono text-sm outline-none placeholder:text-slate-600 focus:border-cyan-400"/></label></details>
        <button type="submit" disabled={busy} className="flex min-h-12 w-full items-center justify-center gap-2 rounded-lg bg-cyan-400 px-5 text-sm font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-wait disabled:opacity-70">{busy ? <LoaderCircle className="animate-spin" size={18}/> : <Github size={18}/>} {busy ? 'Analyzing repository…' : 'Analyze Repository'}</button>
      </form>
      {error && <div role="alert" className="mt-4 flex gap-2 rounded-lg border border-rose-400/30 bg-rose-400/10 p-3 text-sm text-rose-200"><AlertCircle size={17} className="mt-0.5 shrink-0"/>{error}</div>}
      <input ref={zipRef} type="file" accept=".zip" className="hidden" onChange={analyzeZip}/><input ref={fileRef} type="file" accept=".py,.cpp,.cc,.cxx,.h,.hpp,.java" className="hidden" onChange={analyzeFile}/>
      <div className="mt-6 border-t border-slate-800 pt-5"><p className="mb-3 text-xs font-medium uppercase tracking-wide text-slate-500">Other ways to analyze</p><div className="grid gap-2 sm:grid-cols-3"><button onClick={() => zipRef.current?.click()} className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-3 text-sm text-slate-300 hover:border-cyan-400 hover:text-white"><FileArchive size={16}/>Upload Project ZIP</button><button onClick={() => fileRef.current?.click()} className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-3 text-sm text-slate-300 hover:border-cyan-400 hover:text-white"><Upload size={16}/>Upload Code File</button><button onClick={() => setInputMode(inputMode === 'paste' ? null : 'paste')} className="flex items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-3 text-sm text-slate-300 hover:border-cyan-400 hover:text-white"><FileCode2 size={16}/>Paste Code</button></div>{inputMode === 'paste' && <form onSubmit={analyzePasted} className="mt-4 space-y-3"><textarea value={pasteCode} onChange={(event) => setPasteCode(event.target.value)} rows={6} placeholder="Paste code here…" className="w-full rounded-lg border border-slate-700 bg-[#080e18] p-3 font-mono text-xs leading-5 outline-none focus:border-cyan-400"/><button disabled={busy || !pasteCode.trim()} className="rounded-lg bg-slate-700 px-4 py-2 text-sm font-medium text-white hover:bg-slate-600 disabled:opacity-50">{busy ? 'Analyzing…' : 'Analyze pasted code'}</button></form>}</div>
      <details className="mt-5 border-t border-slate-800 pt-4"><summary className="flex cursor-pointer list-none items-center gap-2 text-xs text-slate-500 hover:text-slate-300"><ChevronDown size={14}/>Advanced details</summary><p className="mt-3 text-xs leading-5 text-slate-500">Public GitHub repositories can be analyzed directly. Private repositories require a GitHub access token configured on the server. Submitted source is analyzed as text and is not run.</p></details>
    </Panel></div>;
  }

  function renderResults() {
    if (!result) return <EmptyState message="Analyze a repository to see its results here." onClick={() => setSection('dashboard')}/>;
    const status = score === null ? 'Not available' : healthStatus(score);
    const aiUnavailable = !aiConfigured || result.ai_status !== 'ok';
    return <div className="mx-auto max-w-5xl space-y-6"><div><p className="text-sm text-cyan-300">Analysis Results</p><h1 className="mt-1 text-2xl font-semibold">{repoName}</h1></div>
      <Panel className="p-5 sm:p-6"><div className="flex flex-wrap items-center justify-between gap-5"><div><p className="text-sm text-slate-400">Code Health Score</p><div className="mt-2 flex items-baseline gap-2"><span className="text-5xl font-semibold text-cyan-200">{score ?? '—'}</span><span className="text-slate-500">/100</span></div></div><div><p className="text-sm text-slate-400">Overall status</p><span className="mt-2 inline-flex rounded-full border border-cyan-300/25 bg-cyan-300/10 px-3 py-1.5 text-sm font-medium text-cyan-200">{status}</span></div><div><p className="text-sm text-slate-400">Total issues</p><p className="mt-2 text-3xl font-semibold">{findings.length}</p></div></div>{result.summary && <p className="mt-5 border-t border-slate-800 pt-4 text-sm leading-6 text-slate-300">{result.summary}</p>}</Panel>
      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]"><Panel className="space-y-6 p-5"><h2 className="text-lg font-semibold">Issues Found</h2>{renderFindingGroup('Critical', criticalFindings, 'text-rose-300')}{renderFindingGroup('Warnings', warningFindings, 'text-amber-200')}{renderFindingGroup('Suggestions', suggestionFindings, 'text-cyan-200')}</Panel><div className="space-y-4"><Panel className="p-5"><h2 className="font-semibold">Code Quality</h2><dl className="mt-4 space-y-4 text-sm"><QualityRow label="Code complexity" value={complexity.rating ? `${complexity.rating} (average ${complexity.average_complexity ?? '—'})` : 'Not available'}/><QualityRow label="Maintainability" value={complexity.maintainability_index != null ? `${complexity.maintainability_index}/100` : 'Not available'}/><QualityRow label="Documentation quality" value={`${docs.doc_coverage_before ?? complexity.doc_coverage_pct ?? 0}% documented`}/><QualityRow label="Security status" value={securityFindings.length ? `${securityFindings.length} issue(s) to review` : 'No issues found'} tone={securityFindings.length ? 'text-amber-200' : 'text-emerald-300'}/></dl></Panel><Panel className="p-5"><h2 className="font-semibold">AI Review</h2>{aiUnavailable ? <p className="mt-3 text-sm text-slate-400">AI Review Temporarily Unavailable</p> : aiFindings.length ? <><p className="mt-2 text-xs text-slate-500">AI-generated findings · check before applying</p><div className="mt-4 space-y-3">{aiFindings.map((item, index) => <div key={`${item.file}-${item.line}-${index}`} className="rounded-lg bg-[#0b1220] p-3"><p className="text-sm font-medium">{titleOf(item)}</p><p className="mt-1 text-xs leading-5 text-slate-400">{item.description}</p>{item.fix && <p className="mt-2 text-xs text-emerald-200">Fix: {item.fix}</p>}</div>)}</div></> : <p className="mt-3 text-sm text-slate-400">AI review is available; no additional AI findings were reported.</p>}</Panel></div></div>
      <Panel className="p-5"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">Scanned files</h2><p className="mt-1 text-xs text-slate-500">{repoFiles.length} files included in this analysis</p></div><button onClick={() => setAdvancedOpen(!advancedOpen)} className="text-sm text-cyan-300">{advancedOpen ? 'Hide file list' : 'Show file list'}</button></div>{advancedOpen && <ul className="mt-4 grid gap-2 sm:grid-cols-2">{repoFiles.map((file, index) => <li key={`${file.path}-${index}`} className="flex items-center gap-2 truncate rounded-md bg-[#0b1220] px-3 py-2 text-xs text-slate-300"><FileCode2 size={14} className="shrink-0 text-cyan-300"/><span className="truncate font-mono">{file.path}</span></li>)}</ul>}</Panel>
    </div>;
  }

  function renderSecurity() {
    if (!result) return <EmptyState message="Analyze a repository to see its security results." onClick={() => setSection('dashboard')}/>;
    return <div className="mx-auto max-w-5xl space-y-5"><div><p className="text-sm text-cyan-300">Security</p><h1 className="mt-1 text-2xl font-semibold">Security issues</h1></div><Panel className="p-5"><div className="flex items-center gap-2"><ShieldCheck size={19} className={securityFindings.length ? 'text-amber-300' : 'text-emerald-300'}/><p className="font-medium">{securityFindings.length ? `${securityFindings.length} item(s) need review` : 'No security issues found'}</p></div><p className="mt-2 text-sm text-slate-400">{securityFindings.length ? 'Review each item and apply the suggested fix where appropriate.' : 'No security-related patterns were flagged in the files checked.'}</p></Panel>{securityFindings.map((finding, index) => <Panel key={`${finding.file}-${finding.line}-${index}`} className="p-5"><div className="flex flex-wrap justify-between gap-2"><h2 className="font-semibold">{titleOf(finding)}</h2><span className="font-mono text-xs text-slate-400">{finding.file || 'Source file'}{finding.line ? `:${finding.line}` : ''}</span></div><p className="mt-3 text-sm leading-6 text-slate-300">{finding.description}</p>{finding.fix && <p className="mt-3 text-sm text-emerald-200"><b>How to fix it: </b>{finding.fix}</p>}</Panel>)}</div>;
  }

  function renderReports() {
    if (!result) return <EmptyState message="Analyze a repository to create a report." onClick={() => setSection('dashboard')}/>;
    const report = { repository: repoName, score_out_of_100: score, status: score === null ? 'Not available' : healthStatus(score), total_issues: findings.length, findings, complexity, documentation: docs };
    const textReport = `${repoName}\nCode health: ${score ?? 'Not available'}/100 (${score === null ? 'Not available' : healthStatus(score)})\nIssues: ${findings.length}\n\n${findings.map((item) => `${severityOf(item)} — ${titleOf(item)} — ${item.file || 'Source file'}${item.line ? `:${item.line}` : ''}\n${item.description || ''}${item.fix ? `\nHow to fix: ${item.fix}` : ''}`).join('\n\n')}`;
    const safeName = repoName.replace(/[^a-z0-9-]/gi, '-') || 'analysis';
    return <div className="mx-auto max-w-3xl space-y-5"><div><p className="text-sm text-cyan-300">Reports</p><h1 className="mt-1 text-2xl font-semibold">Download your analysis</h1><p className="mt-2 text-sm text-slate-400">Save a readable copy of the results.</p></div><Panel className="p-5"><button onClick={() => downloadFile(`${safeName}-report.txt`, textReport, 'text/plain')} className="inline-flex items-center gap-2 rounded-lg bg-cyan-400 px-4 py-2.5 text-sm font-semibold text-slate-950 hover:bg-cyan-300"><Download size={17}/>Download Report</button><details className="mt-5 border-t border-slate-800 pt-4"><summary className="cursor-pointer text-sm text-slate-400">More export options</summary><button onClick={() => downloadFile(`${safeName}-report.json`, JSON.stringify(report, null, 2), 'application/json')} className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 hover:border-cyan-400">Download JSON data</button><p className="mt-2 text-xs text-slate-500">PDF export is not enabled in this deployment.</p></details></Panel></div>;
  }

  return <div className="min-h-screen bg-[#080d17] text-slate-100"><header className="sticky top-0 z-20 border-b border-slate-800 bg-[#080d17]/95 backdrop-blur"><div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3 sm:px-7"><button onClick={() => setSection('dashboard')} className="flex items-center gap-2.5 font-semibold"><span className="grid h-8 w-8 place-items-center rounded-lg bg-cyan-400 text-slate-950"><Code2 size={18}/></span><span>TechSpec<span className="text-cyan-300">Analyser</span></span></button><nav className="flex gap-1 overflow-x-auto" aria-label="Main navigation">{navigation.map((item) => <button key={item.id} onClick={() => setSection(item.id)} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs sm:text-sm ${section === item.id ? 'bg-slate-800 text-cyan-200' : 'text-slate-400 hover:bg-slate-800 hover:text-white'}`}>{item.label}</button>)}</nav></div></header><main className="mx-auto max-w-6xl px-4 py-7 sm:px-7 sm:py-10">{section === 'dashboard' && renderDashboard()}{section === 'results' && renderResults()}{section === 'security' && renderSecurity()}{section === 'reports' && renderReports()}</main></div>;
}

function QualityRow({ label, value, tone = 'text-slate-200' }: { label: string; value: string; tone?: string }) {
  return <div className="flex items-start justify-between gap-3 border-b border-slate-800 pb-3 last:border-0 last:pb-0"><dt className="text-slate-400">{label}</dt><dd className={`text-right ${tone}`}>{value}</dd></div>;
}

function EmptyState({ message, onClick }: { message: string; onClick: () => void }) {
  return <div className="mx-auto max-w-3xl"><Panel className="p-8 text-center"><p className="text-slate-300">{message}</p><button onClick={onClick} className="mt-4 rounded-lg bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950">Go to Dashboard</button></Panel></div>;
}
