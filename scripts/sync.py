#!/usr/bin/env python3
"""Download Loon rule sets and rewrite every rule in Surge rule-set syntax."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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


def convert_to_surge(source: str, name: str, url: str) -> tuple[str, int]:
    """Keep every non-comment rule and normalize comma-separated Surge syntax."""
    output = [f"# {name}", f"# Source: {url}"]
    rule_count = 0
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line:
            output.append("")
            continue
        if line.startswith("#"):
            output.append(line)
            continue

        parts = [part.strip() for part in line.split(",")]
        if parts and parts[0].upper() == "GEOIP" and len(parts) > 1:
            parts[1] = parts[1].upper()
        output.append(",".join(parts))
        rule_count += 1

    return "\n".join(output).rstrip() + "\n", rule_count


def sync_one(source: dict[str, Any], user_agent: str) -> tuple[dict[str, Any], str, int]:
    body = fetch(source["url"], user_agent)
    converted, rule_count = convert_to_surge(body, source["name"], source["url"])
    digest = hashlib.sha256(converted.encode("utf-8")).hexdigest()
    return source, converted, rule_count


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(content, encoding="utf-8")
    temp_path.replace(path)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--output", type=Path, default=Path("rules"))
    parser.add_argument("--manifest", type=Path, default=Path("rules/manifest.json"))
    args = parser.parse_args()

    config = json.loads(args.sources.read_text(encoding="utf-8"))
    sources = config["sources"]
    user_agent = config["user_agent"]
    results: list[tuple[dict[str, Any], str, int]] = []
    errors: list[str] = []

    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {executor.submit(sync_one, source, user_agent): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                results.append(future.result())
            except Exception as error:
                errors.append(f"{source['id']}: {error}")

    if errors:
        print("No files were changed because one or more downloads failed:", file=sys.stderr)
        print("\n".join(errors), file=sys.stderr)
        return 1

    result_by_id = {source["id"]: (source, content, rule_count) for source, content, rule_count in results}
    manifest_sources = []
    for source in sources:
        item, content, rule_count = result_by_id[source["id"]]
        target = args.output / f"{item['id']}.list"
        write_if_changed(target, content)
        manifest_sources.append(
            {
                "id": item["id"],
                "name": item["name"],
                "source_url": item["url"],
                "file": target.name,
                "rule_count": rule_count,
                "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            }
        )

    expected = {f"{source['id']}.list" for source in sources} | {args.manifest.name}
    for file_path in args.output.glob("*.list"):
        if file_path.name not in expected:
            file_path.unlink()

    manifest = {"format": "surge-rule-set", "sources": manifest_sources}
    write_if_changed(args.manifest, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(f"Synced {len(sources)} rule sets into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

