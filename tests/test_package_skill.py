from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
import zipfile

from tools import package_skill


class PackageSkillTests(unittest.TestCase):
    def test_package_contains_only_runtime_files_at_archive_root(self) -> None:
        repository = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as temporary:
            output = package_skill.build_package(repository, Path(temporary))
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(
                    set(archive.namelist()),
                    {path.as_posix() for path in package_skill.PACKAGE_FILES},
                )
                self.assertTrue(archive.read("SKILL.md").startswith(b"---\n"))


if __name__ == "__main__":
    unittest.main()
