"""Check the plugin version and the changelog stay in step."""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


class VersionTest(unittest.TestCase):
    def test_changelog_matches_manifest(self) -> None:
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        version = manifest["version"]
        self.assertRegex(version, r"^\d+\.\d+\.\d+$")

        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        sections = re.findall(
            r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$", changelog, re.MULTILINE
        )
        self.assertTrue(sections, "CHANGELOG.md has no version sections")
        self.assertEqual(
            sections[0],
            version,
            "The newest CHANGELOG.md section must match plugin.json's version",
        )


if __name__ == "__main__":
    unittest.main()
