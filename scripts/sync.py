#!/usr/bin/env python3
"""Fetch Loon rules and losslessly generate Surge and Clash/Mihomo providers."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


# Types documented by Loon's rule manual. The min/max counts cover matcher
# arguments only; a routing policy is intentionally not accepted in a provider.
LEAF_RULES = {
    "DOMAIN": (1, 1),
    "DOMAIN-SUFFIX": (1, 1),
    "DOMAIN-KEYWORD": (1, 1),
    "URL-REGEX": (1, 1),
    "USER-AGENT": (1, 1),
    "IP-CIDR": (1, 2),
    "IP-CIDR6": (1, 2),
    "GEOIP": (1, 2),
    "IP-ASN": (1, 2),
    "SRC-PORT": (1, 1),
    "DEST-PORT": (1, 1),
    "PROTOCOL": (1, 1),
}
LOGICAL_RULES = {"AND", "OR", "NOT"}
NO_RESOLVE_RULES = {"IP-CIDR", "IP-CIDR6", "GEOIP", "IP-ASN"}
CLASH_NAME_MAP = {"DEST-PORT": "DST-PORT"}


@dataclass(frozen=True)
class Rule:
    kind: str
    args: tuple[str, ...] = ()
    children: tuple["Rule", ...] = ()


class RuleSyntaxError(ValueError):
    """The source line cannot be represented exactly in a reusable provider."""


def fetch(url: str, user_agent: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Language": "zh-CN,zh-Hans;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://kelee.one/",
        },
    )
    last_error: Exception | None = None
    for _ in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                body = response.read().decode("utf-8-sig", errors="strict")
            if not body.strip() or "<html" in body[:512].lower():
                raise RuntimeError("source returned an empty or HTML response")
            return body
        except (HTTPError, URLError, TimeoutError, UnicodeError, RuntimeError) as error:
            last_error = error
    raise RuntimeError(f"download failed after 3 attempts: {last_error}")


def split_top_level(text: str) -> list[str]:
    """Split commas outside quoted values and balanced parentheses."""
    pieces: list[str] = []
    start = depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                raise RuleSyntaxError("unbalanced closing parenthesis")
        elif char == "," and depth == 0:
            pieces.append(text[start:index].strip())
            start = index + 1
    if quote is not None:
        raise RuleSyntaxError("unterminated quoted value")
    if depth:
        raise RuleSyntaxError("unbalanced parentheses")
    pieces.append(text[start:].strip())
    return pieces


def unwrap_outer_parentheses(text: str) -> str:
    value = text.strip()
    if not value.startswith("(") or not value.endswith(")"):
        raise RuleSyntaxError("logical operands must be enclosed in parentheses")
    depth = 0
    quote: str | None = None
    escaped = False
    for index, char in enumerate(value):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0 or (depth == 0 and index != len(value) - 1):
                raise RuleSyntaxError("unbalanced logical rule parentheses")
    if quote is not None or depth:
        raise RuleSyntaxError("unbalanced logical rule parentheses")
    return value[1:-1].strip()


def strip_inline_comment(text: str) -> str:
    """Remove Loon's whitespace-prefixed // comments without touching URLs or regexes."""
    quote: str | None = None
    escaped = False
    for index, char in enumerate(text[:-1]):
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in {"'", '"'}:
            quote = char
        elif char == "/" and text[index + 1] == "/" and (index == 0 or text[index - 1].isspace()):
            return text[:index].rstrip()
    return text


def parse_rule(text: str) -> Rule:
    parts = split_top_level(text)
    if not parts or not parts[0]:
        raise RuleSyntaxError("missing rule type")
    kind, args = parts[0].upper(), parts[1:]
    if kind in LOGICAL_RULES:
        if len(args) != 1:
            raise RuleSyntaxError(
                f"{kind} expects one operand group; policies are not valid in reusable providers"
            )
        children = tuple(
            parse_rule(unwrap_outer_parentheses(child) if child.strip().startswith("(") else child)
            for child in split_top_level(unwrap_outer_parentheses(args[0]))
        )
        minimum = 1 if kind == "NOT" else 2
        if len(children) < minimum:
            raise RuleSyntaxError(f"{kind} requires at least {minimum} child rules")
        return Rule(kind=kind, children=children)
    if kind not in LEAF_RULES:
        raise RuleSyntaxError(f"unsupported Loon rule type {kind!r}; no rule was discarded")
    minimum, maximum = LEAF_RULES[kind]
    if not minimum <= len(args) <= maximum or any(not arg for arg in args):
        suffix = f"–{maximum}" if minimum != maximum else ""
        raise RuleSyntaxError(
            f"{kind} expects {minimum}{suffix} matcher arguments; a trailing policy cannot be converted"
        )
    if len(args) == 2 and (kind not in NO_RESOLVE_RULES or args[1].lower() != "no-resolve"):
        raise RuleSyntaxError(f"{kind} accepts only no-resolve as a second argument")
    if kind == "GEOIP":
        args[0] = args[0].upper()
    return Rule(kind=kind, args=tuple(args))


def parse_source(body: str, source_id: str) -> tuple[list[Rule], list[str], Counter[str]]:
    rules: list[Rule] = []
    comments: list[str] = []
    rule_types: Counter[str] = Counter()
    for line_number, raw_line in enumerate(body.splitlines(), 1):
        line = strip_inline_comment(raw_line.strip())
        if not line:
            continue
        if line.startswith("#"):
            comments.append(line)
            continue
        if line.startswith("[") and line.endswith("]"):
            if line.upper() == "[RULE]":
                continue
            raise RuleSyntaxError(f"{source_id}:{line_number}: unsupported section {line!r}")
        try:
            rule = parse_rule(line)
        except RuleSyntaxError as error:
            raise RuleSyntaxError(f"{source_id}:{line_number}: {error}") from error
        rules.append(rule)
        rule_types[rule.kind] += 1
    if not rules:
        raise RuleSyntaxError(f"{source_id}: source contains no rules")
    return rules, comments, rule_types


