"""
Pre-computed Big-O complexity profiles and competitive programming (CP)
constraints for Python built-ins and standard library functions.
"""

from typing import Any, Dict, Optional

COMPLEXITY_REGISTRY: Dict[str, Dict[str, Any]] = {
    # heapq
    "heapq.heappush": {
        "time": "O(log N)",
        "space": "O(1) aux",
        "safe_n": "N <= 10^6",
        "pitfall": "Maintains min-heap property. Do not build an entire heap by repeatedly calling heappush on an existing list — use heapq.heapify() instead, which runs in linear time O(N).",
    },
    "heapq.heappop": {
        "time": "O(log N)",
        "space": "O(1) aux",
        "safe_n": "N <= 10^6",
        "pitfall": "Pops the smallest element. Calling heappop on an empty heap raises IndexError.",
    },
    "heapq.heapify": {
        "time": "O(N)",
        "space": "O(1) in-place",
        "safe_n": "N <= 10^7",
        "pitfall": "Transforms a list into a heap in-place in linear time. Much faster than pushing elements one-by-one (which is O(N log N)).",
    },
    "heapq.nlargest": {
        "time": "O(N log K)",
        "space": "O(K) aux",
        "safe_n": "N <= 10^6 (for small K)",
        "pitfall": "Best when K is much smaller than N. If K approaches N, sorted(lst, reverse=True)[:k] is usually faster due to C-level TimSort optimization.",
    },
    "heapq.nsmallest": {
        "time": "O(N log K)",
        "space": "O(K) aux",
        "safe_n": "N <= 10^6 (for small K)",
        "pitfall": "Best when K << N. If K is close to N, use sorted(lst)[:k].",
    },

    # bisect
    "bisect.bisect_left": {
        "time": "O(log N)",
        "space": "O(1)",
        "safe_n": "N <= 10^9",
        "pitfall": "The sequence MUST be pre-sorted. Calling bisect_left on an unsorted list silently returns incorrect indices without raising an exception.",
    },
    "bisect.bisect_right": {
        "time": "O(log N)",
        "space": "O(1)",
        "safe_n": "N <= 10^9",
        "pitfall": "Returns the insertion point after any existing entries equal to the search key. Remember bisect() is an alias for bisect_right().",
    },
    "bisect.insort_left": {
        "time": "O(N)",
        "space": "O(1)",
        "safe_n": "N <= 5,000",
        "pitfall": "The binary search is O(log N), but list.insert() is O(N). Calling insort in a loop of size N results in O(N^2) total time (guaranteed TLE for N >= 10^4).",
    },
    "bisect.insort_right": {
        "time": "O(N)",
        "space": "O(1)",
        "safe_n": "N <= 5,000",
        "pitfall": "Insertion into a standard Python list requires shifting memory pointers in O(N).",
    },

    # collections.deque
    "collections.deque.append": {
        "time": "O(1)",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": None,
    },
    "collections.deque.appendleft": {
        "time": "O(1)",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": None,
    },
    "collections.deque.pop": {
        "time": "O(1)",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": None,
    },
    "collections.deque.popleft": {
        "time": "O(1)",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": "Optimal for BFS queue operations. Never use list.pop(0) which is O(N). Note: random indexed access (d[i]) on a deque is O(N), not O(1).",
    },

    # collections.Counter & defaultdict
    "collections.Counter": {
        "time": "O(N)",
        "space": "O(U) unique keys",
        "safe_n": "N <= 10^6",
        "pitfall": "Building a Counter from an iterable runs in O(N). Key lookups are O(1) average. Counter.most_common(k) runs in O(N + U log K).",
    },
    "collections.defaultdict": {
        "time": "O(1) avg",
        "space": "O(1) per key",
        "safe_n": "N <= 10^6",
        "pitfall": "Accessing a missing key automatically creates it with the default factory. Watch out for unintended memory growth when checking key existence.",
    },

    # list built-ins
    "list.append": {
        "time": "O(1) amortized",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": "Amortized O(1), occasional O(N) over-allocation resize. Pre-allocating [0] * N is slightly faster for fixed-size buffers.",
    },
    "list.pop": {
        "time": "O(1)",
        "space": "O(1)",
        "safe_n": "N <= 10^7",
        "pitfall": "Popping from the end (list.pop()) is O(1). Popping from index 0 (list.pop(0)) is O(N).",
    },
    "list.pop(0)": {
        "time": "O(N)",
        "space": "O(1)",
        "safe_n": "N <= 5,000",
        "pitfall": "CRITICAL TLE PITFALL: list.pop(0) shifts all remaining elements in memory. In a loop, this turns O(N) into O(N^2). Always use collections.deque.popleft() instead.",
    },
    "list.insert": {
        "time": "O(N)",
        "space": "O(1)",
        "safe_n": "N <= 5,000",
        "pitfall": "Inserting at index 0 shifts all elements in contiguous memory. Use collections.deque.appendleft() for front insertions.",
    },
    "list.sort": {
        "time": "O(N log N)",
        "space": "O(N) worst / O(1) best",
        "safe_n": "N <= 10^6",
        "pitfall": "Implements TimSort in C. Extremely fast for partially sorted data (approaching O(N) best case). In-place modification.",
    },
    "sorted": {
        "time": "O(N log N)",
        "space": "O(N)",
        "safe_n": "N <= 10^6",
        "pitfall": "Returns a new sorted list. Takes O(N) auxiliary space compared to list.sort().",
    },

    # dict & set
    "dict.get": {
        "time": "O(1) avg / O(N) worst",
        "space": "O(1)",
        "safe_n": "N <= 10^6",
        "pitfall": "Codeforces test cases sometimes craft anti-hash collision payloads for integers. In Python 3, randomized hash seeding protects dict keys across runs.",
    },
    "set.add": {
        "time": "O(1) avg / O(N) worst",
        "space": "O(1)",
        "safe_n": "N <= 10^6",
        "pitfall": None,
    },
    "set.intersection": {
        "time": "O(min(len(s), len(t)))",
        "space": "O(min(len(s), len(t)))",
        "safe_n": "N <= 10^6",
        "pitfall": "Much faster than manual loops over membership testing.",
    },

    # math
    "math.gcd": {
        "time": "O(log(min(a, b)))",
        "space": "O(1)",
        "safe_n": "N <= 10^9+7 numbers",
        "pitfall": "Implemented via Euclidean algorithm in C. In Python 3.9+, accepts arbitrary arguments math.gcd(*integers).",
    },
    "math.isqrt": {
        "time": "O(log(log N))",
        "space": "O(1)",
        "safe_n": "Arbitrary precision integers",
        "pitfall": "Computes exact integer square root floor(sqrt(n)) using integer arithmetic, avoiding 64-bit floating point precision loss on numbers >= 2^53.",
    },
    "math.comb": {
        "time": "O(min(k, n - k))",
        "space": "O(1)",
        "safe_n": "n, k <= 10^5 (if using modular arithmetic)",
        "pitfall": "Computes full exact integer n! / (k! * (n-k)!). For contest problems modulo 10^9+7, precompute factorials and modular inverse array instead.",
    },

    # itertools
    "itertools.permutations": {
        "time": "O(N! / (N - r)!)",
        "space": "O(r) per tuple",
        "safe_n": "N <= 10-11",
        "pitfall": "Combinatorial explosion: 10! = 3,628,800 (safe for 1s), but 11! = 39,916,800 (close to 1s limit) and 12! will TLE.",
    },
    "itertools.combinations": {
        "time": "O(N! / (r! * (N - r)!))",
        "space": "O(r) per tuple",
        "safe_n": "N <= 25 (for r ~ N/2)",
        "pitfall": "Generates combinations lazily as an iterator, but iterating through all yields can easily TLE if total combinations exceed 10^7.",
    },

    # functools
    "functools.lru_cache": {
        "time": "O(1) lookup",
        "space": "O(maxsize)",
        "safe_n": "States <= 10^6",
        "pitfall": "Always watch out for sys.getrecursionlimit() (default 1000). For deep recursion DP, set sys.setrecursionlimit(200000) or use iterative DP.",
    },

    # sys.stdin
    "sys.stdin.readline": {
        "time": "O(L) line length",
        "space": "O(L)",
        "safe_n": "Lines <= 10^6",
        "pitfall": "Much faster than standard input() which has prompt overhead. Remember sys.stdin.readline() keeps the trailing newline character '\\n' — use .strip() or .split().",
    },
}


def lookup_complexity(query: str) -> Optional[Dict[str, Any]]:
    """
    Search the registry for a match based on keywords in the user query.
    Returns the complexity dict if found, else None.
    """
    q = query.lower()
    
    # Priority: exact method / function name
    # Sort keys by length descending to match more specific names first
    for key in sorted(COMPLEXITY_REGISTRY.keys(), key=len, reverse=True):
        parts = key.lower().split(".")
        func_name = parts[-1]
        
        # Check if full qualified name or specific func is mentioned
        if key.lower() in q:
            return COMPLEXITY_REGISTRY[key]
        if f" {func_name} " in f" {q} " or f"`{func_name}`" in q:
            return COMPLEXITY_REGISTRY[key]

    return None

