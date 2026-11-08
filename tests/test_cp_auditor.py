import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cp_auditor import audit_python_code

def test_tle_pop_zero():
    code = """
for i in range(1000):
    arr.pop(0)
"""
    result = audit_python_code(code)
    assert result["valid"] is True
    assert result["findings_count"] >= 1
    assert any("pop(0)" in f["title"] for f in result["findings"])
    print("[PASS] test_tle_pop_zero")

def test_recursion_limit():
    code = """
def dfs(u, p):
    for v in adj[u]:
        if v != p:
            dfs(v, u)
"""
    result = audit_python_code(code)
    assert result["valid"] is True
    assert any("setrecursionlimit" in f["title"] for f in result["findings"])
    print("[PASS] test_recursion_limit")

def test_clean_idiom():
    code = """
import sys
from collections import deque

input = sys.stdin.readline

q = deque([1, 2, 3])
for _ in range(100):
    val = q.popleft()
"""
    result = audit_python_code(code)
    assert result["valid"] is True
    assert result["findings_count"] == 0
    assert "EXCELLENT" in result["grade"]
    print("[PASS] test_clean_idiom")

if __name__ == "__main__":
    test_tle_pop_zero()
    test_recursion_limit()
    test_clean_idiom()
    print("All cp_auditor unit tests passed successfully!")
