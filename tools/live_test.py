"""Calls every connector action against the live Anakin API and checks each response
against the response schema in apiDefinition.swagger.json.

Usage:
    ANAKIN_API_KEY=... python tools/live_test.py [--yes] [--only Op1,Op2] [--include-costly]
    python tools/live_test.py --key-file ~/.anakin_key --yes

Without --yes it only prints the plan and the estimated credit cost. The key is read
from ANAKIN_API_KEY or --key-file and is never printed.

Skipped unless asked for:
- --include-costly: RequestWireBuild (about 25 credits) and StartBrowserTask.
- DeleteBrowserSession: only with --session-id, which must be a session you can lose.
The monitor test creates its own monitor and deletes it at the end.

Requires: httpx, jsonschema (uv run --no-project --with httpx --with jsonschema ...).
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import httpx
import jsonschema

ROOT = Path(__file__).resolve().parent.parent
SWAGGER = json.loads((ROOT / "certified-connectors/Anakin/apiDefinition.swagger.json").read_text())
BASE = f"https://{SWAGGER['host']}{SWAGGER['basePath']}"
OPS = {o["operationId"]: (m, p, o) for p, ms in SWAGGER["paths"].items() for m, o in ms.items()}

# Rough credits per call, from anakin.io/pricing; Wire and AI visibility vary.
COST = {"ScrapeUrl": 1, "ScrapeUrlNow": 1, "Search": 3, "StartAgenticSearch": 15, "StartMap": 1,
        "StartCrawl": 2, "RunWireAction": 2, "StartAiVisibilitySearch": 3, "RunMonitorNow": 2,
        "RequestWireBuild": 25, "StartBrowserTask": 3}


class Runner:
    def __init__(self, key: str) -> None:
        self.http = httpx.Client(base_url=BASE, headers={"X-API-Key": key}, timeout=120.0)
        self.results: list[tuple[str, str, str]] = []

    def call(self, op_id: str, path_params: dict[str, str] | None = None,
             query: dict[str, Any] | None = None, body: dict[str, Any] | None = None) -> Any:
        method, path, op = OPS[op_id]
        for name, value in (path_params or {}).items():
            path = path.replace("{" + name + "}", httpx.URL(value).raw_path.decode())
        if body is not None:
            schema = next(p for p in op["parameters"] if p["in"] == "body")["schema"]
            jsonschema.validate(body, _strip(schema))  # the test's own input must be valid
        res = self.http.request(method.upper(), path, params=query, json=body)
        data = res.json() if res.content else {}
        if res.status_code >= 400:
            self.results.append((op_id, "FAIL", f"HTTP {res.status_code}: {str(data)[:160]}"))
            return None
        schema = op["responses"]["200"]["schema"]
        problems = _schema_problems(data, schema)
        status = "PASS" if not problems else "SCHEMA"
        detail = f"HTTP {res.status_code}" + (f"; {problems[0]}" if problems else "")
        self.results.append((op_id, status, detail))
        return data

    def wait(self, op_id: str, job_id: str, done: set[str], every: float = 5,
             limit: float = 360) -> Any:
        """Calls a get result action until its status is final; records only the last call."""
        deadline = time.monotonic() + limit
        while True:
            before = len(self.results)
            data = self.call(op_id, {"id": job_id})
            status = (data or {}).get("status")
            if data is None or status in done or time.monotonic() > deadline:
                if status not in done and data is not None:
                    self.results[-1] = (op_id, "FAIL", f"still {status} after {limit:.0f} s")
                return data
            del self.results[before:]
            time.sleep(every)


def _strip(schema: Any) -> Any:
    """The schema without Microsoft extensions, for jsonschema."""
    if isinstance(schema, dict):
        out = {k: _strip(v) for k, v in schema.items()
               if not k.startswith("x-ms-") and k != "x-nullable"}
        if schema.get("x-nullable") and "type" in out:
            out["type"] = [out["type"], "null"]
        return out
    if isinstance(schema, list):
        return [_strip(v) for v in schema]
    return schema


def _schema_problems(data: Any, schema: dict[str, Any]) -> list[str]:
    """Type mismatches between a live response and its declared schema. Fields the API
    returns but the schema leaves out are reported too, since makers can't see them."""
    out: list[str] = []
    validator = jsonschema.Draft4Validator(_strip(schema))
    for err in validator.iter_errors(data):
        out.append(f"{'/'.join(map(str, err.absolute_path)) or '(root)'}: {err.message[:120]}")
    if isinstance(data, dict) and schema.get("properties"):
        extra = sorted(set(data) - set(schema["properties"]))
        if extra:
            out.append(f"undeclared fields: {', '.join(extra[:8])}")
    return out


