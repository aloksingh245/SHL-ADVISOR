"""Quick smoke-test against the running local server."""
import time
import httpx
import json

BASE = "http://localhost:8000"


def pp(label, data):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)
    print(json.dumps(data, indent=2))


def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    pp("GET /health", r.json())


def test_vague_query():
    """Agent must clarify, not recommend."""
    r = httpx.post(f"{BASE}/chat", json={
        "messages": [{"role": "user", "content": "I need an assessment"}]
    }, timeout=30)
    data = r.json()
    pp("Vague query (should clarify)", data)
    assert data["recommendations"] == [], "Should NOT recommend on vague query"
    assert data["end_of_conversation"] == False


def test_java_developer():
    """Multi-turn: Java mid-level developer with stakeholder interaction."""
    messages = [
        {"role": "user", "content": "Hiring a Java developer who works with stakeholders"},
        {"role": "assistant", "content": "Sure. What is the seniority level and main dimensions you want to assess?"},
        {"role": "user", "content": "Mid-level, around 4 years. Want to test Java skills and communication."}
    ]
    r = httpx.post(f"{BASE}/chat", json={"messages": messages}, timeout=30)
    if not r.is_success:
        print(f"  HTTP {r.status_code}: {r.text[:300]}")
        assert False, f"Server error {r.status_code}"
    data = r.json()
    pp("Java developer shortlist", data)
    assert len(data["recommendations"]) >= 1, "Should recommend at least 1"
    for rec in data["recommendations"]:
        assert "shl.com" in rec["url"], f"Bad URL: {rec['url']}"


def test_off_topic():
    """Agent must refuse off-topic."""
    r = httpx.post(f"{BASE}/chat", json={
        "messages": [{"role": "user", "content": "What is the best interview question to ask?"}]
    }, timeout=30)
    data = r.json()
    pp("Off-topic refusal", data)
    assert data["recommendations"] == [], "Should refuse with empty recs"


def test_refinement():
    """User refines: add personality tests."""
    messages = [
        {"role": "user", "content": "Hiring a sales manager, need cognitive assessments"},
        {"role": "assistant", "content": "Here are cognitive assessments for a sales manager: ..."},
        {"role": "user", "content": "Actually, add personality tests too"}
    ]
    r = httpx.post(f"{BASE}/chat", json={"messages": messages}, timeout=30)
    data = r.json()
    pp("Refined shortlist (add personality)", data)
    # Should have recs that include P type
    types = [rec["test_type"] for rec in data["recommendations"]]
    print(f"  test_types in shortlist: {types}")


if __name__ == "__main__":
    print("Running smoke tests against", BASE)
    test_health()
    time.sleep(2)
    test_vague_query()
    time.sleep(3)
    test_java_developer()
    time.sleep(3)
    test_off_topic()
    time.sleep(3)
    test_refinement()
    print("\n✅ All tests completed")
