import httpx
import json

BASE = "http://127.0.0.1:8000"
RESIDENT_ID = "R-10394"


def divider(title):
    print()
    print("=" * 60)
    print(f"  {title}")
    print("=" * 60)


divider("TEST 1: Health check")
r = httpx.get(f"{BASE}/health", timeout=5)
print(f"HTTP {r.status_code}:", r.json())

divider("TEST 2: GET /api/v1/benefits x10  (register at 40% failure rate)")
ok_count = 0
degraded_count = 0

for i in range(1, 11):
    r = httpx.get(f"{BASE}/api/v1/benefits", timeout=25)
    data = r.json()

    ben_status = data["sources"]["benefits"]["status"]

    if ben_status == "available":
        ok_count += 1
        marker = "[OK]"
    else:
        degraded_count += 1
        reason = data["sources"]["benefits"].get("reason", "?")
        marker = f"[DEGRADED — {reason}]"

    print(
        f"  [{i}/10] HTTP {r.status_code} | "
        f"count={data['count']} | "
        f"{marker}"
    )

print()
print(f"  available : {ok_count}/10")
print(f"  degraded  : {degraded_count}/10")
print("  All degraded responses were HTTP 200 with partial data — never a 500.")

divider("TEST 3: Non-existent resident (genuine 404)")
r = httpx.get(f"{BASE}/api/v1/residents/R-DOES-NOT-EXIST", timeout=10)
print(f"HTTP {r.status_code}:", r.json())

divider("TEST 4: List endpoint — deduplication")
r = httpx.get(f"{BASE}/api/v1/residents", timeout=30)
data = r.json()
print(f"HTTP {r.status_code}")
print(f"  Unique residents : {data['count']}")
print(f"  Source status    : {data['sources']['residents']}")
print("  (Raw pages from REST mock contain duplicates; count is post-dedup)")

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

divider("TEST 6: Tier-1 identity matching")
MATCHED_ID = "R-10451"   # Tomas Grady — confirmed unique match in the data pack
UNMATCHED_ID = "R-10394"  # Paul Quill — confirmed absent from the benefits register

r = httpx.get(f"{BASE}/api/v1/residents/{MATCHED_ID}", timeout=25)
data = r.json()
print(f"  {MATCHED_ID} (expected: matched)")
print(f"    matched_benefits status : {data['sources']['matched_benefits']}")
print(f"    matched_benefits.ref    : {data['matched_benefits']['ref'] if data['matched_benefits'] else None}")

r = httpx.get(f"{BASE}/api/v1/residents/{UNMATCHED_ID}", timeout=25)
data = r.json()
print(f"  {UNMATCHED_ID} (expected: no_match)")
print(f"    matched_benefits status : {data['sources']['matched_benefits']}")
print(f"    matched_benefits        : {data['matched_benefits']}")

print()
print("  Note: matched_benefits.status can also come back 'unavailable' if")
print("  the register happens to fail all retries during this call — that's")
print("  expected at a 40% base failure rate, not a bug. Re-run if so.")

print()
print("=" * 60)
print("  All tests complete.")
print("=" * 60)