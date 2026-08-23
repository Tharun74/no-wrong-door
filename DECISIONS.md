# Decisions

## 2026-08-23 — Backend stack

Chose Python + FastAPI because the submission is primarily a backend integration API and FastAPI gives us a lightweight HTTP layer with clear separation between API, services, and source adapters.

## 2026-08-23 — Source adapters

Each external source has its own adapter. The rest of the application does not depend on REST/XML implementation details.

## 2026-08-23 — Benefits failure handling

The Benefits source is deliberately slow and intermittently returns errors. We use a bounded timeout and one retry rather than allowing requests to wait indefinitely.

If the Benefits source remains unavailable, the API returns the Resident information with an explicit Benefits source status instead of failing the entire request.

## 2026-08-23 — Identity matching

Identity matching is not part of the initial floor. The two systems do not provide a shared identifier, so we will not silently merge records based only on similar names or addresses. A conservative matching strategy may be added after the floor is complete.

## Current limitations

The current unified response does not yet correlate a Benefits record to a Resident. The Benefits source is currently retrieved independently. This will be addressed after the required reliability and source-handling behaviour is complete.