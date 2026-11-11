"""
TechSpecAnalyser — JSON and CSV Report Exporters.
Provides structured data exports for CI/CD integrations and spreadsheet analysis.
"""
import csv
import io
import json
from typing import Any, Dict, List


def generate_json_report(data: Dict[str, Any], indent: int = 2) -> str:
    """Exports full review session payload as formatted JSON."""
    return json.dumps(data, indent=indent, ensure_ascii=False)


def generate_csv_findings(data: Dict[str, Any]) -> str:
    """Exports all security issues and bugs as CSV rows."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "Category",
        "Severity",
        "File",
        "Line",
        "Rule / CWE",
        "Title",
        "Description",
        "Source",
        "Confidence",
        "Suggested Fix",
    ])

    # Security findings
    for sf in data.get("security_findings", []):
        writer.writerow([
            "Security",
            sf.get("severity", "warning"),
            sf.get("file", ""),
            sf.get("line", ""),
            sf.get("cwe") or sf.get("rule", ""),
            sf.get("title", ""),
            sf.get("description", ""),
            sf.get("source", "static-security"),
            sf.get("confidence", "high"),
            sf.get("remediation", ""),
        ])

    # Bug findings
    for b in data.get("bugs", []):
        writer.writerow([
            "Bug / Code Smell",
            b.get("severity", "warning"),
            b.get("file", ""),
            b.get("line", ""),
            b.get("rule", ""),
            b.get("title", ""),
            b.get("description", ""),
            b.get("source", "static"),
            b.get("confidence", "high"),
            b.get("fix", ""),
        ])

    return output.getvalue()
