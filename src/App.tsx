import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  AlertTriangle,
  BookOpen,
  CheckCircle2,
  Code2,
  Copy,
  Cpu,
  Download,
  FileArchive,
  FileCode,
  FileText,
  FolderTree,
  GitCompare,
  History,
  Layers,
  Moon,
  Play,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Sun,
  Trash2,
  Upload,
} from 'lucide-react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import {
  LANGUAGE_CONFIG,
  SAMPLES,
  SupportedLanguage,
  TRACEABILITY_MATRIX,
  VIVA_DEMO_STEPS,
  createSampleProjectZipBase64,
  createUnsafeTraversalZipBase64,
} from './data/codelensSamples';
import {
  buildMarkdownReport,
  buildStandaloneHtmlReport,
  triggerFileDownload,
} from './utils/reportExporter';

type ActiveTab =
  | 'overview'
  | 'review'
  | 'complexity'
  | 'security'
  | 'documentation'
  | 'architecture'
  | 'evaluation';

type InputMode = 'paste' | 'file' | 'zip' | 'github';

function scoreBand(score: number): { label: string; colorHex: string; textClass: string } {
  if (score >= 8.5) {
    return { label: 'Excellent', colorHex: '#5BD6A0', textClass: 'text-emerald-600 dark:text-[#5BD6A0]' };
  }
  if (score >= 7.0) {
    return { label: 'Good', colorHex: '#5BD6A0', textClass: 'text-emerald-600 dark:text-[#5BD6A0]' };
  }
  if (score >= 5.0) {
    return { label: 'Needs Work', colorHex: '#FFC857', textClass: 'text-amber-600 dark:text-[#FFC857]' };
  }
  return { label: 'Poor', colorHex: '#FF6B7A', textClass: 'text-rose-600 dark:text-[#FF6B7A]' };
}

