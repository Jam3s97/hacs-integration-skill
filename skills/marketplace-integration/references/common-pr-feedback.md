# What gets hacs/default submissions closed or sent back

Compiled in November 2026 from closed pull requests in
<https://github.com/hacs/default>, the catalog behind the Home Assistant
Marketplace (formerly the HACS default store): search counts across the closed PRs, and a
close reading of the maintainer and bot comments on 48 closed integration
submissions from 2025–2026. Roughly one in four integration submissions closed since
mid-2026 was closed unmerged, and many of those were resubmitted, which resets
a wait measured in months. Use this file as a review checklist: every item is
something a real submission was stopped for. For the code-level findings on
submissions that went on to be merged, and how to answer a review, see
`review-rounds.md`.

Review today is more than the automated checks. Maintainers read the
integration's code and its latest **release**, so code-level problems block
inclusion just as a failed check does.

## Contents

- [1. PR hygiene (caught by bots)](#1-pr-hygiene-caught-by-bots)
- [2. Eligibility and identity](#2-eligibility-and-identity)
- [3. Release and manifest consistency](#3-release-and-manifest-consistency)
- [4. Brands](#4-brands)
- [5. Code problems reviewers flag](#5-code-problems-reviewers-flag)
- [6. Security findings](#6-security-findings)
- [7. Overreach](#7-overreach)
- [8. Bundled frontend](#8-bundled-frontend)
- [9. Process mistakes](#9-process-mistakes)
- [Pre-submission checklist](#pre-submission-checklist)

## 1. PR hygiene (caught by bots)

| Feedback | Fix |
| --- | --- |
| "Your branch seems out of date. Please update your branch with the latest changes from the base branch." / merge conflict on the `integration` file | Merge or rebase `hacs/default` `master` into the PR branch. Expect to do this more than once during the wait. |
| "a store addition should always be `+1/-0`" | After resolving a conflict, check the Files tab shows one added line and nothing removed. A sloppy rebase that deletes a neighbour's entry is rejected. |
| "Limit your PR to a single repository change." | One repository per PR; do not batch your integrations. Also triggered by a rebase that drags other entries into the diff. |
| "Add required repository links to the PR description… Found 1 link(s), but 3 are required for integration repositories." | Release link, HACS action run link, hassfest run link, all three, in the template's Links section. **The single most common bot closure in the sample (9 of 48).** The bot closes the PR rather than waiting, and it re-checks after review rounds, so do not trim the links when editing the description. |
| "Remove "HACS" from your repository name." | Rename the repository (e.g. `ha-foo`, not `hacs-foo`), then update the submitted line to the new exact name. |
| PR auto-closed for a missing or altered template | Keep the template's headings and checklist intact; fill it in rather than replacing it. When creating the PR by API or CLI, check the body rendered properly (one submission had literal `\n` sequences). Use a new branch name for a resubmission. |
| "The submitted name … does not match what GitHub returns for the repository" | Use the exact case of `owner/repo` as GitHub displays it. |
| Entry appended at the end / file not sorted / an unrelated entry moved | Insert one line alphabetically (case-insensitive); touch nothing else. |
| "The PR is not editable by HACS maintainers" | Fork from a personal account and leave "Allow edits by maintainers" ticked. |
| Stale: "Because there hasn't been any activity on this PR for quite some time now, I've decided to close it for being stale." | Respond to review within a few weeks. After fixing, mark the PR ready for review; a silent fix in your own repo is invisible. |

Old "changes requested" reviews from the bot can linger after a rebase.
Opening a fresh PR is what authors usually end up doing; it is cleaner to
keep the branch current so the reviews never appear.

## 2. Eligibility and identity

- **Domain collisions.** "Two integrations cannot share a domain";
  Home Assistant loads one integration per domain, so a domain already used by
  another repository in the default store is a hard block, even if that
  repository is abandoned. Before submitting, search the
  default list (`https://data-v2.hacs.xyz/integration/data.json`) and core for
  the domain. Fix: pick a unique domain (rename directory, manifest, `DOMAIN`,
  translations, services), release, and open a new PR. Taking over an
  abandoned entry requires its removal first, via an issue on
  `hacs/integration`.
- **Duplicates of existing work.** The most common maintainer close reason in
  the sample (7 of the 28 most recent closures read). Not accepted: an integration for devices or a
  service already covered by a core integration ("this is a duplicate of a
  core integration for the catalog"); a fork or
  derivative of an integration already in the default store; a
  second implementation of the same protocol or API as an existing default; add-on quirks or patches for a core integration. The advice each time was to contribute upstream. Before
  building, search core and the HACS store for the device, brand and API,
  and be ready to say in the README what this integration does that the
  existing one cannot.
- **Core overlap.** Alpha/beta builds of core integrations, and integrations
  that override a core domain, are not accepted as defaults. They stay
  custom repositories. Core also gains integrations: a domain that was free
  when you started can collide after a Home Assistant release.
- **Archived or unreachable repository** at review time.
- **Out of scope.** An alternative store installing code from other forges
  was declined as something the default catalog cannot take.
- **Unobtainable prerequisites.** Setup needing vendor keys ordinary users
  cannot get; a documented, authorised route was requested.
- **Not functional yet.** "The integration as released does not create
  anything in Home Assistant yet": an entry that sets up no entities,
  services or other user-visible function is not ready. "The default catalog
  is meant for repositories that are functional for the people who install
  them from the store."
- **Approach.** An integration whose core idea is rewriting the user's
  configuration files or driving non-public Home Assistant internals was
  closed on approach, not code quality.
- **Ownership.** Submitter must be the owner or a major contributor.
- **Duplicates.** Repository already in HACS, or a second PR opened for the
  same repository while one is open. Keep one PR.
- **Licence.** "This needs a `LICENSE` file (or `LICENSE.md`) at the
  repository root"; it must be an OSI licence GitHub recognises.
- **Provenance.** A fork of an unlicensed upstream cannot simply add MIT:
  the licence was "not theirs to grant". Reverse-engineered code
  documented as derived from a private vendor binary raised IP questions. Get upstream's agreement or be able to state it is a clean
  rewrite.

## 3. Release and manifest consistency

Reviewers inspect the latest release, not the default branch.

- `manifest.json` `version` differs from the release tag (1.1.0 vs v1.1.1;
  "0.1.0" vs `v.1.0.3`). Bump the manifest, then tag.
- Pre-release version string on a normal release (`1.3.0-beta` on a
  non-prerelease tag). Either mark the GitHub release as a
  pre-release or use a stable version.
- **Replacing or moving git tags.** "Replacing existing ones is a way to hide
  things and makes versions unstable.". This got submissions
  refused outright. Never delete and recreate a tag or release; publish a new
  version number.
- No `translations/en.json` in the release (only `de.json`, or only
  `strings.json`).
- `hacs.json` `homeassistant` minimum lower than the APIs the code uses
  (options-flow changes need 2024.12; `StaticPathConfig` needs 2024.7; local
  `brand/` needs 2026.3). Raise the floor to the oldest
  release the code really runs on.
- `documentation` / `issue_tracker` pointing at another repository, a
  misspelt owner, or the blueprint.
- `codeowners` naming a GitHub account that does not exist.
- Missing `integration_type`.
- hassfest: "Using component http but it's not in 'dependencies' or
  'after_dependencies'". Any core component the code imports or
  uses (`http`, `frontend`, `websocket_api`, `bluetooth`, `mqtt`…) must be
  listed in `dependencies` or `after_dependencies`.
- A requirement declared in `manifest.json` but never imported, or
  the reverse.
- Fix pushed to the branch but no new release cut: the checks and the
  reviewer still see the old release.

## 4. Brands

"Actions are still failing" on the `brands` check was a routine close reason
while assets had to be merged into home-assistant/brands first.
Still seen: no `brand/` directory in the release, and
`ignore: brands` left in the workflow from the blueprint.
Today: put `icon.png` (256×256) and `icon@2x.png` (512×512) in
`custom_components/<domain>/brand/`, set
`hacs.json` `homeassistant` to `2026.3.0` or later (older Home Assistant
versions do not serve in-tree images), remove `ignore: brands`,
release.

## 5. Code problems reviewers flag

- **Blocking I/O on the event loop**: file reads/writes, ARP table reads,
  parsing a multi-megabyte XML file every hour.
  "Run it in the executor instead:
  `await self.hass.async_add_executor_job(read_local_arp)`".
- Less obvious blocking calls: constructing `ZoneInfo(name)` reads tzdata
  from disk; use `await dt_util.async_get_time_zone(name)`.
  Re-compressing archives on the loop.
- **Config flow and setup disagree**: an options flow saves host/port to
  `entry.options` while setup reads only `entry.data`, so changes never
  apply. Read options first with a fallback to data, or update
  `entry.data` via a reconfigure flow.
- **Advertised features without an implementation**:
  `CoverEntityFeature.SET_POSITION` with no `async_set_cover_position`. Only set feature flags for methods that exist.
- **Unhandled `None`**: `async_turn_on` without `rgb_color` passing `None`
  into the device call and raising `TypeError`. Fall back to the
  last known value.
- **Unverified writes to hardware**: enum values and setpoints marked
  "TODO verify", emergency-stop switches never tested. "Writing unconfirmed
  values to a physical heat pump is not something we can ship."
  Ship only controls that have been tested on a real device; leave the rest
  out or read-only.
- Logging calls whose placeholders and arguments do not match.
- **Code that cannot work**: a service that "raises `NameError` on every
  call"; service fields documented in `services.yaml` but rejected by
  the schema with "extra keys not allowed". Exercise every service and every
  config-flow path once before releasing.
- **Unguarded `entry.runtime_data` access** from services or websocket
  handlers when the entry is not loaded.
- **Aggressive polling** such as a 5-second loop against a vendor cloud.
- **Services that should return data** but only fire events or log: use
  `supports_response`.
- **Private or internal APIs** of Home Assistant used instead of public
  helpers.
- Duplicate or leftover files in the release (repeated images, unused
  modules).
- README leading with manual "add custom repository" steps; once in the
  default store "users can just search for it in HACS, so please lead with
  that" (non-blocking).

## 6. Security findings

- **Shared credentials in source**: "ships a hardcoded, shared TMDB API key
  baked into the source for everyone… have each user supply their own".
- **Password shown in clear** in the config flow; use a password selector.
- **Vendor development/staging host** hardcoded as the API URL.
- **Unescaped values in bundled card HTML** (XSS): names, attributes, card
  config, colours, sizes, `id` attributes, formatted dates all need escaping. This took three or four review rounds each time because
  authors fixed only the lines quoted; audit every `innerHTML` and template
  literal in one pass.
- **WebSocket commands without an admin check**: add
  `@websocket_api.require_admin` and validate inputs (e.g.
  `ipaddress.ip_address()`).
- Service inputs such as `color` and `icon` not validated in the schema.
- **Credentials sent to the wrong host**: an `Authorization` header attached
  to whatever URL a response links to. Send tokens only to the
  host they belong to.
- **Unencrypted transport** (weakly hashed password, cleartext streams) not
  disclosed; reviewers asked for a plain statement in the README.
- Telemetry must be opt-in and documented.

## 7. Overreach

- Writing to device or entity registry entries owned by other integrations:
  "Please limit registry writes to devices and entities this integration
  created."
- Reading another integration's stored tokens: "Please only read and write
  your own `.storage/<domain>/` path."
- Removing or replacing Lovelace resources it did not create: "leave
  resources you did not create alone and keep everything under your own
  … namespace."
- Rewriting `automations.yaml`, `scripts.yaml`, `scenes.yaml` or stored
  dashboards.
- Deleting, hiding or migrating entities that belong to a core integration,
  or monkey-patching its classes process-wide.
- Cleanup code that deletes entities by a broad pattern rather than by its
  own config entry.

## 8. Bundled frontend

- Cards kept in `www/` at the repository root never reach users: "HACS only
  installs files under `custom_components/<domain>/` for integration
  entries". Bundle them in the integration and register with
  `async_register_static_paths` + `add_extra_js_url`.
- Loading the card from a CDN: "Code that runs in the user's frontend should
  ship in the release and be served locally."
- Copying the card into `config/www/` and registering a `/local/` resource:
  "drop the copy and the `/local/` registration."

## 9. Process mistakes

- Requesting a review, pinging maintainers, or "please recheck" comments.
  The template warns the PR will be closed.
- AI-written submissions the author has not reviewed or cannot explain.
  The Open Home Foundation AI policy
  (<https://contributors.home-assistant.io/start/ai-policy/>) allows AI as a
  tool but requires a human who understands the work: PRs that look like
  unreviewed AI output or that bypass the template are closed, autonomous
  agents are not allowed, AI-generated replies to maintainers are not
  allowed, and repeated violations can lead to a block.
- Ticking checklist boxes that are not true (action failing, `ignore` still
  present, no release after the passing run).
- Fixing only the first item of a multi-item review, or only the exact line
  quoted, then asking for re-review: "The second item from last time is still
  open".
- Closing and reopening a new PR to jump the queue or clear reviews; it
  restarts the wait.
- Arguing a domain collision or eligibility rule in the PR instead of
  resolving it.
- Leaving a drafted PR in draft after fixing it.

## Pre-submission checklist

- [ ] Not a duplicate: no core integration or existing HACS default covers
      the same devices/API, and the code is not a fork of one
- [ ] Domain is unique in core **and** in the HACS default list
- [ ] Repository name does not contain "HACS"; licence is yours to grant
- [ ] Integration creates entities/services and has been run end to end
- [ ] Latest release tag == `manifest.json` version; no tag was ever moved
- [ ] Release contains `translations/en.json`, `brand/icon.png`, LICENSE
- [ ] `hacs.json` `homeassistant` floor matches the APIs used
- [ ] `documentation`, `issue_tracker`, `codeowners` are real and correct
- [ ] Every core component used is in `dependencies`/`after_dependencies`
- [ ] Only tested device controls are exposed; feature flags match methods
- [ ] No blocking I/O; no hardcoded keys; production endpoints; password
      fields masked
- [ ] Touches only its own entities, devices, storage and resources
- [ ] Any bundled frontend ships inside the integration and escapes all
      interpolated values
- [ ] HACS action (no `ignore`) and hassfest green on the default branch,
      then a release published
- [ ] PR: personal fork, new branch, one alphabetically placed line,
      template intact with three working links, exact `owner/repo` case
- [ ] Branch kept current with `master`; replies to review cover every item
