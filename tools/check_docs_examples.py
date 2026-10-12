"""Runs tools/live_test.py against a mock API that serves the response examples from
Anakin's public API reference (anakin.io/docs/api-reference), so every connector action's
response schema is checked against the documented response. No key, no credits.

Usage: python tools/check_docs_examples.py
Requires: httpx, jsonschema.
"""

import argparse
import json
import re
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import live_test  # noqa: E402

JOB = {"jobId": "job_abc123xyz", "status": "pending"}
SCRAPE = {
    "id": "job_abc123xyz", "status": "completed", "url": "https://example.com", "jobType": "url_scraper",
    "country": "us", "html": "<html>...</html>", "cleanedHtml": "<div>...</div>",
    "markdown": "# Page content...", "generatedJson": {"data": {}},
    "links": [{"href": "https://example.com/about", "text": "About"}],
    "images": [{"src": "https://example.com/logo.png", "alt": "Logo"}],
    "summary": "A concise AI-generated summary of the page.",
    "cached": False, "error": None, "createdAt": "2024-01-01T12:00:00Z",
    "completedAt": "2024-01-01T12:00:05Z", "durationMs": 5000,
}
MONITOR = {
    "id": "b1e7c2a4", "url": "https://example.com", "watchMode": "full_page", "intervalMinutes": 1440,
    "isActive": True, "aiMode": False, "creditCostPerRun": 2, "nextRunAt": "2026-01-01T12:00:00Z",
    "createdAt": "2026-01-01T11:00:00Z", "updatedAt": "2026-01-01T11:00:00Z",
}
AI_SEARCH = {
    "search_id": "3d9db7ff", "status": "completed", "country": "us",
    "results": [{"source": "chatgpt", "status": "completed", "summary": "As of July 2026...",
                 "full_content": "{}", "latency_ms": 9100, "credits_used": 1}],
}
# (method, path regex) -> documented response
ROUTES = [
    ("POST", r"/url-scraper/scrape$", SCRAPE),
    ("POST", r"/url-scraper$", JOB),
    ("GET", r"/url-scraper/[^/]+$", SCRAPE),
    ("POST", r"/search$", {"id": "63385e99", "results": [{
        "url": "https://example.com/article", "title": "AI Developments 2024",
        "snippet": "Recent advancements in AI...", "date": "2024-01-15", "last_updated": "2024-01-20"}]}),
    ("POST", r"/agentic-search$", {"job_id": "3f8aa45d", "status": "pending",
                                   "message": "Agentic search job queued successfully",
                                   "created_at": "2024-01-01T12:00:00.000Z"}),
    ("GET", r"/agentic-search/[^/]+$", {
        "id": "3f8aa45d", "status": "completed", "jobType": "agentic_search",
        "generatedJson": {"summary": "Summary...", "structured_data": {"developments": []},
                          "data_schema": {"fields": {}}},
        "createdAt": "2024-01-01T12:00:00.000Z", "completedAt": "2024-01-01T12:05:00.000Z",
        "durationMs": 33500}),
    ("POST", r"/map$", JOB),
    ("GET", r"/map/[^/]+$", {
        "id": "job_abc123xyz", "status": "completed", "url": "https://example.com",
        "links": ["https://example.com/about"], "totalLinks": 1, "externalLinks": [],
        "totalExternalLinks": 0, "createdAt": "2024-01-01T12:00:00Z",
        "completedAt": "2024-01-01T12:00:03Z", "durationMs": 3000}),
    ("POST", r"/crawl$", JOB),
    ("GET", r"/crawl/[^/]+$", {
        "id": "job_abc123xyz", "status": "completed", "url": "https://example.com", "totalPages": 1,
        "completedPages": 1, "results": [{"url": "https://example.com", "status": "completed",
                                          "html": "<html>...</html>", "markdown": "# Home",
                                          "durationMs": 2000}],
        "createdAt": "2024-01-01T12:00:00Z", "completedAt": "2024-01-01T12:00:15Z",
        "durationMs": 15000}),
    ("GET", r"/wire/resolve$", {"results": [{
        "action_id": "ab_search_listings", "catalog_name": "Airbnb", "catalog_slug": "airbnb",
        "name": "Search Listings", "description": "Search Airbnb listings.", "mode": "async",
        "auth_mode": "none", "auth_required": False, "connected": False,
        "params": [{"name": "query", "type": "string", "required": True}], "credits": 1}]}),
    ("GET", r"/wire/catalog$", {"catalog": [{
        "id": "a1b2", "slug": "airbnb", "name": "Airbnb", "url": "https://www.airbnb.com",
        "domain": "airbnb.com", "category": "travel", "description": "Search listings.",
        "auth_required": False, "status": "active", "action_count": 4}]}),
    ("GET", r"/wire/catalog/[^/]+$", {
        "catalog": {"id": "a1b2", "slug": "amazon", "name": "Amazon", "auth_required": False,
                    "status": "active", "action_count": 1},
        "actions": [{"action_id": "amz_search", "name": "Search", "description": "Search.",
                     "type": "read", "mode": "async", "auth_mode": "none", "credits_per_call": 1,
                     "parameters": [{"name": "query", "type": "string", "required": True}]}]}),
    ("POST", r"/wire/task$", {"status": "processing", "job_id": "7c3f1a2b",
                              "poll_url": "/v1/wire/jobs/7c3f1a2b"}),
    ("GET", r"/wire/jobs/[^/]+$", {"status": "completed", "data": {"results": []},
                                   "credits_used": 2, "execution_ms": 8420}),
    ("GET", r"/wire/identities$", {"status": "ok", "identities": [{
        "id": "7c3f", "catalog_id": "a1b2", "name": "Personal Amazon", "is_default": True,
        "credentials": [{"id": "1111", "credential_type": "browser_state", "status": "active",
                         "expires_at": "2026-05-15T10:00:00Z"}]}]}),
    ("POST", r"/wire/build-request$", {"status": "ok", "build_request": {
        "id": "b1a2", "website_url": "https://example.com", "domain": "example.com",
        "goal": "Extract", "visibility": "private", "status": "pending", "credits_charged": 25,
        "created_at": "2026-05-28T12:00:00Z", "updated_at": "2026-05-28T12:00:00Z"}}),
    ("GET", r"/wire/build-requests/[^/]+$", {"id": "b1a2", "status": "pending",
                                             "website_url": "https://example.com"}),
    ("POST", r"/monitors$", MONITOR),
    ("GET", r"/monitors$", {"monitors": [MONITOR]}),
    ("GET", r"/monitors/[^/]+/changes$", {"changes": [{
        "id": "c_9a1", "monitorId": "b1e7c2a4", "changedAt": "2026-01-01T12:00:00Z",
        "summary": "The price dropped.", "diffJson": {"type": "fields"},
        "createdAt": "2026-01-01T12:00:00Z"}]}),
    ("GET", r"/monitors/[^/]+$", MONITOR),
    ("POST", r"/monitors/[^/]+/(pause|resume)$", MONITOR),
    ("POST", r"/monitors/[^/]+/run$", {"success": True, "jobId": "job_abc123xyz"}),
    ("DELETE", r"/monitors/[^/]+$", {"success": True}),
    ("POST", r"/ai-visibility/search$", {"search_id": "3d9db7ff", "status": "running",
                                         "results": [], "country": "us"}),
    ("GET", r"/ai-visibility/search/[^/]+$", AI_SEARCH),
    ("GET", r"/ai-visibility/sources$", {"sources": [{"slug": "chatgpt", "label": "ChatGPT"}]}),
    ("GET", r"/sessions$", {"sessions": [{"id": "session_abc", "name": "amazon", "websiteUrl":
                                          "https://amazon.com", "websiteDomain": "amazon.com",
                                          "isActive": True, "createdAt": "2026-01-01T00:00:00Z"}]}),
    ("DELETE", r"/sessions/[^/]+$", {"success": True}),
    ("POST", r"/ai/evaluate$", {"workflow_id": "wf_1", "status": "queued"}),
    ("GET", r"/ai/jobs/[^/]+$", {"status": "completed", "result": {"heading": "Example Domain"}}),
]


def handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path.removeprefix("/v1")
    for method, pattern, body in ROUTES:
        if request.method == method and re.fullmatch(pattern.rstrip("$"), path):
            return httpx.Response(200, json=body)
    return httpx.Response(404, json={"error": f"no documented example for {request.method} {path}"})


def main() -> int:
    real_client = httpx.Client
    httpx.Client = lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw)  # type: ignore[misc]
    live_test.time.sleep = lambda _: None
    args = argparse.Namespace(only=set(), include_costly=True, session_id="session_abc")
    ops = live_test.plan(args)
    r = live_test.Runner("ask_docs_examples")
    live_test.run(r, ops, args)
    covered = {o for o, _, _ in r.results}
    missing = sorted(set(live_test.OPS) - covered)
    bad = [x for x in r.results if x[1] != "PASS"]
    for op_id, status, detail in bad:
        print(f"{status:6} {op_id}  {detail}")
    print(f"{len(r.results)} calls, {len(covered)} of {len(live_test.OPS)} actions covered, "
          f"{len(bad)} not passing" + (f"; never called: {', '.join(missing)}" if missing else ""))
    return 1 if bad or missing else 0


if __name__ == "__main__":
    sys.exit(main())
