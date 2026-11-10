# HACS requirements for integrations

Condensed from <https://hacs.xyz/docs/publish/start>,
<https://hacs.xyz/docs/publish/include>,
<https://hacs.xyz/docs/publish/integration>,
<https://hacs.xyz/docs/publish/action>, the validators in `hacs/integration`,
and the workflow in `hacs/default`. Re-check the live pages if anything here
looks out of date.

## Contents

- [Repository requirements](#repository-requirements)
- [Repository structure](#repository-structure)
- [hacs.json](#hacsjson)
- [manifest.json](#manifestjson)
- [Brand assets](#brand-assets)
- [Versions and releases](#versions-and-releases)
- [Validation workflows](#validation-workflows)
- [Check → fix table](#check--fix-table)
- [Submitting to hacs/default](#submitting-to-hacsdefault)

## Repository requirements

- Public repository on GitHub. Not archived.
- Repository name must not contain "HACS" (a bot on hacs/default rejects
  it); `ha-<thing>` or `hass-<thing>` is the usual convention.
- **Description** set on the repository (shown in HACS).
- **Topics** set (used for search in the HACS store). Sensible ones:
  `home-assistant`, `hacs`, `custom-integration`, plus the brand or protocol.
- **Issues enabled**.
- **README** explaining what it does, how to install and how to use it.
- **Licence** that GitHub can identify and that is OSI approved. A custom or
  edited licence text shows as `NOASSERTION` and fails; so do non-commercial
  and other use-restricting licences.
- A `hacs.json` in the repository root.

A repository that works as a HACS *custom repository* meets most of this; the
default store adds the stricter checks below.

## Repository structure

One integration per repository. Everything the integration needs at runtime
lives in `custom_components/<domain>/`.

```
custom_components/awesome/__init__.py
custom_components/awesome/manifest.json
custom_components/awesome/config_flow.py
custom_components/awesome/sensor.py
custom_components/awesome/translations/en.json
custom_components/awesome/brand/icon.png
hacs.json
README.md
LICENSE
.github/workflows/validate.yml
```

Not valid: integration files in the repository root, or in `awesome/` without
`custom_components/` (unless `content_in_root: true` is set in `hacs.json`,
which is rarely the right choice). If `custom_components/` holds more than one
directory, HACS manages only the first.

## hacs.json

Root of the repository. Only `name` is required.

| Key | Type | Notes |
| --- | --- | --- |
| `name` | string | **Required.** Display name in HACS. |
| `content_in_root` | bool | Content is in the repo root instead of a subdirectory. |
| `zip_release` | bool | Integration is shipped as a zip asset on releases. Requires `filename`. Integrations only. |
| `filename` | string | Name of the zip asset when `zip_release` is true. |
| `hide_default_branch` | bool | Do not offer the default branch as a download. |
| `country` | string or list | ISO 3166-1 alpha-2 code(s). **Required in practice** when the integration is for one or a few countries. |
| `homeassistant` | string | Minimum Home Assistant version. Append `b0` (e.g. `2026.3.0b0`) to allow betas. |
| `hacs` | string | Minimum HACS version. |
| `persistent_directory` | string | Path inside the integration directory preserved across upgrades. Integrations only. |

Unknown keys fail validation. `render_readme` is a leftover from HACS 1; drop
it.

```json
{
  "name": "Awesome",
  "homeassistant": "2026.3.0",
  "country": ["NO", "SE"]
}
```

Set `homeassistant` to the oldest version actually supported. If the
integration relies on local `brand/` images, that is 2026.3.0 or later for the
images to display.

## manifest.json

HACS requires these keys: `domain`, `name`, `codeowners`, `documentation`,
`issue_tracker`, `version`. hassfest additionally expects `iot_class` and
enforces key order (`domain`, `name`, then alphabetical).

```json
{
  "domain": "awesome",
  "name": "Awesome",
  "codeowners": ["@you"],
  "config_flow": true,
  "documentation": "https://github.com/you/ha-awesome",
  "integration_type": "hub",
  "iot_class": "local_polling",
  "issue_tracker": "https://github.com/you/ha-awesome/issues",
  "requirements": ["awesome-client==1.4.2"],
  "version": "1.0.0"
}
```

- `domain`: lowercase, digits, underscores; equals the directory name; must
  not be used by a core integration (including ones landing in the next
  release). Check <https://www.home-assistant.io/integrations/> and
  `homeassistant/components/` on the `dev` branch.
- `version`: required for custom integrations. SemVer or CalVer as understood
  by AwesomeVersion. Keep it equal to the release tag.
- `documentation` and `issue_tracker`: real, reachable URLs for *this*
  repository.
- `codeowners`: GitHub handles with a leading `@`.
- `integration_type`: `hub`, `device`, `service`, `helper` are the normal
  choices; defaults to `hub` if omitted, so set it deliberately.
- `iot_class`: `local_polling`, `local_push`, `cloud_polling`, `cloud_push`,
  `calculated`, `assumed_state`.
- `requirements`: pinned with `==`, published on PyPI.
- `quality_scale` is a core concept (tiers are assigned by the Home Assistant
  core team); leave it out of a custom integration's manifest.
- Discovery keys (`zeroconf`, `dhcp`, `ssdp`, `bluetooth`, `usb`, `mqtt`)
  need the matching `async_step_*` in the config flow.

## Brand assets

Required. Since Home Assistant 2026.3 a custom integration ships its own
images in `custom_components/<domain>/brand/`:

- `icon.png` — **required by the HACS check.** Square.
- `icon@2x.png` — high-DPI version.
- `logo.png` / `logo@2x.png` — landscape logo.
- `dark_icon.png`, `dark_logo.png` (+ `@2x`) — optional dark-mode variants.

Follow the image conventions of home-assistant/brands: PNG, transparent
background, trimmed, optimised; icon 256×256 (`@2x` 512×512); logo with its
shortest side 128–256 px (`@2x` 256–512). Use the manufacturer's or
service's real mark only if you are entitled to; do not reuse Home Assistant's
own logo.

If `brand/icon.png` is absent the HACS check falls back to looking the domain
up in <https://github.com/home-assistant/brands> (`custom_integrations/`).
That repository route is the legacy path; prefer the local directory.

The blueprint ships with `ignore: brands` in its workflow. It must be removed
before submission.

## Versions and releases

- HACS uses the tag name of the latest GitHub **release** as the version.
  Pushing a tag is not enough; publish a release.
- Without releases HACS uses the first 7 characters of the latest commit on
  the default branch. Releases are optional for custom repositories but the
  hacs/default workflow **fails without at least one release**.
- The release must be created *after* the validation workflows passed, so the
  released code is the code that was validated. HACS validates the latest
  release, not the branch, when a release exists: a fix pushed to `main`
  without a new release does not fix a failing check.
- Keep `manifest.json` `version` in step with the tag.

## Validation workflows

`.github/workflows/validate.yml` (the blueprint's is equivalent, with pinned
SHAs):

```yaml
name: Validate

on:
  push:
  pull_request:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions: {}

jobs:
  hassfest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: home-assistant/actions/hassfest@master

  hacs:
    runs-on: ubuntu-latest
    steps:
      - uses: hacs/action@main
        with:
          category: integration
```

Both jobs must pass on the default branch. `ignore:` accepts a
space-separated list of `archived brands description hacsjson images
information issues license topics`; it is acceptable while developing and
**must be absent** when submitting to hacs/default. If pinning `hacs/action`
to a version, enable Dependabot or Renovate to keep it current.

Some checks (`archived`, `description`, `issues`, `license`, `topics`) are
skipped when the action runs on a pull request from a fork, so a green PR run
is not proof; look at a run on the default branch.

## Check → fix table

| Failure | Cause | Fix |
| --- | --- | --- |
| `The repository has no description` | GitHub "About" description empty | Set it in the repo's About panel. |
| `The repository has no valid topics` | No topics | Add topics in the About panel. |
| `The repository does not have issues enabled` | Issues off | Settings → Features → Issues. |
| `The repository has no license` / `missing an SPDX ID` / not OSI approved | No LICENSE, edited text, or restrictive licence | Add an unmodified OSI licence file (MIT, Apache-2.0, GPL-3.0…). |
| `The repository has no 'hacs.json' file` | Missing or not in root | Add `hacs.json` with `name`. |
| `extra keys not allowed @ data['…']` (hacs.json) | Unsupported key | Remove it; see the key table. |
| `zip_release is True, but filename is not set` | — | Add `filename`. |
| `The repository does not provide brand assets and is not listed in the Home Assistant brands repository` | No `brand/icon.png` | Add `custom_components/<domain>/brand/icon.png`. |
| `required key not provided @ data['issue_tracker']` etc. | Manifest key missing | Add the key. |
| `expected a URL` on documentation / issue_tracker | Not a URL | Use a full `https://` URL. |
| Invalid version | Not SemVer/CalVer | Use e.g. `1.2.3`. |
| `The repository is archived` | Archived | Unarchive, or do not submit. |
| hassfest: `Manifest keys are not sorted correctly: domain, name, then alphabetical order` | Order | Reorder keys. |
| hassfest: `Invalid iot_class` / `required key not provided … iot_class` | Missing or wrong | Set a valid `iot_class`. |
| hassfest: `Config flow … config_flow.py` | `config_flow: true` without the file, or the reverse | Make manifest and files agree. |
| hassfest: translation errors | `translations/en.json` does not match the schema or the flow's steps/errors | Fix keys; every `step_id`, `errors` and `abort` reason used in code needs an entry. |
| hassfest: `Domain collides with built-in core integration` | Domain taken by core | Rename the domain (and directory). |
| hassfest: `Using component X but it's not in 'dependencies' or 'after_dependencies'` | Code uses a core component not declared | Add it (e.g. `"dependencies": ["http"]`). |
| hassfest: requirement not pinned | `>=` in `requirements` | Pin with `==`. |
| hacs/default `Releases` job | No release | Publish a release. |
| hacs/default `Owner` job | Submitter is not owner or a major contributor | The owner must submit. |
| hacs/default `Editable PR` job | Maintainer edits disabled or fork owned by an organisation | Submit from a personal fork with "Allow edits by maintainers" ticked. |
| hacs/default `Existing repository` job | Already in HACS (any category) | Nothing to add. |
| hacs/default `Removed repository` job | Previously removed from HACS | Needs agreement with the HACS team first. |
| hacs/default `lint sorted` / `lint jq` | Entry not alphabetical, or broken JSON | Insert in the correct position; keep valid JSON (quotes, commas). |

## Submitting to hacs/default

### Who may submit

- Only the owner or a major contributor of the repository.
- Not accepted as defaults: integrations that are alpha/beta test builds of a
  core integration, or that override a core integration. They can still be
  installed as custom repositories.
- In practice also declined: integrations that duplicate a core integration
  or one already in the default store (same devices, protocol or API), and
  forks of existing defaults. See `common-pr-feedback.md`.
- Publishers who previously deleted a default repository are blocked from
  adding new ones.

### Before opening the PR

1. The repository installs and works as a HACS custom repository.
2. HACS action passes with **no** errors and **no** `ignore`.
3. hassfest passes.
4. A full GitHub release was published after those runs succeeded.
5. `hacs.json` in that release has `country` set if the integration is
   country specific.

### The PR

- Fork `hacs/default` to a **personal** account (organisation forks cannot
  grant maintainer edit access, and the "Editable PR" check fails).
- Create a new branch from `master`. Do not commit to your fork's `master`.
- Edit only the `integration` file. Add `"owner/repo"` in alphabetical,
  case-insensitive order, not at the end. Keep the JSON valid.
- One repository per PR, and the diff must be exactly one added line
  (`+1/-0`). A bot rejects PRs that touch more than one entry; a bad rebase
  that drops someone else's line is caught in review.
- Spell `owner/repo` with the exact capitalisation GitHub shows for the
  repository; a bot compares it.
- Title convention: `Adds new integration [owner/repo]`.
- Keep the branch up to date with `master`. The `integration` file changes
  daily, so conflicts are routine while waiting; a bot requests changes when
  the branch is behind. Merge or rebase `master`, then re-check the diff is
  still `+1/-0`.
- Fill in the template in full. It is, verbatim:

```markdown
## Checklist

- [ ] I've read the [publishing documentation](https://hacs.xyz/docs/publish/start).
- [ ] I've added the [HACS action](https://hacs.xyz/docs/publish/action) to my repository.
- [ ] (For integrations only) I've added the [hassfest action](https://developers.home-assistant.io/blog/2020/04/16/hassfest/) to my repository.
- [ ] The actions are passing without any disabled checks in my repository.
- [ ] I've added a link to the action run on my repository below in the links section.
- [ ] I've created a new release of the repository after the validation actions were run successfully.

## Links

Link to current release: <>
Link to successful HACS action (without the `ignore` key): <>
Link to successful hassfest action (if integration): <>
```

  All three links are required for an integration (a bot counts them and
  closes the PR if any are missing). Links must point at the specific release and the specific workflow *runs*
  (`…/actions/runs/<id>`), not at the Actions tab or the workflow file.

### What closes or drafts a PR

Stated in the docs:

- Template not filled in correctly → closed without further notice.
- Statements in the PR that are not true (e.g. a ticked box for a passing
  action that is failing or uses `ignore`) → closed without further notice.
- Submitter is not owner or major contributor → closed without further notice.
- Requirements not met → drafted for minor issues, closed for major ones.
- Requesting reviews: the template says the PR will be closed.

When a PR is drafted: fix the issue, publish a new release if code or
`hacs.json` changed, update the links, then click "Ready for review".

### Afterwards

Review of new defaults takes months; the queue is
<https://github.com/hacs/default/pulls?q=is%3Apr+is%3Aopen+draft%3Afalse+sort%3Acreated-asc>.
All automated checks must be green when a maintainer gets to it, so keep the
repository healthy while waiting (the nightly scheduled workflow run helps).
Stale PRs are closed automatically. After merge the repository appears after
the next scheduled scan.

Do not delete or rename away a repository that is in the default store; open a
removal request at `hacs/integration` first. Archived repositories are removed
automatically.

Tell users how to add the repository with a My Home Assistant link:
<https://my.home-assistant.io/create-link/?redirect=hacs_repository>.
