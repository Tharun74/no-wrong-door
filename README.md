# No Wrong Door

A single API that returns a unified view of a resident, assembled from two
independent source systems that are slow, unreliable, and have never spoken
to each other.

The API behaves well when the sources do not. If one source is unavailable
the response still returns whatever is known, with a machine-readable
explanation of what is missing and why — never a bare error, never silent.

---

## Prerequisites

- Python 3.10 or later
- `pip` (bundled with Python)

No other runtime dependencies.

---

## 1. Clone and install

```bash
git clone https://github.com/Tharun74/no-wrong-door.git
cd no-wrong-door
```

Create and activate a virtual environment, then install dependencies:

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

---

## 2. Start the mock services

The two source systems are mock servers **provided by the hackathon organisers**
as a starter datapack. Each must run in its own terminal with the virtual
environment activated.

**Terminal A — Resident Index (REST, port 8081)**
```bash
python services/rest_service.py --port 8081
```

**Terminal B — Benefits Register (XML, port 8082)**
```bash
python services/xml_service.py --port 8082 --failure-rate 0.40
```

> **What these are:**
> - The REST service is a paginated JSON endpoint. It intentionally returns
>   the same record on more than one page due to an unstable sort key.
> - The XML service is slow (0.7 – 2.4 s per request) and fails on a
>   configurable percentage of calls with a 500. Both behaviours are
>   normal, not faults to fix.

> **Day 2 update:** the Benefits Register's failure rate was raised to
> **40%** partway through the build and left there permanently — the
> command above already reflects this. The datapack's original default
> was 15%; if you need to reproduce that for comparison, drop the
> `--failure-rate` flag. See `DECISIONS.md` for how the API was adjusted
> in response to this change.

**macOS / Linux only — start both with one command**
```bash
bash services/run_both.sh
```

---

## 3. Start the API

In a third terminal (virtual environment activated):

```bash
python -m uvicorn app.main:app --port 8000
```

The API is now available at `http://127.0.0.1:8000`.

> **Port already in use / Windows `WinError 10013`:** if 8000 is refused
> outright rather than reported as in-use, it's likely reserved by
> Hyper-V/WSL's port exclusion range. Run
> `netsh interface ipv4 show excludedportrange protocol=tcp` to check, or
> just start the API on a different port (`--port 8090`) — nothing else
> is hardcoded to 8000.

---

## 4. Using the API

### Health check

```bash
curl http://127.0.0.1:8000/health
```

```json
{"status": "ok"}
```

---

### List all residents (deduplicated)

```
GET /api/v1/residents
```

```bash
curl http://127.0.0.1:8000/api/v1/residents
```

Returns every resident from the Resident Index, deduplicated across pages.
The `count` field reflects unique records only.

```json
{
  "count": 620,
  "residents": [
    {
      "id": "R-10394",
      "first_name": "Paul",
      "last_name": "Quill",
      "date_of_birth": "1955-06-10",
      "address_line": "261 Sycamore Dr",
      "city": "Weybridge",
      "phone": "555-375-2897",
      "program_status": "Suspended",
      "last_contact": "2025-04-07"
    }
  ],
  "sources": {
    "residents": {"status": "available"}
  }
}
```

---

### List all benefits records

```
GET /api/v1/benefits
```

```bash
curl http://127.0.0.1:8000/api/v1/benefits
```

Returns the full Benefits Register as-is. There is no shared identifier
with the Resident Index, so this endpoint is not scoped to any one
resident — see below.

```json
{
  "count": 540,
  "benefits": [ { "ref": "AS/2024/4702", "name": "...", ... } ],
  "sources": {
    "benefits": {"status": "available"}
  }
}
```

---

### Get a single resident's unified view

```
GET /api/v1/residents/{id}
```

```bash
curl http://127.0.0.1:8000/api/v1/residents/R-10394
```

