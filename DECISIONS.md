# DECISIONS.md

A log of design decisions, trade-offs, and what was deliberately not built.
The degradation policy is stated explicitly because the problem document asks
for it and because it is the central design question of this problem.

---

## Degradation policy

> For each way a source can fail, what does the caller get, and how do they
> know?

The governing principle is: **partial data beats an error page, and silence
is never acceptable**. Every response includes a `sources` block that is
machine-readable. When a source is unavailable its corresponding data field
is `null` and the status block names the reason. The HTTP status code is
always `200` for a request that was well-formed and reached the API — `404`
is reserved for the single case where a source positively confirmed the
resident does not exist.

### Resident Index (REST source)

| Failure mode | Retries | What the caller receives |
|---|---|---|
| 404 from source | none (not an error) | HTTP 404. `{"detail": "Resident not found"}`. The source confirmed the ID does not exist. |
| 5xx from source | 1 retry, 0.1 s gap | HTTP 200. `resident: null`. `sources.residents: {"status": "unavailable", "reason": "HTTP 500"}` |
| Request times out | 1 retry, immediate | HTTP 200. `resident: null`. `sources.residents: {"status": "unavailable", "reason": "timeout"}` |
| Connection refused / DNS failure | 1 retry, immediate | HTTP 200. `resident: null`. `sources.residents: {"status": "unavailable", "reason": "connection error"}` |

When the Resident Index is unavailable for a single-resident lookup, the
Benefits Register is not consulted at all — see "Benefits scoping" below
for why the two are no longer queried together on that endpoint.

### Benefits Register (XML source) — `GET /api/v1/benefits` only

The failure modes below apply to the full-register endpoint. They do not
apply to `GET /api/v1/residents/{id}`, which never queries this source —
see "Benefits scoping" below.

| Failure mode | Retries | What the caller receives |
|---|---|---|
| 5xx from source | 1 retry, 0.1 s gap | HTTP 200. `benefits: null`. `sources.benefits: {"status": "unavailable", "reason": "HTTP 500"}` |
| Request times out (> 2 s) | 1 retry, immediate | HTTP 200. `benefits: null`. `sources.benefits: {"status": "unavailable", "reason": "timeout"}` |
| Connection refused / DNS failure | 1 retry, immediate | HTTP 200. `benefits: null`. `sources.benefits: {"status": "unavailable", "reason": "connection error"}` |
| Malformed XML in response | none | HTTP 200. `benefits: null`. `sources.benefits: {"status": "unavailable", "reason": "invalid XML response"}` |

### Both sources unavailable simultaneously

HTTP 200 is returned. Both `resident` and `benefits` are `null`. Both
`sources` entries carry their individual status and reason. The caller can
distinguish "both down at once" from "one down" by inspecting the `sources`
block. No information is silently dropped.

This applies to independent failures of `GET /api/v1/residents` and
`GET /api/v1/benefits` as separate calls. `GET /api/v1/residents/{id}`
can no longer report "both unavailable," since it only ever queries the
Resident Index.

---

## Retry policy

Both adapters use the same strategy: one retry after the first failure,
with a short sleep (0.1 s) before retrying a 5xx, and no sleep before
retrying a network error (the cost is already a failed connection). After
the retry budget is exhausted a `SourceUnavailableError` is raised with the
specific reason, which the view service catches and converts into the status
block above.

A timeout of **5 s** is applied to the Resident Index (paginated; requests
are fast). A timeout of **2 s** is applied to the Benefits Register (each
call is already expected to take 0.7 – 2.4 s; any response beyond 2 s is
treated as a failure and retried). These values were chosen to give each
source a fair chance while keeping total latency bounded.

---

## Deduplication

The Resident Index uses offset pagination over an unstable sort key. Records
near a page boundary are served again on the next page under normal load.

We collect IDs in a Python `set` as we walk the pages. Before appending any
record to the result we check whether its `id` is already in the set. If it
is, we skip it. The result list therefore contains each resident exactly
once regardless of how many pages the source serves it on. The `count` field
in the list response reflects unique records only, so the caller can verify
deduplication is working.

---

## Adapter independence

Each source has one adapter class that owns everything about how to talk to
that source: the URL scheme, the wire format (JSON vs XML), the retry
policy, and the timeout. Nothing outside the adapter depends on these
details.

The view service (`resident_view.py`) depends only on the two adapter
interfaces — it does not know or care whether the underlying transport is
REST or XML. This means a source's behaviour can change (different URL,
different format, different failure rate) without touching the assembly
logic, the API layer, or the other adapter.

This was deliberate preparation for the day-two change. If a third source
is added, or an existing source's format changes, the change is contained to
one file.

---

## Benefits scoping

An earlier version of `GET /api/v1/residents/{id}` called
`benefits_adapter.get_all()` directly and returned the entire 540-record
register under every resident's `benefits` field — regardless of who was
being looked up. That's wrong in a way that matters: it implies those
records belong to the resident being viewed, when there's no basis for
that claim at all.

