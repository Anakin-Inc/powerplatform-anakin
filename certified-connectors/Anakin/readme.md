# Anakin
Anakin turns websites into clean, structured data. This connector lets flows, apps and agents scrape web pages, search the web, crawl sites, run multi-source research, use ready made actions on hundreds of popular sites, monitor pages for changes, compare how AI answer engines respond to a question and run AI browser tasks.

## Publisher: Anakin

## Prerequisites
You need an Anakin account and API key. Sign up at [anakin.io/signup](https://anakin.io/signup); the free Starter plan includes 300 credits. Each action spends credits from your Anakin account, as listed on the [pricing page](https://anakin.io/pricing).

## Supported Operations
Long running jobs come as two actions: one starts the job and returns its ID, and a matching "Get ... result" action returns the status and result. Call the second action in a loop, with a short delay, until the status is `completed` or `failed`.

### Web data

#### Scrape a web page now
Fetches one web page and waits up to 50 seconds for the result, so no follow up action is needed. This suits apps, which have no loops. If the page takes longer, the status is still processing; pass the returned ID to Get scrape result.

#### Scrape a web page
Starts fetching one web page as markdown and HTML, with optional AI extraction. Use Get scrape result with the returned job ID to get the content.

#### Get scrape result
Gets the status and content of a scrape job. Repeat until the status is completed or failed.

#### Search the web
Searches the web and returns result URLs, titles and snippets right away.

#### Start deep research
Starts researching a question across many sources. It searches, reads the cited pages and returns a summary and structured data, which can take a few minutes. Use Get research result with the returned job ID.

#### Get research result
Gets the status and result of a research job. Repeat until the status is completed or failed.

#### Map website URLs
Starts finding the URLs on a website, to decide which pages to crawl. Use Get map result with the returned job ID.

#### Get map result
Gets the status and URLs of a map job. Repeat until the status is completed or failed.

#### Crawl a website
Starts fetching many pages of one site as markdown. Use Get crawl result with the returned job ID.

#### Get crawl result
Gets the status and pages of a crawl job. Repeat until the status is completed or failed.

### Wire site actions

#### Find Wire actions
Finds ready made Wire actions for a task, such as searching listings on a well known site. Wire actions return structured data and are faster than scraping.

#### List Wire sites
Lists every site in the Wire catalog and how many actions each has.

#### Get Wire site actions
Gets one site in the Wire catalog with all its actions and their parameters.

#### Run Wire action
Runs a Wire action with its parameters. Some actions return data right away; others return a job ID to pass to Get Wire job result.

#### Get Wire job result
Gets the status and data of a Wire job. Repeat until the status is completed or failed.

#### List Wire identities
Lists your saved site sign ins. Use a credential ID from here in Run Wire action.

#### Request new Wire actions
Asks Wire to build and test new actions for a site that is not in the catalog yet. It charges credits, which are refunded if the build fails. Track it with Get Wire build.

#### Get Wire build
Gets a Wire build request, including its status and the published action once it succeeds.

### Website monitors

#### Create website monitor
Creates a monitor that checks a page, a whole site or a Wire action on a schedule and records changes. Every check costs credits.

#### List website monitors
Lists your website monitors with their status and next check.

#### Get website monitor
Gets one monitor's settings and status.

#### Get monitor changes
Gets the changes a monitor detected, each with a summary and the differences.

#### Pause website monitor
Stops a monitor's scheduled checks until it is resumed.

#### Resume website monitor
Restarts a paused monitor's scheduled checks.

#### Check website monitor now
Runs a monitor's check now, outside its schedule. It costs the same as a scheduled check.

#### Delete website monitor
Permanently deletes a monitor and its history.

### AI visibility

#### Compare AI engine answers
Asks AI answer engines such as ChatGPT, Gemini and Google AI Overview the same question, to compare how they answer. Use Get AI answer comparison with the returned search ID.

#### Get AI answer comparison
Gets the answers from each engine. Repeat until the status is completed or failed.

#### List AI engines
Lists the AI answer engines that Compare AI engine answers can ask.

### Browser sessions and tasks

#### List browser sessions
Lists your saved browser sessions, which let other actions reach pages behind a sign in. You create sessions in the Anakin dashboard.

#### Delete browser session
Permanently deletes a saved browser session. You need to sign in again in the dashboard to recreate it.

#### Run AI browser task
Starts an AI agent that drives a real cloud browser through a task, such as finding a product and reading its details. Use Get AI browser task result with the returned workflow ID.

#### Get AI browser task result
Gets the status and result of an AI browser task. Repeat until the status is completed, failed or timed out.

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
