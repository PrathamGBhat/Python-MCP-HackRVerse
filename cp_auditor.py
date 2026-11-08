"""
CP Code Auditor & Performance Linter.
Statically analyzes Python code snippets using Python's AST (Abstract Syntax Tree)
to detect Time Limit Exceeded (TLE) hazards, memory issues, and suboptimal CP idioms.
"""

import ast
from typing import Any, Dict, List, Optional


class CPAuditVisitor(ast.NodeVisitor):
    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
        self.loop_depth: int = 0
        self.has_recursion: bool = False
        self.has_recursion_limit_boost: bool = False
        self.has_sys_stdin: bool = False
        self.uses_input_builtin: bool = False
        self.current_function: Optional[str] = None
        self.called_functions_in_current: List[str] = []

    def visit_For(self, node: ast.For):
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_While(self, node: ast.While):
        self.loop_depth += 1
        self.generic_visit(node)
        self.loop_depth -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_fn = self.current_function
        prev_calls = self.called_functions_in_current

        self.current_function = node.name
        self.called_functions_in_current = []

        self.generic_visit(node)

        # Check self-recursion
        if self.current_function in self.called_functions_in_current:
            self.has_recursion = True

        self.current_function = prev_fn
        self.called_functions_in_current = prev_calls

    def visit_Call(self, node: ast.Call):
        # Track function name if inside a function
        if self.current_function:
            if isinstance(node.func, ast.Name):
                self.called_functions_in_current.append(node.func.id)

        # 1. Check for standard input()
        if isinstance(node.func, ast.Name) and node.func.id == "input":
            self.uses_input_builtin = True
            if self.loop_depth > 0:
                self.findings.append({
                    "line": getattr(node, "lineno", 1),
                    "severity": "HIGH",
                    "title": "Unbuffered `input()` in loop",
                    "message": "Calling `input()` inside loops causes severe I/O overhead. For N >= 10^5, this frequently leads to TLE.",
                    "fix": "Use `import sys; input = sys.stdin.readline` at the top of your script.",
                })

        # 2. Check for sys.setrecursionlimit
        if isinstance(node.func, ast.Attribute) and node.func.attr == "setrecursionlimit":
            self.has_recursion_limit_boost = True

        # 3. Check for sys.stdin / readline
        if isinstance(node.func, ast.Attribute) and node.func.attr in ("readline", "read"):
            self.has_sys_stdin = True

        # 4. Method calls on objects (e.g. pop(0), insert(0), insort)
        if isinstance(node.func, ast.Attribute):
            method_name = node.func.attr

            # pop(0) check
            if method_name == "pop" and self.loop_depth > 0:
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and first_arg.value == 0:
                        self.findings.append({
                            "line": getattr(node, "lineno", 1),
                            "severity": "CRITICAL",
                            "title": "O(N) `list.pop(0)` inside loop",
                            "message": "Popping from index 0 shifts all memory elements left. Inside a loop, this turns O(N) into O(N^2) (guaranteed TLE for N > 5,000).",
                            "fix": "Use `collections.deque` and `.popleft()` for guaranteed O(1) front pops.",
                        })

            # insert(0, x) check
            if method_name == "insert" and self.loop_depth > 0:
                if node.args:
                    first_arg = node.args[0]
                    if isinstance(first_arg, ast.Constant) and first_arg.value == 0:
                        self.findings.append({
                            "line": getattr(node, "lineno", 1),
                            "severity": "CRITICAL",
                            "title": "O(N) `list.insert(0, ...)` inside loop",
                            "message": "Inserting at index 0 requires shifting all existing items in contiguous array memory.",
                            "fix": "Use `collections.deque` and `.appendleft()` for O(1) front insertions.",
                        })

            # bisect.insort inside loop
            if method_name in ("insort", "insort_left", "insort_right") and self.loop_depth > 0:
                self.findings.append({
                    "line": getattr(node, "lineno", 1),
                    "severity": "HIGH",
                    "title": "`bisect.insort()` inside loop",
                    "message": "While binary search takes O(log N), list insertion requires O(N) shifts. Calling this N times causes O(N^2) runtime.",
                    "fix": "Append all items in O(1) and call `list.sort()` once at the end in O(N log N).",
                })

            # Repeated list.sort() inside loop
            if method_name == "sort" and self.loop_depth > 0:
                self.findings.append({
                    "line": getattr(node, "lineno", 1),
                    "severity": "HIGH",
                    "title": "`list.sort()` repeatedly inside loop",
                    "message": "Sorting an array on every iteration yields O(K * N log N), which quickly breaches the standard 1.0s limit.",
                    "fix": "Consider maintaining a heap (`heapq`) or sorting only after batch operations.",
                })

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare):
        # Check for linear search: `x in list` inside loop
        if self.loop_depth > 0:
            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, (ast.In, ast.NotIn)):
                    # Check if comparator is a list literal or slice
                    if isinstance(comparator, (ast.List, ast.Tuple)):
                        self.findings.append({
                            "line": getattr(node, "lineno", 1),
                            "severity": "HIGH",
                            "title": "Linear membership `in [list]` inside loop",
                            "message": "`x in list` takes O(N) time. In a loop of size N, this becomes O(N^2).",
                            "fix": "Convert lookup collection to a `set` or `dict` for O(1) average lookup.",
                        })
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign):
        # String concatenation inside loop
        if self.loop_depth > 0 and isinstance(node.op, ast.Add):
            if isinstance(node.target, ast.Name):
                self.findings.append({
                    "line": getattr(node, "lineno", 1),
                    "severity": "MEDIUM",
                    "title": "Repeated `+=` accumulation in loop",
                    "message": "String concatenation or list repeated re-allocation in loops copies memory each time, leading to O(N^2) memory reallocation.",
                    "fix": "Append items to a list and join at the end with `''.join(lst)`.",
                })
        self.generic_visit(node)


