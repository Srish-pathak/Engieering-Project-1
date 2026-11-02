import JSZip from 'jszip';

export type SupportedLanguage = 'Python' | 'C++' | 'Java';

export const LANGUAGE_CONFIG: Record<
  SupportedLanguage,
  { ext: string; supportsRadonMi: boolean; badge: string }
> = {
  Python: { ext: '.py', supportsRadonMi: true, badge: 'Primary (Full AST + Radon MI)' },
  'C++': { ext: '.cpp', supportsRadonMi: false, badge: 'Supported (g++ / AST + Lizard CC)' },
  Java: { ext: '.java', supportsRadonMi: false, badge: 'Supported (Grammar + Lizard CC)' },
};

export const SAMPLES: Record<SupportedLanguage, Record<string, string>> = {
  Python: {
    'Payment Service (Synopsis Sec. 14 Showcase)': `import os
import pickle

API_SECRET = "sk_live_9876543210abcdef"


def calculate_fee(amount, tax_rate, discount=0):
    return amount * (1 + tax_rate) - discount


class PaymentGateway:
    def __init__(self, merchant_id):
        self.merchant_id = merchant_id

    def process_payment(self, user_id, raw_payload, audit_log=[]):
        audit_log.append(user_id)
        payload = pickle.loads(raw_payload)
        try:
            net_total = calculate_fee(250)
        except:
            pass
        if net_total > 1000:
            if user_id > 0 and self.merchant_id:
                for attempt in range(3):
                    if attempt == 2 or net_total > 5000:
                        net_total -= 10
        settlement_ratio = net_total / 0
        if payload == None:
            return False
        return receipt_id
        print("Transaction finalized")
`,
    'Wrong function calls': `def calculate_total(price, quantity, discount=0):
    return price * quantity - discount


def average(numbers):
    return sum(numbers) / len(numbers)


print(calculate_total(100))
print(calculate_total(100, 2, discount=5))
print(average([4, 8, 15]))
print(totl)
`,
    'Common mistakes': `import os
import json


def add_item(item, items=[]):
    items.append(item)
    return items


def read_number(text):
    try:
        value = int(text)
    except:
        pass
    ratio = 10 / 0
    if value == None:
        return 0
    return value
    print("finished")
`,
    'Clean code': `"""Fibonacci sequence generator module."""


def fibonacci(n: int) -> list[int]:
    """Return the first n Fibonacci numbers."""
    if n < 0:
        raise ValueError("n must not be negative")
    numbers: list[int] = []
    a, b = 0, 1
    for _ in range(n):
        numbers.append(a)
        a, b = b, a + b
    return numbers


if __name__ == "__main__":
    print(fibonacci(10))
`,
    'Syntax error': `def greet(name)
    print("Hello", name)

greet("Asha")
`,
    'High complexity': `def grade(score, attendance, extra):
    if score >= 90:
        if attendance > 75:
            return "A"
        elif extra:
            return "A-"
        else:
            return "B"
    elif score >= 75:
        for bonus in range(3):
            if extra and attendance > 60 or bonus == 2:
                return "B"
        return "C"
    elif score >= 50:
        while attendance < 75 and extra:
            attendance += 5
        return "C" if attendance >= 75 else "D"
    return "F"
`,
  },
  'C++': {
    'Unsafe C functions': `#include <cstdio>
#include <cstring>

int main() {
    char name[8];
    scanf("%s", name);
    strcpy(name, "a very long default name");
    int unused = 3;
    int* data = new int[10];
    int average = 100 / 0;
    return 0;
}
`,
    'Missing semicolon': `#include <iostream>

int add(int a, int b) {
    return a + b
}

int main() {
    std::cout << add(2, 3) << std::endl;
    return 0;
}
`,
    'Clean code': `#include <iostream>
#include <vector>

int sum(const std::vector<int>& values) {
    int total = 0;
    for (int v : values) {
        total += v;
    }
    return total;
}

int main() {
    std::vector<int> numbers = {1, 2, 3, 4};
    std::cout << sum(numbers) << std::endl;
    return 0;
}
`,
    'Branch heavy': `#include <iostream>

int classify(int a, int b, int c) {
    if (a > 0 && b > 0) {
        if (c > 0 || a > b) {
            return 1;
        }
        for (int i = 0; i < a; i++) {
            if (i % 2 == 0) {
                b += i;
            }
        }
        return 2;
    }
    switch (c) {
        case 1: return 3;
        case 2: return 4;
        default: return 0;
    }
}
`,
  },
  Java: {
    'Common mistakes': `import java.util.List;

public class Checker {
    public static boolean isAdmin(String role) {
        if (role == "admin") {
            return true;
        }
        return false;
    }

    public static int ratio(int total) {
        try {
            return total / 0;
        } catch (Exception e) {
        }
        return 0;
    }
}
`,
    'Missing semicolon': `public class Hello {
    public static void main(String[] args) {
        int count = 5
        System.out.println(count);
    }
}
`,
    'Clean code': `public class Counter {
    private int count;

    public void increment() {
        count++;
    }

    public int getCount() {
        return count;
    }

    public static void main(String[] args) {
        Counter counter = new Counter();
        counter.increment();
        System.out.println(counter.getCount());
    }
}
`,
  },
};

