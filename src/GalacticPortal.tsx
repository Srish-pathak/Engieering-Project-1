import React, { useEffect, useMemo, useRef, useState } from 'react';
import type { ChangeEvent, FormEvent } from 'react';
import { SAMPLES, type SupportedLanguage } from './data/codelensSamples';

type Page = 'dashboard' | 'code' | 'github' | 'results' | 'history' | 'reports' | 'settings';
type Finding = { file?: string; line?: number | string; severity?: string; rule?: string; category?: string; description?: string; fix?: string; evidence?: string };
type Result = Record<string, any>;

const nav: { id: Page; label: string; icon: string }[] = [
  { id: 'dashboard', label: 'Dashboard', icon: '▦' },
  { id: 'code', label: 'Code Analysis', icon: '⌘' },
  { id: 'github', label: 'GitHub Repository Review', icon: '⑂' },
  { id: 'history', label: 'Analysis History', icon: '◷' },
  { id: 'reports', label: 'Generated Reports', icon: '▤' },
  { id: 'settings', label: 'Settings', icon: '⚙' },
];

const styles = `
:root{--gp-bg:#080b1a;--gp-panel:rgba(16,22,43,.72);--gp-v:#8b5cf6;--gp-b:#3b82f6;--gp-l:#c4b5fd;--gp-t:#f8fafc;--gp-m:#94a3b8;--gp-line:rgba(196,181,253,.16);color-scheme:dark}
.gp{min-height:100vh;background:var(--gp-bg);color:var(--gp-t);font:15px/1.55 "Segoe UI",system-ui,sans-serif;position:relative;isolation:isolate}
.gp *{box-sizing:border-box}.gp button,.gp input,.gp textarea,.gp select{font:inherit}.gp button{cursor:pointer}.gp button:focus-visible,.gp input:focus-visible,.gp textarea:focus-visible,.gp select:focus-visible{outline:2px solid var(--gp-l);outline-offset:2px}
.gp-sky{position:fixed;inset:0;z-index:-1;pointer-events:none;overflow:hidden;background:radial-gradient(900px 560px at 75% 5%,#8b5cf625,transparent 65%),radial-gradient(700px 550px at 5% 95%,#3b82f620,transparent 65%),var(--gp-bg)}
.gp-orb{position:absolute;width:360px;height:360px;border-radius:50%;filter:blur(80px);opacity:.2;background:var(--gp-v);left:-140px;top:15%;animation:gpdrift 36s ease-in-out infinite alternate}.gp-orb.b{background:var(--gp-b);left:auto;right:-150px;top:auto;bottom:0;animation-duration:44s}
@keyframes gpdrift{to{transform:translate3d(100px,60px,0) scale(1.12)}}@keyframes gpin{from{opacity:0;transform:translateY(8px)}}
.gp.calm *,.gp.calm *:before,.gp.calm *:after{animation:none!important;transition:none!important}
@media(prefers-reduced-motion:reduce){.gp *,.gp *:before,.gp *:after{animation:none!important;transition:none!important}}
.gp-top{height:64px;position:sticky;top:0;z-index:20;display:flex;align-items:center;justify-content:space-between;padding:0 24px;background:#080b1acc;backdrop-filter:blur(15px);border-bottom:1px solid var(--gp-line)}
.gp-logo{display:flex;align-items:center;gap:10px;font-weight:650;font-size:17px}.gp-logo i{width:23px;height:23px;border-radius:50%;background:conic-gradient(var(--gp-v),var(--gp-b),var(--gp-l),var(--gp-v));box-shadow:0 0 16px #8b5cf688}
.gp-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}.gp-btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border:0;border-radius:12px;padding:11px 17px;color:#fff;background:linear-gradient(130deg,var(--gp-v),var(--gp-b));font-weight:600;box-shadow:0 8px 24px #8b5cf644;transition:transform .2s,box-shadow .2s}.gp-btn:hover{transform:translateY(-2px);box-shadow:0 10px 30px #8b5cf677}.gp-btn.ghost{background:#c4b5fd12;box-shadow:inset 0 0 0 1px var(--gp-line);color:var(--gp-l)}.gp-btn:disabled{opacity:.55;cursor:wait;transform:none}
.gp-body{display:flex;min-height:calc(100vh - 64px)}.gp-nav{width:255px;flex:none;position:sticky;top:64px;align-self:flex-start;height:calc(100vh - 64px);overflow:auto;padding:18px 12px;border-right:1px solid var(--gp-line);background:#080b1a66;backdrop-filter:blur(10px)}
.gp-nav button{width:100%;display:flex;align-items:center;gap:12px;border:0;border-radius:11px;padding:11px 13px;margin-bottom:4px;text-align:left;background:transparent;color:var(--gp-m)}.gp-nav button:hover{background:#c4b5fd12;color:#fff}.gp-nav button.on{color:#fff;background:linear-gradient(90deg,#8b5cf640,#3b82f612);box-shadow:inset 0 0 0 1px var(--gp-line),inset 2px 0 var(--gp-l)}.gp-nav .ic{width:20px;color:var(--gp-l);text-align:center}
.gp-main{width:100%;max-width:1240px;margin:0 auto;padding:30px}.gp-view{animation:gpin .3s ease both}.gp-grid{display:grid;gap:16px}.gp-g2{grid-template-columns:repeat(2,minmax(0,1fr))}.gp-g3{grid-template-columns:repeat(3,minmax(0,1fr))}.gp-g4{grid-template-columns:repeat(4,minmax(0,1fr))}
.gp-card{background:var(--gp-panel);backdrop-filter:blur(12px);border:1px solid var(--gp-line);border-radius:18px;padding:22px;box-shadow:0 10px 30px #0005}.gp-card h2,.gp-card h3{margin:0 0 8px}.gp-muted{color:var(--gp-m)}.gp-head{margin-bottom:22px}.gp-head h1{font-size:clamp(25px,3vw,34px);letter-spacing:-.02em;margin:0}.gp-head p{color:var(--gp-m);margin:6px 0 0}
.gp-hero{display:grid;grid-template-columns:1.05fr 1fr;align-items:center;gap:22px;min-height:calc(100vh - 130px);padding:20px}.gp-badge{display:inline-block;border:1px solid var(--gp-line);border-radius:99px;background:#8b5cf620;color:var(--gp-l);padding:5px 13px;margin-bottom:18px}.gp-hero h1{font-size:clamp(42px,6vw,68px);line-height:1.02;margin:0}.gp-hero h2{font-size:clamp(20px,2.5vw,28px);color:var(--gp-l);font-weight:500;margin:14px 0}.gp-hero p{color:var(--gp-m);max-width:500px;margin-bottom:25px}
.gp-planet{width:min(100%,440px);aspect-ratio:1;justify-self:center;position:relative;border-radius:50%;background:radial-gradient(circle at center,#151032 0 32%,#35246b 48%,#3b82f655 58%,transparent 70%);filter:drop-shadow(0 0 34px #8b5cf655);animation:gpfloat 9s ease-in-out infinite}.gp-planet:before,.gp-planet:after{content:"";position:absolute;inset:12%;border-radius:50%;border:2px solid transparent;border-top-color:#c4b5faaa;border-bottom-color:#3b82f6aa;transform:rotate(-24deg);animation:gprotate 30s linear infinite}.gp-planet:after{inset:20%;transform:rotate(48deg);animation-duration:42s;animation-direction:reverse;border-top-color:#8b5cf6}.gp-planet span{position:absolute;width:8px;height:8px;left:50%;top:8%;border-radius:50%;background:#e9ddff;box-shadow:0 0 16px #c4b5fd}
@keyframes gprotate{to{rotate:360deg}}@keyframes gpfloat{50%{transform:translateY(-10px)}}
.gp-tile{min-height:145px;display:block;text-align:left;color:inherit;cursor:pointer;transition:transform .2s,border-color .2s}.gp-tile:hover{transform:translateY(-4px);border-color:#c4b5fd66}.gp-tile .tile-ic{display:grid;place-items:center;width:42px;height:42px;border-radius:12px;color:var(--gp-l);background:#8b5cf633;margin-bottom:14px;font-size:20px}.gp-tile p{color:var(--gp-m);margin:0;font-size:14px}
.gp-form{display:grid;gap:14px}.gp-label{display:grid;gap:7px;font-size:13px;color:#d8d4e8}.gp input,.gp textarea,.gp select{width:100%;border-radius:11px;border:1px solid var(--gp-line);background:#080b1acc;color:var(--gp-t);padding:11px 13px}.gp textarea{min-height:250px;resize:vertical;font:13px/1.65 ui-monospace,Consolas,monospace}.gp input:focus,.gp textarea:focus,.gp select:focus{border-color:var(--gp-v);box-shadow:0 0 0 3px #8b5cf633;outline:0}
.gp-drop{border:1px dashed #c4b5fd66;padding:18px;border-radius:12px;color:var(--gp-m);text-align:center}.gp-alert{padding:12px 14px;border-radius:11px;border:1px solid #f8717166;background:#f8717115;color:#fecaca}.gp-success{padding:12px 14px;border-radius:11px;border:1px solid #4ade8066;background:#4ade8015;color:#bbf7d0}
.gp-stat{font-size:30px;font-weight:650;margin:3px 0}.gp-stat-label{font-size:13px;color:var(--gp-m)}.gp-pill{display:inline-block;padding:3px 10px;border-radius:99px;font-size:12px;border:1px solid var(--gp-line);color:var(--gp-l)}.gp-find{padding:15px;border:1px solid var(--gp-line);border-radius:12px;background:#080b1a66;margin-top:10px}.gp-find p{font-size:14px;color:#cbd5e1;margin:8px 0}.gp-find .fix{color:#bbf7d0}.gp-table{width:100%;border-collapse:collapse}.gp-table th,.gp-table td{text-align:left;padding:11px;border-bottom:1px solid var(--gp-line);font-size:13px}.gp-table th{color:var(--gp-l)}.gp-mobile{display:none}
@media(max-width:950px){.gp-g4{grid-template-columns:repeat(2,minmax(0,1fr))}.gp-hero{grid-template-columns:1fr}.gp-planet{width:min(65vw,330px);grid-row:1}.gp-hero>div:first-child{grid-row:2}}
@media(max-width:720px){.gp-mobile{display:inline-flex}.gp-body{display:block}.gp-nav{display:none;position:fixed;z-index:19;left:0;top:64px;width:min(280px,85vw);height:calc(100vh - 64px);background:#0b1024}.gp-nav.open{display:block}.gp-main{padding:20px 14px}.gp-g2,.gp-g3,.gp-g4{grid-template-columns:1fr}.gp-top{padding:0 14px}}
`;

