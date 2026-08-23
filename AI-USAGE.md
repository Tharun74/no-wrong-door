# AI-USAGE.md

This document describes how AI tooling was used in building this submission,
in accordance with the Brite Spark 2026 AI usage policy.

---

## Tools used

**Antigravity (Google DeepMind)** — an agentic AI coding assistant embedded
in the development environment, used as a pair-programming aid throughout
the build window.

**Claude (Anthropic)** — a conversational AI model, used to plan, analyse,
and reason through different stages of the project before writing code.

---

## How AI was used

AI was used as a pair-programming tool, not as an autonomous author. The
developer drove the session: setting the direction, reviewing every
suggestion before accepting it, and making all architectural calls. No AI
output was copied directly into the repository without being read,
understood, and in many cases edited first.

### Planning and sequencing

The overall approach — FastAPI, the adapter pattern, `SourceUnavailableError`
as the cross-layer signal — emerged from discussion between the developer and
Claude before any code was written. AI helped identify the gap between the
initial scaffold and the floor requirements and proposed a sequencing order,
which the developer revised.

### Code reviewed and accepted with edits

| File | Developer's involvement |
|---|---|
| `app/adapters/resident.py` | Developer wrote the initial scaffold and the `get_all()` pagination loop independently. AI proposed the retry loop for `get_by_id()`; the developer read through every branch, traced the retry logic manually, and removed AI-generated docstrings that added no information. |
| `app/adapters/benefits.py` | Existed in the initial scaffold, written by the developer. AI did not modify it. |
| `services/resident_view.py` | AI drafted the initial version with both adapters called together. The developer later restructured this entirely — removing the benefits call from the per-resident lookup and replacing it with a `not_linked` status — after identifying that returning all 540 records under every resident was semantically wrong (see "Benefits scoping" below). |
| `app/main.py` | AI drafted `list_residents()` and the `SourceUnavailableError` catch pattern. The developer independently added `GET /api/v1/benefits` and applied the benefits-scoping fix. |
| `README.md` | AI drafted the initial version. The developer made significant edits: updated the XML service startup command to reflect the Day 2 failure rate, added the Windows port-exclusion note (`WinError 10013`), rewrote the single-resident response example to reflect `benefits: null`, and updated the degradation table. |
| `DECISIONS.md` | AI drafted the structure and initial tables. The developer reviewed and expanded them, added the "Benefits scoping" section independently, and wrote the Day 2 reflection. |
| `tests/test_api.py` | AI drafted the test script; the developer verified it against the live API and committed it as part of the test evidence. |

---

## What the developer built independently

- **The entire initial project scaffold** — `errors.py`, the initial
  `ResidentAdapter`, `BenefitsAdapter`, `ResidentViewService`, and the
  initial `main.py` with the single-resident endpoint — were written before
  AI was involved in any code generation.
- **The `get_all()` pagination loop** in `resident.py` was written by the
  developer before any AI suggestion on pagination was made.
- **The `GET /api/v1/benefits` endpoint** — added independently after the
  developer decided the full register should be directly reachable without
  being tied to a resident lookup.
- **The benefits-scoping fix** — the developer identified that the previous
  implementation returned all 540 benefits records under every single-resident
  lookup regardless of who was being looked up. There is no shared key
  between the two sources, so those records could not legitimately be
  attributed to that resident. The developer removed the call entirely from
  that endpoint, set `sources.benefits` to `not_linked` with an honest
  reason, and documented the rationale in `DECISIONS.md`. This was the
  developer's decision from start to finish; AI was not involved.
- **All git decisions** — which files to stage, commit message wording,
  commit granularity, and when to push — were made by the developer.

---

## What the developer verified

Every AI-suggested change was read and understood before committing.
The developer did not use AI output as a black box:

- Traced through the retry loop manually for each failure branch before
  accepting it.
- Stopped the REST service deliberately and hit the API to confirm the
  `unavailable` status response rather than a bare 500.
- Confirmed the list endpoint returned 620 unique residents against the
  live mock, proving deduplication was working.
- Ran the full test suite against the XML service at `--failure-rate 0.40`
  to verify the Day 2 change was handled correctly.
- Caught and fixed the semantically incorrect benefits response on the
  per-resident endpoint without any AI prompt.

---

## Decisions that were the developer's, not AI's

- **Declining identity matching.** The problem document flags it as a rabbit
  hole. The developer agreed and did not pursue it.
- **The benefits-scoping fix.** AI's initial design returned all 540 records
  under every resident. The developer rejected that as semantically wrong and
  redesigned it.
- **Adding `GET /api/v1/benefits`.** The developer's call, made to give the
  full register a clean, honest home separate from resident lookups.
- **Keeping the timeout at 2s for Day 2.** The developer accepted the
  latency trade-off rather than loosening the timeout, and documented the
  known edge case (the register's worst-case latency of 2.4s exceeds the
  budget).
- **Increasing `max_retries` to 2.** AI suggested it; the developer
  calculated the residual failure probability (6.4%) and decided it was
  proportionate before accepting.

---

## Summary

AI was used as a pair-programming assistant — consulted for suggestions,
drafts, and reasoning, but not trusted blindly. The developer wrote the
initial scaffold independently, reviewed every AI output before committing,
made all architectural and scoping decisions, and identified and fixed the
most significant design error (the benefits-scoping bug) without any AI
involvement.
