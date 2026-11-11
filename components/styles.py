"""
TechSpecAnalyser — Developer Space Theme CSS & Design System.
Deep Space / Slate (#0B1020), Electric Blue (#4FD1E8), Violet (#9D7BFF), Cyan (#00F0FF).
"""

DEVELOPER_SPACE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #0B1020;
  --panel: #131A33;
  --panel2: #1A2347;
  --panel-hover: #222D5A;
  --line: #263056;
  --text: #E7EBFA;
  --muted: #98A2C8;
  --accent: #4FD1E8;
  --violet: #9D7BFF;
  --cyan: #00F0FF;
  --crit: #FF6B7A;
  --warn: #FFC857;
  --info: #7AA7FF;
  --good: #5BD6A0;
}

body, .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
}

/* Typography */
h1, h2, h3, h4, .ts-display {
  font-family: 'Space Grotesk', system-ui, sans-serif !important;
  letter-spacing: -0.015em;
  font-weight: 700;
}

code, pre, .ts-mono {
  font-family: 'JetBrains Mono', Consolas, monospace !important;
}

/* Sidebar styling */
section[data-testid="stSidebar"] {
  background-color: #0E1428 !important;
  border-right: 1px solid var(--line) !important;
}

section[data-testid="stSidebar"] .stRadio label {
  color: var(--text) !important;
}

/* ============================================================
   HERO SECTION
   ============================================================ */