def serialize(rule: Rule, target: str) -> str:
    kind = CLASH_NAME_MAP.get(rule.kind, rule.kind) if target == "clash" else rule.kind
    if rule.children:
        return f"{kind},(" + ",".join(f"({serialize(child, target)})" for child in rule.children) + ")"
    return ",".join((kind, *rule.args))


def source_stem(source: dict[str, Any]) -> str:
    name = Path(unquote(urlparse(source["url"]).path)).name
    if not name:
        raise ValueError(f"source URL has no filename: {source['url']}")
    return Path(name).stem


def digest(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def render_surge(item: dict[str, Any], rules: list[Rule], comments: list[str]) -> str:
    lines = [
        f"# {item['name']}",
        f"# Source: {item['url']}",
        "# Generated from Loon syntax; do not edit.",
        *comments,
    ]
    lines.extend(serialize(rule, "surge") for rule in rules)
    return "\n".join(lines).rstrip() + "\n"


def render_clash(item: dict[str, Any], rules: list[Rule], comments: list[str]) -> str:
    lines = [
        f"# {item['name']}",
        f"# Source: {item['url']}",
        "# Classical provider generated from Loon syntax.",
        "payload:",
    ]
    lines.extend(f"  {comment}" for comment in comments)
    lines.extend("  - " + json.dumps(serialize(rule, "clash"), ensure_ascii=False) for rule in rules)
    return "\n".join(lines).rstrip() + "\n"


def write_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def previously_managed(manifest: Path) -> set[str]:
    if not manifest.exists():
        return set()
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        return {entry["file"] for entry in payload.get("sources", []) if isinstance(entry.get("file"), str)}
    except (OSError, ValueError, TypeError):
        return set()


def publish(directory: Path, files: dict[str, str], manifest: str) -> None:
    old_files = previously_managed(directory / "manifest.json")
    for stale_name in old_files - set(files):
        stale_path = directory / stale_name
        if stale_path.exists():
            stale_path.unlink()
    for filename, content in files.items():
        write_if_changed(directory / filename, content)
    write_if_changed(directory / "manifest.json", manifest)


def sync_one(item: dict[str, Any], user_agent: str) -> tuple[dict[str, Any], str, list[Rule], list[str], Counter[str]]:
    body = fetch(item["url"], user_agent)
    rules, comments, types = parse_source(body, item["id"])
    return item, body, rules, comments, types


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--output", type=Path, default=Path("rules"))
    args = parser.parse_args()
    config = json.loads(args.sources.read_text(encoding="utf-8"))
    sources: list[dict[str, Any]] = config["sources"]
    if len({source_stem(source) for source in sources}) != len(sources):
        raise ValueError("source URLs must have unique filenames")

    results: list[tuple[dict[str, Any], str, list[Rule], list[str], Counter[str]]] = []
    errors: list[str] = []
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(sync_one, source, config["user_agent"]): source for source in sources}
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                errors.append(f"{futures[future]['id']}: {error}")
    if errors:
        print("No generated files changed because conversion was not lossless:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1

    result_by_id = {result[0]["id"]: result for result in results}
    surge_files: dict[str, str] = {}
    clash_files: dict[str, str] = {}
    surge_records: list[dict[str, Any]] = []
    clash_records: list[dict[str, Any]] = []
    report_sources: list[dict[str, Any]] = []
    for source in sources:
        item, body, rules, comments, types = result_by_id[source["id"]]
        stem = source_stem(item)
        surge_name, clash_name = stem + ".list", stem + ".yaml"
        surge, clash = render_surge(item, rules, comments), render_clash(item, rules, comments)
        surge_files[surge_name], clash_files[clash_name] = surge, clash
        common = {
            "id": item["id"],
            "name": item["name"],
            "source_url": item["url"],
            "source_rule_count": len(rules),
            "rule_types": dict(sorted(types.items())),
        }
        surge_records.append({**common, "file": surge_name, "sha256": digest(surge)})
        clash_records.append({**common, "file": clash_name, "sha256": digest(clash)})
        report_sources.append({
            **common,
            "source_sha256": digest(body),
            "surge": {"file": f"surge/{surge_name}", "sha256": digest(surge)},
            "clash": {"file": f"clash/{clash_name}", "sha256": digest(clash)},
        })

    surge_manifest = json.dumps({"format": "surge-rule-set", "sources": surge_records}, ensure_ascii=False, indent=2) + "\n"
    clash_manifest = json.dumps({"format": "clash-classical-rule-provider", "sources": clash_records}, ensure_ascii=False, indent=2) + "\n"
    report = json.dumps({
        "generator": "strict-loon-rule-converter",
        "source_user_agent": config["user_agent"],
        "conversion_policy": "Unknown, malformed, or non-lossless rules fail the run; no source rule is dropped.",
        "sources": report_sources,
    }, ensure_ascii=False, indent=2) + "\n"

    # No output is touched until every source has downloaded and parsed.
    publish(args.output / "surge", surge_files, surge_manifest)
    publish(args.output / "clash", clash_files, clash_manifest)
    write_if_changed(args.output / "conversion-report.json", report)

    # One-time migration: delete only files named by the previous generated manifest.
    legacy_manifest = args.output / "manifest.json"
    for legacy_name in previously_managed(legacy_manifest):
        legacy_path = args.output / legacy_name
        if legacy_path.exists():
            legacy_path.unlink()
    if legacy_manifest.exists():
        legacy_manifest.unlink()

    print(f"Synced {len(sources)} Loon sources into Surge and Clash provider folders")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
