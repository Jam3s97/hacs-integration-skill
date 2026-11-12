# Changelog

Changes to the skill that users receive. The version is the one in
`.claude-plugin/plugin.json`; plugin installs only update when it changes.

## [0.2.2] - 2026-11-12

### Added

- Create mode works out the integration's type before any code is written:
  local or cloud, polling or push, how the user signs in, Bluetooth,
  discovery, device, hub or service, and whether it needs subentries.
- Build mode ends with a checklist to run before a change is called done.
- `references/ha-best-practices.md` has new sections, from the Home Assistant
  developer docs, on OAuth 2.0 with application credentials, config
  subentries, and Bluetooth devices, plus rules on timezone-aware times and
  JSON-serialisable attributes.

## [0.2.1] - 2026-11-12

### Added

- `references/ha-best-practices.md` now carries the rules from Home
  Assistant core's own agent guidance (`ha-integration-knowledge` and
  `AGENTS.md`) that apply to custom integrations: config-flow error logging,
  entity availability and lifecycle, action enums and admin-only actions,
  exception handling and validation, repair issue content and severity,
  testing practice, and the legacy device tracker removal in 2027.5.

### Changed

- `SKILL.md` explains that core's guidance only loads inside a core checkout
  and which parts of it do not apply to custom integrations.

## [0.2.0] - 2026-11-12

### Changed

- Renamed the skill to `marketplace-integration` and updated it for the Home
  Assistant Marketplace (formerly HACS). The command is now
  `/marketplace-integration`.

## [0.1.2] - 2026-11-12

### Fixed

- Gaps found in a test run of the Create workflow.

## [0.1.1] - 2026-11-11

### Changed

- The integration blueprint is mandatory in the Create workflow.

## [0.1.0] - 2026-11-11

### Added

- Plugin and marketplace manifests for installing with `/plugin`.
- Tests and CI for the pre-flight script.
