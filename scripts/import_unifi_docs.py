from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ENDPOINT_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


def snake_case(value: str) -> str:
    value = value.replace("&", " and ")
    value = re.sub(r"[^0-9A-Za-z]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_").lower()


def tool_name(title: str, fallback: str) -> str:
    slug = snake_case(title) or snake_case(fallback)
    return f"unifi_network_{slug}"


def endpoint_manifest(source_path: Path, raw: dict[str, Any]) -> dict[str, Any] | None:
    method = raw.get("method")
    path = raw.get("path")
    if method not in ENDPOINT_METHODS or not path:
        return None

    title = raw.get("h1") or source_path.stem
    return {
        "schemaVersion": 1,
        "name": tool_name(str(title), source_path.stem),
        "title": str(title),
        "namespace": "network",
        "method": method,
        "path": path,
        "description": raw.get("description") or "",
        "parameters": {
            "path": raw.get("pathParameters") or [],
            "query": raw.get("queryParameters") or [],
            "body": raw.get("requestBody") or [],
        },
        "responses": raw.get("responses") or [],
        "responseSample": raw.get("responseSample"),
        "source": {
            "file": source_path.name,
            "url": raw.get("sourceUrl"),
        },
    }


def import_docs(source_dir: Path, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    names: set[str] = set()

    for source_path in sorted(source_dir.glob("*.json")):
        raw = json.loads(source_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            continue

        manifest = endpoint_manifest(source_path, raw)
        if manifest is None:
            continue

        name = manifest["name"]
        if name in names:
            manifest["name"] = f"{name}_{snake_case(source_path.stem)}"
        names.add(manifest["name"])

        output_path = output_dir / source_path.name
        output_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(output_path)

    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Import UniFi endpoint docs into runtime skills.")
    parser.add_argument("--source", type=Path, default=Path("docs/network"))
    parser.add_argument("--output", type=Path, default=Path("skills/network"))
    args = parser.parse_args()

    written = import_docs(args.source, args.output)
    print(f"Wrote {len(written)} skill manifests to {args.output}")


if __name__ == "__main__":
    main()
