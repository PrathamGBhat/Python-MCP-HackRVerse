import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from guardrails import rule_blocked

SHOULD_BLOCK = [
    "give me the code for two sum from leetcode",
    "two sum python",
    "Solve this Codeforces problem for me",
    "kadane algorithm code",
    "Example 1: Input: nums = [2,7,11,15] Constraints: 2 <= n <= 10",
]
SHOULD_ALLOW = [
    "How does heapq.heappush work?",
    "what does bisect_left return?",
    "How do I read input fast with sys.stdin?",
    "explain collections.defaultdict",
    "how does functools lru cache work",
]

for text in SHOULD_BLOCK:
    assert rule_blocked(text), f"should be BLOCKED: {text}"
for text in SHOULD_ALLOW:
    assert not rule_blocked(text), f"should be ALLOWED: {text}"

print("All rules-layer tests passed.")

