# Certifying the Anakin connector

What's left before the connector is live in Power Automate, Power Apps, Azure Logic
Apps and Copilot Studio, and who does each step. Steps marked **Anakin admin** need
someone who can act for the company on Microsoft accounts; everything else is
scripted in this repo.

## Where things stand

| | State |
|---|---|
| Connector files | Done: 33 actions, readme, icon, connection settings |
| Our checks | Pass: Microsoft's JSON schemas, OpenAPI 2.0, certification string rules, and every response schema against the documented API responses (`tools/check_docs_examples.py`) |
| Live API test | Ready, not run: `tools/live_test.py` needs an Anakin API key |
| Microsoft's own validators | Not run: they're private services that run on the PR, or through `paconn validate` after signing in |
| Power Platform test | Not done: needs a Power Platform environment |
| Microsoft PR | Prepared on a fork branch, not opened (opened after the Power Platform test) |
| Partner Center submission | Not started: needs the Partner Center account |

## 1. Partner Center Seller account (Anakin admin, start first)

Business verification can take days, so start this before anything else.

1. Go to <https://partner.microsoft.com/dashboard/home> and sign in with a work
   account for the company (a Microsoft Entra ID account on an Anakin domain, not a
   personal Microsoft account). If Anakin has no Microsoft 365 or Entra tenant, the
   sign-up creates one.
2. Make sure that account has an email address set in Entra ID. Microsoft rejects
   certification requests from accounts without one.
3. Enroll in Partner Center and complete **business verification**: legal company
   name, address, and a contact who can verify by email. Microsoft may ask for
   documents.
4. Enroll in the **Microsoft 365 and Copilot** program from Partner Center's
   programs settings. Microsoft's guide:
   <https://learn.microsoft.com/partner-center/marketplace/open-a-developer-account>.

Tell me when verification is approved.

## 2. Live API test (anyone with an Anakin API key, 5 minutes)

Runs every action against the real API and checks each response against the
connector's schema. Costs about 30 credits (about 58 with `--include-costly`, which
adds a Wire build and an AI browser task).

```bash
cd powerplatform-anakin
echo 'ask_your_key' > ~/.anakin_key && chmod 600 ~/.anakin_key   # don't paste the key in chat
uv run --no-project --with httpx --with jsonschema \
  python tools/live_test.py --key-file ~/.anakin_key            # dry run: plan and cost
uv run --no-project --with httpx --with jsonschema \
  python tools/live_test.py --key-file ~/.anakin_key --yes
```

Each line is PASS, SCHEMA (the live response differs from the declared schema),
FAIL (an HTTP error) or SKIP. Send me the output; I fix any SCHEMA or FAIL lines.
The test creates its own monitor and deletes it again. It never deletes a browser
session unless you pass `--session-id`.

## 3. Power Platform environment (Anakin admin)

Microsoft requires the connector to be tested in Power Platform before submission,
and the submission package is exported from there.

1. Get a Power Platform environment: <https://make.powerautomate.com> with the
   same work account. The free Power Apps Developer Plan
   (<https://aka.ms/PowerAppsDevPlan>) gives an environment for building and
   testing custom connectors. Certified connectors are premium, so the people who
   use it later need a premium Power Automate or Power Apps licence.
2. Install the connector CLI and import the connector:

   ```bash
   pip install paconn          # Microsoft's connector CLI; works on Python 3.12
   paconn login
   cd certified-connectors/Anakin
   paconn validate --api-def apiDefinition.swagger.json   # Microsoft's validator
   paconn create --api-def apiDefinition.swagger.json --api-prop apiProperties.json --icon icon.png
   ```

   Or I run these if you give me access to the environment.
3. In Power Automate, create a solution, add the custom connector to it, and run
   **Solution checker** on it.
4. Test every action from the custom connector's **Test** tab or in a flow.
   Microsoft asks for at least 10 successful calls per action. Fix any schema
   errors the Test tab reports (send them to me).
5. Create a test flow that uses the connector (for example: Scrape a web page now,
   then Search the web) and add it to a second solution.
6. Export both solutions (connector solution and flow solution) as unmanaged.

## 4. Open the Microsoft PR (me)

After step 3 passes, I open the PR from the prepared fork branch to
`microsoft/PowerPlatformConnectors` (`dev` branch, `certified-connectors/Anakin`).
Their Swagger Validator runs on the PR; I fix anything it reports. The CLA bot
asks the PR author to sign Microsoft's Contributor License Agreement once.

## 5. Package and submit (me to package, Anakin admin to submit)

1. I build the package: `intro.md` (the connector `readme.md`) and `package.zip`
   containing the two exported solutions, and check it with Microsoft's
   `scripts/ConnectorPackageValidator.ps1`.
2. Upload the zip to Azure Blob Storage and create a SAS URL valid for at least
   15 days (needs an Azure subscription on the company tenant).
3. In Partner Center: **Marketplace offers → Microsoft 365 and Copilot → New offer
   → Connectors & Agents in Microsoft Copilot Studio**.
   - **Packages**: paste the SAS URL. There's no OAuth, so leave Client ID and
     Client Secret empty.
   - **Properties**: categories *Data* and *Business Intelligence*; use the
     Microsoft Standard Contract; privacy policy
     `https://anakin.io/connector-privacy`; support `https://anakin.io/support`.
   - **Availability**: no HideKey, so the documentation page is generated.
   - **Review and publish**.
4. Microsoft returns a certification report within 48 hours. If it passes, they
   give a preview environment link that's live for 48 business hours: test the
   connector there and press **Go live**.
5. Microsoft deploys it to all regions over 10 to 14 days, starting the next
   Friday.

## After it's live

- Updates go through a PR to the `dev` branch and a new Partner Center submission.
- After a while in preview, request the general availability tag.
- Keep `https://anakin.io/connector-privacy` and `https://anakin.io/support` live;
  certification requires them.
