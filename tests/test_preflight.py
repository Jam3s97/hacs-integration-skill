"""Tests for hacs_preflight.py and the skill's own structure. Standard library only."""

from __future__ import annotations

import json
import re
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "skills" / "hacs-integration"
SCRIPT = SKILL / "scripts" / "hacs_preflight.py"

MIT = "MIT License\n\nCopyright (c) 2026 Example\n\n" + "Permission is hereby granted. " * 20

MANIFEST = {
    "domain": "awesome",
    "name": "Awesome",
    "codeowners": ["@example"],
    "config_flow": True,
    "documentation": "https://github.com/example/ha-awesome",
    "integration_type": "hub",
    "iot_class": "local_polling",
    "issue_tracker": "https://github.com/example/ha-awesome/issues",
    "requirements": ["awesome-client==1.0.0"],
    "version": "1.0.0",
}

WORKFLOW = """\
jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: home-assistant/actions/hassfest@master
      - uses: hacs/action@main
        with:
          category: integration
"""

EN = {
    "config": {
        "step": {"user": {"data": {"host": "Host"}}, "reauth_confirm": {"title": "Reauth"}},
        "abort": {"reauth_successful": "Done"},
    }
}


def png(width: int, height: int) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    raw = zlib.compress(b"".join(b"\0" + b"\0" * 4 * width for _ in range(height)))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", raw) + chunk(b"IEND", b"")


def make_repo(root: Path) -> Path:
    """Write a minimal integration repository that should pass cleanly."""
    integ = root / "custom_components" / "awesome"
    (integ / "translations").mkdir(parents=True)
    (integ / "brand").mkdir()
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / "tests").mkdir()
    (root / "scripts").mkdir()
    (root / "scripts" / "develop").write_text("#!/usr/bin/env bash\n")
    (root / "scripts" / "lint").write_text("#!/usr/bin/env bash\n")
    (root / ".devcontainer.json").write_text("{}")
    (root / ".ruff.toml").write_text("line-length = 100\n")
    (root / "hacs.json").write_text(
        json.dumps({"name": "Awesome", "homeassistant": "2026.3.0", "country": "NO"})
    )
    (root / "README.md").write_text("# Awesome\n\n" + "Install it from HACS and set it up. " * 20)
    (root / "LICENSE").write_text(MIT)
    (root / ".github" / "workflows" / "validate.yml").write_text(WORKFLOW)
    (integ / "manifest.json").write_text(json.dumps(MANIFEST, indent=2))
    (integ / "__init__.py").write_text('"""Awesome."""\n')
    (integ / "config_flow.py").write_text('"""Config flow."""\n')
    (integ / "translations" / "en.json").write_text(json.dumps(EN))
    (integ / "brand" / "icon.png").write_bytes(png(256, 256))
    return integ


def run(root: Path) -> tuple[int, str]:
    out = subprocess.run(
        [sys.executable, str(SCRIPT), str(root)], capture_output=True, text=True, check=False
    )
    return out.returncode, out.stdout + out.stderr


class PreflightTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name).resolve()
        self.integ = make_repo(self.root)

    def manifest(self, **changes: object) -> None:
        data = {**MANIFEST, **changes}
        data = {k: v for k, v in data.items() if v is not None}
        ordered = {k: data[k] for k in ("domain", "name") if k in data}
        ordered.update({k: data[k] for k in sorted(data) if k not in ordered})
        (self.integ / "manifest.json").write_text(json.dumps(ordered))

    def assert_flags(self, level: str, text: str) -> None:
        _, out = run(self.root)
        hits = [line for line in out.splitlines() if line.startswith(level) and text in line]
        self.assertTrue(hits, f"expected a {level} containing {text!r} in:\n{out}")

    def test_clean_repo_passes(self) -> None:
        code, out = run(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("0 error(s), 0 warning(s), 0 note(s)", out)

    def test_missing_hacs_json(self) -> None:
        (self.root / "hacs.json").unlink()
        code, _ = run(self.root)
        self.assertEqual(code, 1)
        self.assert_flags("ERROR", "hacs.json is missing")

    def test_unknown_hacs_json_key(self) -> None:
        (self.root / "hacs.json").write_text(json.dumps({"name": "A", "domains": ["sensor"]}))
        self.assert_flags("ERROR", "unsupported key `domains`")

    def test_missing_manifest_key(self) -> None:
        self.manifest(issue_tracker=None)
        self.assert_flags("ERROR", "required key `issue_tracker`")

    def test_unsorted_manifest(self) -> None:
        data = {"version": "1.0.0", **MANIFEST}
        (self.integ / "manifest.json").write_text(json.dumps(data))
        self.assert_flags("ERROR", "then alphabetical")

    def test_unpinned_requirement(self) -> None:
        self.manifest(requirements=["awesome-client>=1.0.0"])
        self.assert_flags("WARN", "not pinned")

    def test_ignore_in_workflow(self) -> None:
        wf = self.root / ".github" / "workflows" / "validate.yml"
        wf.write_text(WORKFLOW + "          ignore: brands\n")
        self.assert_flags("ERROR", "`ignore:`")

    def test_missing_brand_icon(self) -> None:
        (self.integ / "brand" / "icon.png").unlink()
        self.assert_flags("WARN", "brand/icon.png is missing")

    def test_non_square_icon(self) -> None:
        (self.integ / "brand" / "icon.png").write_bytes(png(256, 128))
        self.assert_flags("WARN", "must be square")

    def test_brand_needs_2026_3(self) -> None:
        (self.root / "hacs.json").write_text(
            json.dumps({"name": "Awesome", "homeassistant": "2025.1.0", "country": "NO"})
        )
        self.assert_flags("WARN", "2026.3.0")

    def test_missing_en_translation(self) -> None:
        (self.integ / "translations" / "en.json").rename(self.integ / "translations" / "de.json")
        self.assert_flags("ERROR", "translations/en.json is missing")

    def test_licence_wrong_name(self) -> None:
        (self.root / "LICENSE").rename(self.root / "LICENSE.txt")
        self.assert_flags("ERROR", "rename it to LICENSE")

    def test_licence_empty(self) -> None:
        (self.root / "LICENSE").write_text("")
        self.assert_flags("ERROR", "empty or truncated")

    def test_blueprint_leftovers(self) -> None:
        (self.integ / "const.py").write_text('DOMAIN = "integration_blueprint"\n')
        self.assert_flags("ERROR", "still reference `integration_blueprint`")

    def test_blocking_and_secret_patterns(self) -> None:
        (self.integ / "api.py").write_text(
            "import requests\n"
            "import time\n"
            'API_KEY = "abcdefghijklmnopqrstuvwxyz0123456789"\n'
            "def f():\n"
            "    time.sleep(1)\n"
            '    _LOGGER.info("Password=%s", password)\n'
        )
        self.assert_flags("WARN", "`requests`")
        self.assert_flags("WARN", "time.sleep()")
        self.assert_flags("WARN", "hardcoded credential")
        self.assert_flags("WARN", "include a credential")

    def test_auth_failed_without_reauth(self) -> None:
        (self.integ / "coordinator.py").write_text("raise ConfigEntryAuthFailed\n")
        self.assert_flags("WARN", "no async_step_reauth")

    def test_reauth_strings_missing(self) -> None:
        (self.integ / "config_flow.py").write_text("async def async_step_reauth(self): ...\n")
        (self.integ / "translations" / "en.json").write_text(json.dumps({"config": {}}))
        self.assert_flags("WARN", "`reauth_confirm`")

    def test_version_floor(self) -> None:
        (self.root / "hacs.json").write_text(
            json.dumps({"name": "Awesome", "homeassistant": "2024.1.0", "country": "NO"})
        )
        (self.integ / "brand" / "icon.png").unlink()
        (self.integ / "brand").rmdir()
        (self.integ / "http.py").write_text(
            "from homeassistant.components.http import StaticPathConfig\n"
        )
        self.assert_flags("WARN", "needs Home Assistant 2024.7")

    def test_undeclared_service(self) -> None:
        (self.integ / "services.yaml").write_text("do_thing:\n  name: Do thing\n")
        self.assert_flags("WARN", "declares `do_thing`")

    def test_inner_html(self) -> None:
        (self.integ / "card.js").write_text("el.innerHTML = `<b>${name}</b>`;\n")
        self.assert_flags("WARN", "innerHTML")

    def test_root_www(self) -> None:
        (self.root / "www").mkdir()
        (self.root / "www" / "card.js").write_text("// card\n")
        self.assert_flags("WARN", "www/ at the repository root")

    def test_no_dev_setup(self) -> None:
        (self.root / ".devcontainer.json").unlink()
        (self.root / ".ruff.toml").unlink()
        (self.root / "scripts" / "develop").unlink()
        (self.root / "scripts" / "lint").unlink()
        self.assert_flags("WARN", "ludeeus/integration_blueprint")

    def test_partial_dev_setup(self) -> None:
        (self.root / ".devcontainer.json").unlink()
        self.assert_flags("INFO", "missing a devcontainer")

    def test_two_integrations(self) -> None:
        (self.root / "custom_components" / "other").mkdir()
        self.assert_flags("ERROR", "more than one integration")


class PluginManifestTest(unittest.TestCase):
    def test_manifests_agree(self) -> None:
        plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertRegex(plugin["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertIn("owner", market)
        entries = {entry["name"]: entry for entry in market["plugins"]}
        self.assertIn(plugin["name"], entries)
        source = entries[plugin["name"]]["source"]
        self.assertTrue((REPO / source / "skills" / SKILL.name / "SKILL.md").is_file())


class SkillStructureTest(unittest.TestCase):
    def setUp(self) -> None:
        self.text = (SKILL / "SKILL.md").read_text(encoding="utf-8")

    def test_frontmatter(self) -> None:
        match = re.match(r"^---\n(.*?)\n---\n", self.text, re.S)
        self.assertIsNotNone(match, "SKILL.md must start with YAML frontmatter")
        front = dict(line.split(": ", 1) for line in match[1].splitlines())
        self.assertEqual(front["name"], SKILL.name)
        self.assertRegex(front["name"], r"^[a-z0-9]+(-[a-z0-9]+)*$")
        self.assertLessEqual(len(front["description"]), 1024)

    def test_body_length(self) -> None:
        self.assertLess(len(self.text.splitlines()), 500)

    def test_links_resolve(self) -> None:
        for path in [SKILL / "SKILL.md", *(SKILL / "references").glob("*.md"), REPO / "README.md"]:
            text = path.read_text(encoding="utf-8")
            for target in re.findall(r"\]\(([^)#\s]+)(?:#[^)]*)?\)", text):
                if "://" in target or target.startswith("mailto:"):
                    continue
                self.assertTrue(
                    (path.parent / target).exists(), f"{path.name}: broken link to {target}"
                )


if __name__ == "__main__":
    unittest.main()
