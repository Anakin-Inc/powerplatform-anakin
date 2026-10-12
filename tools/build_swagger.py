"""Generates the Anakin Power Platform connector's apiDefinition.swagger.json.

Usage: python build_swagger.py <output dir>
"""

import json
import sys
from pathlib import Path

# ── Schema helpers ────────────────────────────────────────────────────────


def s(desc, title=None, **kw):
    out = {"type": "string", "description": desc}
    if title:
        out["title"] = title
    out.update(kw)
    return out


def i(desc, title=None, **kw):
    out = {"type": "integer", "format": "int32", "description": desc}
    if title:
        out["title"] = title
    out.update(kw)
    return out


def n(desc, title=None):
    out = {"type": "number", "description": desc}
    if title:
        out["title"] = title
    return out


def b(desc, title=None):
    out = {"type": "boolean", "description": desc}
    if title:
        out["title"] = title
    return out


def arr(items, desc, title=None):
    out = {"type": "array", "items": items, "description": desc}
    if title:
        out["title"] = title
    return out


def obj(props, desc, title=None, required=None):
    out = {"type": "object", "description": desc}
    if title:
        out["title"] = title
    if props:
        out["properties"] = props
    if required:
        out["required"] = required
    return out


def dyn(desc, title=None):
    """An object whose shape depends on the request (AI output, a Wire action's data)."""
    out = {"type": "object", "description": desc, "additionalProperties": {}}
    if title:
        out["title"] = title
    return out


# ── Parameter helpers ─────────────────────────────────────────────────────


def path_param(name, summary, desc):
    return {
        "name": name,
        "in": "path",
        "required": True,
        "type": "string",
        "x-ms-summary": summary,
        "description": desc,
        "x-ms-url-encoding": "single",
    }


def query_param(name, summary, desc, typ="string", visibility=None, **kw):
    p = {"name": name, "in": "query", "required": False, "type": typ, "x-ms-summary": summary,
         "description": desc}
    if typ == "integer":
        p["format"] = "int32"
    if visibility:
        p["x-ms-visibility"] = visibility
    p.update(kw)
    return p


def body_param(props, required=None):
    schema = {"type": "object", "properties": props}
    if required:
        schema["required"] = required
    return {"name": "body", "in": "body", "required": True, "schema": schema}


def f(typ, summary, desc, visibility=None, **kw):
    """A body field."""
    out = {"type": typ, "x-ms-summary": summary, "description": desc}
    if typ == "integer":
        out["format"] = "int32"
    if visibility:
        out["x-ms-visibility"] = visibility
    out.update(kw)
    return out


def f_list(summary, desc, visibility=None):
    out = {"type": "array", "items": {"type": "string"}, "x-ms-summary": summary,
           "description": desc}
    if visibility:
        out["x-ms-visibility"] = visibility
    return out


def f_obj(summary, desc, visibility=None):
    out = {"type": "object", "x-ms-summary": summary, "description": desc,
           "additionalProperties": {}}
    if visibility:
        out["x-ms-visibility"] = visibility
    return out


# ── Shared response schemas ───────────────────────────────────────────────

JOB_STARTED = obj(
    {
        "jobId": s("The job ID. Pass it to the matching get result action.", "Job ID"),
        "status": s("The job status, pending when the job is queued.", "Status"),
    },
    "The started job.",
)

JOB_STATUS = s("The job status: pending, processing, completed or failed.", "Status")
JOB_ERROR = s("The error message, present when the job failed.", "Error")
DURATION = i("The processing time in milliseconds.", "Duration (ms)")
CREATED_AT = s("When the job was created.", "Created at", format="date-time")
COMPLETED_AT = s("When the job finished.", "Completed at", format="date-time")

SCRAPE_RESULT = obj(
    {
        "id": s("The job ID.", "Job ID"),
        "status": JOB_STATUS,
        "url": s("The scraped URL.", "URL"),
        "country": s("The country the page was fetched from.", "Country"),
        "markdown": s("The page content as markdown.", "Markdown"),
        "html": s("The raw HTML of the page.", "HTML"),
        "cleanedHtml": s("The HTML with nonessential elements removed.", "Cleaned HTML"),
        "generatedJson": dyn("Structured data extracted by AI, when JSON extraction was on.",
                             "Extracted JSON"),
        "summary": s("An AI summary of the page, when the summary format was requested.",
                     "Summary"),
        "links": arr(obj({"href": s("The link target.", "Link URL"),
                          "text": s("The link text.", "Link text")}, "A link on the page."),
                     "The links on the page, when the links format was requested.", "Links"),
        "images": arr(obj({"src": s("The image URL.", "Image URL"),
                           "alt": s("The image alternative text.", "Image alt text")},
                          "An image on the page."),
                      "The images on the page, when the images format was requested.", "Images"),
        "cached": b("Whether the result came from the 24 hour cache.", "Cached"),
        "error": JOB_ERROR,
        "createdAt": CREATED_AT,
        "completedAt": COMPLETED_AT,
        "durationMs": DURATION,
    },
    "The scrape job and its result.",
)