def audit_python_code(code: str) -> Dict[str, Any]:
    """
    Parses and audits a Python snippet for Competitive Programming traps.
    Returns structured results: clean status, grade, findings, and fast I/O recommendations.
    """
    cleaned = code.strip()
    if not cleaned:
        return {
            "valid": False,
            "error": "Code snippet is empty.",
            "grade": "N/A",
            "findings": []
        }

    try:
        tree = ast.parse(cleaned)
    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Python SyntaxError at line {e.lineno}: {e.msg}",
            "grade": "Syntax Error",
            "findings": []
        }

    visitor = CPAuditVisitor()
    visitor.visit(tree)

    findings = visitor.findings

    # Check for recursion without sys.setrecursionlimit
    if visitor.has_recursion and not visitor.has_recursion_limit_boost:
        findings.append({
            "line": 1,
            "severity": "HIGH",
            "title": "Recursion without `sys.setrecursionlimit`",
            "message": "Python's default recursion limit is 1,000. Deep DFS / recursive tree traversals on N >= 10^4 will crash with RecursionError.",
            "fix": "Add `import sys; sys.setrecursionlimit(200000)` at the beginning.",
        })

    # Global I/O check if input() was used without fast I/O
    if visitor.uses_input_builtin and not visitor.has_sys_stdin:
        # Only add if not already flagged in loop
        if not any(f["title"] == "Unbuffered `input()` in loop" for f in findings):
            findings.append({
                "line": 1,
                "severity": "MEDIUM",
                "title": "Slow I/O: using `input()` instead of `sys.stdin`",
                "message": "For competitive programming inputs with > 10^5 lines or tokens, `input()` is noticeably slower.",
                "fix": "Use `import sys; input = sys.stdin.readline`.",
            })

    # Calculate overall CP Grade
    has_critical = any(f["severity"] == "CRITICAL" for f in findings)
    has_high = any(f["severity"] == "HIGH" for f in findings)
    has_medium = any(f["severity"] == "MEDIUM" for f in findings)

    if has_critical:
        grade = "FAIL (Guaranteed TLE)"
        badge_color = "danger"
    elif has_high:
        grade = "RISKY (Likely TLE on N >= 10^5)"
        badge_color = "warning"
    elif has_medium:
        grade = "MODERATE (Suboptimal CP Idioms)"
        badge_color = "caution"
    else:
        grade = "EXCELLENT (Contest Ready O(1)/O(N log N))"
        badge_color = "success"

    return {
        "valid": True,
        "grade": grade,
        "badge_color": badge_color,
        "findings_count": len(findings),
        "findings": findings,
    }