function severity(f: Finding) {
  const s = (f.severity || '').toLowerCase();
  return ['critical','high','error'].includes(s) ? 'Critical' : ['warning','medium','moderate'].includes(s) ? 'Warning' : 'Info';
}
function saveFile(name: string, text: string, mime: string) {
  const url = URL.createObjectURL(new Blob([text], { type: mime }));
  const a = document.createElement('a'); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
}
async function zipBase64(file: File) {
  const bytes = new Uint8Array(await file.arrayBuffer()); let binary = '';
  for (let i=0; i<bytes.length; i+=0x8000) binary += String.fromCharCode(...bytes.subarray(i, Math.min(i+0x8000, bytes.length)));
  return btoa(binary);
}

export default function GalacticPortal() {
  const [page,setPage]=useState<Page>('dashboard');
  const [mobileOpen,setMobileOpen]=useState(false);
  const [calm,setCalm]=useState(false);
  const [language,setLanguage]=useState<SupportedLanguage>('Python');
  const [sample,setSample]=useState('Payment Service (Synopsis Sec. 14 Showcase)');
  const [code,setCode]=useState(SAMPLES.Python['Payment Service (Synopsis Sec. 14 Showcase)']);
  const [repoUrl,setRepoUrl]=useState('');
  const [branch,setBranch]=useState('');
  const [file,setFile]=useState<File|null>(null);
  const [result,setResult]=useState<Result|null>(null);
  const [history,setHistory]=useState<any[]>([]);
  const [ai,setAi]=useState(false);
  const [model,setModel]=useState('');
  const [busy,setBusy]=useState(false);
  const [error,setError]=useState('');
  const fileRef=useRef<HTMLInputElement>(null);
  const zipRef=useRef<HTMLInputElement>(null);

  useEffect(()=>{fetch('/api/status').then(r=>r.json()).then(d=>{setAi(Boolean(d.api_key_configured));setModel(d.model||'')}).catch(()=>{});},[]);
  useEffect(()=>{if(page==='history')fetch('/api/history').then(r=>r.json()).then(d=>setHistory(d.history||[])).catch(()=>setHistory([]));},[page]);
  const findings:Finding[]=result?.bugs||result?.deterministic_bugs||[];
  const crit=findings.filter(f=>severity(f)==='Critical');
  const warn=findings.filter(f=>severity(f)==='Warning');
  const info=findings.filter(f=>severity(f)==='Info');
  const score=typeof result?.overall_score==='number'?Math.round(result.overall_score*10):null;
  const files:any[]=result?.files_inventory||[];
  const languages=Object.keys(SAMPLES) as SupportedLanguage[];

  async function send(endpoint:string,payload:any,name:string){
    setBusy(true);setError('');
    try{
      const response=await fetch(endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      const data=await response.json().catch(()=>({}));
      if(!response.ok||data.error||data.valid===false)throw new Error(data.error||data.summary||'Analysis could not be completed.');
      const final=data.result||data;
      setResult(final);setRepoUrl('');setFile(null);setPage('results');
      if(name)document.title=name+' · TechSpecAnalyser';
    }catch(e){setError(e instanceof Error?e.message:'Analysis failed. Please try again.')}
    finally{setBusy(false)}
  }
  function submitCode(e:FormEvent){e.preventDefault();if(!code.trim())return;void send('/api/analyze',{code,language,file_name:'pasted-code',project_name:'Pasted Code',input_mode:'paste',use_ai:ai},'Code Analysis')}
  function submitRepo(e:FormEvent){e.preventDefault();if(!repoUrl.trim())return;void send('/api/import-github',{repo_url:repoUrl,branch,use_ai:ai},'GitHub Review')}
  async function submitFile(e:ChangeEvent<HTMLInputElement>,zip=false){
    const chosen=e.target.files?.[0];e.target.value='';if(!chosen)return;setFile(chosen);
    if(zip){void send('/api/upload-zip',{zip_base64:await zipBase64(chosen),project_name:chosen.name.replace(/\.zip$/i,''),use_ai:ai},chosen.name);return}
    const ext=chosen.name.split('.').pop()?.toLowerCase();
    const lang:SupportedLanguage=['cpp','cc','cxx','h','hpp'].includes(ext||'')?'C++':ext==='java'?'Java':'Python';
    void send('/api/analyze',{code:await chosen.text(),language:lang,file_name:chosen.name,project_name:chosen.name,input_mode:'file',use_ai:ai},chosen.name);
  }
  function openPage(p:Page){setPage(p);setError('');setMobileOpen(false)}
  function exportReport(kind:'md'|'json'){
    if(!result)return;
    const base=(result.project_name||'analysis').toLowerCase().replace(/[^a-z0-9]+/g,'-');
    if(kind==='json')saveFile(base+'.json',JSON.stringify(result,null,2),'application/json');
    else{
      const lines=[`# ${result.project_name||'Code Review'}`, '',result.summary||'', '',`Score: ${score??'—'}/100`, '', '## Findings'];
      findings.forEach(f=>lines.push(`- **${severity(f)} — ${f.rule||f.category||'Finding'}** (${f.file||''}${f.line?':'+f.line:''}): ${f.description||''}`,f.fix?`  - Fix: ${f.fix}`:'' ));
      saveFile(base+'.md',lines.join('\n'),'text/markdown');
    }
  }
  function FindingList({items}:{items:Finding[]}){
    if(!items.length)return <p className="gp-muted">No findings in this group.</p>;
    return <div>{items.map((f,i)=><article className="gp-find" key={i}><div className="gp-row" style={{justifyContent:'space-between'}}><b>{(f.rule||f.category||'Finding').replace(/[-_]/g,' ')}</b><span className="gp-pill">{f.file||'Source'}{f.line?':'+f.line:''}</span></div><p>{f.description||'Review this finding.'}</p>{f.fix&&<p className="fix"><b>Suggested fix:</b> {f.fix}</p>}</article>)}</div>;
  }
  function FormError(){return error?<p role="alert" className="gp-alert">{error}</p>:null}
  function AnalysisResults(){if(!result)return <div className="gp-card"><p>No analysis yet.</p><button className="gp-btn" onClick={()=>openPage('code')}>Start an analysis</button></div>;
    return <><div className="gp-head"><h1>{result.project_name||'Analysis Results'}</h1><p>{result.files_count??files.length} source file(s) reviewed · {result.ai_status==='ok'?'Gemini review completed':ai?'Deterministic results shown':'Offline deterministic analysis'}</p></div>
      <div className="gp-grid gp-g4"><div className="gp-card"><div className="gp-stat-label">Code Health Score</div><div className="gp-stat">{score??'—'}<small className="gp-muted">/100</small></div></div><div className="gp-card"><div className="gp-stat-label">Critical</div><div className="gp-stat">{crit.length}</div></div><div className="gp-card"><div className="gp-stat-label">Warnings</div><div className="gp-stat">{warn.length}</div></div><div className="gp-card"><div className="gp-stat-label">Info notes</div><div className="gp-stat">{info.length}</div></div></div>
      <div className="gp-grid gp-g2" style={{marginTop:16}}><div className="gp-card"><h2>Executive Summary</h2><p className="gp-muted">{result.summary||'No summary returned.'}</p><h3 style={{marginTop:18}}>Critical findings</h3><FindingList items={crit}/><h3 style={{marginTop:18}}>Warnings</h3><FindingList items={warn}/><h3 style={{marginTop:18}}>Information</h3><FindingList items={info}/></div><div className="gp-grid"><div className="gp-card"><h2>Code Metrics</h2><p>Complexity: <b>{result.complexity?.rating||'—'}</b> · average {result.complexity?.average_complexity??'—'}</p><p>Maintainability: <b>{result.complexity?.maintainability_index??'—'}</b></p><p>Documentation coverage: <b>{result.documentation?.doc_coverage_before??result.complexity?.doc_coverage_pct??0}%</b></p><p>Duration: {result.execution_ms??'—'} ms</p></div><div className="gp-card"><h2>Files Reviewed</h2>{files.length?<ul>{files.map((f,i)=><li key={i} className="gp-muted">{f.path||f.file||'Source file'}</li>)}</ul>:<p className="gp-muted">Single-file review</p>}</div><div className="gp-card"><h2>Reports</h2><div className="gp-row"><button className="gp-btn ghost" onClick={()=>exportReport('md')}>Download .MD</button><button className="gp-btn ghost" onClick={()=>exportReport('json')}>Download .JSON</button></div></div></div></div></>;
  }

  return <div className={`gp ${calm?'calm':''}`}><style>{styles}</style><div className="gp-sky"><div className="gp-orb"/><div className="gp-orb b"/></div>
    <header className="gp-top"><div className="gp-row"><button className="gp-btn ghost gp-mobile" onClick={()=>setMobileOpen(!mobileOpen)}>☰</button><button className="gp-logo" onClick={()=>openPage('dashboard')} style={{border:0,background:'none',color:'inherit'}}><i/>TechSpecAnalyser</button></div><div className="gp-row"><span className="gp-pill">{ai?('Gemini · '+(model||'ready')):'Offline analysis'}</span><button className="gp-btn ghost" onClick={()=>setCalm(!calm)}>{calm?'Motion off':'Light'}</button></div></header>
    <div className="gp-body"><nav className={`gp-nav ${mobileOpen?'open':''}`}>{nav.map(n=><button key={n.id} className={page===n.id?'on':''} onClick={()=>openPage(n.id)}><span className="ic">{n.icon}</span>{n.label}</button>)}<button onClick={()=>openPage('code')}><span className="ic">⬆</span>Project ZIP / File</button><div className="gp-card" style={{marginTop:20,padding:14}}><div className="gp-stat-label">Analysis engine</div><b>Static + optional Gemini</b><p className="gp-muted" style={{fontSize:12}}>Source is analyzed as text; it is not run.</p></div></nav>
    <main className="gp-main"><div className="gp-view">
      {page==='dashboard'&&<><section className="gp-hero"><div><span className="gp-badge">AI-Powered Developer Intelligence</span><h1>TechSpecAnalyser</h1><h2>Understand your code. Improve it.</h2><p>Review source code and GitHub repositories for bugs, security risks, complexity, and documentation quality.</p><div className="gp-row"><button className="gp-btn" onClick={()=>openPage('code')}>⌘ Analyze Code</button><button className="gp-btn ghost" onClick={()=>openPage('github')}>⑂ Review GitHub</button></div></div><div className="gp-planet" aria-hidden="true"><span/></div></section><div className="gp-grid gp-g4"><button className="gp-card gp-tile" onClick={()=>openPage('code')}><div className="tile-ic">⌘</div><h3>Code Analysis</h3><p>Paste code or upload a source file.</p></button><button className="gp-card gp-tile" onClick={()=>openPage('github')}><div className="tile-ic">⑂</div><h3>GitHub Review</h3><p>Analyze a repository and its supported files.</p></button><button className="gp-card gp-tile" onClick={()=>openPage('history')}><div className="tile-ic">◷</div><h3>Analysis History</h3><p>Revisit saved analysis runs.</p></button><div className="gp-card gp-tile" style={{opacity:.75,cursor:'default'}}><div className="tile-ic">▧</div><h3>PDF Analysis</h3><p>Not connected in this project yet.</p></div></div></>}
      {page==='code'&&<><div className="gp-head"><h1>Code Analysis</h1><p>Paste a sample or upload a source file / project ZIP.</p></div><div className="gp-card"><form className="gp-form" onSubmit={submitCode}><div className="gp-grid gp-g2"><label className="gp-label">Language<select value={language} onChange={e=>{const l=e.target.value as SupportedLanguage;setLanguage(l);setSample(Object.keys(SAMPLES[l])[0]);setCode(SAMPLES[l][Object.keys(SAMPLES[l])[0]])}}>{languages.map(l=><option key={l}>{l}</option>)}</select></label><label className="gp-label">Ready-made sample<select value={sample} onChange={e=>{setSample(e.target.value);setCode(SAMPLES[language][e.target.value])}}>{Object.keys(SAMPLES[language]).map(s=><option key={s}>{s}</option>)}</select></label></div><label className="gp-label">Source code<textarea value={code} onChange={e=>setCode(e.target.value)} spellCheck={false}/></label><FormError/><div className="gp-row"><button className="gp-btn" disabled={busy}>{busy?'Analyzing…':'Analyze Code'}</button><button type="button" className="gp-btn ghost" onClick={()=>{setCode('');setResult(null)}}>Clear</button><button type="button" className="gp-btn ghost" onClick={()=>fileRef.current?.click()}>Upload File</button><button type="button" className="gp-btn ghost" onClick={()=>zipRef.current?.click()}>Project ZIP</button></div></form><input ref={fileRef} hidden type="file" accept=".py,.cpp,.cc,.cxx,.h,.hpp,.java" onChange={e=>void submitFile(e)}/><input ref={zipRef} hidden type="file" accept=".zip" onChange={e=>void submitFile(e,true)}/></div></>}
      {page==='github'&&<><div className="gp-head"><h1>GitHub Repository Review</h1><p>Analyze public repositories, or private repositories if the server has a GitHub token.</p></div><div className="gp-card"><form className="gp-form" onSubmit={submitRepo}><label className="gp-label">Repository URL<input required value={repoUrl} onChange={e=>setRepoUrl(e.target.value)} placeholder="https://github.com/owner/repository"/></label><label className="gp-label">Branch (optional)<input value={branch} onChange={e=>setBranch(e.target.value)} placeholder="Default branch if blank"/></label><FormError/><button className="gp-btn" disabled={busy}>{busy?'Fetching and analyzing…':'Analyze Repository'}</button></form></div></>}
      {page==='results'&&<AnalysisResults/>}
      {page==='history'&&<><div className="gp-head"><h1>Analysis History</h1><p>Saved runs from the project’s local database.</p></div><div className="gp-card">{history.length?<div style={{overflowX:'auto'}}><table className="gp-table"><thead><tr><th>Project</th><th>Time</th><th>Score</th><th>Summary</th></tr></thead><tbody>{history.map((h,i)=><tr key={h.id||i}><td>{h.project_name||'Analysis'}</td><td>{h.time||'—'}</td><td>{h.score??'—'}</td><td>{h.summary||''}</td></tr>)}</tbody></table></div>:<p className="gp-muted">No saved analyses yet.</p>}</div></>}
      {page==='reports'&&<><div className="gp-head"><h1>Generated Reports</h1><p>Download a report for the latest analysis.</p></div><div className="gp-card">{result?<><p>{result.project_name||'Latest analysis'} · score {score??'—'}/100</p><div className="gp-row"><button className="gp-btn" onClick={()=>exportReport('md')}>Download Markdown</button><button className="gp-btn ghost" onClick={()=>exportReport('json')}>Download JSON</button></div></>:<p className="gp-muted">Run an analysis first to generate reports.</p>}</div></>}
      {page==='settings'&&<><div className="gp-head"><h1>Settings</h1><p>Connection status and display preferences.</p></div><div className="gp-card"><p>Gemini: <b>{ai?'Configured':'Not configured'}</b></p><p>Model: <b>{model||'—'}</b></p><p>AI review is optional. Deterministic analysis remains available when Gemini is offline.</p><label className="gp-row"><input type="checkbox" checked={calm} onChange={e=>setCalm(e.target.checked)} style={{width:18}}/>Reduce background motion</label></div></>}
    </div></main></div></div>;
}
