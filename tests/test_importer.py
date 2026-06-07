from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from scripts.import_unifi_docs import endpoint_manifest, import_docs
from tests.helpers import DOCS


def endpoint_docs() -> list[tuple[Path, dict]]:
    endpoints: list[tuple[Path, dict]] = []
    for path in sorted(DOCS.glob("*.json")):
        raw = json.loads(path.read_text())
        if isinstance(raw, dict) and endpoint_manifest(path, raw) is not None:
            endpoints.append((path, raw))
    return endpoints


def non_endpoint_docs() -> list[Path]:
    ignored: list[Path] = []
    for path in sorted(DOCS.glob("*.json")):
        raw = json.loads(path.read_text())
        if not isinstance(raw, dict) or endpoint_manifest(path, raw) is None:
            ignored.append(path)
    return ignored


def test_importer_writes_only_endpoint_manifests(tmp_path: Path) -> None:
    output = tmp_path / "skills"

    written = import_docs(DOCS, output)

    assert len(written) == len(endpoint_docs())
    for path in non_endpoint_docs():
        assert not (output / path.name).exists()

    counts = Counter(json.loads(path.read_text())["method"] for path in written)
    expected_counts = Counter(raw["method"] for _, raw in endpoint_docs())
    assert counts == expected_counts


def test_importer_preserves_endpoint_fields(tmp_path: Path) -> None:
    output = tmp_path / "skills"

    import_docs(DOCS, output)

    for source_path, source in endpoint_docs():
        manifest = json.loads((output / source_path.name).read_text())

        assert manifest["parameters"]["path"] == source["pathParameters"]
        assert manifest["parameters"]["query"] == source["queryParameters"]
        assert manifest["parameters"]["body"] == source["requestBody"]
        assert manifest["responses"] == source["responses"]
        assert manifest["responseSample"] == source["responseSample"]
        assert manifest["source"]["url"] == source["sourceUrl"]
