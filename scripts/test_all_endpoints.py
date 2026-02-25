#!/usr/bin/env python3
"""Test all API endpoints after router refactoring."""

import asyncio
import sys
from datetime import datetime

import httpx

BASE_URL = "http://localhost:8000"


async def get_auth_token() -> str:
    """Get authentication token."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "dev@example.com", "password": "testpassword123"},
        )
        if resp.status_code == 200:
            return resp.json()["access_token"]
        return ""


async def test_endpoint(
    client: httpx.AsyncClient,
    method: str,
    path: str,
    token: str | None = None,
    json_data: dict | None = None,
    expected_status: list[int] | None = None,
) -> dict:
    """Test a single endpoint."""
    if expected_status is None:
        expected_status = [200, 201]

    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        if method == "GET":
            resp = await client.get(f"{BASE_URL}{path}", headers=headers)
        elif method == "POST":
            resp = await client.post(f"{BASE_URL}{path}", headers=headers, json=json_data or {})
        elif method == "PUT":
            resp = await client.put(f"{BASE_URL}{path}", headers=headers, json=json_data or {})
        elif method == "DELETE":
            resp = await client.delete(f"{BASE_URL}{path}", headers=headers)
        else:
            return {"status": "error", "message": f"Unknown method: {method}"}

        success = resp.status_code in expected_status
        return {
            "status": "ok" if success else "fail",
            "code": resp.status_code,
            "expected": expected_status,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def main() -> int:
    """Run all endpoint tests."""
    print("=" * 70)
    print("API Endpoint Test Suite")
    print(f"Started at: {datetime.now().isoformat()}")
    print("=" * 70)

    # Get auth token
    token = await get_auth_token()
    if not token:
        print("❌ Failed to get auth token")
        return 1
    print("✅ Auth token obtained\n")

    # Test cases: (router, method, path, requires_auth, expected_status, description)
    test_cases = [
        # Health
        ("health", "GET", "/health", False, [200], "Basic health check"),
        ("health", "GET", "/health/detailed", False, [200], "Detailed health check"),
        # Auth (login tested separately for token)
        ("auth", "POST", "/api/auth/logout", True, [200], "Logout"),
        # Config
        ("config", "GET", "/api/config/models", False, [200], "Get models config"),
        # Prompts
        ("prompts", "GET", "/api/prompts", False, [200], "List prompts"),
        ("prompts", "GET", "/api/prompts/step/step0", False, [200, 404], "Get prompt"),
        # Runs
        ("runs", "GET", "/api/runs", True, [200], "List runs"),
        (
            "runs",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000",
            True,
            [404],
            "Get non-existent run",
        ),
        # Artifacts (need a real run_id, expect 404 for fake one)
        (
            "artifacts",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/files",
            True,
            [404],
            "List artifacts (fake run)",
        ),
        # Events
        (
            "events",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/events",
            True,
            [404],
            "List events (fake run)",
        ),
        # Cost
        (
            "cost",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/cost",
            True,
            [404],
            "Get cost (fake run)",
        ),
        # Internal (no auth required)
        (
            "internal",
            "POST",
            "/api/internal/ws/broadcast",
            False,
            [200],
            "WS broadcast",
        ),
        # Diagnostics (uses /api/runs prefix)
        (
            "diagnostics",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/diagnostics/errors",
            True,
            [404],
            "Diagnostics errors (fake run)",
        ),
        # Keywords
        (
            "keywords",
            "POST",
            "/api/keywords/suggest",
            True,
            [200, 422],
            "Keyword suggest",
        ),
        # Hearing
        ("hearing", "GET", "/api/hearing/templates", True, [200], "List templates"),
        # Step11
        (
            "step11",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/step11/status",
            True,
            [404],
            "Step11 status (fake run)",
        ),
        # Step12
        (
            "step12",
            "GET",
            "/api/runs/00000000-0000-0000-0000-000000000000/step12/status",
            True,
            [404],
            "Step12 status (fake run)",
        ),
    ]

    results = {"ok": 0, "fail": 0, "error": 0}
    failures = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for router, method, path, requires_auth, expected, desc in test_cases:
            result = await test_endpoint(
                client,
                method,
                path,
                token if requires_auth else None,
                json_data=({"run_id": "test", "step": "step0", "event_type": "test"} if path == "/api/internal/ws/broadcast" else None),
                expected_status=expected,
            )

            status_icon = {"ok": "✅", "fail": "❌", "error": "⚠️"}[result["status"]]
            print(f"{status_icon} [{router}] {method} {path}")
            print(f"   {desc}: {result}")

            results[result["status"]] += 1
            if result["status"] != "ok":
                failures.append((router, method, path, result))

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"  ✅ OK:    {results['ok']}")
    print(f"  ❌ Fail:  {results['fail']}")
    print(f"  ⚠️  Error: {results['error']}")

    if failures:
        print("\nFailures:")
        for router, method, path, result in failures:
            print(f"  - [{router}] {method} {path}: {result}")

    total = sum(results.values())
    success_rate = (results["ok"] / total * 100) if total > 0 else 0
    print(f"\nSuccess rate: {success_rate:.1f}%")

    return 0 if results["fail"] == 0 and results["error"] == 0 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