export default function App() {
  // Theme state (Default: Dark Space-Slate #0B1020 with Light Mode toggle)
  const [isDark, setIsDark] = useState(true);
  useEffect(() => {
    const root = document.documentElement;
    if (isDark) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }
  }, [isDark]);

  // Navigation tab
  const [activeTab, setActiveTab] = useState<ActiveTab>('overview');

  // Input system state
  const [inputMode, setInputMode] = useState<InputMode>('paste');
  const [language, setLanguage] = useState<SupportedLanguage>('Python');
  const [selectedSample, setSelectedSample] = useState<string>(
    'Payment Service (Synopsis Sec. 14 Showcase)'
  );
  const [projectName, setProjectName] = useState<string>('payment_service_project');
  const [fileName, setFileName] = useState<string>('payment_service.py');
  const [codeInput, setCodeInput] = useState<string>(
    SAMPLES.Python['Payment Service (Synopsis Sec. 14 Showcase)']
  );
  const [projectFiles, setProjectFiles] = useState<
    Array<{ path: string; language: string; code: string }>
  >([]);
  const [activeProjectFileIdx, setActiveProjectFileIdx] = useState<number>(0);
  const [ignoredZipFiles, setIgnoredZipFiles] = useState<string[]>([]);
  const [zipAlert, setZipAlert] = useState<{ type: 'error' | 'success'; message: string } | null>(
    null
  );
  const [githubRepoUrl, setGithubRepoUrl] = useState<string>(
    'https://github.com/StudyTrigger/ai-code-reviewer'
  );
  const [githubBranch, setGithubBranch] = useState<string>('');
  const [showGitPushGuide, setShowGitPushGuide] = useState<boolean>(false);

  // AI & Backend status
  const [apiKeyConfigured, setApiKeyConfigured] = useState<boolean>(false);
  const [modelName, setModelName] = useState<string>('gemini-3.8-flash');
  const [useAi, setUseAi] = useState<boolean>(true);

  // Analysis execution state
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [pipelineStage, setPipelineStage] = useState<string>('Ready');
  const [result, setResult] = useState<any | null>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [evaluationData, setEvaluationData] = useState<any | null>(null);
  const [isEvaluating, setIsEvaluating] = useState<boolean>(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  // Code Review tab filters
  const [severityFilter, setSeverityFilter] = useState<'all' | 'critical' | 'warning' | 'info'>(
    'all'
  );
  const [originFilter, setOriginFilter] = useState<'all' | 'deterministic' | 'ai'>('all');
  const [diffViewMode, setDiffViewMode] = useState<'side-by-side' | 'unified'>('side-by-side');

  // Security verification statuses (interactive developer verification)
  const [securityVerifications, setSecurityVerifications] = useState<
    Record<string, 'Unverified' | 'Confirmed' | 'Dismissed'>
  >({});

  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const zipInputRef = useRef<HTMLInputElement | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3200);
  };

  // Initial load: fetch status, history, evaluation, and run initial analysis on default showcase
  useEffect(() => {
    async function bootstrap() {
      try {
        const [statusRes, histRes, evalRes] = await Promise.all([
          fetch('/api/status').then((r) => r.json()),
          fetch('/api/history').then((r) => r.json()),
          fetch('/api/evaluate').then((r) => r.json()),
        ]);
        setApiKeyConfigured(Boolean(statusRes.api_key_configured));
        if (statusRes.model) setModelName(statusRes.model);
        if (histRes.history) setHistory(histRes.history);
        if (evalRes.approaches) setEvaluationData(evalRes);
      } catch {
        // Ignore bootstrap network errors
      }
      // Run initial deterministic + multi-agent analysis so dashboard is populated on load
      await triggerAnalysis({
        codeOverride: SAMPLES.Python['Payment Service (Synopsis Sec. 14 Showcase)'],
        langOverride: 'Python',
        fileOverride: 'payment_service.py',
        projOverride: 'payment_service_project',
      });
    }
    bootstrap();
  }, []);

  const triggerAnalysis = async (opts?: {
    codeOverride?: string;
    langOverride?: SupportedLanguage;
    fileOverride?: string;
    projOverride?: string;
    filesOverride?: Array<{ path: string; language: string; code: string }>;
    modeOverride?: InputMode;
  }) => {
    const targetCode = opts?.codeOverride ?? codeInput;
    const targetLang = opts?.langOverride ?? language;
    const targetFile = opts?.fileOverride ?? fileName;
    const targetProj = opts?.projOverride ?? projectName;
    const targetFiles = opts?.filesOverride ?? (inputMode === 'zip' && projectFiles.length > 0 ? projectFiles : undefined);
    const targetMode = opts?.modeOverride ?? inputMode;

    if (!targetFiles && !targetCode.trim()) {
      showToast('Editor is empty. Paste code or select a sample case first.');
      return;
    }

    setIsAnalyzing(true);
    setPipelineStage('1/5 Checking syntax & AST structure...');
    try {
      const timer1 = setTimeout(() => setPipelineStage('2/5 Running deterministic static rules...'), 220);
      const timer2 = setTimeout(() => setPipelineStage('3/5 Computing McCabe CC & Radon MI...'), 450);
      const timer3 = setTimeout(
        () =>
          setPipelineStage(
            useAi
              ? '4/5 Orchestrating 6 specialized AI review agents...'
              : '4/5 Building evidence-grounded static synthesis...'
          ),
        700
      );

      const response = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          project_name: targetProj,
          input_mode: targetMode,
          code: targetCode,
          language: targetLang,
          file_name: targetFile,
          files: targetFiles,
          use_ai: useAi,
        }),
      });
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);

      const data = await response.json();
      setResult(data);
      if (data.history) {
        setHistory(data.history);
      }
      setPipelineStage('Complete');
    } catch (err: any) {
      showToast(`Analysis error: ${err?.message || 'Failed to reach server'}`);
      setPipelineStage('Error');
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleLanguageChange = (newLang: SupportedLanguage) => {
    setLanguage(newLang);
    const firstSample = Object.keys(SAMPLES[newLang])[0];
    setSelectedSample(firstSample);
    const sampleCode = SAMPLES[newLang][firstSample];
    setCodeInput(sampleCode);
    const ext = LANGUAGE_CONFIG[newLang].ext;
    setFileName(`submission${ext}`);
    setProjectFiles([]);
    setInputMode('paste');
    setZipAlert(null);
  };

  const handleSampleChange = (sampleKey: string) => {
    setSelectedSample(sampleKey);
    const sampleCode = SAMPLES[language][sampleKey];
    setCodeInput(sampleCode);
    const ext = LANGUAGE_CONFIG[language].ext;
    const slug = sampleKey.toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_|_$/g, '');
    setFileName(`${slug}${ext}`);
    setProjectName(`${slug}_project`);
    setProjectFiles([]);
    setInputMode('paste');
    setZipAlert(null);
  };

  const handleSingleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const text = await file.text();
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase();
    let detectedLang: SupportedLanguage = language;
    if (ext === '.py') detectedLang = 'Python';
    else if (['.cpp', '.cc', '.cxx', '.h', '.hpp'].includes(ext)) detectedLang = 'C++';
    else if (ext === '.java') detectedLang = 'Java';

    setLanguage(detectedLang);
    setFileName(file.name);
    setProjectName(file.name.replace(/\.[^.]+$/, ''));
    setCodeInput(text);
    setProjectFiles([]);
    setInputMode('file');
    setZipAlert(null);
    showToast(`Loaded file ${file.name} (${detectedLang})`);
    await triggerAnalysis({
      codeOverride: text,
      langOverride: detectedLang,
      fileOverride: file.name,
      projOverride: file.name.replace(/\.[^.]+$/, ''),
      modeOverride: 'file',
    });
  };

  const processZipBase64 = async (b64: string, archiveName: string) => {
    setIsAnalyzing(true);
    setZipAlert(null);
    setPipelineStage('Validating ZIP archive & checking for path traversal...');
    try {
      const response = await fetch('/api/upload-zip', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          zip_base64: b64,
          project_name: archiveName.replace(/\.zip$/i, ''),
          use_ai: useAi,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.valid) {
        setZipAlert({
          type: 'error',
          message: data.error || 'Archive validation failed.',
        });
        showToast(data.error || 'Blocked invalid ZIP archive');
        return;
      }

      const analyzedResult = data.result;
      const inventory = analyzedResult.files_inventory || [];
      setInputMode('zip');
      setProjectName(archiveName.replace(/\.zip$/i, ''));
      setProjectFiles(inventory);
      setActiveProjectFileIdx(0);
      if (inventory.length > 0) {
        setCodeInput(inventory[0].code);
        setFileName(inventory[0].path);
        setLanguage((inventory[0].language as SupportedLanguage) || 'Python');
      }
      setIgnoredZipFiles(data.ignored_files || []);
      setResult(analyzedResult);
      setZipAlert({
        type: 'success',
        message: `Validated & analyzed ${inventory.length} source file(s) from ${archiveName}. Ignored ${(data.ignored_files || []).length} non-source/venv file(s).`,
      });
    } catch (err: any) {
      setZipAlert({
        type: 'error',
        message: err?.message || 'Failed to process ZIP archive.',
      });
    } finally {
      setIsAnalyzing(false);
      setPipelineStage('Complete');
    }
  };

  const handleZipFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const buf = await file.arrayBuffer();
    const bytes = new Uint8Array(buf);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    const b64 = btoa(binary);
    await processZipBase64(b64, file.name);
  };

  const handleLoadSampleZip = async () => {
    const b64 = await createSampleProjectZipBase64();
    await processZipBase64(b64, 'payment_platform_project.zip');
  };

  const handleTestUnsafeZip = async () => {
    const b64 = await createUnsafeTraversalZipBase64();
    await processZipBase64(b64, 'malicious_path_traversal.zip');
  };

  const handleConnectGithubRepo = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!githubRepoUrl.trim()) {
      showToast('Enter a GitHub repository URL first.');
      return;
    }
    setIsAnalyzing(true);
    setZipAlert(null);
    setPipelineStage('Connecting to GitHub repository & fetching source tree...');
    try {
      const response = await fetch('/api/import-github', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          repo_url: githubRepoUrl.trim(),
          branch: githubBranch.trim(),
          use_ai: useAi,
        }),
      });
      const data = await response.json();
      if (!response.ok || !data.valid) {
        setZipAlert({
          type: 'error',
          message: data.error || 'Could not fetch GitHub repository.',
        });
        showToast(data.error || 'GitHub connection failed');
        return;
      }

      const analyzedResult = data.result;
      const inventory = analyzedResult.files_inventory || [];
      setInputMode('github');
      setProjectName(data.repo || 'github_repo');
      setProjectFiles(inventory);
      setActiveProjectFileIdx(0);
      if (inventory.length > 0) {
        setCodeInput(inventory[0].code);
        setFileName(inventory[0].path);
        setLanguage((inventory[0].language as SupportedLanguage) || 'Python');
      }
      setIgnoredZipFiles(data.ignored_files || []);
      setResult(analyzedResult);
      setZipAlert({
        type: 'success',
        message: `Connected to GitHub repo ${data.repo} (${inventory.length} source files analyzed).`,
      });
      showToast(`Connected & analyzed GitHub repository ${data.repo}`);
    } catch (err: any) {
      setZipAlert({
        type: 'error',
        message: err?.message || 'GitHub repository connection error.',
      });
    } finally {
      setIsAnalyzing(false);
      setPipelineStage('Complete');
    }
  };

  const handleRunVivaStep = async (stepObj: (typeof VIVA_DEMO_STEPS)[number]) => {
    setLanguage(stepObj.language);
    setSelectedSample(stepObj.sampleName);
    const sampleCode = SAMPLES[stepObj.language][stepObj.sampleName];
    setCodeInput(sampleCode);
    const ext = LANGUAGE_CONFIG[stepObj.language].ext;
    const fname = `${stepObj.sampleName.toLowerCase().replace(/[^a-z0-9]+/g, '_')}${ext}`;
    setFileName(fname);
    setProjectName(`viva_step_${stepObj.step}`);
    setProjectFiles([]);
    setInputMode('paste');
    setActiveTab(stepObj.targetTab);
    await triggerAnalysis({
      codeOverride: sampleCode,
      langOverride: stepObj.language,
      fileOverride: fname,
      projOverride: `viva_step_${stepObj.step}`,
      modeOverride: 'paste',
    });
    showToast(`Viva Demo Step ${stepObj.step}: ${stepObj.title}`);
  };

  const handleReopenHistory = (entry: any) => {
    if (!entry) return;
    setLanguage((entry.language as SupportedLanguage) || 'Python');
    setCodeInput(entry.code || '');
    setProjectName(entry.project_name || 'Restored Project');
    if (entry.result) {
      setResult(entry.result);
    }
    setActiveTab('overview');
    showToast(`Restored review from ${entry.time}`);
  };

  const handleClearHistory = async () => {
    await fetch('/api/history', { method: 'DELETE' });
    setHistory([]);
    showToast('Cleared SQLite review history');
  };

  const handleRefreshEvaluation = async () => {
    setIsEvaluating(true);
    try {
      const res = await fetch('/api/evaluate').then((r) => r.json());
      setEvaluationData(res);
      showToast('Re-evaluated Approaches A, B, and C against ground-truth dataset');
    } finally {
      setIsEvaluating(false);
    }
  };

  // Derived metrics & filtered bugs
  const bugs: any[] = result?.bugs || [];
  const counts = useMemo(() => {
    return {
      critical: bugs.filter((b) => b.severity === 'critical').length,
      warning: bugs.filter((b) => b.severity === 'warning').length,
      info: bugs.filter((b) => b.severity === 'info').length,
      deterministic: bugs.filter((b) => b.deterministic).length,
      ai: bugs.filter((b) => !b.deterministic).length,
    };
  }, [bugs]);

  const filteredBugs = useMemo(() => {
    return bugs.filter((b) => {
      const matchSev = severityFilter === 'all' || b.severity === severityFilter;
      const matchOrigin =
        originFilter === 'all' ||
        (originFilter === 'deterministic' && b.deterministic) ||
        (originFilter === 'ai' && !b.deterministic);
      return matchSev && matchOrigin;
    });
  }, [bugs, severityFilter, originFilter]);

  const securityFindings = useMemo(() => {
    return bugs.filter(
      (b) =>
        b.category === 'security' ||
        [
          'hardcoded-secret',
          'sql-injection-risk',
          'dangerous-call',
          'unsafe-deserialization',
          'subprocess-shell-true',
          'unsafe-call',
          'possible-leak',
        ].includes(b.rule) ||
        String(b.source || '').includes('security')
    );
  }, [bugs]);

  const complexity = result?.complexity || null;
  const documentation = result?.documentation || null;
  const agents: any[] = result?.agents || [];
  const overallScore = result?.overall_score ?? 0;
  const band = scoreBand(overallScore);

  const navItems: Array<{ id: ActiveTab; label: string }> = [
    { id: 'overview', label: 'Overview' },
    { id: 'review', label: `Code Review (${bugs.length})` },
    { id: 'complexity', label: 'Complexity' },
    { id: 'security', label: `Security (${securityFindings.length})` },
    { id: 'documentation', label: 'Documentation' },
    { id: 'architecture', label: 'Architecture' },
    { id: 'evaluation', label: 'Evaluation & Viva' },
  ];

  return (
    <div className="min-h-screen flex flex-col bg-slate-50 dark:bg-[#0B1020] text-slate-900 dark:text-[#E7EBFA] transition-colors">
      {/* Top Bar Contract: Strictly 3 zones separated by gap-8 */}
      <header className="sticky top-0 z-30 flex items-center justify-between gap-8 px-6 py-3.5 bg-white dark:bg-[#131A33] border-b border-slate-200 dark:border-[#263056]">
        {/* Zone 1: Single text element wordmark */}
        <a
          href="#top"
          onClick={(e) => {
            e.preventDefault();
            setActiveTab('overview');
          }}
          className="text-base font-bold tracking-tight text-slate-900 dark:text-[#E7EBFA] whitespace-nowrap shrink-0"
        >
          TechSpecAnalyser
        </a>

        {/* Zone 2: Concise single-line navigation links */}
        <nav className="flex items-center gap-5 text-xs font-medium text-slate-600 dark:text-[#98A2C8] overflow-x-auto">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              onClick={() => setActiveTab(item.id)}
              className={`py-1 transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                activeTab === item.id
                  ? 'text-slate-900 dark:text-[#4FD1E8] underline underline-offset-8 decoration-2 decoration-sky-500 dark:decoration-[#4FD1E8] font-semibold'
                  : 'hover:text-slate-900 dark:hover:text-white'
              }`}
            >
              {item.label}
            </button>
          ))}
        </nav>

        {/* Zone 3: Primary action */}
        <div className="flex items-center shrink-0">
          <button
            type="button"
            disabled={isAnalyzing}
            onClick={() => triggerAnalysis()}
            className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 disabled:opacity-60 rounded-lg transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            {isAnalyzing ? (
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 fill-current" />
            )}
            <span>{isAnalyzing ? 'Analyzing...' : 'Analyze Code'}</span>
          </button>
        </div>
      </header>

      {/* Main Workspace Container */}
      <div className="flex-1 flex flex-col lg:flex-row max-w-[1600px] w-full mx-auto">
        {/* Left Sidebar: Source Input Manager, Samples, ZIP Loader & Pipeline Controls */}
        <aside className="w-full lg:w-80 shrink-0 bg-white dark:bg-[#131A33] border-b lg:border-b-0 lg:border-r border-slate-200 dark:border-[#263056] p-5 flex flex-col gap-5">
          {/* Workspace Mode & Theme Switcher */}
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xs font-semibold text-slate-900 dark:text-[#E7EBFA]">
                Source Input Manager
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                Static-Grounded Multi-Agent Pipeline
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsDark((prev) => !prev)}
              title="Toggle Dark / Light Theme"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 text-xs font-medium bg-slate-100 dark:bg-[#1A2347] text-slate-700 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded-md hover:opacity-90 transition-opacity whitespace-nowrap shrink-0 cursor-pointer"
            >
              {isDark ? <Sun className="w-3.5 h-3.5 text-amber-400" /> : <Moon className="w-3.5 h-3.5" />}
              <span>{isDark ? 'Light' : 'Dark'}</span>
            </button>
          </div>

          {/* 4 Principal Input Modes (Paste, File, ZIP, GitHub Repo) */}
          <div className="grid grid-cols-2 gap-1 p-1 bg-slate-100 dark:bg-[#0B1020] rounded-lg border border-slate-200 dark:border-[#263056]">
            {(
              [
                { id: 'paste', label: 'Paste Code' },
                { id: 'file', label: 'Upload File' },
                { id: 'zip', label: 'Project ZIP' },
                { id: 'github', label: 'GitHub Repo' },
              ] as const
            ).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setInputMode(m.id)}
                className={`px-2 py-1.5 text-xs font-medium rounded-md transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                  inputMode === m.id
                    ? 'bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#4FD1E8] shadow-xs font-semibold'
                    : 'text-slate-600 dark:text-[#98A2C8] hover:text-slate-900 dark:hover:text-white'
                }`}
              >
                {m.label}
              </button>
            ))}
          </div>

          {/* Language & Test Case Selector */}
          <div className="flex flex-col gap-3">
            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-[#98A2C8] mb-1">
                Language ({LANGUAGE_CONFIG[language].badge})
              </label>
              <div className="grid grid-cols-3 gap-1.5">
                {(['Python', 'C++', 'Java'] as SupportedLanguage[]).map((lang) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => handleLanguageChange(lang)}
                    className={`py-1.5 px-2.5 text-xs font-medium rounded-md border transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                      language === lang
                        ? 'bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 border-sky-600 dark:border-[#4FD1E8] font-semibold'
                        : 'bg-slate-50 dark:bg-[#0B1020] text-slate-700 dark:text-[#E7EBFA] border-slate-200 dark:border-[#263056] hover:border-slate-400'
                    }`}
                  >
                    {lang}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-700 dark:text-[#98A2C8] mb-1">
                Load Ready-Made Test Case
              </label>
              <select
                value={selectedSample}
                onChange={(e) => handleSampleChange(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] rounded-md text-slate-900 dark:text-[#E7EBFA] focus:outline-none focus:border-sky-500 cursor-pointer"
              >
                {Object.keys(SAMPLES[language]).map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* File / ZIP / GitHub Upload Actions */}
          {inputMode === 'file' && (
            <div className="p-3.5 bg-slate-50 dark:bg-[#0B1020] border border-dashed border-slate-300 dark:border-[#263056] rounded-lg flex flex-col gap-2">
              <p className="text-xs text-slate-600 dark:text-[#98A2C8]">
                Upload a single source file (`.py`, `.cpp`, `.java`). Parsed via AST without executing code.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".py,.cpp,.cc,.cxx,.h,.hpp,.java"
                onChange={handleSingleFileUpload}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded-md hover:border-sky-500 transition-colors cursor-pointer"
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Select Source File (.py / .cpp / .java)</span>
              </button>
            </div>
          )}

          {inputMode === 'zip' && (
            <div className="p-3.5 bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] rounded-lg flex flex-col gap-2.5">
              <p className="text-xs text-slate-600 dark:text-[#98A2C8]">
                Upload a `.zip` project archive. Automatically blocks `..` path traversal and ignores `.venv`, `__pycache__`, and `node_modules`.
              </p>
              <input
                ref={zipInputRef}
                type="file"
                accept=".zip"
                onChange={handleZipFileUpload}
                className="hidden"
              />
              <button
                type="button"
                onClick={() => zipInputRef.current?.click()}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 rounded-md hover:opacity-90 transition-opacity cursor-pointer"
              >
                <FileArchive className="w-3.5 h-3.5" />
                <span>Upload Project Archive (.zip)</span>
              </button>

              <button
                type="button"
                onClick={handleLoadSampleZip}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white dark:bg-[#1A2347] text-slate-800 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded-md hover:border-sky-400 transition-colors cursor-pointer"
              >
                <FolderTree className="w-3.5 h-3.5 text-sky-500" />
                <span>Load Sample 3-File Project ZIP</span>
              </button>

              <button
                type="button"
                onClick={handleTestUnsafeZip}
                className="w-full inline-flex items-center justify-center gap-1.5 px-3 py-1.5 text-[11px] font-medium bg-rose-500/10 text-rose-600 dark:text-[#FF6B7A] border border-rose-500/30 rounded-md hover:bg-rose-500/20 transition-colors cursor-pointer"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Test ZIP Path-Traversal Guard (../)</span>
              </button>
            </div>
          )}

          {inputMode === 'github' && (
            <form
              onSubmit={handleConnectGithubRepo}
              className="p-3.5 bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] rounded-lg flex flex-col gap-2.5"
            >
              <div>
                <label className="block text-[11px] font-medium text-slate-700 dark:text-[#98A2C8] mb-1">
                  GitHub Repository URL or owner/repo
                </label>
                <input
                  type="text"
                  value={githubRepoUrl}
                  onChange={(e) => setGithubRepoUrl(e.target.value)}
                  placeholder="https://github.com/owner/repo"
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-md text-slate-900 dark:text-[#E7EBFA] focus:outline-none focus:border-sky-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-medium text-slate-700 dark:text-[#98A2C8] mb-1">
                  Branch / Tag (Optional, defaults to default branch)
                </label>
                <input
                  type="text"
                  value={githubBranch}
                  onChange={(e) => setGithubBranch(e.target.value)}
                  placeholder="main"
                  className="w-full px-2.5 py-1.5 text-xs font-mono bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-md text-slate-900 dark:text-[#E7EBFA] focus:outline-none focus:border-sky-500"
                />
              </div>

              <button
                type="submit"
                disabled={isAnalyzing}
                className="w-full inline-flex items-center justify-center gap-2 px-3 py-2 text-xs font-semibold bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 rounded-md hover:opacity-90 disabled:opacity-60 transition-opacity cursor-pointer"
              >
                <GitCompare className="w-3.5 h-3.5" />
                <span>Connect &amp; Analyze GitHub Repo</span>
              </button>

              {/* Connected Streamlit Community Cloud Deployment Card */}
              <div className="mt-1 p-2.5 rounded-md bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-semibold text-slate-800 dark:text-[#E7EBFA]">
                    Streamlit Cloud Runtime
                  </span>
                  <span className="font-mono text-[10px] text-emerald-600 dark:text-[#5BD6A0]">
                    SYNCED (app.py)
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 dark:text-[#98A2C8] leading-snug">
                  Root <code className="font-mono">app.py</code> &amp; <code className="font-mono">requirements.txt</code> are kept in sync with your deployed Streamlit Cloud app.
                </p>
                <a
                  href="https://code-visualiser-python-n4usxyvc8j48unplx6kh3m.streamlit.app/"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-full inline-flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-[11px] font-semibold bg-emerald-500/15 text-emerald-700 dark:text-[#5BD6A0] border border-emerald-500/30 rounded hover:bg-emerald-500/25 transition-colors"
                >
                  <span>Open Live Streamlit Cloud App ↗</span>
                </a>
              </div>

              <button
                type="button"
                onClick={() => setShowGitPushGuide((prev) => !prev)}
                className="text-[11px] text-left text-sky-600 dark:text-[#4FD1E8] hover:underline cursor-pointer pt-1"
              >
                {showGitPushGuide
                  ? 'Hide Git Remote Push Commands'
                  : 'Push updates to GitHub & Streamlit Cloud?'}
              </button>

              {showGitPushGuide && (
                <div className="p-2.5 rounded bg-slate-950 text-slate-200 font-mono text-[10px] leading-relaxed overflow-x-auto">
                  <div>git add .</div>
                  <div>git commit -m &quot;feat: TechSpecAnalyser unified release&quot;</div>
                  <div>git branch -M main</div>
                  <div>
                    git remote set-url origin{' '}
                    {githubRepoUrl.trim().endsWith('.git')
                      ? githubRepoUrl.trim()
                      : `${githubRepoUrl.trim().replace(/\/+$/, '')}.git`}
                  </div>
                  <div>git push -u origin main</div>
                </div>
              )}
            </form>
          )}

          {/* Multi-Agent AI Review Toggle */}
          <div className="pt-3 border-t border-slate-200 dark:border-[#263056] flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-slate-800 dark:text-[#E7EBFA]">
                6-Agent Gemini AI Swarm
              </span>
              <button
                type="button"
                onClick={() => setUseAi((prev) => !prev)}
                className={`px-2.5 py-1 text-xs font-mono font-semibold rounded transition-colors cursor-pointer ${
                  useAi
                    ? 'bg-emerald-500/20 text-emerald-700 dark:text-[#5BD6A0] border border-emerald-500/40'
                    : 'bg-slate-200 dark:bg-[#0B1020] text-slate-600 dark:text-[#98A2C8] border border-slate-300 dark:border-[#263056]'
                }`}
              >
                {useAi ? 'ENABLED' : 'OFFLINE ONLY'}
              </button>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
              {apiKeyConfigured
                ? `Connected to ${modelName} · Grounded with AST & static facts.`
                : 'Local deterministic mode active · Syntax, AST static rules, Radon MI, and Doc Generator run without an API key.'}
            </p>
          </div>

          {/* 5-Stage Pipeline Legend */}
          <div className="pt-3 border-t border-slate-200 dark:border-[#263056] flex flex-col gap-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-700 dark:text-[#98A2C8]">
                Processing Workflow
              </span>
              <span className="font-mono text-[11px] text-sky-600 dark:text-[#4FD1E8]">
                {result?.execution_ms ? `${result.execution_ms}ms` : pipelineStage}
              </span>
            </div>
            <ol className="text-[11px] text-slate-600 dark:text-[#98A2C8] space-y-1.5 font-sans">
              <li>1. Input Validation &amp; Safe AST Parse</li>
              <li>2. Deterministic Static Rules (14 Py / C++ / Java)</li>
              <li>3. Measured McCabe CC &amp; Radon MI</li>
              <li>4. 6-Agent Evidence-Grounded Review</li>
              <li>5. Synthesizer Deduplication &amp; 60/40 Score</li>
            </ol>
          </div>

          {/* Report Export Buttons */}
          {result && (
            <div className="pt-3 border-t border-slate-200 dark:border-[#263056] flex flex-col gap-2">
              <span className="text-xs font-semibold text-slate-700 dark:text-[#98A2C8]">
                Download Reports
              </span>
              <div className="grid grid-cols-3 gap-1.5">
                <button
                  type="button"
                  onClick={() =>
                    triggerFileDownload(
                      `codelens_report_${language.toLowerCase()}.md`,
                      buildMarkdownReport(result),
                      'text/markdown'
                    )
                  }
                  className="inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium bg-slate-100 dark:bg-[#1A2347] text-slate-800 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded hover:border-sky-400 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span>.MD</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    triggerFileDownload(
                      `codelens_report_${language.toLowerCase()}.html`,
                      buildStandaloneHtmlReport(result),
                      'text/html'
                    )
                  }
                  className="inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium bg-slate-100 dark:bg-[#1A2347] text-slate-800 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded hover:border-sky-400 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span>.HTML</span>
                </button>
                <button
                  type="button"
                  onClick={() =>
                    triggerFileDownload(
                      `codelens_data_${language.toLowerCase()}.json`,
                      JSON.stringify(result, null, 2),
                      'application/json'
                    )
                  }
                  className="inline-flex items-center justify-center gap-1 px-2 py-1.5 text-xs font-medium bg-slate-100 dark:bg-[#1A2347] text-slate-800 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded hover:border-sky-400 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span>.JSON</span>
                </button>
              </div>
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 min-w-0 p-6 flex flex-col gap-6">
          {/* Toast Notification */}
          {toastMessage && (
            <div className="flex items-center justify-between px-4 py-2.5 bg-sky-500/15 border border-sky-500/40 text-sky-900 dark:text-[#4FD1E8] text-xs rounded-lg">
              <span>{toastMessage}</span>
              <button
                type="button"
                onClick={() => setToastMessage(null)}
                className="text-xs underline ml-4 cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          )}

          {/* ZIP Security / Validation Banner */}
          {zipAlert && (
            <div
              className={`flex items-center justify-between px-4 py-3 rounded-lg border text-xs ${
                zipAlert.type === 'error'
                  ? 'bg-rose-500/10 border-rose-500/40 text-rose-700 dark:text-[#FF6B7A]'
                  : 'bg-emerald-500/10 border-emerald-500/40 text-emerald-800 dark:text-[#5BD6A0]'
              }`}
            >
              <div className="flex items-center gap-2">
                {zipAlert.type === 'error' ? (
                  <ShieldAlert className="w-4 h-4 shrink-0" />
                ) : (
                  <ShieldCheck className="w-4 h-4 shrink-0" />
                )}
                <span>{zipAlert.message}</span>
              </div>
              <button
                type="button"
                onClick={() => setZipAlert(null)}
                className="text-xs underline ml-4 cursor-pointer"
              >
                Close
              </button>
            </div>
          )}

          {/* Source Code Editor Panel (Collapsible / Always Accessible) */}
          <section className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl overflow-hidden">
            <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 bg-slate-50 dark:bg-[#1A2347] border-b border-slate-200 dark:border-[#263056]">
              <div className="flex items-center gap-2 text-xs">
                <Code2 className="w-4 h-4 text-sky-600 dark:text-[#4FD1E8]" />
                <span className="font-semibold text-slate-900 dark:text-[#E7EBFA]">
                  {projectName}
                </span>
                <span aria-hidden="true" className="text-slate-400">
                  /
                </span>
                <span className="font-mono text-sky-600 dark:text-[#4FD1E8]">{fileName}</span>
                <span aria-hidden="true" className="text-slate-400">
                  ·
                </span>
                <span className="font-mono tabular-nums text-slate-500 dark:text-[#98A2C8]">
                  {codeInput.split('\n').length} lines
                </span>
              </div>

              {/* Multi-file switcher when a ZIP project is loaded */}
              {projectFiles.length > 1 && (
                <div className="flex items-center gap-1 overflow-x-auto">
                  {projectFiles.map((pf, idx) => (
                    <button
                      key={pf.path}
                      type="button"
                      onClick={() => {
                        setActiveProjectFileIdx(idx);
                        setCodeInput(pf.code);
                        setFileName(pf.path);
                      }}
                      className={`px-2.5 py-1 text-xs font-mono rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                        activeProjectFileIdx === idx
                          ? 'bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 font-semibold'
                          : 'bg-white dark:bg-[#0B1020] text-slate-600 dark:text-[#98A2C8] hover:text-white'
                      }`}
                    >
                      {pf.path}
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard?.writeText(codeInput);
                    showToast('Copied source code to clipboard');
                  }}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-[#98A2C8] hover:text-slate-900 dark:hover:text-white cursor-pointer"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>Copy</span>
                </button>
                <button
                  type="button"
                  onClick={() => setResult(null)}
                  className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-slate-600 dark:text-[#98A2C8] hover:text-rose-500 cursor-pointer"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                  <span>Clear Results</span>
                </button>
              </div>
            </div>

            {/* Line-Numbered Code Editor */}
            <div className="relative flex max-h-72 overflow-y-auto bg-slate-950 dark:bg-[#080C1A] font-mono text-xs leading-6">
              <div
                aria-hidden="true"
                className="select-none py-3 px-3 text-right text-slate-600 bg-slate-900/60 border-r border-slate-800 font-mono tabular-nums"
              >
                {codeInput.split('\n').map((_, idx) => (
                  <div key={idx}>{idx + 1}</div>
                ))}
              </div>
              <textarea
                value={codeInput}
                onChange={(e) => {
                  const val = e.target.value;
                  setCodeInput(val);
                  if (projectFiles.length > 0) {
                    setProjectFiles((prev) =>
                      prev.map((pf, i) => (i === activeProjectFileIdx ? { ...pf, code: val } : pf))
                    );
                  }
                }}
                spellCheck={false}
                rows={Math.min(14, Math.max(6, codeInput.split('\n').length))}
                className="flex-1 p-3 bg-transparent text-slate-100 focus:outline-none resize-y font-mono leading-6"
                placeholder="Paste Python, C++, or Java source code here..."
              />
            </div>
          </section>

          {/* If no result yet, prompt to run */}
          {!result ? (
            <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-10 text-center">
              <p className="text-sm text-slate-600 dark:text-[#98A2C8] mb-4">
                Select a test case from the sidebar or paste your own source code, then click{' '}
                <strong className="text-slate-900 dark:text-white">Analyze Code</strong>.
              </p>
              <button
                type="button"
                onClick={() => triggerAnalysis()}
                className="inline-flex items-center gap-2 px-5 py-2.5 text-xs font-semibold text-slate-950 bg-cyan-400 hover:bg-cyan-300 rounded-lg cursor-pointer"
              >
                <Play className="w-4 h-4 fill-current" />
                <span>Run 5-Stage TechSpecAnalyser Pipeline</span>
              </button>
            </div>
          ) : (
            <>
              {/* PAGE 1: OVERVIEW DASHBOARD (Part 9.1 & Part 10) */}
              {activeTab === 'overview' && (
                <div className="flex flex-col gap-6">
                  {/* Top Summary Strip: Conic Score Ring + 6 KPI Metrics */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6 flex flex-col lg:flex-row items-center gap-6">
                    {/* Score Ring */}
                    <div className="flex items-center gap-5 shrink-0">
                      <div
                        className="w-32 h-32 rounded-full grid place-items-center shrink-0"
                        style={{
                          background: `conic-gradient(${band.colorHex} ${Math.max(
                            0,
                            Math.min(100, overallScore * 10)
                          )}%, #232C58 0)`,
                        }}
                      >
                        <div className="w-26 h-26 rounded-full bg-white dark:bg-[#0B1020] flex flex-col items-center justify-center">
                          <span className="text-3xl font-bold font-mono tabular-nums text-slate-900 dark:text-[#E7EBFA]">
                            {overallScore}
                          </span>
                          <span className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                            /10 · {band.label}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* 6 Metric Cards */}
                    <div className="flex-1 w-full grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-3.5">
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Critical</div>
                        <div
                          className={`text-2xl font-bold font-mono tabular-nums mt-0.5 ${
                            counts.critical > 0
                              ? 'text-rose-600 dark:text-[#FF6B7A]'
                              : 'text-emerald-600 dark:text-[#5BD6A0]'
                          }`}
                        >
                          {counts.critical}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          must fix
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Warnings</div>
                        <div
                          className={`text-2xl font-bold font-mono tabular-nums mt-0.5 ${
                            counts.warning > 0
                              ? 'text-amber-600 dark:text-[#FFC857]'
                              : 'text-emerald-600 dark:text-[#5BD6A0]'
                          }`}
                        >
                          {counts.warning}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          should fix
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Info Notes</div>
                        <div className="text-2xl font-bold font-mono tabular-nums mt-0.5 text-sky-600 dark:text-[#7AA7FF]">
                          {counts.info}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          style &amp; clean code
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Complexity Grade
                        </div>
                        <div className="text-2xl font-bold font-mono tabular-nums mt-0.5 text-slate-900 dark:text-[#E7EBFA]">
                          {complexity?.rating || 'N/A'}
                        </div>
                        <div className="text-[11px] font-mono tabular-nums text-slate-500 dark:text-[#98A2C8]">
                          {complexity?.analysis_type || 'measured'} · avg{' '}
                          {complexity?.average_complexity ?? 0}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Maintainability
                        </div>
                        <div className="text-2xl font-bold font-mono tabular-nums mt-0.5 text-emerald-600 dark:text-[#5BD6A0]">
                          {complexity?.maintainability_index ?? 'N/A'}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          {complexity?.maintainability_index != null
                            ? complexity.mi_label
                            : 'Python only'}
                        </div>
                      </div>

                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Doc Coverage
                        </div>
                        <div className="text-2xl font-bold font-mono tabular-nums mt-0.5 text-sky-600 dark:text-[#4FD1E8]">
                          {documentation?.doc_coverage_before ?? 0}%
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          100% with proposals
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Executive Summary & AI Fallback Notice */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-5 flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-sky-600 dark:text-[#4FD1E8]">
                        Synthesizer Executive Summary
                      </span>
                      <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-[#98A2C8]">
                        {counts.deterministic} Deterministic Facts · {counts.ai} AI Suggestions
                      </span>
                    </div>
                    <p className="text-sm text-slate-800 dark:text-[#E7EBFA] leading-relaxed">
                      {result.summary}
                    </p>
                  </div>

                  {/* 6 Specialized AI Agents Orchestrator Grid (Part 7) */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Six-Agent Review Orchestrator Telemetry
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Each agent receives role-specific AST structure, measured complexity, and confirmed static findings.
                        </p>
                      </div>
                      <span className="text-xs font-mono tabular-nums text-slate-500 dark:text-[#98A2C8]">
                        Orchestrator Mode:{' '}
                        {result.ai_status === 'ok'
                          ? `Live Multi-Agent (${result.model})`
                          : 'Evidence-Grounded Deterministic Mode'}
                      </span>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                      {agents.map((ag) => (
                        <div
                          key={ag.id}
                          className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] flex flex-col justify-between gap-3"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="text-xs font-bold text-slate-900 dark:text-[#E7EBFA]">
                                {ag.name}
                              </span>
                              <span className="text-[11px] font-mono tabular-nums text-emerald-600 dark:text-[#5BD6A0]">
                                {ag.status} · {ag.latency_ms}ms
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-500 dark:text-[#98A2C8] mb-2">
                              {ag.role}
                            </p>
                            <p className="text-xs text-slate-700 dark:text-[#E7EBFA] leading-relaxed">
                              {ag.summary}
                            </p>
                          </div>
                          <div className="pt-2 border-t border-slate-200/70 dark:border-[#263056] flex items-center justify-between text-[11px] text-slate-500 dark:text-[#98A2C8] font-mono tabular-nums">
                            <span>{ag.findings?.length || 0} finding(s)</span>
                            <span>{ag.recommendations?.length || 0} recommendation(s)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Transparent Code Health Score Breakdown (Part 10) */}
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                      <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA] mb-1">
                        How the Code Health Score Was Calculated
                      </h3>
                      <p className="text-xs text-slate-500 dark:text-[#98A2C8] mb-4">
                        Deterministic rule penalties account for 60% of the score; AI review assessment accounts for 40% when active.
                      </p>

                      <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                            <th className="py-2">Scoring Factor</th>
                            <th className="py-2 text-right">Points Impact</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                          <tr>
                            <td className="py-2 font-sans text-slate-800 dark:text-[#E7EBFA]">
                              Starting Baseline Score
                            </td>
                            <td className="py-2 text-right font-semibold text-emerald-600 dark:text-[#5BD6A0]">
                              10.0
                            </td>
                          </tr>
                          {(result.score_details?.penalties || []).map((p: any, idx: number) => (
                            <tr key={idx}>
                              <td className="py-2 font-sans text-slate-700 dark:text-[#98A2C8]">
                                Deduction: {p.label}
                              </td>
                              <td className="py-2 text-right text-rose-600 dark:text-[#FF6B7A]">
                                -{p.points}
                              </td>
                            </tr>
                          ))}
                          <tr className="font-semibold">
                            <td className="py-2 font-sans text-slate-900 dark:text-[#E7EBFA]">
                              Deterministic Rule-Based Score
                            </td>
                            <td className="py-2 text-right text-sky-600 dark:text-[#4FD1E8]">
                              {result.score_details?.rule_score ?? overallScore}/10
                            </td>
                          </tr>
                          {result.score_details?.ai_score != null && (
                            <tr>
                              <td className="py-2 font-sans text-slate-700 dark:text-[#98A2C8]">
                                AI Multi-Agent Assessment (40% weight)
                              </td>
                              <td className="py-2 text-right text-slate-900 dark:text-[#E7EBFA]">
                                {result.score_details.ai_score}/10
                              </td>
                            </tr>
                          )}
                          <tr className="font-bold text-sm">
                            <td className="py-2.5 font-sans text-slate-900 dark:text-white">
                              Final Code Health Score
                            </td>
                            <td className="py-2.5 text-right text-emerald-600 dark:text-[#5BD6A0]">
                              {overallScore}/10
                            </td>
                          </tr>
                        </tbody>
                      </table>

                      <p className="mt-4 text-[11px] text-slate-500 dark:text-[#98A2C8] leading-relaxed">
                        {result.score_details?.limitations_note}
                      </p>
                    </div>

                    {/* Issues by Severity & Function Complexity Bars */}
                    <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6 flex flex-col justify-between gap-5">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA] mb-3">
                          Issues by Severity &amp; Function Complexity
                        </h3>
                        <div className="space-y-3">
                          {(
                            [
                              { key: 'critical', label: 'Critical', count: counts.critical, color: 'bg-rose-500' },
                              { key: 'warning', label: 'Warning', count: counts.warning, color: 'bg-amber-400' },
                              { key: 'info', label: 'Info', count: counts.info, color: 'bg-sky-400' },
                            ] as const
                          ).map((row) => {
                            const maxVal = Math.max(1, counts.critical, counts.warning, counts.info);
                            const pct = row.count === 0 ? 0 : Math.max(6, Math.round((row.count / maxVal) * 100));
                            return (
                              <div key={row.key} className="flex items-center gap-3 text-xs">
                                <span className="w-20 text-slate-600 dark:text-[#98A2C8]">
                                  {row.label}
                                </span>
                                <div className="flex-1 h-2.5 bg-slate-100 dark:bg-[#0B1020] rounded-full overflow-hidden">
                                  <div
                                    className={`h-full ${row.color} rounded-full`}
                                    style={{ width: `${pct}%` }}
                                  />
                                </div>
                                <span className="w-10 text-right font-mono tabular-nums font-semibold">
                                  {row.count}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      <div>
                        <h4 className="text-xs font-semibold text-slate-700 dark:text-[#98A2C8] mb-2.5">
                          Measured Function Complexity Breakdown
                        </h4>
                        {(complexity?.details || []).length === 0 ? (
                          <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                            No function definitions found in current snippet.
                          </p>
                        ) : (
                          <div className="space-y-2">
                            {(complexity?.details || []).slice(0, 6).map((fn: any) => {
                              const pct = Math.min(100, Math.max(8, Math.round((fn.complexity / 20) * 100)));
                              return (
                                <div key={`${fn.file}-${fn.name}-${fn.line}`} className="flex items-center gap-3 text-xs">
                                  <span className="w-36 truncate font-mono text-slate-800 dark:text-[#E7EBFA]">
                                    {fn.name}()
                                  </span>
                                  <div className="flex-1 h-2 bg-slate-100 dark:bg-[#0B1020] rounded-full overflow-hidden">
                                    <div
                                      className={`h-full rounded-full ${
                                        fn.complexity <= 5
                                          ? 'bg-emerald-400'
                                          : fn.complexity <= 10
                                          ? 'bg-sky-400'
                                          : 'bg-rose-500'
                                      }`}
                                      style={{ width: `${pct}%` }}
                                    />
                                  </div>
                                  <span className="w-20 text-right font-mono tabular-nums text-slate-500 dark:text-[#98A2C8]">
                                    CC {fn.complexity} · {fn.rank}
                                  </span>
                                </div>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* PAGE 2: CODE REVIEW & BEFORE/AFTER DIFF (Part 9.2) */}
              {activeTab === 'review' && (
                <div className="flex flex-col gap-6">
                  {/* Filter Bar */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                        Consolidated Code Review Findings ({filteredBugs.length})
                      </h2>
                      <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                        Deterministic AST findings are separated from AI agent suggestions. Verify AI suggestions before applying changes.
                      </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                      {/* Origin Filter */}
                      <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-[#0B1020] rounded-lg border border-slate-200 dark:border-[#263056]">
                        {(
                          [
                            { id: 'all', label: `All (${bugs.length})` },
                            { id: 'deterministic', label: `Deterministic (${counts.deterministic})` },
                            { id: 'ai', label: `AI Suggested (${counts.ai})` },
                          ] as const
                        ).map((o) => (
                          <button
                            key={o.id}
                            type="button"
                            onClick={() => setOriginFilter(o.id)}
                            className={`px-2.5 py-1 text-xs font-medium rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                              originFilter === o.id
                                ? 'bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#4FD1E8]'
                                : 'text-slate-600 dark:text-[#98A2C8]'
                            }`}
                          >
                            {o.label}
                          </button>
                        ))}
                      </div>

                      {/* Severity Filter */}
                      <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-[#0B1020] rounded-lg border border-slate-200 dark:border-[#263056]">
                        {(['all', 'critical', 'warning', 'info'] as const).map((sev) => (
                          <button
                            key={sev}
                            type="button"
                            onClick={() => setSeverityFilter(sev)}
                            className={`px-2.5 py-1 text-xs font-medium capitalize rounded transition-colors whitespace-nowrap shrink-0 cursor-pointer ${
                              severityFilter === sev
                                ? 'bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#4FD1E8]'
                                : 'text-slate-600 dark:text-[#98A2C8]'
                            }`}
                          >
                            {sev}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Findings List */}
                  <div className="flex flex-col gap-3">
                    {filteredBugs.length === 0 ? (
                      <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-8 text-center">
                        <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-2" />
                        <p className="text-sm font-medium text-slate-900 dark:text-[#E7EBFA]">
                          No findings match the selected filter criteria.
                        </p>
                      </div>
                    ) : (
                      filteredBugs.map((bug, idx) => (
                        <div
                          key={`${bug.file}-${bug.line}-${bug.rule}-${idx}`}
                          className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-5 flex flex-col gap-2.5"
                        >
                          {/* Unboxed metadata line */}
                          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                            <div className="flex flex-wrap items-center gap-2">
                              {bug.severity === 'critical' ? (
                                <span className="inline-flex items-center gap-1 font-semibold text-rose-600 dark:text-[#FF6B7A]">
                                  <AlertCircle className="w-3.5 h-3.5" />
                                  <span>Critical</span>
                                </span>
                              ) : bug.severity === 'warning' ? (
                                <span className="inline-flex items-center gap-1 font-semibold text-amber-600 dark:text-[#FFC857]">
                                  <AlertTriangle className="w-3.5 h-3.5" />
                                  <span>Warning</span>
                                </span>
                              ) : (
                                <span className="inline-flex items-center gap-1 font-semibold text-sky-600 dark:text-[#7AA7FF]">
                                  <Sparkles className="w-3.5 h-3.5" />
                                  <span>Info</span>
                                </span>
                              )}
                              <span aria-hidden="true" className="text-slate-400">
                                ·
                              </span>
                              <span className="font-mono tabular-nums text-slate-800 dark:text-[#E7EBFA]">
                                {bug.file || fileName}:Line {bug.line}
                              </span>
                              <span aria-hidden="true" className="text-slate-400">
                                ·
                              </span>
                              <span className="font-mono text-slate-500 dark:text-[#98A2C8]">
                                Rule: {bug.rule || 'general'}
                              </span>
                            </div>

                            <span className="text-xs font-mono text-slate-500 dark:text-[#98A2C8]">
                              {bug.deterministic
                                ? 'Confirmed Deterministic Fact (AST/Static)'
                                : `AI Suggestion (${bug.source}) · Developer Verification Required`}
                            </span>
                          </div>

                          <p className="text-sm text-slate-900 dark:text-[#E7EBFA]">
                            {bug.description}
                          </p>

                          {bug.evidence && (
                            <pre className="p-2.5 rounded-md bg-slate-950 dark:bg-[#080C1A] text-slate-200 font-mono text-xs overflow-x-auto">
                              {bug.evidence}
                            </pre>
                          )}

                          {bug.fix && (
                            <div className="text-xs text-emerald-800 dark:text-[#5BD6A0] pt-1">
                              <strong className="font-semibold">Recommended Fix:</strong> {bug.fix}
                            </div>
                          )}
                        </div>
                      ))
                    )}
                  </div>

                  {/* Multi-Agent Improvement Recommendations */}
                  {(result.improvements || []).length > 0 && (
                    <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                      <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA] mb-3">
                        Agent Refactoring &amp; Improvement Suggestions
                      </h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {(result.improvements || []).map((imp: any, i: number) => (
                          <div
                            key={i}
                            className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]"
                          >
                            <div className="text-[11px] font-mono text-sky-600 dark:text-[#4FD1E8] mb-1">
                              {imp.agent || 'Review Agent'}
                            </div>
                            <h4 className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA] mb-1">
                              {imp.title}
                            </h4>
                            <p className="text-xs text-slate-600 dark:text-[#98A2C8] leading-relaxed">
                              {imp.detail}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Before / After Comparison & Diff Viewer */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Before / After Code Comparison &amp; Validation
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          AI-proposed code is automatically syntax-checked and static-analyzed before display.
                        </p>
                      </div>

                      {result.improved_code && (
                        <div className="flex items-center gap-2">
                          <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-[#0B1020] rounded-lg border border-slate-200 dark:border-[#263056]">
                            <button
                              type="button"
                              onClick={() => setDiffViewMode('side-by-side')}
                              className={`px-2.5 py-1 text-xs font-medium rounded cursor-pointer ${
                                diffViewMode === 'side-by-side'
                                  ? 'bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#4FD1E8]'
                                  : 'text-slate-600 dark:text-[#98A2C8]'
                              }`}
                            >
                              Side by Side
                            </button>
                            <button
                              type="button"
                              onClick={() => setDiffViewMode('unified')}
                              className={`px-2.5 py-1 text-xs font-medium rounded cursor-pointer ${
                                diffViewMode === 'unified'
                                  ? 'bg-white dark:bg-[#1A2347] text-slate-900 dark:text-[#4FD1E8]'
                                  : 'text-slate-600 dark:text-[#98A2C8]'
                              }`}
                            >
                              Unified Diff
                            </button>
                          </div>

                          <button
                            type="button"
                            onClick={() => {
                              setCodeInput(result.improved_code);
                              showToast('Applied improved code to editor. Click Analyze Code to re-verify.');
                            }}
                            className="px-3 py-1.5 text-xs font-semibold bg-emerald-500 text-slate-950 rounded-md hover:bg-emerald-400 cursor-pointer"
                          >
                            Apply to Editor
                          </button>
                        </div>
                      )}
                    </div>

                    {!result.improved_code ? (
                      <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                        {apiKeyConfigured && useAi
                          ? 'No code rewrite was required or syntax errors halted AI refactoring.'
                          : 'Enable the 6-Agent Gemini AI Swarm (with GEMINI_API_KEY configured) to generate full refactored code.'}
                      </p>
                    ) : (
                      <>
                        {result.improved_code_valid ? (
                          <div className="mb-4 px-3.5 py-2 rounded-md bg-emerald-500/10 border border-emerald-500/30 text-xs text-emerald-700 dark:text-[#5BD6A0]">
                            Verified: The AI-improved code passed deterministic syntax and critical static analysis checks.
                          </div>
                        ) : (
                          <div className="mb-4 px-3.5 py-2 rounded-md bg-amber-500/10 border border-amber-500/30 text-xs text-amber-700 dark:text-[#FFC857]">
                            Warning: Automated validation flagged remaining issues in the proposed code:{' '}
                            {(result.improved_code_issues || []).join('; ')}
                          </div>
                        )}

                        {diffViewMode === 'side-by-side' ? (
                          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                            <div>
                              <div className="text-xs font-semibold text-slate-500 dark:text-[#98A2C8] mb-1.5">
                                Original Submitted Code
                              </div>
                              <pre className="p-4 rounded-lg bg-slate-950 dark:bg-[#080C1A] text-slate-200 font-mono text-xs overflow-x-auto max-h-96">
                                {codeInput}
                              </pre>
                            </div>
                            <div>
                              <div className="text-xs font-semibold text-emerald-600 dark:text-[#5BD6A0] mb-1.5">
                                AI-Proposed Improved Code (Verify Before Production Use)
                              </div>
                              <pre className="p-4 rounded-lg bg-slate-950 dark:bg-[#080C1A] text-emerald-200 font-mono text-xs overflow-x-auto max-h-96">
                                {result.improved_code}
                              </pre>
                            </div>
                          </div>
                        ) : (
                          <pre className="p-4 rounded-lg bg-slate-950 dark:bg-[#080C1A] text-slate-200 font-mono text-xs overflow-x-auto max-h-96">
                            {result.unified_diff || 'No line differences.'}
                          </pre>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )}

              {/* PAGE 3: COMPLEXITY ANALYSIS (Part 6 & Part 9.3) */}
              {activeTab === 'complexity' && complexity && (
                <div className="flex flex-col gap-6">
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                      <div>
                        <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Software Metrics &amp; Cyclomatic Complexity Engine
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          {complexity.note}
                        </p>
                      </div>
                      <span className="text-xs font-mono font-semibold text-emerald-600 dark:text-[#5BD6A0]">
                        {String(complexity.analysis_type || 'measured').toUpperCase()} · {complexity.method}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Avg Complexity</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5">
                          {complexity.average_complexity}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          Grade {complexity.rating}
                        </div>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Max Function CC</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5">
                          {complexity.max_complexity}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          {complexity.high_complexity_count} high-CC fn(s)
                        </div>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Maintainability</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5 text-emerald-600 dark:text-[#5BD6A0]">
                          {complexity.maintainability_index ?? 'N/A'}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          {complexity.mi_label || 'Python only'}
                        </div>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Functions / Classes</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5">
                          {complexity.function_count} / {complexity.class_count}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          avg len {complexity.avg_function_length} LOC
                        </div>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Total / Code Lines</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5">
                          {complexity.lines?.['Total lines'] ?? complexity.lines?.['Code lines (NLOC)'] ?? 0} /{' '}
                          {complexity.lines?.['Code lines'] ?? complexity.lines?.['Code lines (NLOC)'] ?? 0}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          LOC / SLOC
                        </div>
                      </div>
                      <div className="p-3.5 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="text-xs text-slate-500 dark:text-[#98A2C8]">Comments / Blank</div>
                        <div className="text-xl font-bold font-mono tabular-nums mt-0.5">
                          {complexity.lines?.['Comment lines'] ?? 0} / {complexity.lines?.['Blank lines'] ?? 0}
                        </div>
                        <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                          Doc cov {complexity.doc_coverage_pct}%
                        </div>
                      </div>
                    </div>

                    {/* Recharts Function Complexity Chart */}
                    {(complexity.details || []).length > 0 && (
                      <div className="h-64 w-full mb-6">
                        <ResponsiveContainer width="100%" height="100%">
                          <BarChart data={complexity.details}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#263056" />
                            <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#98A2C8' }} />
                            <YAxis tick={{ fontSize: 11, fill: '#98A2C8' }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#0B1020',
                                borderColor: '#263056',
                                color: '#E7EBFA',
                                fontSize: '12px',
                              }}
                            />
                            <Bar
                              dataKey="complexity"
                              name="Cyclomatic Complexity (M)"
                              fill="#4FD1E8"
                              radius={[4, 4, 0, 0]}
                            />
                          </BarChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    {/* Function-Level Complexity Table */}
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                            <th className="py-2.5 px-3">Function / Method</th>
                            <th className="py-2.5 px-3">File</th>
                            <th className="py-2.5 px-3 text-right">Line Span</th>
                            <th className="py-2.5 px-3 text-right">Length (LOC)</th>
                            <th className="py-2.5 px-3 text-right">Cyclomatic Complexity</th>
                            <th className="py-2.5 px-3 text-right">Rank</th>
                            <th className="py-2.5 px-3">Refactoring Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                          {(complexity.details || []).map((fn: any, i: number) => (
                            <tr key={i}>
                              <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-[#E7EBFA]">
                                {fn.name}()
                              </td>
                              <td className="py-2.5 px-3 text-slate-500 dark:text-[#98A2C8]">
                                {fn.file || fileName}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                L{fn.line}–L{fn.end_line || fn.line}
                              </td>
                              <td className="py-2.5 px-3 text-right">{fn.length || 1}</td>
                              <td className="py-2.5 px-3 text-right font-bold">{fn.complexity}</td>
                              <td className="py-2.5 px-3 text-right font-bold text-sky-600 dark:text-[#4FD1E8]">
                                {fn.rank}
                              </td>
                              <td className="py-2.5 px-3 font-sans">
                                {fn.complexity > 10 ? (
                                  <span className="text-rose-600 dark:text-[#FF6B7A] font-semibold">
                                    Decompose Function (CC &gt; 10)
                                  </span>
                                ) : fn.complexity > 5 ? (
                                  <span className="text-amber-600 dark:text-[#FFC857]">
                                    Moderate Branching
                                  </span>
                                ) : (
                                  <span className="text-emerald-600 dark:text-[#5BD6A0]">
                                    Clean &amp; Testable
                                  </span>
                                )}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* PAGE 4: SECURITY ANALYSIS (Part 7.3 & Part 9.4) */}
              {activeTab === 'security' && (
                <div className="flex flex-col gap-6">
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
                      <div>
                        <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Security Review &amp; Pattern Verification
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Distinguishes deterministic static security matches from AI-suggested potential risks. Does not replace a full penetration audit.
                        </p>
                      </div>
                      <span className="text-xs font-mono text-slate-500 dark:text-[#98A2C8]">
                        {securityFindings.length} security-relevant finding(s)
                      </span>
                    </div>

                    {securityFindings.length === 0 ? (
                      <div className="p-8 text-center bg-slate-50 dark:bg-[#0B1020] rounded-lg border border-slate-200 dark:border-[#263056]">
                        <ShieldCheck className="w-7 h-7 text-emerald-500 mx-auto mb-2" />
                        <p className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Zero security patterns triggered in static or multi-agent checks.
                        </p>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8] mt-1">
                          Checked for hardcoded credentials, SQL string interpolation, unsafe deserialization (`pickle`), `eval`/`exec`, `subprocess(shell=True)`, and C buffer overflows (`gets`/`strcpy`/`scanf`).
                        </p>
                      </div>
                    ) : (
                      <div className="flex flex-col gap-4">
                        {securityFindings.map((sec, idx) => {
                          const key = `${sec.file}-${sec.line}-${sec.rule}-${idx}`;
                          const currentStatus =
                            securityVerifications[key] ||
                            (sec.deterministic ? 'Confirmed' : 'Unverified');
                          return (
                            <div
                              key={key}
                              className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] flex flex-col gap-2"
                            >
                              <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                                <div className="flex items-center gap-2">
                                  <ShieldAlert className="w-4 h-4 text-rose-500 shrink-0" />
                                  <span className="font-bold uppercase text-rose-600 dark:text-[#FF6B7A]">
                                    {sec.severity}
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span className="font-mono">
                                    {sec.file || fileName}:Line {sec.line}
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span className="font-mono text-sky-600 dark:text-[#4FD1E8]">
                                    {sec.rule}
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span>
                                    {sec.deterministic
                                      ? 'Detection: Deterministic AST Security Rule'
                                      : 'Detection: Security Review Agent (Heuristic)'}
                                  </span>
                                </div>

                                {/* Interactive Developer Verification Status */}
                                <div className="flex items-center gap-1.5">
                                  <span className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                                    Verification:
                                  </span>
                                  {(['Unverified', 'Confirmed', 'Dismissed'] as const).map((st) => (
                                    <button
                                      key={st}
                                      type="button"
                                      onClick={() =>
                                        setSecurityVerifications((prev) => ({ ...prev, [key]: st }))
                                      }
                                      className={`px-2 py-0.5 text-[11px] font-medium rounded border cursor-pointer ${
                                        currentStatus === st
                                          ? 'bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 border-sky-600 dark:border-[#4FD1E8]'
                                          : 'bg-white dark:bg-[#131A33] text-slate-600 dark:text-[#98A2C8] border-slate-200 dark:border-[#263056]'
                                      }`}
                                    >
                                      {st}
                                    </button>
                                  ))}
                                </div>
                              </div>

                              <p className="text-sm text-slate-900 dark:text-[#E7EBFA]">
                                {sec.description}
                              </p>
                              {sec.evidence && (
                                <pre className="p-2.5 rounded bg-slate-950 dark:bg-[#080C1A] text-rose-200 font-mono text-xs overflow-x-auto">
                                  {sec.evidence}
                                </pre>
                              )}
                              {sec.fix && (
                                <p className="text-xs text-emerald-700 dark:text-[#5BD6A0]">
                                  <strong>Recommended Mitigation:</strong> {sec.fix}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* PAGE 5: AUTOMATED DOCUMENTATION GENERATOR (Part 8 & Part 9.5) */}
              {activeTab === 'documentation' && documentation && (
                <div className="flex flex-col gap-6">
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                      <div>
                        <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Automated Documentation Generator (AST + Documentation Agent)
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Extracts factual signatures from the AST and generates PEP-257 docstrings, module tables, and a complete README.md draft.
                        </p>
                      </div>

                      <button
                        type="button"
                        onClick={() =>
                          triggerFileDownload(
                            `${projectName}_README.md`,
                            documentation.readme_markdown || '',
                            'text/markdown'
                          )
                        }
                        className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 rounded-lg hover:opacity-90 cursor-pointer"
                      >
                        <Download className="w-3.5 h-3.5" />
                        <span>Download Generated README.md</span>
                      </button>
                    </div>

                    {/* Doc Coverage Before vs After Bar */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                      <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="text-slate-600 dark:text-[#98A2C8]">
                            Existing Source Docstring Coverage
                          </span>
                          <span className="font-mono font-bold text-amber-600 dark:text-[#FFC857]">
                            {documentation.doc_coverage_before}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-slate-200 dark:bg-[#1A2347] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-amber-400"
                            style={{ width: `${documentation.doc_coverage_before}%` }}
                          />
                        </div>
                      </div>

                      <div className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056]">
                        <div className="flex items-center justify-between text-xs mb-1.5">
                          <span className="text-slate-600 dark:text-[#98A2C8]">
                            Coverage After Applying Proposed Docstrings
                          </span>
                          <span className="font-mono font-bold text-emerald-600 dark:text-[#5BD6A0]">
                            {documentation.doc_coverage_after}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-slate-200 dark:bg-[#1A2347] rounded-full overflow-hidden">
                          <div
                            className="h-full bg-emerald-400"
                            style={{ width: `${documentation.doc_coverage_after}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Proposed PEP-257 Docstrings */}
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA] mb-3">
                      Proposed PEP-257 Docstrings ({(documentation.suggested_docstrings || []).length})
                    </h3>
                    {(documentation.suggested_docstrings || []).length === 0 ? (
                      <p className="text-xs text-emerald-600 dark:text-[#5BD6A0] mb-6">
                        All classes and functions already contain docstrings (100% symbol coverage).
                      </p>
                    ) : (
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                        {(documentation.suggested_docstrings || []).map((item: any, idx: number) => (
                          <div
                            key={idx}
                            className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] flex flex-col gap-2"
                          >
                            <div className="flex items-center justify-between text-xs">
                              <span className="font-mono font-semibold text-sky-600 dark:text-[#4FD1E8]">
                                {item.target_type}: {item.name} ({item.file}:L{item.line})
                              </span>
                              <button
                                type="button"
                                onClick={() => {
                                  navigator.clipboard?.writeText(item.docstring);
                                  showToast(`Copied docstring for ${item.name}`);
                                }}
                                className="text-[11px] text-slate-500 hover:text-white cursor-pointer"
                              >
                                Copy Docstring
                              </button>
                            </div>
                            <pre className="p-3 rounded bg-slate-950 dark:bg-[#080C1A] text-slate-200 font-mono text-xs overflow-x-auto">
                              {item.docstring}
                            </pre>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Generated README.md Preview */}
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA] mb-2">
                      Generated README.md Draft
                    </h3>
                    <pre className="p-4 rounded-lg bg-slate-950 dark:bg-[#080C1A] text-slate-200 font-mono text-xs overflow-x-auto max-h-96 leading-relaxed">
                      {documentation.readme_markdown}
                    </pre>
                  </div>
                </div>
              )}

              {/* PAGE 6: ARCHITECTURE EXPLORER & SQLITE HISTORY (Part 9.6 & Part 11) */}
              {activeTab === 'architecture' && (
                <div className="flex flex-col gap-6">
                  {/* Dual-Runtime GitHub & Streamlit Cloud Integration Banner */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-5 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-col gap-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Dual-Runtime GitHub &amp; Streamlit Cloud Deployment
                        </span>
                        <span className="text-[11px] font-mono text-emerald-600 dark:text-[#5BD6A0]">
                          CONNECTED
                        </span>
                      </div>
                      <p className="text-xs text-slate-600 dark:text-[#98A2C8]">
                        This unified repository runs both the Full-Stack React/Express/Python workbench (<code className="font-mono">npm run dev</code>) and your live Streamlit Community Cloud app (<code className="font-mono">streamlit run app.py</code>).
                      </p>
                    </div>
                    <div className="flex items-center gap-2.5">
                      <button
                        type="button"
                        onClick={() => setInputMode('github')}
                        className="px-3 py-1.5 text-xs font-semibold bg-slate-100 dark:bg-[#1A2347] text-slate-800 dark:text-[#E7EBFA] border border-slate-200 dark:border-[#263056] rounded-lg hover:border-sky-500 transition-colors cursor-pointer"
                      >
                        GitHub Repo Sync
                      </button>
                      <a
                        href="https://code-visualiser-python-n4usxyvc8j48unplx6kh3m.streamlit.app/"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="px-3.5 py-1.5 text-xs font-semibold bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 rounded-lg hover:opacity-90 transition-opacity"
                      >
                        Launch Streamlit Cloud App ↗
                      </a>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    {/* Directory & Module Tree */}
                    <div className="lg:col-span-5 bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6 flex flex-col gap-4">
                      <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                        Project File Inventory &amp; Directory Tree
                      </h2>
                      <pre className="p-4 rounded-lg bg-slate-950 dark:bg-[#080C1A] text-sky-300 font-mono text-xs overflow-x-auto">
                        {documentation?.directory_structure || `${projectName}/\n├── ${fileName}`}
                      </pre>
                      <p className="text-xs text-slate-600 dark:text-[#98A2C8] leading-relaxed">
                        {documentation?.architecture_summary}
                      </p>
                      {ignoredZipFiles.length > 0 && (
                        <div className="p-3 rounded bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] text-xs">
                          <div className="font-semibold text-slate-700 dark:text-[#98A2C8] mb-1">
                            Filtered Non-Source / Virtual-Env Entries ({ignoredZipFiles.length}):
                          </div>
                          <div className="font-mono text-[11px] text-slate-500">
                            {ignoredZipFiles.join(', ')}
                          </div>
                        </div>
                      )}
                    </div>

                    {/* AST Extracted Symbols, Calls & Imports */}
                    <div className="lg:col-span-7 bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6 flex flex-col gap-4">
                      <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                        AST Call Graph &amp; Control-Flow Topology
                      </h2>
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                          <thead>
                            <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                              <th className="py-2 px-2.5">Symbol</th>
                              <th className="py-2 px-2.5">Parameters</th>
                              <th className="py-2 px-2.5">Outgoing Calls</th>
                              <th className="py-2 px-2.5 text-right">Branches / Loops</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                            {(result.ast_facts || [])
                              .flatMap((ff: any) => ff.functions || [])
                              .map((fn: any, i: number) => (
                                <tr key={i}>
                                  <td className="py-2.5 px-2.5 font-semibold text-slate-900 dark:text-[#E7EBFA]">
                                    {fn.name}()
                                  </td>
                                  <td className="py-2.5 px-2.5 text-slate-600 dark:text-[#98A2C8]">
                                    {(fn.args || []).map((a: any) => a.name).join(', ') || 'none'}
                                  </td>
                                  <td className="py-2.5 px-2.5 text-sky-600 dark:text-[#4FD1E8]">
                                    {(fn.calls || []).join(', ') || 'leaf function'}
                                  </td>
                                  <td className="py-2.5 px-2.5 text-right">
                                    {fn.branches} if · {fn.loops} loop · {fn.try_blocks} try
                                  </td>
                                </tr>
                              ))}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  </div>

                  {/* SQLite Persistent Review History & Score Trend */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          SQLite Persistent Review History ({history.length})
                        </h3>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Stored in `backend/codelens.db` (API credentials are never persisted). Click any run to restore its code and report.
                        </p>
                      </div>
                      {history.length > 0 && (
                        <button
                          type="button"
                          onClick={handleClearHistory}
                          className="px-3 py-1.5 text-xs font-medium text-rose-600 dark:text-[#FF6B7A] border border-rose-500/30 rounded-md hover:bg-rose-500/10 cursor-pointer"
                        >
                          Clear History
                        </button>
                      )}
                    </div>

                    {history.length > 1 && (
                      <div className="h-44 w-full mb-5">
                        <ResponsiveContainer width="100%" height="100%">
                          <LineChart data={[...history].reverse()}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#263056" />
                            <XAxis dataKey="time" tick={{ fontSize: 10, fill: '#98A2C8' }} />
                            <YAxis domain={[0, 10]} tick={{ fontSize: 11, fill: '#98A2C8' }} />
                            <Tooltip
                              contentStyle={{
                                backgroundColor: '#0B1020',
                                borderColor: '#263056',
                                color: '#E7EBFA',
                                fontSize: '12px',
                              }}
                            />
                            <Line
                              type="monotone"
                              dataKey="score"
                              name="Code Health Score (/10)"
                              stroke="#5BD6A0"
                              strokeWidth={2.5}
                              dot={{ r: 4 }}
                            />
                          </LineChart>
                        </ResponsiveContainer>
                      </div>
                    )}

                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                            <th className="py-2 px-3">Timestamp</th>
                            <th className="py-2 px-3">Project</th>
                            <th className="py-2 px-3">Language</th>
                            <th className="py-2 px-3 text-right">Score</th>
                            <th className="py-2 px-3 text-right">Crit / Warn / Info</th>
                            <th className="py-2 px-3 text-right">Action</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                          {history.map((h) => (
                            <tr key={h.id}>
                              <td className="py-2.5 px-3 text-slate-500 dark:text-[#98A2C8]">
                                {h.time}
                              </td>
                              <td className="py-2.5 px-3 font-sans font-medium text-slate-900 dark:text-[#E7EBFA]">
                                {h.project_name}
                              </td>
                              <td className="py-2.5 px-3">{h.language}</td>
                              <td className="py-2.5 px-3 text-right font-bold text-emerald-600 dark:text-[#5BD6A0]">
                                {h.score}/10
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                {h.critical} / {h.warning} / {h.info}
                              </td>
                              <td className="py-2.5 px-3 text-right">
                                <button
                                  type="button"
                                  onClick={() => handleReopenHistory(h)}
                                  className="px-2.5 py-1 text-xs font-sans font-medium text-sky-600 dark:text-[#4FD1E8] hover:underline cursor-pointer"
                                >
                                  Open Review
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}

              {/* PAGE 7: EXPERIMENTAL EVALUATION, TRACEABILITY MATRIX & VIVA GUIDE (Part 2, Part 12, Viva) */}
              {activeTab === 'evaluation' && (
                <div className="flex flex-col gap-6">
                  {/* Experimental Evaluation: Approach A vs B vs C */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
                      <div>
                        <h2 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA]">
                          Experimental Evaluation: Approach A vs. Approach B vs. Approach C
                        </h2>
                        <p className="text-xs text-slate-500 dark:text-[#98A2C8]">
                          Evaluated against ground-truth annotated benchmark datasets (`payment_service.py` &amp; `user_auth_dao.py`, 16 known issues).
                        </p>
                      </div>
                      <button
                        type="button"
                        disabled={isEvaluating}
                        onClick={handleRefreshEvaluation}
                        className="inline-flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold bg-sky-600 dark:bg-[#4FD1E8] text-white dark:text-slate-950 rounded-lg cursor-pointer"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isEvaluating ? 'animate-spin' : ''}`} />
                        <span>Run Reproducible Benchmark</span>
                      </button>
                    </div>

                    {evaluationData && (
                      <>
                        <div className="h-64 w-full mb-6">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={evaluationData.approaches}>
                              <CartesianGrid strokeDasharray="3 3" stroke="#263056" />
                              <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#98A2C8' }} />
                              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: '#98A2C8' }} />
                              <Tooltip
                                contentStyle={{
                                  backgroundColor: '#0B1020',
                                  borderColor: '#263056',
                                  color: '#E7EBFA',
                                  fontSize: '12px',
                                }}
                              />
                              <Legend wrapperStyle={{ fontSize: '11px' }} />
                              <Bar dataKey="precision" name="Precision" fill="#7AA7FF" radius={[3, 3, 0, 0]} />
                              <Bar dataKey="recall" name="Recall" fill="#4FD1E8" radius={[3, 3, 0, 0]} />
                              <Bar dataKey="f1_score" name="F1 Score" fill="#5BD6A0" radius={[3, 3, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>

                        <div className="overflow-x-auto">
                          <table className="w-full text-left border-collapse text-xs font-mono tabular-nums">
                            <thead>
                              <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                                <th className="py-2.5 px-3">Review Architecture</th>
                                <th className="py-2.5 px-3 text-right">TP / FP / FN</th>
                                <th className="py-2.5 px-3 text-right">Precision</th>
                                <th className="py-2.5 px-3 text-right">Recall</th>
                                <th className="py-2.5 px-3 text-right">F1 Score</th>
                                <th className="py-2.5 px-3 text-right">FP Rate</th>
                                <th className="py-2.5 px-3 text-right">Issue Coverage</th>
                                <th className="py-2.5 px-3 text-right">Doc Coverage After</th>
                              </tr>
                            </thead>
                            <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                              {evaluationData.approaches.map((app: any) => (
                                <tr key={app.id}>
                                  <td className="py-3 px-3 font-sans">
                                    <div className="font-semibold text-slate-900 dark:text-[#E7EBFA]">
                                      {app.name}
                                    </div>
                                    <div className="text-[11px] text-slate-500 dark:text-[#98A2C8]">
                                      {app.description}
                                    </div>
                                  </td>
                                  <td className="py-3 px-3 text-right">
                                    {app.true_positives} / {app.false_positives} / {app.false_negatives}
                                  </td>
                                  <td className="py-3 px-3 text-right font-semibold">
                                    {app.precision}
                                  </td>
                                  <td className="py-3 px-3 text-right font-semibold">
                                    {app.recall}
                                  </td>
                                  <td className="py-3 px-3 text-right font-bold text-emerald-600 dark:text-[#5BD6A0]">
                                    {app.f1_score}
                                  </td>
                                  <td className="py-3 px-3 text-right">
                                    {app.false_positive_rate_pct}%
                                  </td>
                                  <td className="py-3 px-3 text-right">
                                    {app.known_issue_coverage_pct}%
                                  </td>
                                  <td className="py-3 px-3 text-right text-sky-600 dark:text-[#4FD1E8]">
                                    {app.doc_coverage_after_pct}%
                                  </td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </>
                    )}
                  </div>

                  {/* Interactive 8-Step Viva Presentation & Demo Script Runner */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA] mb-1">
                      Interactive Viva Demo Walkthrough (1-Click Live Scenarios)
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-[#98A2C8] mb-4">
                      Click any step below during your presentation to load the corresponding code sample, run the 5-stage pipeline, and jump directly to the target view.
                    </p>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                      {VIVA_DEMO_STEPS.map((st) => (
                        <div
                          key={st.step}
                          className="p-4 rounded-lg bg-slate-50 dark:bg-[#0B1020] border border-slate-200 dark:border-[#263056] flex flex-col justify-between gap-3"
                        >
                          <div>
                            <div className="flex items-center justify-between gap-2 mb-1">
                              <span className="text-xs font-mono font-bold text-sky-600 dark:text-[#4FD1E8]">
                                Demo Step 0{st.step} · {st.language}
                              </span>
                              <button
                                type="button"
                                onClick={() => handleRunVivaStep(st)}
                                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-cyan-400 text-slate-950 rounded hover:bg-cyan-300 cursor-pointer"
                              >
                                <Play className="w-3 h-3 fill-current" />
                                <span>Run Step</span>
                              </button>
                            </div>
                            <h4 className="text-sm font-semibold text-slate-900 dark:text-[#E7EBFA] mb-1">
                              {st.title}
                            </h4>
                            <p className="text-xs text-slate-600 dark:text-[#98A2C8] leading-relaxed">
                              {st.talkingPoint}
                            </p>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Requirements Traceability Matrix (Part 2 Audit) */}
                  <div className="bg-white dark:bg-[#131A33] border border-slate-200 dark:border-[#263056] rounded-xl p-6">
                    <h3 className="text-base font-semibold text-slate-900 dark:text-[#E7EBFA] mb-1">
                      Requirements Traceability Matrix (Audit of Existing Codebase vs. TechSpecAnalyser Synopsis)
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-[#98A2C8] mb-4">
                      Maps every requirement from the Central University of Jharkhand M.Tech Project Synopsis against the original repository and final implementation.
                    </p>
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse text-xs">
                        <thead>
                          <tr className="border-b border-slate-200 dark:border-[#263056] text-slate-500 dark:text-[#98A2C8]">
                            <th className="py-2.5 px-3">Synopsis Requirement</th>
                            <th className="py-2.5 px-3">Original Project Status</th>
                            <th className="py-2.5 px-3">Gap Addressed</th>
                            <th className="py-2.5 px-3">Final Verification Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-[#263056]">
                          {TRACEABILITY_MATRIX.map((row, idx) => (
                            <tr key={idx}>
                              <td className="py-2.5 px-3 font-semibold text-slate-900 dark:text-[#E7EBFA]">
                                {row.req}
                              </td>
                              <td className="py-2.5 px-3 text-slate-600 dark:text-[#98A2C8]">
                                {row.existing}
                              </td>
                              <td className="py-2.5 px-3 text-slate-600 dark:text-[#98A2C8]">
                                {row.gap}
                              </td>
                              <td className="py-2.5 px-3 font-mono font-semibold text-emerald-600 dark:text-[#5BD6A0]">
                                {row.status}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
