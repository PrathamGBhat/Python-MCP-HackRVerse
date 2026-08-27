import os
import sys
from fastapi.testclient import TestClient

# Ensure parent directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import app

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


def main():
    print("=== Running Phase 4 & 5 Integration Tests ===")

    # Test 5.1: Health Endpoint Check
    with TestClient(app) as client:
        print("[Test 5.1] Testing GET /health...")
        res = client.get("/health")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"
        assert res.json() == {"status": "ok"}, "Health payload mismatch"
        print("[Test 5.1 PASS] Health check returned 200 OK.")

        # Test 4.3: Empty Message Validation Check
        print("[Test 4.3] Testing POST /chat with empty message...")
        res_empty = client.post("/chat", json={"message": ""})
        assert res_empty.status_code == 400, f"Expected 400, got {res_empty.status_code}"
        print("[Test 4.3 PASS] Empty message returned 400 Bad Request.")

        # Test 4.2 & 5.2: Real Chat Query with MCP Doc Fetch
        print("[Test 4.2 & 5.2] Testing POST /chat with standard lib query 'What is itertools.permutations in Python?'...")
        res_chat = client.post("/chat", json={"message": "What is itertools.permutations in Python?"})
        assert res_chat.status_code == 200, f"Expected 200, got {res_chat.status_code}"
        
        reply_json = res_chat.json()
        assert "response" in reply_json, "Response key missing in JSON"
        
        reply_text = reply_json["response"]
        print("\n--- API Endpoint Reply ---")
        print(reply_text[:500])
        print("--------------------------\n")
        assert "permutations" in reply_text.lower(), "Reply does not mention permutations!"
        print("[Test 4.2 & 5.2 PASS] Successfully returned official docs via FastAPI chat endpoint!")

    print("=== Phase 4 & 5 Integration Tests PASSED ===")


if __name__ == "__main__":
    main()
