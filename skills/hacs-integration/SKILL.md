---
name: hacs-integration
description: Create, build and review Home Assistant custom integrations that are distributed through HACS, and prepare them for inclusion in the HACS default store (hacs/default). Use when the user wants to scaffold a new custom integration (custom_components), add or fix config flows, coordinators, entities, manifest.json, hacs.json, brand images, hassfest or HACS action workflows, review an integration against Home Assistant best practice, fix a failing HACS/hassfest check, or open or repair a pull request to hacs/default. Not for dashboards, cards, themes, AppDaemon or other HACS categories.
---

# HACS integration skill

Helps with the three stages of a Home Assistant custom integration: **create**
(scaffold from the blueprint), **build** (write code the Home Assistant way),
and **review** (find what will fail validation or be flagged before a
maintainer does). Scope is HACS category `integration` only.

Requirements move. HACS and Home Assistant change their rules several times a
year, so when a reference file here disagrees with the live docs
(<https://hacs.xyz/docs/publish/start>, <https://hacs.xyz/docs/publish/include>,
<https://developers.home-assistant.io>), the live docs win; say so and follow
them.

## Pick the mode

| The user wants to… | Do |
| --- | --- |
| Start a new integration | [Create](#create) |
| Add features or fix code in an existing one | [Build](#build) |
| Know whether it is good / ready, or why a check fails | [Review](#review) |
| Get listed in the HACS default store | [Publish](#publish) |
| Answer a maintainer's review on their hacs/default PR | [Respond to a review](#respond-to-a-review) |

When invoked as a command, the first word of the argument selects the mode:
`create`, `build`, `review`, `publish` or `respond` (for example
`/hacs-integration review`). With no argument, or anything else, infer the
mode from the request; if the working directory already holds an integration
and nothing else was asked, default to Review.

## Create

Start from <https://github.com/ludeeus/integration_blueprint>. It already has
the layout HACS expects, a config flow, a `DataUpdateCoordinator`, typed
`entry.runtime_data`, ruff config, a devcontainer, and the hassfest and HACS
validation workflows.

1. Check it should exist. Search Home Assistant core
   (<https://www.home-assistant.io/integrations/>) and the HACS store for the
   same device, brand or API. Duplicates of core or of an existing default,
   and forks of them, are the most common reason maintainers decline a
   submission; contributing to the existing integration is the usual
   advice. A custom repository is still fine for personal use.
2. Ask for (or infer) the display name, the **domain** (lowercase,
   underscores, must not match any Home Assistant core integration), what
   device or service it talks to, local or cloud, polling or push, and the
   owner's GitHub handle.
3. Get the template: "Use this template" on GitHub, or
   `git clone --depth 1 https://github.com/ludeeus/integration_blueprint <repo> && rm -rf <repo>/.git && git -C <repo> init`.
4. Rename everything. Directory `custom_components/integration_blueprint` →
   `custom_components/<domain>`; then replace `integration_blueprint`,
   `IntegrationBlueprint`, `Blueprint`, `Integration blueprint` and `ludeeus`
   across the tree (code, `manifest.json`, `hacs.json`, `README.md`,
   `translations/en.json`, `.devcontainer.json`, `scripts/develop`, issue
   templates). Leftover template names are a common reason submissions are
   closed.
5. Fix `manifest.json`: real `documentation` and `issue_tracker` URLs,
   `codeowners`, correct `iot_class`, add `integration_type`, add
   `requirements` (pinned `==`) for the client library. Keys ordered `domain`,
   `name`, then alphabetical.
6. Replace the blueprint's sample API client, entities and the
   `unique_id=slugify(username)` placeholder with real ones (see Build).
   The blueprint's coordinator raises `ConfigEntryAuthFailed` but its config
   flow has no reauth step; add `async_step_reauth` / `reauth_confirm` and
   their strings, or reviewers will ask for it.
7. Add `custom_components/<domain>/brand/icon.png` (and ideally `logo.png`),
   then **delete `ignore: brands`** from `.github/workflows/validate.yml`.
8. Replace the README with real install, configuration and entity
   documentation. Keep the LICENSE (MIT) or swap for another OSI licence.
9. Run `scripts/setup`, `scripts/lint`, and `scripts/develop` to load it in a
   local Home Assistant; then run the pre-flight script (see Review).

## Build

Read [references/ha-best-practices.md](references/ha-best-practices.md) before
writing or changing integration code. The non-negotiables:

- UI setup through a config flow that tests the connection before creating the
  entry and sets a stable unique ID. No YAML configuration for new work.
- Everything on the event loop is async. No `requests`, `time.sleep`, file or
  socket I/O without `hass.async_add_executor_job`. Device/protocol logic
  lives in a PyPI library, not in the integration.
- Use `async_get_clientsession(hass)`; do not create your own session.
- Runtime objects go in `entry.runtime_data` (typed `ConfigEntry` alias), not
  `hass.data[DOMAIN]`.
- One `DataUpdateCoordinator` per polled endpoint; raise `UpdateFailed` for
  transient errors and `ConfigEntryAuthFailed` for bad credentials.
- Entities: `_attr_has_entity_name = True`, stable `unique_id`, `DeviceInfo`,
  device classes / state classes / units from the enums, names from
  `translation_key`, `available` reflecting reality.
- `async_unload_entry` must cleanly undo setup.
- User-facing strings live in `translations/en.json` (custom integrations do
  not load `strings.json`).

Follow the blueprint's file split (`api.py`, `coordinator.py`, `data.py`,
`entity.py`, one file per platform) unless the repo already has its own
convention.

## Review

Work in this order and report findings grouped as **Blocking** (a HACS or
hassfest check fails, or the PR would be closed), **Should fix** (Home
Assistant best practice, user-visible bugs) and **Nice to have**. Give
file:line and the concrete fix for each.

1. Run the offline pre-flight:
   `python3 <skill-dir>/scripts/hacs_preflight.py <repo-path>`.
   It covers repository layout, `hacs.json`, `manifest.json`, brand icon,
   translations, workflows, and a scan for common code smells. It cannot see
   GitHub-side settings, so check those by hand (step 3).
2. Read the code against
   [references/ha-best-practices.md](references/ha-best-practices.md). The
   script's pattern hits are leads, not verdicts; confirm each by reading the
   code.
3. Check what only GitHub knows, using
   [references/hacs-requirements.md](references/hacs-requirements.md):
   description, topics, issues enabled, licence detected, not archived, a
   full **release** (not just a tag) made *after* the last green workflow
   run, and both workflows green with no `ignore`.
4. Go through [references/review-rounds.md](references/review-rounds.md),
   the code-level findings maintainers raised on submissions that were later
   merged (auth and reauth, exceptions, blocking calls, privacy, access
   control, frontend escaping, device safety, minimum-version floor). This is
   the closest thing to the reviewer's own checklist.
5. Compare against
   [references/common-pr-feedback.md](references/common-pr-feedback.md), the
   catalogue of what gets hacs/default submissions closed or drafted.

Review the code as it is in the latest release tag, not only the working
tree: that is what HACS validates and what maintainers read.

If hassfest or the HACS action is failing, map the message to its fix with the
table in `references/hacs-requirements.md` before changing anything.

## Publish

Only when the Review is clean. The full procedure, the PR template and the
rules that get PRs closed without comment are in
[references/hacs-requirements.md](references/hacs-requirements.md#submitting-to-hacsdefault).
In short:

1. HACS action and hassfest both pass on the default branch with no `ignore`.
2. Publish a GitHub release after that passing run.
3. Repository name has no "HACS" in it. Fork `hacs/default` from a
   **personal** account, branch from `master` (not
   on `master`), add `owner/repo` to the `integration` file in alphabetical
   (case-insensitive) position, one repository per PR.
4. Fill in the PR template completely, with working links to the release and
   to the two passing workflow runs. Leave "allow edits by maintainers" on.
5. Do not request reviews, ping maintainers or bump the PR. Review takes
   months; a drafted PR means "fix, then mark ready".

The person submitting must be the owner or a major contributor of the
repository. Never open the hacs/default PR, tick the checklist, or write the
PR text for a user unless they ask, and never tick a box that is not true:
misrepresenting the checklist gets the PR closed.

## Respond to a review

When the user has change requests on their hacs/default PR, follow
[references/review-rounds.md](references/review-rounds.md#responding-to-a-review).
The rule that saves the most time: fix the whole class of problem, not the
quoted line. Reviews that ran to four or five rounds did so because the same
kind of issue (an unescaped value, a logged secret, a blocking call) was still
present elsewhere. Then bump the version, publish a new non-pre-release
release, update the PR branch and its three links, and reply once with an
item-by-item summary. Draft the reply for the user to post; do not post on
their behalf unless asked.

## Things this skill should refuse to paper over

- Adding `ignore:` to the HACS action, or disabling hassfest, to get green.
- Moving or re-creating a git tag or release to hide a change.
- Using a domain that shadows a core integration, or publishing an alpha/beta
  copy of a core integration as a default.
- Copying another project's brand assets or code without a compatible licence.
- Submitting a repository the user does not own or substantially maintain.

Explain why, and fix the underlying problem instead.