MAP_RESULT = obj(
    {
        "id": s("The job ID.", "Job ID"),
        "status": JOB_STATUS,
        "url": s("The URL the discovery started from.", "URL"),
        "links": arr({"type": "string"}, "The URLs found on the site.", "Links"),
        "totalLinks": i("The number of URLs found on the site.", "Total links"),
        "externalLinks": arr({"type": "string"}, "The URLs found on other sites.",
                             "External links"),
        "totalExternalLinks": i("The number of URLs found on other sites.",
                                "Total external links"),
        "error": JOB_ERROR,
        "createdAt": CREATED_AT,
        "completedAt": COMPLETED_AT,
        "durationMs": DURATION,
    },
    "The map job and the URLs it found.",
)

CRAWL_RESULT = obj(
    {
        "id": s("The job ID.", "Job ID"),
        "status": JOB_STATUS,
        "url": s("The URL the crawl started from.", "URL"),
        "totalPages": i("The number of pages attempted.", "Total pages"),
        "completedPages": i("The number of pages fetched successfully.", "Completed pages"),
        "results": arr(
            obj(
                {
                    "url": s("The page URL.", "Page URL"),
                    "status": s("The page status, completed or failed.", "Page status"),
                    "markdown": s("The page content as markdown.", "Page markdown"),
                    "html": s("The raw HTML of the page.", "Page HTML"),
                    "error": s("The error message, present when the page failed.",
                               "Page error"),
                    "durationMs": i("The time taken for this page in milliseconds.",
                                    "Page duration (ms)"),
                },
                "One crawled page.",
            ),
            "The crawled pages.",
            "Pages",
        ),
        "error": JOB_ERROR,
        "createdAt": CREATED_AT,
        "completedAt": COMPLETED_AT,
        "durationMs": DURATION,
    },
    "The crawl job and its pages.",
)

AGENTIC_RESULT = obj(
    {
        "id": s("The job ID, once the job has finished.", "Job ID"),
        "job_id": s("The job ID, while the job is still running.", "Running job ID"),
        "status": JOB_STATUS,
        "message": s("A status message.", "Message"),
        "generatedJson": obj(
            {
                "summary": s("A summary of the research findings.", "Research summary"),
                "structured_data": dyn("The structured findings, shaped by the data schema.",
                                       "Structured data"),
                "data_schema": dyn("The schema of the structured findings.", "Data schema"),
            },
            "The research result.",
            "Research result",
        ),
        "error": JOB_ERROR,
        "createdAt": CREATED_AT,
        "completedAt": COMPLETED_AT,
        "durationMs": DURATION,
    },
    "The research job and its result.",
)

WIRE_ACTION_MATCH = obj(
    {
        "action_id": s("The action ID to pass to Run Wire action.", "Action ID"),
        "catalog_slug": s("The slug of the site the action belongs to.", "Site slug"),
        "catalog_name": s("The name of the site the action belongs to.", "Site name"),
        "name": s("The action name.", "Action name"),
        "description": s("What the action does.", "Action description"),
        "mode": s("How the action runs, sync or async.", "Mode"),
        "auth_mode": s("Whether the action needs a sign in: none, optional or required.",
                       "Authentication mode"),
        "connected": b("Whether you already have an active credential for this site.",
                       "Connected"),
        "credits": i("The base credit cost of one run.", "Credits"),
        "params": arr(
            obj(
                {
                    "name": s("The parameter name.", "Parameter name"),
                    "type": s("The parameter type.", "Parameter type"),
                    "required": b("Whether the parameter is required.", "Parameter required"),
                    "description": s("What the parameter is for.", "Parameter description"),
                },
                "A parameter the action takes.",
            ),
            "The parameters the action takes.",
            "Parameters",
        ),
    },
    "A matching Wire action.",
)

WIRE_CATALOG = obj(
    {
        "id": s("The site ID.", "Site ID"),
        "slug": s("The site slug.", "Site slug"),
        "name": s("The site name.", "Site name"),
        "url": s("The site URL.", "Site URL"),
        "domain": s("The site domain.", "Site domain"),
        "category": s("The site category.", "Site category"),
        "description": s("What the site's actions cover.", "Site description"),
        "auth_required": b("Whether any action on the site needs a sign in.",
                           "Sign in required"),
        "status": s("The site status, active or pending review.", "Site status"),
        "action_count": i("The number of actions available on the site.", "Action count"),
    },
    "A site in the Wire catalog.",
)

