#!/usr/bin/env python3
"""Offline pre-flight check for a Home Assistant custom integration repository.

Mirrors the checks HACS runs (hacs/action and the hacs/default PR workflow) as
far as they can be evaluated from a local checkout, plus a few static scans for
problems that commonly surface in review. Standard library only.

Usage: hacs_preflight.py [path-to-repo]   (exit code 1 if any ERROR is found)

Not checked here (needs GitHub): repository description, topics, issues
enabled, licence detected by GitHub, not archived, a published release, and
whether the domain collides with a Home Assistant core integration.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

MANIFEST_REQUIRED = (
    "domain",
    "name",
    "codeowners",
    "documentation",
    "issue_tracker",
    "version",
)
HACS_JSON_KEYS = {
    "name",
    "content_in_root",
    "country",
    "filename",
    "hacs",
    "hide_default_branch",
    "homeassistant",
    "persistent_directory",
    "render_readme",
    "zip_release",
}
IOT_CLASSES = {
    "assumed_state",
    "calculated",
    "cloud_polling",
    "cloud_push",
    "local_polling",
    "local_push",
}
INTEGRATION_TYPES = {
    "device",
    "entity",
    "hardware",
    "helper",
    "hub",
    "service",
    "system",
    "virtual",
}
VERSION_RE = re.compile(r"^v?\d+(\.\d+){1,3}([.\-+]?[0-9A-Za-z.\-+]+)?$")
DOMAIN_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")

# (regex, level, message) scanned over every .py file in the integration.
CODE_PATTERNS = (
    (r"^\s*import requests\b|^\s*from requests\b", "WARN",
     "uses `requests` (blocking); use aiohttp via async_get_clientsession(hass) "
     "or wrap calls in hass.async_add_executor_job"),
    (r"\btime\.sleep\(", "WARN",
     "time.sleep() blocks the event loop; use `await asyncio.sleep()`"),
    (r"aiohttp\.ClientSession\(", "WARN",
     "creates its own aiohttp session; inject async_get_clientsession(hass) "
     "(or async_create_clientsession)"),
    (r"hass\.data\[DOMAIN\]|hass\.data\.setdefault\(DOMAIN", "INFO",
     "stores runtime objects in hass.data; prefer entry.runtime_data with a "
     "typed ConfigEntry alias"),
    (r"async_forward_entry_setup\(", "ERROR",
     "async_forward_entry_setup was removed; use `await "
     "hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`"),
    (r"async_get_event_loop\(\)|asyncio\.get_event_loop\(\)", "WARN",
     "asyncio.get_event_loop() in integration code; use hass.loop / "
     "hass.async_create_task"),
    (r"except\s*:\s*$|except Exception\s*:\s*\n\s*pass", "WARN",
     "bare/swallowed exception; catch specific errors and raise "
     "UpdateFailed / ConfigEntryNotReady / HomeAssistantError"),
    (r"\b(TEMP_CELSIUS|TEMP_FAHRENHEIT|ENERGY_KILO_WATT_HOUR|POWER_WATT|"
     r"DEVICE_CLASS_[A-Z_]+|STATE_CLASS_[A-Z_]+|SUPPORT_[A-Z_]+)\b", "WARN",
     "removed/deprecated constant; use the enum (UnitOfTemperature, "
     "SensorDeviceClass, SensorStateClass, <Domain>EntityFeature, ...)"),
    (r"^\s*async def async_setup_platform\(|^\s*def setup_platform\(", "INFO",
     "YAML platform setup; new integrations should be config-entry only"),
    (r"verify_ssl\s*=\s*False|ssl\s*=\s*False", "INFO",
     "TLS verification disabled; make sure this is opt-in and documented"),
    (r"(?i)^\s*\w*(api_?key|secret|token|password)\w*\s*=\s*[\"'][A-Za-z0-9_\-]{20,}[\"']", "WARN",
     "looks like a hardcoded credential; never ship shared keys, have each "
     "user supply their own"),
    (r"register_static_path\(", "WARN",
     "register_static_path is removed; use `await "
     "hass.http.async_register_static_paths([StaticPathConfig(...)])`"),
    (r"[\"']/local/|hass\.config\.path\(\s*[\"']www", "WARN",
     "copies/serves frontend files via config/www (/local/); serve them from "
     "the integration directory instead"),
    (r"https?://[^\s\"']*(cdn\.jsdelivr|unpkg\.com|cdnjs)[^\s\"']*\.js", "WARN",
     "loads JavaScript from a CDN at runtime; ship frontend code in the release"),
    (r"https?://[^\s\"']*\b(dev|staging|sandbox|test)\b[.\-][^\s\"']*", "INFO",
     "URL looks like a development/staging host; use the production endpoint"),
    (r"automations\.yaml|scripts\.yaml|scenes\.yaml|configuration\.yaml", "INFO",
     "touches the user's YAML configuration files; integrations should not "
     "rewrite user config"),
    (r"_LOGGER\.(info|warning|error)\(f[\"']", "INFO",
     "f-string in log call; use lazy %s formatting"),
)

results: list[tuple[str, str]] = []


def report(level: str, msg: str) -> None:
    results.append((level, msg))


def load_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        report("ERROR", f"{path}: not valid JSON ({err})")
        return None
    if not isinstance(data, dict):
        report("ERROR", f"{path}: top level must be an object")
        return None
    return data


def check_hacs_json(root: Path) -> dict:
    path = root / "hacs.json"
    if not path.is_file():
        report("ERROR", "hacs.json is missing from the repository root")
        return {}
    data = load_json(path) or {}
    if not isinstance(data.get("name"), str) or not data.get("name"):
        report("ERROR", "hacs.json: `name` (string) is required")
    for key in sorted(set(data) - HACS_JSON_KEYS):
        report("ERROR", f"hacs.json: unsupported key `{key}`")
    if data.get("zip_release") and not data.get("filename"):
        report("ERROR", "hacs.json: zip_release is true but `filename` is not set")
    if "render_readme" in data:
        report("INFO", "hacs.json: `render_readme` is obsolete in HACS 2; remove it")
    if "country" not in data:
        report("INFO", "hacs.json: set `country` if the integration only serves "
                       "specific countries (ISO 3166-1 alpha-2)")
    return data


def find_integration(root: Path, hacs: dict) -> Path | None:
    if hacs.get("content_in_root"):
        return root
    base = root / "custom_components"
    if not base.is_dir():
        report("ERROR", "custom_components/ directory is missing (HACS expects "
                        "custom_components/<domain>/ unless content_in_root)")
        return None
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith((".", "__")))
    if not dirs:
        report("ERROR", "custom_components/ contains no integration directory")
        return None
    if len(dirs) > 1:
        names = ", ".join(p.name for p in dirs)
        report("ERROR", f"more than one integration in custom_components/ ({names}); "
                        "HACS manages one integration per repository")
    return dirs[0]


def check_manifest(integ: Path) -> dict:
    path = integ / "manifest.json"
    if not path.is_file():
        report("ERROR", f"{path}: manifest.json is missing")
        return {}
    data = load_json(path) or {}
    for key in MANIFEST_REQUIRED:
        if key not in data:
            report("ERROR", f"manifest.json: required key `{key}` is missing")
    domain = data.get("domain", "")
    if domain and not DOMAIN_RE.match(domain):
        report("ERROR", f"manifest.json: domain `{domain}` must be lowercase "
                        "letters, digits and underscores")
    if domain and domain != integ.name and integ.parent.name == "custom_components":
        report("ERROR", f"manifest.json: domain `{domain}` does not match "
                            f"directory name `{integ.name}`")
    for key in ("documentation", "issue_tracker"):
        value = data.get(key)
        if value is not None and not re.match(r"^https?://\S+$", str(value)):
            report("ERROR", f"manifest.json: `{key}` must be a URL")
        if value and "integration_blueprint" in str(value):
            report("ERROR", f"manifest.json: `{key}` still points at the blueprint")
    owners = data.get("codeowners")
    if owners is not None and (not isinstance(owners, list) or not owners):
        report("ERROR", "manifest.json: `codeowners` must be a non-empty list")
    elif owners and any(not str(o).startswith("@") for o in owners):
        report("ERROR", "manifest.json: codeowners must be GitHub handles starting with @")
    version = data.get("version")
    if version is not None and not VERSION_RE.match(str(version)):
        report("ERROR", f"manifest.json: version `{version}` is not a valid "
                        "SemVer/CalVer string (AwesomeVersion)")
    if "iot_class" not in data:
        report("WARN", "manifest.json: `iot_class` is missing (hassfest requires it)")
    elif data["iot_class"] not in IOT_CLASSES:
        report("ERROR", f"manifest.json: invalid iot_class `{data['iot_class']}`")
    if "integration_type" not in data:
        report("WARN", "manifest.json: set `integration_type` explicitly "
                       "(defaults to hub)")
    elif data["integration_type"] not in INTEGRATION_TYPES:
        report("ERROR", f"manifest.json: invalid integration_type "
                        f"`{data['integration_type']}`")
    if data.get("config_flow") and not (integ / "config_flow.py").is_file():
        report("ERROR", "manifest.json: config_flow is true but config_flow.py is missing")
    if not data.get("config_flow"):
        report("WARN", "no config flow; UI setup is the expected baseline")
    for req in data.get("requirements", []):
        if "==" not in req and "@" not in req:
            report("WARN", f"manifest.json: requirement `{req}` is not pinned (use ==)")
    keys = list(data)
    expected = [k for k in ("domain", "name") if k in data] + sorted(
        k for k in keys if k not in ("domain", "name"))
    if keys != expected:
        report("ERROR", "manifest.json: keys must be `domain`, `name`, then "
                        "alphabetical (hassfest fails otherwise)")
    return data


def check_brand(integ: Path) -> None:
    icon = integ / "brand" / "icon.png"
    if icon.is_file():
        try:
            head = icon.read_bytes()[:24]
            if head[:8] != b"\x89PNG\r\n\x1a\n":
                report("ERROR", "brand/icon.png is not a PNG file")
            else:
                w, h = int.from_bytes(head[16:20], "big"), int.from_bytes(head[20:24], "big")
                if w != h:
                    report("WARN", f"brand/icon.png is {w}x{h}; icons must be square "
                                   "(256x256, with icon@2x.png at 512x512)")
        except OSError as err:
            report("ERROR", f"brand/icon.png unreadable: {err}")
    else:
        report("WARN", f"{integ.name}/brand/icon.png is missing; the HACS `brands` "
                       "check then only passes if the domain is already in "
                       "home-assistant/brands")


def check_translations(integ: Path, manifest: dict) -> None:
    en = integ / "translations" / "en.json"
    others = (integ / "translations").is_dir() and any((integ / "translations").glob("*.json"))
    if not manifest.get("config_flow") and not others:
        return
    strings = integ / "strings.json"
    if not en.is_file():
        hint = " (strings.json alone is not loaded for custom integrations)" if strings.is_file() else ""
        report("ERROR", f"translations/en.json is missing{hint}")
    else:
        load_json(en)


def check_extras(root: Path, integ: Path, hacs: dict, manifest: dict) -> None:
    """Checks drawn from recurring hacs/default review feedback."""
    for name in ("www", "dist"):
        if (root / name).is_dir() and any((root / name).rglob("*.js")):
            report("WARN", f"{name}/ at the repository root contains JS; HACS only "
                           "installs custom_components/<domain>/, so bundle frontend "
                           "files inside the integration and register them with "
                           "async_register_static_paths")
    floor = str(hacs.get("homeassistant", ""))
    match = re.match(r"^(\d{4})\.(\d{1,2})", floor)
    if (integ / "brand").is_dir() and (not match or (int(match[1]), int(match[2])) < (2026, 3)):
        report("WARN", "local brand/ images are only served from Home Assistant "
                       "2026.3.0; set hacs.json `homeassistant` to 2026.3.0 or later")
    version = str(manifest.get("version", ""))
    if re.search(r"(a|b|rc|alpha|beta|dev)\d*$", version, re.I):
        report("WARN", f"manifest.json: version `{version}` is a pre-release; "
                       "the release submitted to hacs/default should be a stable one")
    try:
        import subprocess
        tag = subprocess.run(["git", "-C", str(root), "describe", "--tags", "--abbrev=0"],
                             capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        tag = ""
    if tag and version and tag.lstrip("vV.") != version.lstrip("vV."):
        report("WARN", f"manifest.json version `{version}` does not match the latest "
                       f"git tag `{tag}`; bump the manifest before tagging a release")


def check_workflows(root: Path) -> None:
    wf_dir = root / ".github" / "workflows"
    text = ""
    if wf_dir.is_dir():
        text = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                         for p in wf_dir.iterdir() if p.suffix in (".yml", ".yaml"))
    if "hacs/action" not in text:
        report("ERROR", "no workflow runs hacs/action (required for default inclusion)")
    elif re.search(r"^\s*ignore\s*:", text, re.M):
        report("ERROR", "hacs/action is configured with `ignore:`; all checks must "
                        "pass with nothing ignored before submitting to hacs/default")
    if "hassfest" not in text:
        report("ERROR", "no workflow runs hassfest (home-assistant/actions/hassfest)")
    if text and "category" in text and not re.search(r"category:\s*[\"']?integration", text):
        report("WARN", "hacs/action `category` should be `integration`")


def check_repo_files(root: Path) -> None:
    if not any((root / n).is_file() for n in ("README.md", "README", "readme.md", "README.rst")):
        report("ERROR", "README is missing")
    else:
        readme = next(p for p in root.iterdir() if p.name.lower().startswith("readme"))
        body = readme.read_text(encoding="utf-8", errors="replace")
        if len(body) < 400:
            report("WARN", "README is very short; document install, setup and entities")
        if "blueprint" in body.lower() and "integration_blueprint" in body:
            report("ERROR", "README still contains blueprint template text")
    if not any((root / n).is_file() for n in ("LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING")):
        report("ERROR", "LICENSE file is missing (must be an OSI-approved licence "
                        "GitHub can identify)")


def scan_code(integ: Path) -> None:
    leftovers = 0
    for path in sorted(integ.rglob("*.py")):
        rel = path.relative_to(integ)
        text = path.read_text(encoding="utf-8", errors="replace")
        if "integration_blueprint" in text or "IntegrationBlueprint" in text:
            leftovers += 1
        for pattern, level, msg in CODE_PATTERNS:
            match = re.search(pattern, text, re.M)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                report(level, f"{rel}:{line}: {msg}")
    if leftovers:
        report("ERROR", f"{leftovers} file(s) still reference `integration_blueprint`; "
                        "finish renaming the template")
    if not (integ.parent.parent / "tests").is_dir() and not (integ / "tests").is_dir():
        report("INFO", "no tests/ directory; add at least config-flow tests "
                       "(pytest-homeassistant-custom-component)")


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"not a directory: {root}")
        return 2
    hacs = check_hacs_json(root)
    check_repo_files(root)
    check_workflows(root)
    integ = find_integration(root, hacs)
    if integ:
        manifest = check_manifest(integ)
        check_brand(integ)
        check_translations(integ, manifest)
        check_extras(root, integ, hacs, manifest)
        scan_code(integ)

    order = {"ERROR": 0, "WARN": 1, "INFO": 2}
    for level, msg in sorted(results, key=lambda r: order[r[0]]):
        print(f"{level:5} {msg}")
    counts = {k: sum(1 for lvl, _ in results if lvl == k) for k in order}
    print(f"\n{counts['ERROR']} error(s), {counts['WARN']} warning(s), {counts['INFO']} note(s)")
    print("Not checked locally: repo description, topics, issues enabled, GitHub-detected "
          "licence, release published, core-domain conflict.")
    return 1 if counts["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
