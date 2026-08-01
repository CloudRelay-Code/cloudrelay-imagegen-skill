#!/usr/bin/env python3
"""Persist the CloudRelay image API key in the Windows user environment."""

from __future__ import annotations

import argparse
import ctypes
import getpass
import os
import sys


ENV_NAME = "CLOUDRELAY_IMAGE_API_KEY"


def _configure_console_utf8() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, OSError):
            pass


def _read_key() -> str:
    key = getpass.getpass("CloudRelay image API key: ").strip()
    if not key:
        raise ValueError("No API key was provided.")
    if any(character.isspace() for character in key):
        raise ValueError("The API key must not contain whitespace.")
    return key


def _persist_windows_user_variable(key: str) -> None:
    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Environment") as registry_key:
        winreg.SetValueEx(registry_key, ENV_NAME, 0, winreg.REG_SZ, key)

    # Notify running applications that the user environment has changed.
    hwnd_broadcast = 0xFFFF
    wm_settingchange = 0x001A
    smto_abortifhung = 0x0002
    ctypes.windll.user32.SendMessageTimeoutW(
        hwnd_broadcast,
        wm_settingchange,
        0,
        "Environment",
        smto_abortifhung,
        5000,
        None,
    )


def main() -> int:
    _configure_console_utf8()
    parser = argparse.ArgumentParser(
        description=f"Save {ENV_NAME} as a persistent Windows user environment variable."
    )
    parser.parse_args()

    if os.name != "nt":
        parser.error("This configuration helper currently supports Windows only.")

    try:
        key = _read_key()
        _persist_windows_user_variable(key)
    except (OSError, ValueError) as error:
        print(f"Configuration failed: {error}", file=sys.stderr)
        return 1

    print(f"Configured the user environment variable {ENV_NAME}.")
    print("The key value was not displayed or written to the skill directory.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