WIRE_JOB = obj(
    {
        "status": s("The run status: processing, completed or failed.", "Status"),
        "job_id": s("The job ID, when the action runs in the background.", "Job ID"),
        "poll_url": s("The path to check the job.", "Poll path"),
        "retry_after_ms": i("How long to wait before checking again, in milliseconds.",
                            "Retry after (ms)"),
        "data": dyn("The data the action returned.", "Data"),
        "files": arr(
            obj(
                {
                    "name": s("The file name.", "File name"),
                    "content_type": s("The file type.", "File type"),
                    "size_bytes": i("The file size in bytes.", "File size"),
                },
                "A file the action produced.",
            ),
            "The files the action produced, when it returns files instead of data.",
            "Files",
        ),
        "credits_used": i("The credits charged for this run.", "Credits used"),
        "execution_ms": i("The run time in milliseconds.", "Execution time (ms)"),
        "error": obj(
            {
                "code": s("The error code.", "Error code"),
                "message": s("The error message.", "Error message"),
            },
            "The error, when the run failed.",
            "Error",
        ),
    },
    "The Wire run and its result.",
)

WIRE_BUILD = obj(
    {
        "id": s("The build request ID.", "Build ID"),
        "website_url": s("The site the actions are built for.", "Website URL"),
        "domain": s("The site domain.", "Domain"),
        "goal": s("What the actions should do.", "Goal"),
        "visibility": s("Who can use the actions, private or public.", "Visibility"),
        "status": s("The build status: pending, processing, success or failed.", "Status"),
        "credits_charged": i("The credits held for the build, refunded if it fails.",
                             "Credits charged"),
        "action_id": s("The ID of the published action, once the build succeeds.", "Action ID"),
        "catalog_slug": s("The slug of the site the action was published under.", "Site slug"),
        "error": s("The error message, when the build failed.", "Error"),
        "created_at": s("When the build was requested.", "Created at", format="date-time"),
        "updated_at": s("When the build last changed.", "Updated at", format="date-time"),
    },
    "A Wire build request.",
)

MONITOR = obj(
    {
        "id": s("The monitor ID.", "Monitor ID"),
        "url": s("The watched URL.", "URL"),
        "scope": s("What is watched: page, site or wire.", "Scope"),
        "watchMode": s("How changes are compared: full page or specific data.", "Watch mode"),
        "intervalMinutes": i("The minutes between checks.", "Interval (minutes)"),
        "isActive": b("Whether the monitor is running.", "Active"),
        "aiMode": b("Whether AI filters out trivial changes.", "AI mode"),
        "creditCostPerRun": i("The credits each check costs.", "Credits per check"),
        "nextRunAt": s("When the next check runs.", "Next check", format="date-time"),
        "lastCheckedAt": s("When the last check ran.", "Last check", format="date-time"),
        "expiresAt": s("When the monitor pauses itself.", "Expires at", format="date-time"),
        "alertWebhookUrl": s("The webhook that receives change alerts.", "Alert webhook URL"),
        "createdAt": s("When the monitor was created.", "Created at", format="date-time"),
        "updatedAt": s("When the monitor last changed.", "Updated at", format="date-time"),
    },
    "A website monitor.",
)

MONITOR_CHANGE = obj(
    {
        "id": s("The change ID.", "Change ID"),
        "monitorId": s("The monitor that detected the change.", "Monitor ID"),
        "changedAt": s("When the change was detected.", "Changed at", format="date-time"),
        "summary": s("A summary of the change.", "Change summary"),
        "diffJson": dyn("The structured difference between the two checks.", "Difference"),
        "createdAt": s("When the change was recorded.", "Created at", format="date-time"),
    },
    "A detected change.",
)

AI_SEARCH = obj(
    {
        "search_id": s("The search ID.", "Search ID"),
        "status": s("The search status: running, completed or failed.", "Status"),
        "country": s("The country the engines were asked from.", "Country"),
        "synthesis": s("Where the engines agree and differ, once at least two have answered.",
                       "Synthesis"),
        "results": arr(
            obj(
                {
                    "source": s("The engine slug.", "Engine"),
                    "status": s("The engine's status: completed, failed or timed out.",
                                "Engine status"),
                    "summary": s("A summary of the engine's answer.", "Answer summary"),
                    "full_content": s("The engine's full answer as a JSON string.",
                                      "Full answer"),
                    "verdict": s("Whether the answer agrees with the others: consensus or "
                                 "outlier.", "Verdict"),
                    "latency_ms": i("How long the engine took, in milliseconds.",
                                    "Latency (ms)"),
                    "credits_used": i("The credits charged for this engine.", "Credits used"),
                    "error": s("The error message, when the engine failed.", "Engine error"),
                },
                "One engine's answer.",
            ),
            "The answers from each engine.",
            "Results",
        ),
    },
    "The AI visibility search and its answers.",
)

SESSION = obj(
    {
        "id": s("The session ID. Use it as the session ID in other actions.", "Session ID"),
        "name": s("The session name.", "Session name"),
        "websiteUrl": s("The site the session is signed in to.", "Website URL"),
        "websiteDomain": s("The domain the session is signed in to.", "Website domain"),
        "isActive": b("Whether the session can be used.", "Active"),
        "createdAt": s("When the session was saved.", "Created at", format="date-time"),
        "lastUsedAt": s("When the session was last used.", "Last used at", format="date-time"),
        "expiresAt": s("When the session expires.", "Expires at", format="date-time"),
    },
    "A saved browser session.",
)

