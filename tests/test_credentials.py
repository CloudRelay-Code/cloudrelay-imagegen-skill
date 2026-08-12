from __future__ import annotations

from pathlib import Path
import os
import stat
import tempfile
import unittest
from unittest import mock

from scripts import configure_api_key
from scripts import generate_image


class CredentialTests(unittest.TestCase):
    def test_key_validation_trims_outer_whitespace(self) -> None:
        self.assertEqual(configure_api_key._validate_key("  test-key-value\n"), "test-key-value")

    def test_key_validation_rejects_internal_whitespace(self) -> None:
        with self.assertRaisesRegex(ValueError, "must not contain whitespace"):
            configure_api_key._validate_key("test key value")

    def test_key_stdin_reader_does_not_use_command_line_arguments(self) -> None:
        with mock.patch.object(configure_api_key.sys, "stdin") as stdin:
            stdin.read.return_value = "test-key-value\n"
            self.assertEqual(configure_api_key._read_key_from_stdin(), "test-key-value")

    def test_posix_persistence_writes_outside_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_file = Path(temporary) / "cloudrelay" / "imagegen-api-key"
            with mock.patch.object(
                configure_api_key,
                "_secret_file",
                return_value=secret_file,
            ):
                result = configure_api_key._persist_posix_secret_file("test-key-value")
            self.assertEqual(result, secret_file)
            self.assertEqual(secret_file.read_text(encoding="utf-8"), "test-key-value\n")
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(secret_file.stat().st_mode), 0o600)
                self.assertEqual(stat.S_IMODE(secret_file.parent.stat().st_mode), 0o700)

    def test_generator_reads_xdg_secret_file(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_file = Path(temporary) / "cloudrelay" / "imagegen-api-key"
            secret_file.parent.mkdir(parents=True)
            secret_file.write_text("test-key-value\n", encoding="utf-8")
            with mock.patch.dict(
                generate_image.os.environ,
                {"XDG_CONFIG_HOME": temporary},
                clear=False,
            ):
                self.assertEqual(
                    generate_image._read_posix_secret_file(),
                    "test-key-value",
                )

    def test_empty_secret_file_is_treated_as_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            secret_file = Path(temporary) / "cloudrelay" / "imagegen-api-key"
            secret_file.parent.mkdir(parents=True)
            secret_file.write_text("\n", encoding="utf-8")
            with mock.patch.dict(
                generate_image.os.environ,
                {"XDG_CONFIG_HOME": temporary},
                clear=False,
            ):
                self.assertIsNone(generate_image._read_posix_secret_file())


if __name__ == "__main__":
    unittest.main()
