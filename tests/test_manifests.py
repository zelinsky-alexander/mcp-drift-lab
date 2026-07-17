from pathlib import Path

from mcp_drift_lab.manifests import TAG_END, TAG_START, ManifestStore

ROOT = Path(__file__).resolve().parents[1]


def test_all_manifests_load_and_have_unique_ids() -> None:
    store = ManifestStore(ROOT)
    loaded = [store.load(name) for name in store.list_manifests()]
    assert len(loaded) == 6
    assert len({item.raw["id"] for item in loaded}) == len(loaded)


def test_behavior_only_has_same_toolset_as_baseline() -> None:
    store = ManifestStore(ROOT)
    baseline = store.load("v0-benign.json")
    behavior_only = store.load("v5-behavior-only.json")
    assert baseline.toolset_hash == behavior_only.toolset_hash
    assert baseline.manifest_hash != behavior_only.manifest_hash


def test_unicode_manifest_materializes_tag_block() -> None:
    store = ManifestStore(ROOT)
    loaded = store.load("v4-unicode-tag-concealment.json")
    description = loaded.tools[0]["description"]
    assert TAG_START in description
    assert TAG_END in description
    assert "x-lab-tag-payload" not in loaded.tools[0]


def test_schema_mutation_changes_toolset_hash() -> None:
    store = ManifestStore(ROOT)
    baseline = store.load("v0-benign.json")
    changed = store.load("v2-schema-mutation.json")
    assert baseline.toolset_hash != changed.toolset_hash