SUCCESS = obj({"success": b("Whether the request succeeded.", "Success")}, "The outcome.")

COUNTRY_FIELD = f("string", "Country",
                  "The two letter country code to fetch from, for example us or de.",
                  "advanced", default="us")
SESSION_FIELD = f("string", "Session ID",
                  "The ID of a saved browser session, for pages behind a sign in.", "advanced")

# ── Operations ────────────────────────────────────────────────────────────

OPS = []


def op(method, path, op_id, summary, description, params, schema, visibility=None,
       status="200"):
    entry = {
        "method": method,
        "path": path,
        "body": {
            "operationId": op_id,
            "summary": summary,
            "description": description,
            "parameters": params,
            "responses": {status: {"description": "Success", "schema": schema}},
        },
    }
    # Microsoft's checklist wants visibility on every operation, and its schema only allows
    # important, advanced or internal. Everyday actions are important, the rest advanced.
    entry["body"]["x-ms-visibility"] = (
        visibility or ("important" if op_id in EVERYDAY else "advanced")
    )
    OPS.append(entry)


EVERYDAY = {
    "ScrapeUrl", "ScrapeUrlNow", "GetScrapeResult", "Search", "StartAgenticSearch", "GetAgenticSearchResult",
    "StartCrawl", "GetCrawlResult", "DiscoverWireActions", "RunWireAction", "GetWireJobResult",
    "CreateMonitor", "GetMonitorChanges",
}


JOB_ID_PATH = path_param("id", "Job ID", "The job ID returned by the start action.")

# Web data
op("post", "/url-scraper", "ScrapeUrl", "Scrape a web page",
   "Starts fetching one web page as markdown and HTML, with optional AI extraction. Use Get "
   "scrape result with the returned job ID to get the content.",
   [body_param({
       "url": f("string", "URL", "The page to fetch, starting with http or https."),
       "useBrowser": f("boolean", "Use browser",
                       "Whether to render the page in a browser. Use it for pages that need "
                       "JavaScript; it is slower and costs more.", default=False),
       "generateJson": f("boolean", "Extract JSON",
                         "Whether to also extract structured data from the page with AI.",
                         default=False),
       "outputSchema": f_obj("Output schema",
                             "A JSON schema of the fields to extract. Setting it turns on "
                             "JSON extraction.", "advanced"),
       "formats": f_list("Formats",
                         "The outputs to produce: markdown, html, cleanedHtml, links, images "
                         "or summary. By default markdown, HTML and cleaned HTML.", "advanced"),
       "country": COUNTRY_FIELD,
       "forceFresh": f("boolean", "Skip cache",
                       "Whether to fetch the page again instead of using the 24 hour cache.",
                       "advanced", default=False),
       "sessionId": SESSION_FIELD,
   }, ["url"])],
   JOB_STARTED)

op("post", "/url-scraper/scrape", "ScrapeUrlNow", "Scrape a web page now",
   "Fetches one web page and waits up to 50 seconds for the result, so no follow up action is "
   "needed. This suits apps, which have no loops. If the page takes longer, the status is "
   "still processing; pass the returned ID to Get scrape result.",
   [body_param({
       "url": f("string", "URL", "The page to fetch, starting with http or https."),
       "useBrowser": f("boolean", "Use browser",
                       "Whether to render the page in a browser. Use it for pages that need "
                       "JavaScript; it is slower.", default=False),
       "generateJson": f("boolean", "Extract JSON",
                         "Whether to also extract structured data from the page with AI.",
                         default=False),
       "outputSchema": f_obj("Output schema",
                             "A JSON schema of the fields to extract. Setting it turns on "
                             "JSON extraction.", "advanced"),
       "formats": f_list("Formats",
                         "The outputs to produce: markdown, html, cleanedHtml, links, images "
                         "or summary. By default markdown, HTML and cleaned HTML.", "advanced"),
       "country": COUNTRY_FIELD,
       "forceFresh": f("boolean", "Skip cache",
                       "Whether to fetch the page again instead of using the 24 hour cache.",
                       "advanced", default=False),
       "sessionId": SESSION_FIELD,
   }, ["url"])],
   SCRAPE_RESULT)

op("get", "/url-scraper/{id}", "GetScrapeResult", "Get scrape result",
   "Gets the status and content of a scrape job. Repeat until the status is completed or "
   "failed.",
   [JOB_ID_PATH], SCRAPE_RESULT)