Fixed by removing the call entirely on that endpoint. `benefits` is now
always `null` there, with `sources.benefits: {"status": "not_linked"}` and
a reason. The full register is still reachable, unscoped and honestly
labelled as such, via `GET /api/v1/benefits`. Nothing is hidden — the
data a caller needs to attempt their own matching is all present, just
not falsely pre-merged.

---

## What was not built, and why

### Identity matching across sources

The two sources share no key. The only candidates for matching are name,
date of birth, and address — all of which are free text with realistic
formatting variation. A match on these fields would be probabilistic.

The problem document is explicit: *"being wrong quietly is much worse than
declining to merge."* We declined. The unified view returns residents and
benefits as independent lists. A caller who wants to attempt matching has all
the data they need and can apply their own policy.

If identity matching is attempted as a stretch goal it will be added behind
a clearly labelled field (e.g. `candidate_matches`) with a stated confidence
score and an explicit policy for uncertain matches. It will not silently
merge records.

### Caching

Not implemented. The Benefits Register is slow but the problem document
accepts that cost. Adding a cache introduces staleness, which requires a
defensible expiry policy. That decision belongs after the floor is met,
because a wrong expiry (too long → stale data surfaced to staff; too short →
cache provides no benefit) is a policy choice, not an engineering one.

### Circuit breaking

Not implemented. The retry budget provides bounded protection against a
flaky source. A circuit breaker would stop calling a source that has failed
consistently, reducing latency and load on a broken service. It was not
added at this stage because it requires state across requests (failure
counts, half-open windows) and the problem does not require persistence. It
is the natural next step if the retry-based approach proves insufficient
under sustained failure.

---

## Backend stack

Python + FastAPI. The submission is a backend integration API with no UI
requirement. FastAPI provides a lightweight HTTP layer, automatic request
validation, and interactive documentation at `/docs` with minimal boilerplate.
The standard library's `xml.etree.ElementTree` handles XML parsing; no
additional parsing dependency is needed.

---

## Starter datapack

`services/rest_service.py`, `services/xml_service.py`,
`services/run_both.sh`, `services/_rest_data.json`, and
`services/_xml_data.json` were provided by the hackathon organisers and were
not modified. Every other file in the repository was written for this
submission.

---

## Day 2 change — 2026-08-23

### What changed

The Benefits Register failure rate increased from 15% to 40%. No new
endpoints, no new data, no structural change to the service — only the
`--failure-rate` argument to `xml_service.py` changed.

### What changed in this codebase

**One line.** In `app/main.py`, the `BenefitsAdapter` instantiation was
updated from `max_retries=1` (the default) to `max_retries=2`.

```python
# before
benefits_adapter = BenefitsAdapter("http://127.0.0.1:8082")

# after
benefits_adapter = BenefitsAdapter("http://127.0.0.1:8082", max_retries=2)
```

**Why:** At 15% failure, one retry meant the caller saw a failed benefits
fetch roughly 15% × 15% = 2.25% of the time. At 40%, that rises to
40% × 40% = 16% — about one in six requests. Two retries brings it to
40% × 40% × 40% ≈ 6.4%, which is more acceptable for a service that is
described as permanently degraded rather than occasionally flaky.

The timeout (2 s) was not changed. At two retries and a 2 s timeout per
attempt the worst-case wait for the benefits call is 6 s. That is slow but
bounded, and it is the cost of a service described as permanently in this
state.

### What did not change

The graceful degradation logic, the adapter interface, the view service, and
the API contract are unchanged. The adapter boundary absorbed the new
failure rate entirely — the rest of the system did not need to know about it.

That was the intended design. Each adapter owns the full behaviour of its
source, including its failure characteristics. Changing the retry count in
one constructor argument is the largest code change this failure rate increase
should require, and it is.

### What we would have done differently

**Caching.** The Benefits Register is both slow (0.7 – 2.4 s per call) and
now fails 40% of the time. A short-lived in-memory cache (TTL of a few
minutes) would mean most requests to a given resident bypass the register
entirely on the fast path, and the slow + flaky call only happens on the
first request after expiry. The staleness trade-off (benefits data up to
N minutes old) is acceptable for most public-service workflows and should
have been named upfront as a deliberate choice rather than left as future
work.

**Circuit breaking.** At 40% failure across all calls, a circuit breaker
would stop calling the register for a short window after a run of failures,
reducing latency and server load during the worst periods. Without it, every
request still pays the retry cost even when the service is comprehensively
down. We would have added this alongside the cache had we anticipated a
sustained high failure rate.

**A higher default retry count.** The original `max_retries=1` default was
sized for a service that fails 15% of the time. If the adapter had been
initialised with `max_retries=2` from the start, the Day 2 change would have
required zero code changes at all. A more conservative default would have
been the right call.