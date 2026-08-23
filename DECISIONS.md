# DECISIONS.md

## Degradation policy

**Partial data beats an error page; silence is never acceptable.** Every
response has a `sources` block. HTTP is always `200` for a well-formed
request, except a source positively confirming a resident doesn't exist
(`404`).

| Source / endpoint | Failure | Retries · timeout | Caller receives |
|---|---|---|---|
| Residents — `GET /api/v1/residents/{id}` | 404 | — | `404`, resident confirmed absent |
| Residents — any endpoint | 5xx / timeout / conn error | 1 retry · 5s | `resident: null`, `status: "unavailable"` + reason |
| Residents — `GET /api/v1/residents` | failure after page 1 | as above | partial list returned, `status: "degraded"` + which page failed |
| Benefits — `GET /api/v1/benefits` | 5xx / timeout / conn error / bad XML | 2 retries (raised from 1, day 2) · 2s | `benefits: null`, `status: "unavailable"` + reason |
| `GET /api/v1/residents/{id}` | — | — | never calls the Benefits Register at all — see "Benefits scoping" |
| Both sources down at once | — | — | both fields `null`, independent statuses; nothing silently dropped |

Benefits timeout (2s) is tighter than the register's own documented
worst-case latency (2.4s) — some `"reason": "timeout"` results reflect our
budget, not genuine unavailability. Known trade-off, not fixed.

## Deduplication

REST pagination has an unstable sort key and can repeat a record across
pages. Records are collected into a `set` keyed by `id`; each is kept once
regardless of how many pages it appears on. `count` in the list response
reflects unique records only.

## Adapter independence

Each source has one adapter owning its own URL, wire format, retries, and
timeout. The assembly layer depends only on that interface, not on REST
vs. XML specifics. This is why the day-two change (below) was one line.

## Benefits scoping

An earlier version returned the entire 540-record register under every
single resident's `benefits` field, regardless of who was being looked
up — wrong, since it implied ownership that didn't exist. Fixed by
removing that call entirely from the per-resident endpoint: `benefits` is
now always `null` there, honestly labelled `not_linked`. The full register
is still reachable, unscoped, at `GET /api/v1/benefits`.

## What's not built, and why

- **Fuzzy/probabilistic matching, or any fallback for benefits records
  missing a date of birth (~11% of the register).** See "Innovation" —
  tested and rejected, not just skipped.
- **Caching.** Needs a defensible expiry policy, which is a product
  decision, not an engineering one — not made under time pressure.
- **Circuit breaking.** Retries already bound the cost of a single call;
  a breaker would reduce load during a *sustained* outage. Natural next
  step if retries prove insufficient.

## Innovation: Tier-1 identity matching

Before writing matching code, the full dataset was checked: first name +
last name + date of birth matched **306 of 620** residents to a **unique**
benefits record, with **zero collisions** either direction, and address
agreement on all 306 (after normalising `Ave`/`Avenue` etc.). Name alone
was ambiguous for 93 residents — date of birth is doing the real work.

`services/matching.py` implements exactly that key. `matched_benefits` is
**additive** to the response — it never changes the `benefits` /
`not_linked` default above. `sources.matched_benefits.status` is one of:
`matched`, `no_match`, `ambiguous` (possible in principle, not observed in
this data — handled rather than assumed away), `unavailable` (register
unreachable), `not_attempted` (no resident to match against).

**Deliberately not attempted:** a name+address fallback for the ~58
benefits records with a blank date of birth — checked, and about a third
of those candidate matches had a different house number at the "matched"
address, meaning the fallback would produce real false positives, not
just missed matches. The register is also re-fetched and re-indexed on
every request rather than cached, to sidestep staleness entirely (see
"Caching" above).

## Day 2 — 2026-08-23: Benefits Register failure rate 15% → 40%

One-line fix: `BenefitsAdapter(..., max_retries=2)` in `app/main.py`. At
15%, one retry meant ~2.25% of calls still failed after retries. At 40%,
one retry would mean ~16%; two retries brings it to ~6.4% — proportionate
for a service now described as permanently degraded. Timeout (2s) left
unchanged; worst case is now a 6s wait, bounded.

Nothing else changed — the adapter boundary absorbed the new failure rate
entirely, which was the point of keeping sources independent.

**What we'd have done differently:** size `max_retries=2` as the original
default rather than reacting to day 2; a short-lived cache and a circuit
breaker would both have reduced load and latency during sustained
failure, and were deferred for the same reasons stated above, not because
they weren't worth doing.

## Stack

Python + FastAPI — no UI requirement for this problem. Standard library
`xml.etree.ElementTree` for XML; no extra parsing dependency needed.
`services/rest_service.py`, `xml_service.py`, `run_both.sh`, and both
`_*_data.json` files were provided by the organisers and unmodified.
Everything else was written for this submission.