def plan(args: argparse.Namespace) -> list[str]:
    ops = [o for o in OPS if not args.only or o in args.only]
    if not args.include_costly:
        ops = [o for o in ops if o not in ("RequestWireBuild", "StartBrowserTask", "GetWireBuild",
                                           "GetBrowserTaskResult")]
    if not args.session_id:
        ops = [o for o in ops if o != "DeleteBrowserSession"]
    return ops


def run(r: Runner, ops: list[str], args: argparse.Namespace) -> None:
    want = set(ops)

    def on(*names: str) -> bool:
        return bool(want & set(names))

    if on("ScrapeUrlNow"):
        r.call("ScrapeUrlNow", body={"url": "https://example.com"})
    if on("ScrapeUrl", "GetScrapeResult"):
        started = r.call("ScrapeUrl", body={"url": "https://example.com", "formats": ["markdown", "links"]})
        if started and on("GetScrapeResult"):
            r.wait("GetScrapeResult", started["jobId"], {"completed", "failed"}, every=3)
    if on("Search"):
        r.call("Search", body={"prompt": "Anakin web scraping API", "limit": 3})
    if on("StartMap", "GetMapResult"):
        started = r.call("StartMap", body={"url": "https://example.com", "limit": 10, "depth": 1})
        if started and on("GetMapResult"):
            r.wait("GetMapResult", started["jobId"], {"completed", "failed"}, every=3)
    if on("StartCrawl", "GetCrawlResult"):
        started = r.call("StartCrawl", body={"url": "https://example.com", "maxPages": 2})
        if started and on("GetCrawlResult"):
            r.wait("GetCrawlResult", started["jobId"], {"completed", "failed"}, every=5)
    if on("StartAgenticSearch", "GetAgenticSearchResult"):
        started = r.call("StartAgenticSearch",
                         body={"prompt": "What does example.com say it is for?", "useBrowser": False})
        if started and on("GetAgenticSearchResult"):
            r.wait("GetAgenticSearchResult", started["job_id"], {"completed", "failed"}, every=10,
                   limit=600)

    # A keyless Wire action whose only required input is a search term, so the test can fill it.
    action_id, required = None, set()
    if on("DiscoverWireActions", "RunWireAction", "GetWireJobResult"):
        found = r.call("DiscoverWireActions", query={"q": "search products", "auth_mode": "none"})
        for match in (found or {}).get("results", []):
            needed = {p["name"] for p in match.get("params") or [] if p.get("required")}
            if match.get("auth_mode") == "none" and needed <= {"query", "q", "keyword"}:
                action_id, required = match["action_id"], needed
                break
    if on("ListWireCatalogs"):
        r.call("ListWireCatalogs")
    if on("GetWireCatalog"):
        r.call("GetWireCatalog", {"slug": "amazon"})
    if on("RunWireAction", "GetWireJobResult"):
        if not action_id:
            r.results.append(("RunWireAction", "SKIP", "no keyless action with simple params found"))
        else:
            params = {name: "usb c cable" for name in required}
            ran = r.call("RunWireAction", body={"action_id": action_id, "params": params})
            if ran and ran.get("job_id") and ran.get("status") not in ("completed", "failed"):
                if on("GetWireJobResult"):
                    r.wait("GetWireJobResult", ran["job_id"], {"completed", "failed"}, every=3)
            elif on("GetWireJobResult"):
                r.results.append(("GetWireJobResult", "SKIP", "the action answered inline"))
    if on("ListWireIdentities"):
        r.call("ListWireIdentities")
    if on("RequestWireBuild", "GetWireBuild"):
        built = r.call("RequestWireBuild", body={"website_url": "https://example.com",
                                                 "goal": "Extract the page heading and paragraph"})
        if built and on("GetWireBuild"):
            r.call("GetWireBuild", {"id": built["build_request"]["id"]})

    monitor_id = None
    if on("CreateMonitor", "ListMonitors", "GetMonitor", "GetMonitorChanges", "PauseMonitor",
          "ResumeMonitor", "RunMonitorNow", "DeleteMonitor"):
        created = r.call("CreateMonitor", body={"url": "https://example.com",
                                                "intervalMinutes": 1440})
        monitor_id = (created or {}).get("id")
        if monitor_id:
            for op_id in ("ListMonitors", "GetMonitor", "GetMonitorChanges", "PauseMonitor",
                          "ResumeMonitor", "RunMonitorNow"):
                if on(op_id):
                    r.call(op_id, None if op_id == "ListMonitors" else {"id": monitor_id})
            r.call("DeleteMonitor", {"id": monitor_id})  # always clean up

    if on("ListAiVisibilitySources"):
        r.call("ListAiVisibilitySources")
    if on("StartAiVisibilitySearch", "GetAiVisibilitySearch"):
        started = r.call("StartAiVisibilitySearch",
                         body={"query": "What is Anakin web scraping?", "sources": ["chatgpt"]})
        if started and on("GetAiVisibilitySearch"):
            r.wait("GetAiVisibilitySearch", started["search_id"], {"completed", "failed"},
                   every=5, limit=300)

    if on("ListBrowserSessions"):
        r.call("ListBrowserSessions")
    if on("DeleteBrowserSession") and args.session_id:
        r.call("DeleteBrowserSession", {"id": args.session_id})
    if on("StartBrowserTask", "GetBrowserTaskResult"):
        started = r.call("StartBrowserTask", body={"prompt": "Open the page and return its heading.",
                                                   "url": "https://example.com", "async": True,
                                                   "max_steps": 5})
        if started and on("GetBrowserTaskResult"):
            r.wait("GetBrowserTaskResult", started["workflow_id"],
                   {"completed", "failed", "timed_out"}, every=5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--yes", action="store_true", help="actually call the API")
    ap.add_argument("--only", type=lambda v: set(v.split(",")), default=set())
    ap.add_argument("--include-costly", action="store_true")
    ap.add_argument("--session-id", help="a saved browser session that may be deleted")
    ap.add_argument("--key-file", type=Path)
    args = ap.parse_args()

    ops = plan(args)
    credits = sum(COST.get(o, 0) for o in ops)
    print(f"{len(ops)} of {len(OPS)} actions, about {credits} credits. Skipped: "
          f"{', '.join(sorted(set(OPS) - set(ops))) or 'none'}")
    if not args.yes:
        print("Dry run. Add --yes to call the API.")
        return 0
    key = (args.key_file.read_text().strip() if args.key_file else os.environ.get("ANAKIN_API_KEY"))
    if not key:
        print("No key: set ANAKIN_API_KEY or pass --key-file.", file=sys.stderr)
        return 2

    r = Runner(key)
    try:
        run(r, ops, args)
    finally:
        r.http.close()
    width = max(len(o) for o, _, _ in r.results)
    for op_id, status, detail in r.results:
        print(f"{status:6} {op_id:{width}}  {detail}")
    failed = [x for x in r.results if x[1] in ("FAIL", "SCHEMA")]
    print(f"\n{len(r.results) - len(failed)} passed, {len(failed)} need attention")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
