# Anakin connector for Microsoft Power Platform

Source for Anakin's Microsoft certified connector. Once certified, one connector
appears in Power Automate, Power Apps, Azure Logic Apps and Copilot Studio: 33
actions for scraping, search, crawling, deep research, Wire site actions,
website monitors, AI answer comparison and AI browser tasks.

The connector files in `certified-connectors/Anakin` are what Microsoft
publishes in [microsoft/PowerPlatformConnectors](https://github.com/microsoft/PowerPlatformConnectors)
(a PR to its `dev` branch, under `certified-connectors/Anakin`):

| File | What it is |
|---|---|
| `apiDefinition.swagger.json` | The 33 actions, as OpenAPI 2.0 with Microsoft's extensions |
| `apiProperties.json` | The API-key connection and brand color |
| `icon.png` | 230×230 icon on the brand color `#1F302C` |
| `readme.md` | The connector's documentation page |

## Editing

Don't edit `apiDefinition.swagger.json` or `readme.md` by hand. Change the
generators, then rebuild and check:

```bash
python tools/build_swagger.py certified-connectors/Anakin
python tools/build_readme.py certified-connectors/Anakin
uv run --no-project --with jsonschema --with openapi-spec-validator --with json5 \
  python tools/check_connector.py certified-connectors/Anakin tools/schemas
```

`check_connector.py` validates against Microsoft's JSON schemas
(`tools/schemas`), the OpenAPI 2.0 spec, and the certification rules for
titles, summaries, descriptions, visibility, response schemas and path
parameters. CI runs the same checks and fails if the committed files differ
from what the generators produce.

To redraw the icon: `node tools/render_icon.cjs <playwright module path> <light logo svg> certified-connectors/Anakin/icon.png`.

## Status and next steps

Not yet certified. Remaining, in order:

1. Microsoft Partner Center Seller account with business verification, enrolled
   in the Microsoft 365 and Copilot program.
2. Import into a Power Platform environment
   (`paconn create --api-def apiDefinition.swagger.json --api-prop apiProperties.json --icon icon.png`),
   test every action (Microsoft asks for at least 10 successful calls each) and
   run Solution Checker.
3. Open the PR to `microsoft/PowerPlatformConnectors` (`dev` branch).
4. Export the connector and a test flow as solutions, package them with an
   `intro.md`, and submit in Partner Center. Microsoft reviews in 24 to 48 hours,
   then deploys over 10 to 14 days.

## License

MIT