op("post", "/search", "Search", "Search the web",
   "Searches the web and returns result URLs, titles and snippets right away.",
   [body_param({
       "prompt": f("string", "Query", "What to search for, in natural language."),
       "limit": f("integer", "Number of results",
                  "The number of results to return, from 1 to 20.", default=5),
   }, ["prompt"])],
   obj({
       "id": s("The search ID.", "Search ID"),
       "results": arr(obj({
           "url": s("The result URL.", "Result URL"),
           "title": s("The page title.", "Result title"),
           "snippet": s("A relevant excerpt from the page.", "Result snippet"),
           "date": s("The publication date, when known.", "Result date"),
           "last_updated": s("When the page was last updated, when known.",
                             "Result last updated"),
       }, "A search result."), "The search results.", "Results"),
   }, "The search results."),
   "important")

op("post", "/agentic-search", "StartAgenticSearch", "Start deep research",
   "Starts researching a question across many sources. It searches, reads the cited pages and "
   "returns a summary and structured data, which can take a few minutes. Use Get research "
   "result with the returned job ID.",
   [body_param({
       "prompt": f("string", "Research question",
                   "The question to research, as specific as possible."),
       "useBrowser": f("boolean", "Use browser",
                       "Whether to render cited pages in a browser.", "advanced", default=True),
       "schema": f_obj("Output schema",
                       "A JSON schema for the structured result. By default it is inferred "
                       "from the question.", "advanced"),
   }, ["prompt"])],
   obj({
       "job_id": s("The job ID. Pass it to Get research result.", "Job ID"),
       "status": s("The job status, pending when the job is queued.", "Status"),
       "message": s("A confirmation message.", "Message"),
       "created_at": s("When the job was created.", "Created at", format="date-time"),
   }, "The started research job."))

op("get", "/agentic-search/{id}", "GetAgenticSearchResult", "Get research result",
   "Gets the status and result of a research job. Repeat until the status is completed or "
   "failed.",
   [JOB_ID_PATH], AGENTIC_RESULT)

op("post", "/map", "StartMap", "Map website URLs",
   "Starts finding the URLs on a website, to decide which pages to crawl. Use Get map result "
   "with the returned job ID.",
   [body_param({
       "url": f("string", "URL", "The site or section to start from."),
       "limit": f("integer", "Maximum URLs", "The maximum number of URLs to return, up to 5000.",
                  default=100),
       "depth": f("integer", "Depth", "How many links to follow from the start URL, up to 5.",
                  "advanced", default=2),
       "search": f("string", "Filter", "Only return URLs that contain this text.", "advanced"),
       "includeSubdomains": f("boolean", "Include subdomains",
                              "Whether to also follow links to subdomains.", "advanced",
                              default=False),
       "includeExternalLinks": f("boolean", "Include external links",
                                 "Whether to also return links to other sites.", "advanced",
                                 default=False),
       "useBrowser": f("boolean", "Use browser",
                       "Whether to render pages in a browser before reading links.",
                       "advanced", default=False),
   }, ["url"])],
   JOB_STARTED)

op("get", "/map/{id}", "GetMapResult", "Get map result",
   "Gets the status and URLs of a map job. Repeat until the status is completed or failed.",
   [JOB_ID_PATH], MAP_RESULT)

op("post", "/crawl", "StartCrawl", "Crawl a website",
   "Starts fetching many pages of one site as markdown. Use Get crawl result with the "
   "returned job ID.",
   [body_param({
       "url": f("string", "URL", "The URL to start crawling from."),
       "maxPages": f("integer", "Maximum pages",
                     "The maximum number of pages to fetch, up to 100. This is the main cost "
                     "control.", default=10),
       "depth": f("integer", "Depth", "How many links to follow from the start URL, up to 5.",
                  "advanced", default=1),
       "includePatterns": f_list("Include patterns",
                                 "Only crawl URLs that match one of these patterns, for "
                                 "example /blog/*.", "advanced"),
       "excludePatterns": f_list("Exclude patterns",
                                 "Skip URLs that match any of these patterns.", "advanced"),
       "useBrowser": f("boolean", "Use browser", "Whether to render each page in a browser.",
                       "advanced", default=False),
       "country": COUNTRY_FIELD,
       "sessionId": SESSION_FIELD,
   }, ["url"])],
   JOB_STARTED)

op("get", "/crawl/{id}", "GetCrawlResult", "Get crawl result",
   "Gets the status and pages of a crawl job. Repeat until the status is completed or failed.",
   [JOB_ID_PATH], CRAWL_RESULT)

# Wire
op("get", "/wire/resolve", "DiscoverWireActions", "Find Wire actions",
   "Finds ready made Wire actions for a task, such as searching listings on a well known site. "
   "Wire actions return structured data and are faster than scraping.",
   [
       query_param("q", "Task", "The task in natural language, for example top phones on "
                   "walmart."),
       query_param("catalog", "Site", "Only return actions for this site slug, for example "
                   "amazon.", visibility="advanced"),
       query_param("auth_mode", "Sign in", "Only return actions with this sign in mode.",
                   visibility="advanced", enum=["none", "optional", "required"]),
   ],
   obj({"results": arr(WIRE_ACTION_MATCH, "The matching actions.", "Actions")},
       "The matching Wire actions."))