export async function createSampleProjectZipBase64(): Promise<string> {
  const zip = new JSZip();
  zip.file(
    'services/payment_service.py',
    `"""Payment processing service module."""
import os
from models.ledger import record_entry
from utils.validators import validate_amount


def authorize_charge(account_id: str, amount: float, metadata={}):
    if not validate_amount(amount):
        return False
    fee = amount * 0.029
    record_entry(account_id, amount - fee)
    return True
`
  );
  zip.file(
    'models/ledger.py',
    `def record_entry(account_id: str, net_amount: float, history=[]) -> dict:
    history.append((account_id, net_amount))
    if net_amount == None:
        return {"status": "invalid"}
    return {"account": account_id, "net": net_amount, "count": len(history)}
`
  );
  zip.file(
    'utils/validators.py',
    `"""Input validation helpers."""


def validate_amount(value: float) -> bool:
    """Verify that transaction amount is positive and within limits."""
    if value <= 0:
        return False
    if value > 100000:
        return False
    return True
`
  );
  // Add an ignored .venv file to demonstrate automatic virtual-env filtering
  zip.file('.venv/lib/site_packages_dummy.py', 'x = 1\n');
  zip.file('__pycache__/cached.pyc', 'binary');
  return await zip.generateAsync({ type: 'base64' });
}

export async function createUnsafeTraversalZipBase64(): Promise<string> {
  const zip = new JSZip();
  zip.file('../../etc/malicious_traversal.py', 'import os\n');
  return await zip.generateAsync({ type: 'base64' });
}

export const TRACEABILITY_MATRIX = [
  {
    req: '1. Source Input Manager (Paste, File Upload, Project ZIP)',
    existing: 'Partially implemented (Paste & single file only)',
    gap: 'Missing multi-file ZIP upload, path-traversal protection, and ignored directory filtering.',
    status: 'Implemented & Tested',
  },
  {
    req: '2. AST Structural & Docstring Coverage Extractor',
    existing: 'Partially implemented (AST walked for bug rules only)',
    gap: 'Did not extract classes, method signatures, parameter/return annotations, call graph, or docstring coverage %.',
    status: 'Implemented & Tested',
  },
  {
    req: '3. Deterministic Static Analysis Engine (14 Python + C++/Java Rules)',
    existing: 'Already implemented & tested (13 Python + C++/Java rules)',
    gap: 'Needed deterministic security pattern checks (SQLi, hardcoded secrets, unsafe deserialization, subprocess shell=True).',
    status: 'Implemented & Tested',
  },
  {
    req: '4. Software Metrics Engine (McCabe CC & Radon Maintainability Index)',
    existing: 'Already implemented & tested',
    gap: 'Added zero-dependency AST McCabe CC + Halstead MI calculation alongside Radon & function length/doc metrics.',
    status: 'Implemented & Tested',
  },
  {
    req: '5. 6-Agent Multi-Agent Review System & Orchestrator',
    existing: 'Not implemented (Single LLM call only)',
    gap: 'Implemented centralized Orchestrator dispatching AST & static evidence to 6 specialized agents (Quality, Simplification, Security, Complexity, Type/API, Documentation).',
    status: 'Implemented & Tested',
  },
  {
    req: '6. Review Synthesizer & Fact vs. AI Separation',
    existing: 'Partially implemented (basic merge_bugs)',
    gap: 'Synthesizer now deduplicates across all 6 agents, preserves file:line:rule evidence, and separates Deterministic Facts from AI Suggestions.',
    status: 'Implemented & Tested',
  },
  {
    req: '7. Automated Documentation Generator (Docstrings & README.md)',
    existing: 'Not implemented',
    gap: 'Generates PEP-257 proposed docstrings, module/class/function tables, architecture summary, and downloadable README.md.',
    status: 'Implemented & Tested',
  },
  {
    req: '8. SQLite Persistence & Downloadable Reports (.md, .html, .json)',
    existing: 'Partially implemented (JSON file history)',
    gap: 'Migrated history & project runs to modular SQLite database (`codelens.db`) while preserving Markdown, HTML, and JSON exports.',
    status: 'Implemented & Tested',
  },
  {
    req: '9. Experimental Evaluation (Approach A vs. B vs. C)',
    existing: 'Not implemented',
    gap: 'Implemented ground-truth annotated evaluation calculating Precision, Recall, F1, False-Positive Rate, Latency, and Doc Coverage delta.',
    status: 'Implemented & Tested',
  },
];

