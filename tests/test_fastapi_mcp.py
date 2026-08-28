import os
import sys
from fastapi.testclient import TestClient

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=== Running Integration Tests ===")

    with TestClient(app) as client:
        # Test 1: Health Check
        print("[Test 1] Testing GET /health...")
        res = client.get("/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.json() == {"status": "ok"}, "Health payload mismatch"
        print("[Test 1 PASS] Health check returned 200 OK.")

        # Test 2: Empty Message Validation Check
        print("[Test 2] Testing POST /chat with empty message...")
        res_empty = client.post("/chat", json={"message": ""})
        assert res_empty.status_code == 400, f"Expected 400, got {res_empty.status_code}"
        print("[Test 2 PASS] Empty message returned 400 Bad Request.")

        # Test 3: Prompt Character Cap Validation Check (> 400 chars)
        print("[Test 3] Testing POST /chat with prompt length > 400 characters...")
        long_prompt = "A" * 405
        res_long = client.post("/chat", json={"message": long_prompt})
        assert res_long.status_code in (400, 422), f"Expected 400 or 422, got {res_long.status_code}"
        print("[Test 3 PASS] Prompt over 400 chars rejected with HTTP error.")

        # Test 4: Real Chat Query with MCP Doc Fetch
        print("[Test 4] Testing POST /chat with standard lib query 'What is itertools.permutations in Python?'...")
        res_chat = client.post("/chat", json={"message": "What is itertools.permutations in Python?"})
        assert res_chat.status_code == 200, f"Expected 200, got {res_chat.status_code}"
        
        reply_json = res_chat.json()
        assert "response" in reply_json, "Response key missing in JSON"
        
        reply_text = reply_json["response"]
        print("\n--- API Endpoint Reply ---")
        print(reply_text[:400])
        print("--------------------------\n")
        assert "permutations" in reply_text.lower(), "Reply does not mention permutations!"
        print("[Test 4 PASS] Successfully returned official docs via FastAPI chat endpoint!")

    print("=== All Integration Tests PASSED ===")


if __name__ == "__main__":
    main()
