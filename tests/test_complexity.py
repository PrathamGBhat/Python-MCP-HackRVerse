import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from complexity_data import COMPLEXITY_REGISTRY, lookup_complexity
from groq_api import parse_complexity_payload
from guardrails import REFUSAL


def test_parse_standard_complexity_block():
    sample = (
        "Here is how bisect_left works in Python.\n\n"
        ":::complexity\n"
        "time: O(log N)\n"
        "space: O(1)\n"
        "safe_n: N <= 10^9\n"
        "pitfall: Calling bisect on an unsorted list produces wrong answers.\n"
        ":::"
    )
    parsed = parse_complexity_payload(sample, query="bisect_left")
    assert parsed["complexity"] is not None
    assert parsed["complexity"]["time"] == "O(log N)"
    assert parsed["complexity"]["space"] == "O(1)"
    assert parsed["complexity"]["safe_n"] == "N <= 10^9"
    assert "unsorted list" in parsed["complexity"]["pitfall"]
    assert ":::complexity" not in parsed["text"]
    assert "bisect_left works in Python" in parsed["text"]


def test_parse_loose_complexity_block():
    sample = (
        "deque.popleft is O(1).\n\n"
        ":::complexity\n"
        "TIME: O(1)\n"
        "SPACE: O(1)\n"
        "SAFE_N: N <= 10^7\n"
        "PITFALL: None\n"
        ":::"
    )
    parsed = parse_complexity_payload(sample)
    assert parsed["complexity"] is not None
    assert parsed["complexity"]["time"] == "O(1)"
    assert parsed["complexity"]["pitfall"] is None
    assert ":::complexity" not in parsed["text"]


def test_fallback_lookup_on_missing_block():
    sample = "heapq.heappush maintains the min-heap."
    parsed = parse_complexity_payload(sample, query="How does heapq.heappush work in python?")
    assert parsed["complexity"] is not None
    assert "log N" in parsed["complexity"]["time"]
    assert parsed["text"] == sample


def test_refusal_has_no_complexity():
    parsed = parse_complexity_payload(REFUSAL, query="two sum leetcode")
    assert parsed["complexity"] is None
    assert parsed["text"] == REFUSAL


def test_lookup_registry_keys():
    assert lookup_complexity("how does bisect_left work?") is not None
    assert lookup_complexity("heapq.heapify runtime") is not None
    assert lookup_complexity("list.pop(0) slow") is not None
    assert lookup_complexity("unknown_custom_function_xyz") is None


def test_sanitize_tables_with_code():
    raw = (
        "Here is the comparison:\n\n"
        "| Algorithm | Typical time-complexity | Quick illustration |\n"
        "| --- | --- | --- |\n"
        "| Timsort | O(n log n) | python\\narr = [5, 2, 9]\\narr.sort()\\n |\n"
    )
    parsed = parse_complexity_payload(raw)
    assert "|" not in parsed["text"]
    assert "### Timsort" in parsed["text"]
    assert "O(n log n)" in parsed["text"]
    assert "```python" in parsed["text"]
    assert "arr.sort()" in parsed["text"]


if __name__ == "__main__":
    test_parse_standard_complexity_block()
    test_parse_loose_complexity_block()
    test_fallback_lookup_on_missing_block()
    test_refusal_has_no_complexity()
    test_lookup_registry_keys()
    test_sanitize_tables_with_code()
    print("All complexity unit tests passed successfully.")

