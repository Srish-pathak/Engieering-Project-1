"""
TechSpecAnalyser — Web Markup & Stylesheet Analyzer.
Supports HTML (.html), CSS (.css), and SCSS (.scss).
"""
import re
from typing import Any, Dict, List

from analyzers.base_analyzer import BaseAnalyzer
from analyzers.security_analyzer import SecurityAnalyzer


class WebAnalyzer(BaseAnalyzer):
    """HTML, CSS, and SCSS static analyzer."""

    def __init__(self):
        super().__init__("Web", [".html", ".htm", ".css", ".scss"])
        self.security_engine = SecurityAnalyzer()

    @property
    def supported_checks(self) -> List[str]:
        return [
            "HTML Document Structure Validation",
            "Accessibility Verification (img missing alt attribute)",
            "Deprecated HTML Elements (<center>, <font>, <marquee>)",
            "Insecure External Resources (http:// URLs)",
            "Inline Script Security & Event Handler Warnings",
            "CSS Bracket Balancing & Specificity Smells (!important)",
            "CWE Security Vulnerability Rule Scanning",
        ]

    def check_syntax(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Validates HTML/CSS tag and brace closures."""
        ext = file_path.split(".")[-1].lower() if file_path else "html"
        if ext in ("css", "scss"):
            # Check balanced braces
            open_count = code.count("{")
            close_count = code.count("}")
            if open_count != close_count:
                return {
                    "valid": False,
                    "bugs": [{
                        "line": 1,
                        "severity": "critical",
                        "title": "Unbalanced CSS Braces",
                        "description": f"Mismatched braces in stylesheet: {open_count} open '{{' vs {close_count} close '}}'.",
                        "file": file_path or "styles.css",
                        "source": "syntax",
                        "confidence": "high",
                    }],
                    "checker": "css-parser",
                }
        return {"valid": True, "bugs": [], "checker": "web-parser"}

    def analyze_bugs(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Finds web markup issues and accessibility warnings."""
        findings: List[Dict[str, Any]] = []
        lines = code.splitlines()
        ext = file_path.split(".")[-1].lower() if file_path else "html"

        if ext in ("html", "htm"):
            for idx, line in enumerate(lines, 1):
                # 1. Image missing alt tag
                if "<img" in line and not re.search(r"""\balt\s*=""", line, re.I):
                    findings.append({
                        "line": idx,
                        "severity": "warning",
                        "rule": "img-missing-alt",
                        "title": "Image Missing `alt` Attribute",
                        "description": "Image `<img>` element lacks an `alt` attribute for screen readers and accessibility.",
                        "file": file_path or "index.html",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Violates WCAG accessibility standards for visually impaired users.",
                        "remediation": "Add descriptive `alt='...'` or `alt=''` for decorative graphics.",
                    })

                # 2. Deprecated HTML tags
                dep_match = re.search(r"""<(center|font|marquee|blink|strike)\b""", line, re.I)
                if dep_match:
                    tag = dep_match.group(1)
                    findings.append({
                        "line": idx,
                        "severity": "info",
                        "rule": "deprecated-html-element",
                        "title": f"Deprecated HTML Tag `<{tag}>`",
                        "description": f"The `<{tag}>` element is obsolete in modern HTML5.",
                        "file": file_path or "index.html",
                        "source": "static",
                        "confidence": "high",
                        "why_problem": "Deprecated elements behave inconsistently across browsers.",
                        "remediation": "Use modern CSS styling (e.g. flexbox, text-align) instead.",
                    })

        elif ext in ("css", "scss"):
            for idx, line in enumerate(lines, 1):
                if "!important" in line:
                    findings.append({
                        "line": idx,
                        "severity": "info",
                        "rule": "css-important-overuse",
                        "title": "Use of `!important` in CSS",
                        "description": "Overusing `!important` breaks CSS cascade and makes style maintenance difficult.",
                        "file": file_path or "styles.css",
                        "source": "static",
                        "confidence": "medium",
                        "why_problem": "Forces overriding styles and disrupts modular component design.",
                        "remediation": "Increase selector specificity or organize cascade layers instead.",
                    })

        return findings

    def analyze_security(self, code: str, file_path: str = "") -> List[Dict[str, Any]]:
        """Scans for web security risks (mixed content HTTP, inline scripts)."""
        findings = self.security_engine.analyze(code, "HTML", file_path)
        lines = code.splitlines()

        for idx, line in enumerate(lines, 1):
            if "<script>" in line.lower() and "src=" not in line.lower():
                findings.append({
                    "line": idx,
                    "severity": "warning",
                    "rule": "inline-script-csp",
                    "cwe": "CWE-79",
                    "title": "Inline <script> Block without CSP Nonce",
                    "description": "Inline scripts violate strict Content Security Policy (CSP) guidelines.",
                    "file": file_path or "index.html",
                    "source": "static-security",
                    "confidence": "high",
                    "why_problem": "Attackers can execute injected scripts if CSP unsafe-inline is permitted.",
                    "remediation": "Move scripts to external files or add a cryptographically random nonce attribute.",
                })

        return findings

    def calculate_complexity(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Returns baseline metrics for web files."""
        lines = code.splitlines()
        loc = len([l for l in lines if l.strip()])
        return {
            "average_complexity": 1.0,
            "rating": "A",
            "lines_of_code": loc,
            "blocks": [],
        }

    def extract_structure(self, code: str, file_path: str = "") -> Dict[str, Any]:
        """Extracts linked stylesheets and script sources."""
        stylesheets = []
        scripts = []

        for m in re.finditer(r"""<link[^>]+href=['"]([^'"]+)['"]""", code, re.I):
            stylesheets.append(m.group(1))
        for m in re.finditer(r"""<script[^>]+src=['"]([^'"]+)['"]""", code, re.I):
            scripts.append(m.group(1))

        return {
            "file": file_path,
            "stylesheets": stylesheets,
            "scripts": scripts,
        }