export const VIVA_DEMO_STEPS = [
  {
    step: 1,
    title: 'Synopsis Showcase: payment_service.py (All 6 Agents + Static Grounding)',
    language: 'Python' as SupportedLanguage,
    sampleName: 'Payment Service (Synopsis Sec. 14 Showcase)',
    targetTab: 'review' as const,
    talkingPoint:
      'Demonstrates the core TechSpecAnalyser thesis: AST static checks catch hardcoded secrets, pickle deserialization, missing arguments, mutable defaults, and division by zero first, then ground the 6 specialized AI agents.',
  },
  {
    step: 2,
    title: 'Python Arity & NameError Detection (Wrong function calls)',
    language: 'Python' as SupportedLanguage,
    sampleName: 'Wrong function calls',
    targetTab: 'review' as const,
    talkingPoint:
      'Shows AST signature inspection (`calculate_total` missing required `quantity` argument on line 9) and scope analysis (`totl` undefined NameError on line 12) without executing code.',
  },
  {
    step: 3,
    title: 'Stop-Early Syntax Gate (Python Syntax error)',
    language: 'Python' as SupportedLanguage,
    sampleName: 'Syntax error',
    targetTab: 'overview' as const,
    talkingPoint:
      'Proves pipeline efficiency: `compile()` catches the missing colon on line 1, halts before wasting AI tokens, and assigns a deterministic 1.0/10 score.',
  },
  {
    step: 4,
    title: 'Measured McCabe Complexity & Radon MI (High complexity)',
    language: 'Python' as SupportedLanguage,
    sampleName: 'High complexity',
    targetTab: 'complexity' as const,
    talkingPoint:
      'Opens the Complexity Analysis view to show exact AST-measured Cyclomatic Complexity (`M = E - N + 2P`), Maintainability Index (0-100), and Complexity Agent decomposition advice.',
  },
  {
    step: 5,
    title: 'C++ Buffer Overflow & Memory Leak Detection (Unsafe C functions)',
    language: 'C++' as SupportedLanguage,
    sampleName: 'Unsafe C functions',
    targetTab: 'security' as const,
    talkingPoint:
      'Demonstrates multi-language support: flags `scanf("%s")`, `strcpy`, raw `new[]` without `delete[]`, and division by zero in the Security & Review tabs.',
  },
  {
    step: 6,
    title: 'Java Reference Equality & Swallowed Exceptions (Common mistakes)',
    language: 'Java' as SupportedLanguage,
    sampleName: 'Common mistakes',
    targetTab: 'review' as const,
    talkingPoint:
      'Catches `role == "admin"` string reference comparison, unused `java.util.List` import, and empty `catch (Exception e) {}` block.',
  },
  {
    step: 7,
    title: 'Automated PEP-257 Docstrings & README Generation',
    language: 'Python' as SupportedLanguage,
    sampleName: 'Payment Service (Synopsis Sec. 14 Showcase)',
    targetTab: 'documentation' as const,
    talkingPoint:
      'Shows how AST-extracted function signatures and the Documentation Agent take docstring coverage from 0% to 100% with downloadable README.md output.',
  },
  {
    step: 8,
    title: 'Experimental Evaluation: Approach A vs. Approach B vs. Approach C',
    language: 'Python' as SupportedLanguage,
    sampleName: 'Clean code',
    targetTab: 'evaluation' as const,
    talkingPoint:
      'Presents the research contribution: comparing Direct Single-LLM (Approach A), Un-grounded Multi-Agent (Approach B), and Static-Grounded Multi-Agent CodeLens AI (Approach C) using Precision, Recall, and F1.',
  },
];
