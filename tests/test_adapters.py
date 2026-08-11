from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from tools import sync_adapters


class AdapterTests(unittest.TestCase):
    def test_adapter_manifests_and_copies_match_root_version(self) -> None:
        root = Path(__file__).resolve().parent.parent
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        for adapter in sync_adapters.ADAPTERS:
            adapter_root = root / adapter
            manifest_name = ".codex-plugin/plugin.json" if adapter.name == "codex" else ".claude-plugin/plugin.json"
            manifest = json.loads((adapter_root / manifest_name).read_text(encoding="utf-8"))
            self.assertEqual(manifest["version"], version)
            for relative in sync_adapters.MANAGED_FILES:
                source = root / relative
                copy = adapter_root / "skills" / sync_adapters.SKILL_NAME / relative
                self.assertEqual(
                    hashlib.sha256(source.read_bytes()).digest(),
                    hashlib.sha256(copy.read_bytes()).digest(),
                    f"adapter drift: {adapter}/{relative}",
                )

    def test_sync_rejects_symlinked_source(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for relative in sync_adapters.MANAGED_FILES:
                source = root / relative
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("managed", encoding="utf-8")
            outside = root / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            linked_source = root / "SKILL.md"
            linked_source.unlink()
            try:
                os.symlink(outside, linked_source)
            except (NotImplementedError, OSError) as error:
                self.skipTest(f"symlink creation is unavailable: {error}")

            original_root = sync_adapters.REPOSITORY_ROOT
            sync_adapters.REPOSITORY_ROOT = root
            try:
                with self.assertRaises((FileNotFoundError, RuntimeError)):
                    sync_adapters.sync_adapter(Path("adapters/codex"))
            finally:
                sync_adapters.REPOSITORY_ROOT = original_root


if __name__ == "__main__":
    unittest.main()