.ts-hero {
  background: linear-gradient(135deg, #0B1020 0%, #131A33 50%, #0D1535 100%);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 14px;
  padding: 2rem 2.4rem;
  margin-bottom: 1.5rem;
  position: relative;
  overflow: hidden;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4), inset 0 1px 0 rgba(79,209,232,0.1);
}
.ts-hero::before {
  content: '';
  position: absolute;
  top: -60px; right: -60px;
  width: 240px; height: 240px;
  background: radial-gradient(circle, rgba(79,209,232,0.08) 0%, transparent 70%);
  pointer-events: none;
}
.ts-hero h1 {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2.2rem;
  font-weight: 700;
  letter-spacing: -0.025em;
  margin: 0 0 0.3rem;
  background: linear-gradient(90deg, #E7EBFA 0%, #4FD1E8 50%, #9D7BFF 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.ts-hero p {
  margin: 0 0 1rem;
  color: var(--muted);
  font-size: 1rem;
  line-height: 1.6;
}

/* Pipeline stage pills */
.ts-stages {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.75rem;
}
.ts-stage {
  background: rgba(79, 209, 232, 0.1);
  border: 1px solid rgba(79, 209, 232, 0.3);
  border-radius: 999px;
  padding: 0.2rem 0.75rem;
  font-size: 0.78rem;
  color: var(--accent);
  font-weight: 600;
  letter-spacing: 0.03em;
}

/* ============================================================
   CIRCULAR SCORE RING
   ============================================================ */
.ts-ring {
  width: var(--size, 132px);
  height: var(--size, 132px);
  border-radius: 50%;
  background: conic-gradient(
    var(--ring, #4FD1E8) calc(var(--pct, 0) * 1%),
    #1A2347 0
  );
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  box-shadow: 0 0 20px rgba(79, 209, 232, 0.25);
  flex-shrink: 0;
}
.ts-ring-inner {
  width: calc(var(--size, 132px) - 22px);
  height: calc(var(--size, 132px) - 22px);
  border-radius: 50%;
  background: #0B1020;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.ts-ring-num {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 1.9rem;
  font-weight: 700;
  color: #E7EBFA;
  line-height: 1;
}
.ts-ring-den {
  font-size: 0.65rem;
  color: #98A2C8;
  text-align: center;
  margin-top: 0.1rem;
}

/* ============================================================
   SUMMARY CONTAINER
   ============================================================ */
.ts-summary {
  display: flex;
  gap: 1.5rem;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

/* ============================================================
   METRIC CARDS GRID
   ============================================================ */
.ts-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 0.75rem;
  flex: 1;
}

.ts-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.9rem 1rem;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.ts-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(79, 209, 232, 0.2);
}
.ts-card .k { color: var(--muted); font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600; }
.ts-card .v { font-family: 'Space Grotesk', sans-serif; font-size: 1.6rem; font-weight: 700; line-height: 1.2; margin-top: 0.1rem; }
.ts-card .h { color: var(--muted); font-size: 0.75rem; margin-top: 0.2rem; }
.ts-card.ts-critical { border-left: 3px solid var(--crit); --c: var(--crit); }
.ts-card.ts-warning  { border-left: 3px solid var(--warn); --c: var(--warn); }
.ts-card.ts-good     { border-left: 3px solid var(--good); --c: var(--good); }
.ts-card.ts-info     { border-left: 3px solid var(--info); --c: var(--info); }

/* ============================================================
   STAGE / STATUS CARDS
   ============================================================ */
.ts-stagecard {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0.75rem 0.9rem;
  transition: border-color 0.15s;
}
.ts-stagecard .k { color: var(--muted); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.04em; }
.ts-stagecard .v { font-weight: 700; font-size: 1rem; margin-top: 0.15rem; }
.ts-stagecard .h { color: var(--muted); font-size: 0.72rem; margin-top: 0.1rem; }
.ts-stagecard.ts-critical { border-left: 3px solid var(--crit); }
.ts-stagecard.ts-warning  { border-left: 3px solid var(--warn); }
.ts-stagecard.ts-good     { border-left: 3px solid var(--good); }
.ts-stagecard.ts-info     { border-left: 3px solid var(--info); }

/* ============================================================
   BAR CHART ROWS
   ============================================================ */
.ts-bar-row {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}
.ts-bar-row .n {
  flex: 0 0 110px;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
}
.ts-bar {
  flex: 1;
  height: 6px;
  background: var(--panel2);
  border-radius: 3px;
  overflow: hidden;
}
.ts-bar span {
  display: block;
  height: 100%;
  border-radius: 3px;
  transition: width 0.4s ease;
  background: var(--accent);
}
.ts-bar-row.ts-critical .ts-bar span { background: var(--crit); }
.ts-bar-row.ts-warning  .ts-bar span { background: var(--warn); }
.ts-bar-row.ts-good     .ts-bar span { background: var(--good); }
.ts-bar-row.ts-info     .ts-bar span { background: var(--info); }
.ts-bar-row .x { flex: 0 0 50px; text-align: right; color: var(--muted); font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; }

/* ============================================================
   ISSUE / FINDING CARDS
   ============================================================ */
.ts-issue {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 4px solid var(--info);
  border-radius: 8px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.75rem;
  transition: border-color 0.15s;
}
.ts-issue:hover { border-color: var(--accent); }
.ts-issue.ts-critical { border-left-color: var(--crit); }
.ts-issue.ts-warning  { border-left-color: var(--warn); }
.ts-issue.ts-good     { border-left-color: var(--good); }
.ts-issue.ts-info     { border-left-color: var(--info); }

.ts-issue-head {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  margin-bottom: 0.4rem;
  flex-wrap: wrap;
}
.ts-issue-head span { color: var(--muted); font-size: 0.8rem; }

/* Severity pill badge */
.ts-pill {
  display: inline-block;
  padding: 0.1rem 0.55rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.ts-issue.ts-critical .ts-pill { background: rgba(255,107,122,0.18); color: var(--crit); border: 1px solid rgba(255,107,122,0.4); }
.ts-issue.ts-warning  .ts-pill { background: rgba(255,200,87,0.18);  color: var(--warn); border: 1px solid rgba(255,200,87,0.4); }
.ts-issue.ts-info     .ts-pill { background: rgba(122,167,255,0.18); color: var(--info); border: 1px solid rgba(122,167,255,0.4); }
.ts-issue.ts-good     .ts-pill { background: rgba(91,214,160,0.18);  color: var(--good); border: 1px solid rgba(91,214,160,0.4); }

/* Inline code snippet */
.ts-snippet {
  display: block;
  background: #080D1F;
  border: 1px solid var(--line);
  border-radius: 5px;
  padding: 0.4rem 0.75rem;
  margin: 0.4rem 0;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.82rem;
  color: #A9B4D9;
  overflow-x: auto;
  white-space: pre;
}

/* Fix suggestion */
.ts-fix {
  background: rgba(91, 214, 160, 0.07);
  border-left: 2px solid rgba(91, 214, 160, 0.4);
  padding: 0.4rem 0.7rem;
  margin-top: 0.5rem;
  border-radius: 0 4px 4px 0;
  font-size: 0.85rem;
  color: var(--text);
}

/* Improvement tip card */
.ts-tip {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 4px solid var(--violet);
  border-radius: 8px;
  padding: 0.9rem 1.1rem;
  margin-bottom: 0.75rem;
}
.ts-tip h4 { margin: 0 0 0.4rem; color: var(--violet); font-size: 0.95rem; }

/* ============================================================
   DASHBOARD HEADER CARD (legacy .ts-header)
   ============================================================ */
.ts-header {
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: 12px;
  background: linear-gradient(135deg, var(--panel) 0%, #151D3B 100%);
  padding: 1.4rem 1.8rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.ts-header h1 {
  margin: 0;
  font-size: 2.1rem;
  background: linear-gradient(90deg, #E7EBFA 0%, #4FD1E8 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}
.ts-header p {
  margin: 0.4rem 0 0;
  color: var(--muted);
  font-size: 0.98rem;
}

/* ============================================================
   DASHBOARD METRIC GRID (legacy .ts-metric-*)
   ============================================================ */
.ts-metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}
.ts-metric-card {
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 1rem 1.2rem;
  transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
}
.ts-metric-card:hover {
  transform: translateY(-2px);
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(79, 209, 232, 0.2);
}
.ts-metric-label {
  color: var(--muted);
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}
.ts-metric-value {
  font-family: 'Space Grotesk', sans-serif;
  font-size: 2rem;
  font-weight: 700;
  line-height: 1.2;
  margin-top: 0.2rem;
}
.ts-metric-sub {
  color: var(--muted);
  font-size: 0.78rem;
  margin-top: 0.25rem;
}

/* ============================================================
   FINDING CARDS (legacy .ts-finding / .ts-badge)
   ============================================================ */
.ts-finding {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 4px solid var(--border-color, var(--info));
  border-radius: 8px;
  padding: 1rem 1.2rem;
  margin-bottom: 0.85rem;
}
.ts-finding-crit { --border-color: var(--crit); }
.ts-finding-warn { --border-color: var(--warn); }
.ts-finding-info { --border-color: var(--info); }
.ts-finding-good { --border-color: var(--good); }

.ts-badge {
  display: inline-block;
  padding: 0.15rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ts-badge-crit   { background: rgba(255, 107, 122, 0.18); color: var(--crit); border: 1px solid rgba(255,107,122,0.4); }
.ts-badge-warn   { background: rgba(255, 200, 87, 0.18);  color: var(--warn); border: 1px solid rgba(255,200,87,0.4); }
.ts-badge-info   { background: rgba(122, 167, 255, 0.18); color: var(--info); border: 1px solid rgba(122,167,255,0.4); }
.ts-badge-source { background: rgba(157, 123, 255, 0.18); color: var(--violet); border: 1px solid rgba(157,123,255,0.4); }

.ts-code-snippet {
  background: #0A0F22;
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 0.5rem 0.8rem;
  margin: 0.5rem 0;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.85rem;
  color: #C9D3F5;
  overflow-x: auto;
}

/* ============================================================
   ANIMATIONS & STATUS INDICATORS
   ============================================================ */
@keyframes ts-pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50%       { opacity: 0.6; transform: scale(0.85); }
}

@keyframes ts-glow-anim {
  0%, 100% { text-shadow: 0 0 8px rgba(79, 209, 232, 0.5); }
  50%       { text-shadow: 0 0 20px rgba(79, 209, 232, 0.9), 0 0 40px rgba(79, 209, 232, 0.4); }
}

@keyframes ts-orbit {
  from { transform: rotate(0deg) translateX(18px) rotate(0deg); }
  to   { transform: rotate(360deg) translateX(18px) rotate(-360deg); }
}

.ts-status-dot {
  display: inline-block;
  width: 8px; height: 8px;
  border-radius: 50%;
  animation: ts-pulse 2s ease-in-out infinite;
}
.ts-status-dot.green  { background: var(--good); box-shadow: 0 0 6px var(--good); }
.ts-status-dot.red    { background: var(--crit); box-shadow: 0 0 6px var(--crit); }
.ts-status-dot.yellow { background: var(--warn); box-shadow: 0 0 6px var(--warn); }

.ts-glow { animation: ts-glow-anim 3s ease-in-out infinite; }

/* ============================================================
   NAVIGATION PILL
   ============================================================ */
.ts-nav-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: rgba(79, 209, 232, 0.08);
  border: 1px solid rgba(79, 209, 232, 0.2);
  border-radius: 999px;
  padding: 0.25rem 0.8rem;
  font-size: 0.8rem;
  color: var(--accent);
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
}
.ts-nav-pill:hover {
  background: rgba(79, 209, 232, 0.16);
  border-color: var(--accent);
}

/* ============================================================
   SCROLLBAR OVERRIDES
   ============================================================ */
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--panel); }
::-webkit-scrollbar-thumb { background: var(--line); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ============================================================
   INPUT / FORM OVERRIDES
   ============================================================ */
.stTextInput input,
.stTextArea textarea,
.stSelectbox select {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  color: var(--text) !important;
  border-radius: 8px !important;
}
.stTextInput input:focus,
.stTextArea textarea:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px rgba(79, 209, 232, 0.3) !important;
}

/* ============================================================
   DATAFRAME OVERRIDES
   ============================================================ */
.stDataFrame { border: 1px solid var(--line) !important; border-radius: 8px !important; }
.stDataFrame [data-testid="StyledDataFrameDataCell"] {
  background: var(--panel) !important;
  color: var(--text) !important;
}

/* ============================================================
   COMPONENT OVERRIDES
   ============================================================ */
/* Expander */
.stExpander {
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
  background: var(--panel) !important;
}

/* Alert boxes */
.stAlert { border-radius: 8px !important; }

/* Primary button */
.stButton > button[kind="primary"] {
  background: linear-gradient(135deg, #2A6CDF 0%, #4FD1E8 100%) !important;
  border: none !important;
  color: #fff !important;
  font-weight: 700 !important;
  box-shadow: 0 4px 15px rgba(79, 209, 232, 0.35) !important;
}
.stButton > button[kind="primary"]:hover {
  box-shadow: 0 6px 20px rgba(79, 209, 232, 0.5) !important;
  transform: translateY(-1px);
}

/* Default button */
.stButton > button {
  background: linear-gradient(135deg, #1A2347 0%, #263056 100%) !important;
  color: var(--text) !important;
  border: 1px solid var(--line) !important;
  border-radius: 8px !important;
  font-weight: 600 !important;
}
.stButton > button:hover {
  border-color: var(--accent) !important;
  color: #FFFFFF !important;
  box-shadow: 0 0 10px rgba(79, 209, 232, 0.3) !important;
}

/* Metric widget */
[data-testid="metric-container"] {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  border-radius: 10px !important;
  padding: 0.8rem 1rem !important;
}
[data-testid="metric-container"]:hover {
  border-color: var(--accent) !important;
}

/* Code blocks */
.stCodeBlock { border-radius: 8px !important; }
pre { background: #080D1F !important; border: 1px solid var(--line) !important; border-radius: 8px !important; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 0.4rem;
  border-bottom: 1px solid var(--line);
}
.stTabs [data-baseweb="tab"] {
  background-color: var(--panel);
  border: 1px solid var(--line);
  border-bottom: none;
  border-radius: 6px 6px 0 0;
  color: var(--muted);
  font-weight: 600;
  padding: 0.4rem 1rem;
}
.stTabs [aria-selected="true"] {
  background-color: var(--panel2) !important;
  color: var(--accent) !important;
  border-color: var(--accent) !important;
}
</style>
"""
