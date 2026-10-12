"""Writes the connector readme.md, with Supported Operations generated from the swagger.

Usage: python build_readme.py <connector dir>
"""

import json
import sys
from pathlib import Path

conn = Path(sys.argv[1])
swagger = json.loads((conn / "apiDefinition.swagger.json").read_text())
ops = {o["operationId"]: o for methods in swagger["paths"].values() for o in methods.values()}

GROUPS = [
    ("Web data", ["ScrapeUrlNow", "ScrapeUrl", "GetScrapeResult", "Search", "StartAgenticSearch",
                  "GetAgenticSearchResult", "StartMap", "GetMapResult", "StartCrawl",
                  "GetCrawlResult"]),
    ("Wire site actions", ["DiscoverWireActions", "ListWireCatalogs", "GetWireCatalog",
                           "RunWireAction", "GetWireJobResult", "ListWireIdentities",
                           "RequestWireBuild", "GetWireBuild"]),
    ("Website monitors", ["CreateMonitor", "ListMonitors", "GetMonitor", "GetMonitorChanges",
                          "PauseMonitor", "ResumeMonitor", "RunMonitorNow", "DeleteMonitor"]),
    ("AI visibility", ["StartAiVisibilitySearch", "GetAiVisibilitySearch",
                       "ListAiVisibilitySources"]),
    ("Browser sessions and tasks", ["ListBrowserSessions", "DeleteBrowserSession",
                                    "StartBrowserTask", "GetBrowserTaskResult"]),
]
listed = [o for _, ids in GROUPS for o in ids]
assert sorted(listed) == sorted(ops), set(ops) ^ set(listed)

parts = []
for group, ids in GROUPS:
    parts.append(f"### {group}\n")
    for op_id in ids:
        o = ops[op_id]
        parts.append(f"#### {o['summary']}\n{o['description']}\n")
operations = "\n".join(parts)

readme = f"""# Anakin
Anakin turns websites into clean, structured data. This connector lets flows, apps and agents scrape web pages, search the web, crawl sites, run multi-source research, use ready made actions on hundreds of popular sites, monitor pages for changes, compare how AI answer engines respond to a question and run AI browser tasks.

## Publisher: Anakin

## Prerequisites
You need an Anakin account and API key. Sign up at [anakin.io/signup](https://anakin.io/signup); the free Starter plan includes 300 credits. Each action spends credits from your Anakin account, as listed on the [pricing page](https://anakin.io/pricing).

## Supported Operations
Long running jobs come as two actions: one starts the job and returns its ID, and a matching "Get ... result" action returns the status and result. Call the second action in a loop, with a short delay, until the status is `completed` or `failed`.

{operations}
## Obtaining Credentials
The connector uses an API key.

1. Sign in at [anakin.io/dashboard](https://anakin.io/dashboard).
2. Copy your API key, which starts with `ask_`.
3. When you create a connection, paste the key into **API Key**.

## Getting Started
1. Add the **Scrape a web page** action and enter a URL.
2. Add a **Do until** loop that runs **Get scrape result** with the job ID from the first action, with a 5 second delay, until **Status** is `completed` or `failed`.
3. Use **Markdown** from the result in the following steps.

In an app, where there are no loops, use **Scrape a web page now** instead: it waits up to 50 seconds and returns the page in one step. **Search the web** also returns results right away. For well known sites such as Amazon or LinkedIn, **Find Wire actions** and **Run Wire action** return structured data without scraping.

## Known Issues and Limitations
- Scrape, crawl, map, research, AI answer comparison and AI browser tasks run in the background. Use the matching get result action in a loop to wait for them.
- Wire actions that need a sign in use a credential from **List Wire identities**. Signing in to a site happens in the Anakin dashboard, not in the connector, so that site passwords never pass through flow inputs.
- Browser sessions for pages behind a sign in are created in the Anakin dashboard. The connector can list and delete them.

## Frequently Asked Questions
### How are actions billed?
Each action spends credits from your Anakin account. A scrape costs 1 credit, with no extra charge for browser rendering and 2 more credits for AI JSON extraction. A crawl is charged upfront by its maximum pages, and monitors spend credits on every check. Wire actions show their cost in the catalog and are refunded if they fail. See the [pricing page](https://anakin.io/pricing) for every action.

### Where do I get help?
Visit [anakin.io/support](https://anakin.io/support) or email support@anakin.io.

## Deployment Instructions
Run the following commands with the [Power Platform Connectors CLI](https://learn.microsoft.com/connectors/custom-connectors/paconn-cli) to deploy this connector as a custom connector:

```bash
paconn login
paconn create --api-def apiDefinition.swagger.json --api-prop apiProperties.json --icon icon.png
```
"""
(conn / "readme.md").write_text(readme)
print(f"readme.md written with {len(ops)} operations")