Returns the resident's record from the Resident Index. The Benefits
Register has no field in common with the Resident Index, so identity
matching across the two sources was out of scope for this submission —
`benefits` is always `null` here, with `sources.benefits` explaining why.
The full register is still reachable via `GET /api/v1/benefits` above.

```json
{
  "resident": {
    "id": "R-10394",
    "first_name": "Paul",
    "last_name": "Quill",
    "date_of_birth": "1955-06-10",
    "address_line": "261 Sycamore Dr",
    "city": "Weybridge",
    "phone": "555-375-2897",
    "program_status": "Suspended",
    "last_contact": "2025-04-07"
  },
  "benefits": null,
  "sources": {
    "residents": {"status": "available"},
    "benefits": {
      "status": "not_linked",
      "reason": "no shared identifier between sources; matching not attempted"
    }
  }
}
```

**404 — resident does not exist**

```bash
curl http://127.0.0.1:8000/api/v1/residents/R-DOES-NOT-EXIST
```

```json
{"detail": "Resident not found"}
```

---

## 5. Degradation behaviour

The `sources` block in every response is machine-readable. When a source
is unavailable its field is `null` and the status block explains why.

| Source | Timeout | Retries | On failure |
|---|---|---|---|
| Resident Index | 5s | 1 (2 attempts total) | `{"status": "unavailable", "reason": "timeout" \| "HTTP 5xx" \| "connection error"}` |
| Benefits Register | 2s | 2 (3 attempts total — raised from 1 on day 2, see `DECISIONS.md`) | `{"status": "unavailable", "reason": "timeout" \| "HTTP 5xx" \| "connection error"}` |
| Benefits Register, per-resident lookup | — | — | always `{"status": "not_linked"}` on `GET /api/v1/residents/{id}` — not a failure mode, see above |

> **Known limitation:** the Benefits Register's 2s timeout is tighter than
> its own documented worst-case latency (2.4s). Some `"reason": "timeout"`
> results reflect our timeout budget rather than the source genuinely
> being down. Noted in `DECISIONS.md`.

**Example — Benefits Register down (on `GET /api/v1/benefits`):**

```json
{
  "count": 0,
  "benefits": [],
  "sources": {
    "benefits": {"status": "unavailable", "reason": "timeout"}
  }
}
```

**Example — Resident Index down (on `GET /api/v1/residents/{id}`):**

```json
{
  "resident": null,
  "benefits": null,
  "sources": {
    "residents": {"status": "unavailable", "reason": "HTTP 500"},
    "benefits": {"status": "not_linked", "reason": "no shared identifier between sources; matching not attempted"}
  }
}
```

The HTTP status code is always `200` when a valid request was made and at
least one source was reachable. `404` is returned only when the Resident
Index confirms the ID does not exist.

---

## Project layout

Files marked `[provided]` were part of the hackathon starter datapack.
Everything else was written for this submission.

```
no-wrong-door/
├── app/
│   ├── main.py               # FastAPI app — routes only          [built]
│   └── adapters/
│       ├── resident.py       # REST adapter: pagination+dedup+retry [built]
│       └── benefits.py       # XML adapter: retry + timeout         [built]
├── services/
│   ├── resident_view.py      # Assembly + degradation logic          [built]
│   ├── rest_service.py       # Mock: Resident Index (REST)          [provided]
│   ├── xml_service.py        # Mock: Benefits Register (XML)        [provided]
│   ├── run_both.sh           # Unix helper to start both mocks      [provided]
│   ├── _rest_data.json       # Seed data for the REST mock          [provided]
│   └── _xml_data.json        # Seed data for the XML mock           [provided]
├── errors.py                 # SourceUnavailableError               [built]
├── requirements.txt          #                                      [built]
├── DECISIONS.md              #                                      [built]
└── AI-USAGE.md               #                                      [built]
```

---

## Interactive API docs

FastAPI generates documentation automatically. With the API running, open:

```
http://127.0.0.1:8000/docs
```