op("get", "/wire/catalog", "ListWireCatalogs", "List Wire sites",
   "Lists every site in the Wire catalog and how many actions each has.",
   [], obj({"catalog": arr(WIRE_CATALOG, "The sites in the catalog.", "Sites")},
           "The Wire catalog."))

op("get", "/wire/catalog/{slug}", "GetWireCatalog", "Get Wire site actions",
   "Gets one site in the Wire catalog with all its actions and their parameters.",
   [path_param("slug", "Site slug", "The site slug, for example walmart.")],
   obj({
       "catalog": WIRE_CATALOG,
       "actions": arr(obj({
           "action_id": s("The action ID to pass to Run Wire action.", "Action ID"),
           "name": s("The action name.", "Action name"),
           "description": s("What the action does.", "Action description"),
           "type": s("Whether the action reads data or changes something: read or write.",
                     "Action type"),
           "mode": s("How the action runs, sync or async.", "Mode"),
           "auth_mode": s("Whether the action needs a sign in: none, optional or required.",
                          "Authentication mode"),
           "credits_per_call": i("The base credit cost of one run.", "Credits per run"),
           "parameters": arr(obj({
               "name": s("The parameter name.", "Parameter name"),
               "type": s("The parameter type.", "Parameter type"),
               "required": b("Whether the parameter is required.", "Parameter required"),
               "description": s("What the parameter is for.", "Parameter description"),
           }, "A parameter the action takes."), "The parameters the action takes.",
               "Parameters"),
       }, "A Wire action."), "The site's actions.", "Actions"),
   }, "The Wire site and its actions."))

op("post", "/wire/task", "RunWireAction", "Run Wire action",
   "Runs a Wire action with its parameters. Some actions return data right away; others "
   "return a job ID to pass to Get Wire job result.",
   [body_param({
       "action_id": f("string", "Action ID",
                      "The action to run, from Find Wire actions or Get Wire site actions."),
       "params": f_obj("Parameters",
                       "The action's parameters as JSON, matching its parameter list."),
       "credential_id": f("string", "Credential ID",
                          "The credential to use for actions that need a sign in, from List "
                          "Wire identities.", "advanced"),
   }, ["action_id"])],
   WIRE_JOB)

op("get", "/wire/jobs/{id}", "GetWireJobResult", "Get Wire job result",
   "Gets the status and data of a Wire job. Repeat until the status is completed or failed.",
   [path_param("id", "Job ID", "The job ID returned by Run Wire action.")], WIRE_JOB)

op("get", "/wire/identities", "ListWireIdentities", "List Wire identities",
   "Lists your saved site sign ins. Use a credential ID from here in Run Wire action.",
   [query_param("catalog_id", "Site ID", "Only return identities for this site ID.",
                visibility="advanced")],
   obj({
       "status": s("The request status.", "Request status"),
       "identities": arr(obj({
           "id": s("The identity ID.", "Identity ID"),
           "catalog_id": s("The site the identity belongs to.", "Site ID"),
           "name": s("The identity name.", "Identity name"),
           "is_default": b("Whether this is your default identity for the site.", "Default"),
           "credentials": arr(obj({
               "id": s("The credential ID. Use it as the credential ID in Run Wire action.",
                       "Credential ID"),
               "credential_type": s("The credential type.", "Credential type"),
               "status": s("The credential status, active or expired.", "Credential status"),
               "expires_at": s("When the credential expires.", "Credential expires at",
                               format="date-time"),
           }, "A credential."), "The identity's credentials.", "Credentials"),
       }, "A saved identity."), "Your identities.", "Identities"),
   }, "Your Wire identities."))

op("post", "/wire/build-request", "RequestWireBuild", "Request new Wire actions",
   "Asks Wire to build and test new actions for a site that is not in the catalog yet. It "
   "charges credits, which are refunded if the build fails. Track it with Get Wire build.",
   [body_param({
       "website_url": f("string", "Website URL", "The site to build actions for."),
       "goal": f("string", "Goal",
                 "What the actions should extract or do. Be specific, since the builder works "
                 "from this description."),
       "actions": f_list("Capabilities",
                         "Separate capabilities to build as separate actions, for example "
                         "search products.", "advanced"),
       "visibility": f("string", "Visibility",
                       "Who can use the actions: private, the default, or public.", "advanced",
                       enum=["private", "public"]),
       "force": f("boolean", "Build anyway",
                  "Whether to build even if similar actions already exist for the site.",
                  "advanced", default=False),
   }, ["website_url", "goal"])],
   obj({"status": s("The request status.", "Request status"), "build_request": WIRE_BUILD},
       "The new build request."))

op("get", "/wire/build-requests/{id}", "GetWireBuild", "Get Wire build",
   "Gets a Wire build request, including its status and the published action once it "
   "succeeds.",
   [path_param("id", "Build ID", "The build ID returned by Request new Wire actions.")],
   WIRE_BUILD, "advanced")

