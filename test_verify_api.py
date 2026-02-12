"""
Test script for POST /api/verify-agent-license endpoint.

Usage:
    python test_verify_api.py              # Test Render deployment
    python test_verify_api.py --local      # Test localhost:5000
    python test_verify_api.py --production # Test Finfo production
"""

import sys
import json
import requests

RENDER_URL = "https://lia-agent-verifier.onrender.com/api/verify-agent-license"
FINFO_PRODUCTION_URL = "https://agent-verify.finfo.tw/api/verify-agent-license"
LOCAL_URL = "http://localhost:5000/api/verify-agent-license"
TIMEOUT = 180  # 3 minutes for Render cold start


def run_test(name, url, payload, send_json, expected_http, expected_status_code):
    """Run a single test case and print the result."""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Payload: {payload}")
    print(f"Send as JSON: {send_json}")
    print(f"Expected: HTTP {expected_http}", end="")
    if expected_status_code is not None:
        print(f", status_code={expected_status_code}")
    else:
        print()
    print("-" * 60)

    try:
        if send_json:
            resp = requests.post(url, json=payload, timeout=TIMEOUT)
        else:
            resp = requests.post(
                url,
                data=payload,
                headers={"Content-Type": "text/plain"},
                timeout=TIMEOUT,
            )

        print(f"HTTP Status: {resp.status_code}")

        try:
            body = resp.json()
            print(f"Response JSON: {json.dumps(body, ensure_ascii=False)}")
        except ValueError:
            body = None
            print(f"Response Text: {resp.text[:200]}")

        http_ok = resp.status_code == expected_http
        if expected_status_code is not None and body is not None:
            sc_ok = body.get("status_code") == expected_status_code
        else:
            sc_ok = expected_status_code is None

        passed = http_ok and sc_ok
        verdict = "PASS" if passed else "FAIL"
        print(f"Result: {verdict}")
        if not passed:
            if not http_ok:
                print(f"  -> HTTP mismatch: got {resp.status_code}, expected {expected_http}")
            if not sc_ok:
                got_sc = body.get("status_code") if body else None
                print(f"  -> status_code mismatch: got {got_sc}, expected {expected_status_code}")
        return passed

    except requests.exceptions.Timeout:
        print(f"Result: FAIL (timeout after {TIMEOUT}s)")
        return False
    except requests.exceptions.ConnectionError as e:
        print(f"Result: FAIL (connection error: {e})")
        return False


def main():
    if "--local" in sys.argv:
        url, env = LOCAL_URL, "localhost"
    elif "--production" in sys.argv:
        url, env = FINFO_PRODUCTION_URL, "Finfo Production"
    else:
        url, env = RENDER_URL, "Render"

    print(f"Testing POST /api/verify-agent-license")
    print(f"Target: {url} ({env})")
    print(f"Timeout: {TIMEOUT}s")

    tests = [
        # (name, payload, send_json, expected_http, expected_status_code)
        (
            "1. Approved new agent (0113403577)",
            {"license_number": "0113403577"},
            True, 200, 0,
        ),
        (
            "2. Not qualified - over 1 year (0102204809)",
            {"license_number": "0102204809"},
            True, 200, 1,
        ),
        (
            "3. License not found (01134035)",
            {"license_number": "01134035"},
            True, 200, 3,  # May return 999 if third-party service is down
        ),
        (
            "4. Invalid format - alphanumeric (A123456789)",
            {"license_number": "A123456789"},
            True, 200, 2,
        ),
        (
            "5. Empty JSON body ({})",
            {},
            True, 200, 2,
        ),
        (
            "6. Non-JSON body",
            "not json",
            False, 400, 2,
        ),
    ]

    results = []
    for name, payload, send_json, exp_http, exp_sc in tests:
        passed = run_test(name, url, payload, send_json, exp_http, exp_sc)
        results.append((name, passed))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("=" * 60)
    total = len(results)
    passed_count = sum(1 for _, p in results if p)
    for name, passed in results:
        print(f"  {'PASS' if passed else 'FAIL'}  {name}")
    print(f"\n{passed_count}/{total} tests passed.")


if __name__ == "__main__":
    main()
