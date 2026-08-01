from __future__ import annotations

from pathlib import Path
import unittest

import yaml


class SkillContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = Path(__file__).resolve().parent.parent
        text = (cls.repository / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            raise AssertionError("SKILL.md must start with YAML frontmatter")
        _, frontmatter, cls.body = text.split("---", 2)
        cls.metadata = yaml.safe_load(frontmatter)

    def test_frontmatter_uses_portable_fields_only(self) -> None:
        self.assertEqual(set(self.metadata), {"name", "description"})
        self.assertEqual(self.metadata["name"], "cloudrelay-imagegen")
        self.assertIsInstance(self.metadata["description"], str)
        self.assertIn("CloudRelay", self.metadata["description"])

    def test_runtime_files_exist(self) -> None:
        for relative_path in (
            "scripts/configure_api_key.py",
            "scripts/generate_image.py",
            "agents/openai.yaml",
        ):
            with self.subTest(path=relative_path):
                self.assertTrue((self.repository / relative_path).is_file())

    def test_openai_metadata_is_valid(self) -> None:
        metadata = yaml.safe_load(
            (self.repository / "agents/openai.yaml").read_text(encoding="utf-8")
        )
        prompt = metadata["interface"]["default_prompt"]
        self.assertIn("$cloudrelay-imagegen", prompt)


if __name__ == "__main__":
    unittest.main()