# Monitors
op("post", "/monitors", "CreateMonitor", "Create website monitor",
   "Creates a monitor that checks a page, a whole site or a Wire action on a schedule and "
   "records changes. Every check costs credits.",
   [body_param({
       "url": f("string", "URL", "The page to watch, or the root URL for a site monitor."),
       "intervalMinutes": f("integer", "Interval (minutes)",
                            "The minutes between checks, at least 15.", default=60,
                            minimum=15),
       "scope": f("string", "Scope", "What to watch: page, site or wire.", "advanced",
                  enum=["page", "site", "wire"], default="page"),
       "watchMode": f("string", "Watch mode",
                      "Compare the full page, or only the fields in the output schema.",
                      "advanced", enum=["full_page", "specific_data"], default="full_page"),
       "outputSchema": f_obj("Output schema",
                             "A JSON schema of the fields to track, required for the specific "
                             "data watch mode.", "advanced"),
       "aiMode": f("boolean", "AI mode",
                   "Whether AI should ignore trivial changes and summarize real ones. It adds "
                   "1 credit per check.", "advanced", default=False),
       "aiGoal": f("string", "AI goal",
                   "Which changes count, for example only when the price drops.", "advanced"),
       "alertWebhookUrl": f("string", "Alert webhook URL",
                            "A webhook to send each change to.", "advanced"),
       "alertEmails": f("string", "Alert emails",
                        "Email addresses to notify, separated by commas.", "advanced"),
       "useBrowser": f("boolean", "Use browser",
                       "Whether to render the page in a browser for each check.", "advanced",
                       default=False),
       "country": COUNTRY_FIELD,
       "sessionId": SESSION_FIELD,
       "maxPages": f("integer", "Maximum pages", "For site monitors, the pages to crawl per "
                     "check.", "advanced"),
       "wireActionId": f("string", "Wire action ID",
                         "For Wire monitors, the action to run each check.", "advanced"),
       "wireParams": f_obj("Wire parameters",
                           "For Wire monitors, the action's parameters as JSON.", "advanced"),
       "expiresAt": f("string", "End date",
                      "The date the monitor pauses itself, such as 2026-12-31.", "advanced"),
   }, ["url", "intervalMinutes"])],
   MONITOR)

op("get", "/monitors", "ListMonitors", "List website monitors",
   "Lists your website monitors with their status and next check.",
   [], obj({"monitors": arr(MONITOR, "Your monitors.", "Monitors")}, "Your monitors."))

MONITOR_ID_PATH = path_param("id", "Monitor ID", "The monitor ID, from List website monitors.")

op("get", "/monitors/{id}", "GetMonitor", "Get website monitor",
   "Gets one monitor's settings and status.", [MONITOR_ID_PATH], MONITOR, "advanced")

op("get", "/monitors/{id}/changes", "GetMonitorChanges", "Get monitor changes",
   "Gets the changes a monitor detected, each with a summary and the differences.",
   [MONITOR_ID_PATH],
   obj({"changes": arr(MONITOR_CHANGE, "The detected changes.", "Changes")},
       "The monitor's changes."))

op("post", "/monitors/{id}/pause", "PauseMonitor", "Pause website monitor",
   "Stops a monitor's scheduled checks until it is resumed.", [MONITOR_ID_PATH], MONITOR,
   "advanced")

op("post", "/monitors/{id}/resume", "ResumeMonitor", "Resume website monitor",
   "Restarts a paused monitor's scheduled checks.", [MONITOR_ID_PATH], MONITOR, "advanced")

op("post", "/monitors/{id}/run", "RunMonitorNow", "Check website monitor now",
   "Runs a monitor's check now, outside its schedule. It costs the same as a scheduled check.",
   [MONITOR_ID_PATH],
   obj({
       "success": b("Whether the check started.", "Success"),
       "jobId": s("The job started for this check, for page and site monitors.", "Job ID"),
       "message": s("A status message.", "Message"),
   }, "The started check."))

op("delete", "/monitors/{id}", "DeleteMonitor", "Delete website monitor",
   "Permanently deletes a monitor and its history.", [MONITOR_ID_PATH], SUCCESS, "advanced")

# AI visibility
op("post", "/ai-visibility/search", "StartAiVisibilitySearch", "Compare AI engine answers",
   "Asks AI answer engines such as ChatGPT, Gemini and Google AI Overview the same question, "
   "to compare how they answer. Use Get AI answer comparison with the returned search ID.",
   [body_param({
       "query": f("string", "Question", "The question to ask every engine.", maxLength=2000),
       "sources": f_list("Engines",
                         "The engine slugs to ask, from List AI engines. By default all of "
                         "them.", "advanced"),
       "country": f("string", "Country",
                    "The two letter country code to ask from, for example us or in.",
                    "advanced", default="us"),
   }, ["query"])],
   AI_SEARCH)

