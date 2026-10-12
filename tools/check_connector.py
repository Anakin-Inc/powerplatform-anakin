"""Checks a Power Platform connector folder against Microsoft's certification rules.

Usage: python check_connector.py <connector dir> <schemas dir>
Covers Microsoft's JSON schemas, the OpenAPI 2.0 spec, and the string and
response rules in "Prepare connector files for certification" and the
Swagger Validator rule list.
"""

import json
import re
import sys
from pathlib import Path

import json5
import jsonschema
from openapi_spec_validator import validate
from openapi_spec_validator.validation.exceptions import OpenAPIValidationError

conn, schemas = Path(sys.argv[1]), Path(sys.argv[2])
swagger = json.loads((conn / "apiDefinition.swagger.json").read_text())
props = json.loads((conn / "apiProperties.json").read_text())
problems: list[str] = []


def bad(msg: str) -> None:
    problems.append(msg)


# 1. Microsoft's JSON schemas.
for doc, name in ((swagger, "apiDefinition.swagger.schema.json"),
                  (props, "paconn-apiProperties.schema.json")):
    # Microsoft's schema files aren't strict JSON (trailing commas), so parse leniently.
    schema = json5.loads((schemas / name).read_text())
    for err in jsonschema.Draft7Validator(schema).iter_errors(doc):
        bad(f"{name}: {'/'.join(map(str, err.absolute_path))}: {err.message[:200]}")

# 2. OpenAPI 2.0.
try:
    validate(swagger)
except OpenAPIValidationError as err:
    bad(f"OpenAPI 2.0: {str(err)[:300]}")

# 3. Certification rules.
PRODUCT_NAMES = ["power apps", "power automate", "copilot studio", "logic apps", "power bi",
                 "power platform", "copilot"]
SUMMARY_RE = re.compile(r"^[A-Za-z0-9 ()]+$")


def no_products(where: str, text: str) -> None:
    low = text.lower()
    for p in PRODUCT_NAMES:
        if p in low:
            bad(f"{where}: mentions product name {p!r}")


def summary_ok(where: str, text: str | None) -> None:
    if not text:
        bad(f"{where}: missing summary")
        return
    if len(text) > 80:
        bad(f"{where}: summary longer than 80 characters")
    if not SUMMARY_RE.match(text):
        bad(f"{where}: summary {text!r} has characters other than letters, digits, spaces "
            "and parentheses")
    no_products(where, text)


def description_ok(where: str, text: str | None) -> None:
    if not text:
        bad(f"{where}: missing description")
        return
    if text.rstrip()[-1] not in ".!?":
        bad(f"{where}: description doesn't end with punctuation: {text[-40:]!r}")
    no_products(where, text)


info = swagger["info"]
title = info["title"]
if len(title) > 30 or not title[-1].isalnum():
    bad("info.title: over 30 characters or ends with a non-alphanumeric character")
for word in ["api", "connector"]:
    if re.search(rf"\b{word}\b", title, re.I):
        bad(f"info.title contains {word!r}")
no_products("info.title", title)
if not 30 < len(info["description"]) < 500:
    bad(f"info.description is {len(info['description'])} characters, needs 31 to 499")
no_products("info.description", info["description"])
meta = {m["propertyName"].lower(): m["propertyValue"] for m in swagger.get("x-ms-connector-metadata", [])}
for key in ("website", "privacy policy", "categories"):
    if key not in meta:
        bad(f"x-ms-connector-metadata missing {key}")
color = props["properties"].get("iconBrandColor", "").lower()
if not re.fullmatch(r"#[0-9a-f]{6}", color) or color in ("#ffffff", "#007ee5"):
    bad(f"iconBrandColor {color!r} is invalid, white or the default")

op_ids = set()


def walk_schema(where: str, sch: dict, is_input: bool) -> None:
    t = sch.get("type")
    if t == "array" and "items" not in sch:
        bad(f"{where}: array without items")
    req = sch.get("required")
    if req is not None:
        if not req:
            bad(f"{where}: empty required list")
        for r in req:
            if r not in sch.get("properties", {}):
                bad(f"{where}: required {r!r} not in properties")
    if "enum" in sch and "default" in sch and sch["default"] not in sch["enum"]:
        bad(f"{where}: default not in enum")
    if is_input:
        vis = sch.get("x-ms-visibility")
        if vis == "internal" and "default" in sch:
            pass  # checked by the parent, which knows the required list
    for name, child in sch.get("properties", {}).items():
        cw = f"{where}.{name}"
        if is_input:
            summary_ok(cw, child.get("x-ms-summary"))
            description_ok(cw, child.get("description"))
            if child.get("x-ms-visibility") == "internal" and name not in (req or []):
                bad(f"{cw}: internal field with a default must be required")
        else:
            no_products(cw, child.get("description", ""))
        walk_schema(cw, child, is_input)
    if "items" in sch:
        walk_schema(f"{where}[]", sch["items"], is_input)


for path, methods in swagger["paths"].items():
    for method, op in methods.items():
        where = f"{method.upper()} {path}"
        oid = op.get("operationId")
        if not oid or not re.fullmatch(r"[A-Za-z0-9]+", oid):
            bad(f"{where}: operationId {oid!r} missing or not alphanumeric")
        if oid in op_ids:
            bad(f"{where}: duplicate operationId {oid}")
        op_ids.add(oid)
        summary_ok(where, op.get("summary"))
        description_ok(where, op.get("description"))
        if op.get("x-ms-visibility") not in ("important", "advanced", "internal"):
            bad(f"{where}: missing x-ms-visibility")
        params = op.get("parameters", [])
        has_body = any(p["in"] == "body" for p in params)
        if method == "get" and has_body:
            bad(f"{where}: GET with a body")
        if has_body and not op.get("consumes"):
            bad(f"{where}: body operation without consumes")
        for p in params:
            pw = f"{where} param {p['name']}"
            if p["in"] == "path":
                if not p.get("required"):
                    bad(f"{pw}: path parameter not required")
                if p.get("x-ms-url-encoding") != "single":
                    bad(f"{pw}: path parameter without x-ms-url-encoding single")
                if "{" + p["name"] + "}" not in path:
                    bad(f"{pw}: not in the path template")
            if p["in"] == "body":
                walk_schema(pw, p["schema"], is_input=True)
            else:
                summary_ok(pw, p.get("x-ms-summary"))
                description_ok(pw, p.get("description"))
        for name in re.findall(r"{(\w+)}", path):
            if not any(p["in"] == "path" and p["name"] == name for p in params):
                bad(f"{where}: path variable {name} has no parameter")
        responses = op.get("responses", {})
        ok = [c for c in responses if c in ("200", "201")]
        if not ok or "schema" not in responses[ok[0]]:
            bad(f"{where}: no 200 or 201 response with a schema")
        if "default" in responses and "schema" in responses["default"]:
            bad(f"{where}: default response has a schema")
        for code, r in responses.items():
            if "schema" in r:
                walk_schema(f"{where} response {code}", r["schema"], is_input=False)

print(f"{len(op_ids)} operations checked")
if problems:
    print(f"{len(problems)} problem(s):")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print("No problems found.")
