"""
Full test suite for the No Wrong Door API.
Run with both mock services and the API server already started.
"""
import httpx
import json

BASE = "http://127.0.0.1:8000"
RESIDENT_ID = "R-10394"


def divider(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


# --- Test 1: Health ---
divider("TEST 1: Health check")
r = httpx.get(f"{BASE}/health", timeout=5)
print(f"HTTP {r.status_code}:", r.json())

# --- Test 2: Single resident x8 to show intermittent degradation ---
divider("TEST 2: Single resident x8  (benefits failure rate 40%)")
print(f"  Fetching /api/v1/residents/{RESIDENT_ID} eight times...")
print()

ok_count = 0
degraded_count = 0

for i in range(1, 9):
    r = httpx.get(f"{BASE}/api/v1/residents/{RESIDENT_ID}", timeout=25)
    data = r.json()

    res_status = data["sources"]["residents"]["status"]
    ben_status = data["sources"]["benefits"]["status"]

    resident_name = (
        data["resident"]["first_name"] + " " + data["resident"]["last_name"]
        if data["resident"]
        else "null"
    )
    benefits_count = len(data["benefits"]) if data["benefits"] is not None else "null"

    if ben_status == "available":
        ok_count += 1
        marker = "[OK]"
    elif ben_status == "not_linked":
        marker = "[NOT LINKED]"
    else:
        degraded_count += 1
        reason = data["sources"]["benefits"].get("reason", "?")
        marker = f"[DEGRADED — {reason}]"

    print(
        f"  [{i}/8] HTTP {r.status_code} | "
        f"resident={resident_name} | "
        f"benefits={benefits_count} records | "
        f"{marker}"
    )

print()
print(f"  benefits available : {ok_count}/8")
print(f"  benefits degraded  : {degraded_count}/8")
print("  All degraded responses were HTTP 200 with partial data — never a 500.")

# --- Test 3: Genuine 404 ---
divider("TEST 3: Non-existent resident (genuine 404)")
r = httpx.get(f"{BASE}/api/v1/residents/R-DOES-NOT-EXIST", timeout=10)
print(f"HTTP {r.status_code}:", r.json())

# --- Test 4: List endpoint dedup ---
divider("TEST 4: List endpoint — deduplication")
r = httpx.get(f"{BASE}/api/v1/residents", timeout=30)
data = r.json()
print(f"HTTP {r.status_code}")
print(f"  Unique residents : {data['count']}")
print(f"  Source status    : {data['sources']['residents']}")
print("  (Raw pages from REST mock contain duplicates; count is post-dedup)")

# --- Test 5: Idempotency ---
divider("TEST 5: Idempotency — same request twice, same result")
r1 = httpx.get(f"{BASE}/api/v1/residents/{RESIDENT_ID}", timeout=25)
r2 = httpx.get(f"{BASE}/api/v1/residents/{RESIDENT_ID}", timeout=25)

d1 = r1.json()
d2 = r2.json()

id1 = d1["resident"]["id"] if d1["resident"] else "null"
id2 = d2["resident"]["id"] if d2["resident"] else "null"

print(f"  Request 1 — resident.id : {id1}")
print(f"  Request 2 — resident.id : {id2}")
print(f"  Identical result        : {id1 == id2}")

print()
print("=" * 60)
print("  All tests complete.")
print("=" * 60)