op("get", "/ai-visibility/search/{id}", "GetAiVisibilitySearch", "Get AI answer comparison",
   "Gets the answers from each engine. Repeat until the status is completed or failed.",
   [path_param("id", "Search ID", "The search ID returned by Compare AI engine answers.")],
   AI_SEARCH)

op("get", "/ai-visibility/sources", "ListAiVisibilitySources", "List AI engines",
   "Lists the AI answer engines that Compare AI engine answers can ask.",
   [], obj({"sources": arr(obj({
       "slug": s("The engine slug.", "Engine slug"),
       "label": s("The engine name.", "Engine name"),
   }, "An AI answer engine."), "The engines.", "Engines")}, "The AI answer engines."),
   "advanced")

# Browser sessions and browser tasks
op("get", "/sessions", "ListBrowserSessions", "List browser sessions",
   "Lists your saved browser sessions, which let other actions reach pages behind a sign in. "
   "You create sessions in the Anakin dashboard.",
   [query_param("domain", "Domain", "Only return sessions for this domain, for example "
                "amazon.com.", visibility="advanced")],
   obj({"sessions": arr(SESSION, "Your sessions.", "Sessions")}, "Your browser sessions."),
   "advanced")

op("delete", "/sessions/{id}", "DeleteBrowserSession", "Delete browser session",
   "Permanently deletes a saved browser session. You need to sign in again in the dashboard "
   "to recreate it.",
   [path_param("id", "Session ID", "The session ID, from List browser sessions.")],
   SUCCESS, "advanced")

op("post", "/ai/evaluate", "StartBrowserTask", "Run AI browser task",
   "Starts an AI agent that drives a real cloud browser through a task, such as finding a "
   "product and reading its details. Use Get AI browser task result with the returned "
   "workflow ID.",
   [body_param({
       "prompt": f("string", "Task",
                   "The task in natural language, specific about what to return. Never put "
                   "passwords in it; use a session ID for pages behind a sign in."),
       "url": f("string", "Start URL", "The page to open before starting.", "advanced"),
       "session_id": f("string", "Session ID",
                       "A saved browser session, for tasks behind a sign in.", "advanced"),
       "output_schema": f_obj("Output schema", "A JSON schema for a structured result.",
                              "advanced"),
       "max_steps": f("integer", "Maximum steps", "A cap on the number of browser steps.",
                      "advanced"),
       "async": f("boolean", "Run in background",
                  "Whether the task runs in the background. Keep it on, since tasks can take "
                  "several minutes.", "internal", default=True),
   }, ["prompt", "async"])],
   obj({
       "workflow_id": s("The task ID. Pass it to Get AI browser task result.", "Workflow ID"),
       "status": s("The task status.", "Status"),
   }, "The started browser task."))

op("get", "/ai/jobs/{id}", "GetBrowserTaskResult", "Get AI browser task result",
   "Gets the status and result of an AI browser task. Repeat until the status is completed, "
   "failed or timed out.",
   [path_param("id", "Workflow ID", "The workflow ID returned by Run AI browser task.")],
   obj({
       "status": s("The task status: running, completed, failed or timed out.", "Status"),
       "result": dyn("The task result, shaped by the output schema when one was given.",
                     "Result"),
       "error": s("The error message, when the task failed.", "Error"),
   }, "The browser task and its result."))


def build():
    paths = {}
    for o in OPS:
        body = o["body"]
        if any(p["in"] == "body" for p in body["parameters"]):
            body["consumes"] = ["application/json"]
        body["produces"] = ["application/json"]
        paths.setdefault(o["path"], {})[o["method"]] = body
    return {
        "swagger": "2.0",
        "info": {
            "title": "Anakin",
            "description": (
                "Anakin turns websites into clean, structured data. Scrape pages, search the "
                "web, crawl sites, run deep research, use ready made actions on hundreds of "
                "popular sites, monitor pages for changes, compare AI engine answers and run "
                "AI browser tasks."
            ),
            "version": "1.0",
            "contact": {"name": "Anakin Support", "url": "https://anakin.io/support",
                        "email": "support@anakin.io"},
        },
        "host": "api.anakin.io",
        "basePath": "/v1",
        "schemes": ["https"],
        "consumes": [],
        "produces": [],
        "paths": paths,
        "definitions": {},
        "parameters": {},
        "responses": {},
        "securityDefinitions": {
            "api_key": {"type": "apiKey", "in": "header", "name": "X-API-Key"},
        },
        "security": [{"api_key": []}],
        "tags": [],
        "x-ms-connector-metadata": [
            {"propertyName": "Website", "propertyValue": "https://anakin.io"},
            {"propertyName": "Privacy policy",
             "propertyValue": "https://anakin.io/connector-privacy"},
            {"propertyName": "Categories", "propertyValue": "Data;Business Intelligence"},
        ],
    }


if __name__ == "__main__":
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    doc = build()
    (out / "apiDefinition.swagger.json").write_text(json.dumps(doc, indent=2) + "\n")
    print(f"{len(OPS)} operations written to {out / 'apiDefinition.swagger.json'}")
