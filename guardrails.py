import re

REFUSAL = (
    "I can only help with Python syntax, built-in functions and standard library "
    "usage. I can't solve contest or LeetCode problems or write full solutions. "
    "Ask me about a specific function, like `dict`, `heapq` or `bisect`."
)

# Famous problems. Extend this list for your contest.
KNOWN_PROBLEMS = [
    "two sum", "2sum", "3sum", "three sum", "longest increasing subsequence",
    "knapsack", "n-queens", "n queens", "valid parentheses", "merge intervals",
    "reverse linked list", "coin change", "word ladder", "climbing stairs",
    "maximum subarray", "kadane",
]

BLOCK_PATTERNS = [
    r"\b(leetcode|codeforces|codechef|atcoder|hackerrank|geeksforgeeks)\b",
    r"\b(solve|solution|solutions)\b.{0,40}\b(contest|problem statement|puzzle)\b",
]
_COMPILED = [re.compile(p, re.I | re.S) for p in BLOCK_PATTERNS]

# Phrases that appear in pasted problem statements. Two or more together = block.
STATEMENT_MARKERS = [
    "input format", "output format", "sample input", "sample output",
    "constraints:", "example 1:", "expected output",
]


def rule_blocked(text: str) -> bool:
    t = text.lower()
    if any(name in t for name in KNOWN_PROBLEMS):
        return True
    if any(p.search(t) for p in _COMPILED):
        return True
    return sum(m in t for m in STATEMENT_MARKERS) >= 2

