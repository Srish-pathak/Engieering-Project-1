# TecSpace Analyser: viva guide

Plain-language answers you can say out loud.

## 1. What problem does it solve?
Beginners often do not know *why* their code is poor. TecSpace Analyser checks code in layers, explains problems, and
gives a score that is calculated, not guessed.

## 2. The pipeline (draw this on the board)
`Code → Syntax check → Static analysis → Complexity → Gemini review → Validate improved code → Score → Report`

If the syntax check fails we stop early, because everything after it needs valid code.
If Gemini fails (no internet, quota) we still show the first three layers. The tool never depends on the AI alone.

## 3. Each part in one minute
**Syntax check.** Python: `compile()` builds bytecode without running it. C++: `g++ -fsyntax-only`. Java: a tree-sitter grammar.
*Why not just try running it?* Running unknown code is unsafe, and some errors only appear when a branch executes.

**AST and static analysis.** An AST (Abstract Syntax Tree) is the code turned into a tree of statements and expressions.
We walk the tree and apply rules, for example "a call node whose function takes 2 required arguments but gets 1".
It never executes the code and the same input always gives the same output.
*Why no false positives?* Each rule skips cases it cannot be sure about (decorated functions, `*args`, redefined names).

**Cyclomatic complexity.** The number of independent paths through a function: start at 1, add 1 for each `if`, loop,
`case`, `and`/`or`. Ranks: A 1-5, B 6-10, C 11-20, D 21-30, E 31-40, F 41+. radon (Python) and lizard (C++/Java) compute it.
Only when no function is found do we fall back to a keyword estimate, and the screen says **ESTIMATED**.

**Maintainability Index.** A 0-100 number from radon combining Halstead volume, complexity and lines of code. Python only.

**Gemini review.** We send the numbered code plus the bugs already found, and ask for JSON that follows a schema
(`response_schema`). Why numbered lines? So the model reports correct line numbers. Why send known findings? So it does not repeat them.
We retry temporary errors (429/503) with a growing delay and translate errors into readable messages.

**Validating the AI's code.** The improved code goes through our own syntax and static checks. If it fails, Gemini gets one
chance to fix it. If it still fails the UI shows a warning instead of pretending it is fine.

**Score.** `rule_score = 10 − penalties` (critical −2, warning −1, info −0.25, plus complexity and maintainability penalties).
`final = 0.6 × rule_score + 0.4 × AI score`. The penalty table is shown in the Score tab.
*Why not trust the AI score alone?* LLM scores vary between runs; rule penalties are repeatable.

**Security.** Key only from `.env`/environment and `.env` is git-ignored. AI text is HTML-escaped. The user's code is placed
inside tags and the prompt says it is data, so "ignore your rules" written in code is not obeyed. A closing tag inside the code is neutralised.

## 4. Demo script (5 minutes)
1. Test case **Python → Wrong function calls**: Analyze. Show the exact line, `missing required argument`, and `totl is not defined`.
2. **Python → Syntax error**: shows the stop-early behaviour with a line number.
3. **C++ → Unsafe C functions**: buffer overflow warnings, division by zero, possible leak.
4. **Java → Common mistakes**: `==` on strings, empty catch.
5. **Python → High complexity**: open the Complexity tab, point at MEASURED and the per-function bars.
6. Open **Score**: explain the table. Then **Before / After** and the diff.
7. Download the HTML report. Open **History** and reopen an earlier review.
8. If the Wi-Fi fails: switch **AI review** off in the sidebar. Everything else still works. Say this proudly; it is a design decision.

## 5. Questions to expect
* *Is the AI always right?* No. That is why rule-based results are separate, labelled with their source, and weigh 60% of the score.
* *Why Streamlit?* Python-only UI, fast to build, and `session_state` keeps results across reruns.
* *What would you add next?* `javac`/`clang-tidy` integration, security rules (SQL injection patterns), multi-file projects, GitHub repository review.
* *What are the limits?* See "Known limitations" in the README. Say them first; it shows you understand your tool.
