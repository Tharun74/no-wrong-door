# No Wrong Door

A single API that returns a unified view of a resident, assembled from two
independent, unreliable source systems. If a source is down, the response
still returns what's known, with a machine-readable reason for what's
missing — never a bare error, never silent.

---

## Run it

**Prerequisites:** Python 3.10+, `pip`. No other dependencies.

```bash
git clone https://github.com/Tharun74/no-wrong-door.git
cd no-wrong-door
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Three terminals, venv activated in each:

```bash
# Terminal 1 — Resident Index (REST)
python services/rest_service.py --port 8081

# Terminal 2 — Benefits Register (XML). --failure-rate 0.40 reflects the
# day-two change; see DECISIONS.md.
python services/xml_service.py --port 8082 --failure-rate 0.40

# Terminal 3 — the API
uvicorn app.main:app --port 8000
```

API: `http://127.0.0.1:8000` · Interactive docs: `http://127.0.0.1:8000/docs`

> **Windows, port refused outright (`WinError 10013`):** likely a
> Hyper-V/WSL reserved port range. Use `--port 8090` instead — nothing
> else is hardcoded to 8000.

---

## Endpoints

| Endpoint | Returns |
|---|---|
| `GET /health` | Liveness check |
| `GET /api/v1/residents` | All residents, deduplicated across pages |
| `GET /api/v1/benefits` | Full benefits register, unscoped to any resident |
| `GET /api/v1/residents/{id}` | One resident, plus a Tier-1 matched benefit if one is found (see below) |

```bash
curl http://127.0.0.1:8000/api/v1/residents/R-10451
```

```json
{
  "resident": {
    "id": "R-10451", "first_name": "Tomas", "last_name": "Grady",
    "date_of_birth": "1950-04-21", "address_line": "326 Sycamore Ave",
    "city": "Northgate", "phone": "555-920-1839",
    "program_status": "Suspended", "last_contact": "2025-07-31"
  },
  "benefits": null,
  "matched_benefits": {
    "ref": "NO/2015/4451", "name": "GRADY, Tomas", "born": "1950-04-21",
    "address": "326 Sycamore Avenue", "town": "Northgate",
    "benefit_code": "HSP-A", "review_due": "2026-04-29"
  },
  "sources": {
    "residents": {"status": "available"},
    "benefits": {"status": "not_linked", "reason": "no shared identifier between sources; matching not attempted"},
    "matched_benefits": {"status": "matched", "reason": "first name, last name, and date of birth matched exactly one benefits record"}
  }
}
```

`benefits` is always `null` — there's no shared key between the two
sources, so the full register is never merged into a resident's view
(it's reachable, unscoped, at `GET /api/v1/benefits`). `matched_benefits`
is additive: a conservative exact-match attempt on top of that honest
default. `GET /api/v1/residents/R-DOES-NOT-EXIST` → `404`.

---

## Degradation

Every response includes a `sources` block. A down source never produces a
bare error — always HTTP `200` with the affected field `null` and a
reason (`unavailable`, `degraded`, `not_linked`, `no_match`, `ambiguous`).
`404` is reserved for a source positively confirming a resident doesn't
exist. Full failure-mode table, retry/timeout values, and the reasoning
behind them: **`DECISIONS.md`**.

---

## Tests

```bash
python tests/test_api.py
```

Six live scenarios against the running API: health, benefits degradation
under the 40% failure rate, a genuine 404, pagination dedup, idempotency,
and Tier-1 matching (both a confirmed match and a confirmed non-match).

---

## Project layout

```
app/
├── main.py                 # routes
└── adapters/
    ├── resident.py          # REST: pagination, dedup, retry
    └── benefits.py          # XML: retry, timeout
services/
├── resident_view.py         # assembly + degradation + matching
├── matching.py               # Tier-1 identity matching
└── rest_service.py, xml_service.py, run_both.sh   # [provided by organisers]
errors.py                    # SourceUnavailableError
DECISIONS.md · AI-USAGE.md
```