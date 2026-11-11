# What reviewers ask for before merging

Compiled in November 2026 from 32 integration submissions to
<https://github.com/hacs/default> that **were merged** after one to five
rounds of requested changes (PR numbers in brackets are examples). Where
`common-pr-feedback.md` lists what stops a submission, this file lists what a
careful code review finds in integrations that were otherwise good enough to
get in, and the fix that was accepted. Use it as the code-review checklist,
and for responding to a review.

Typical path to merge: two or three change-request rounds over several weeks
to months, almost always including at least one "branch out of date" notice
(25 of the 32). Reviews are of the latest **release**, with file and line
references.

## Contents

- [Auth and reauth](#auth-and-reauth)
- [Errors and exceptions](#errors-and-exceptions)
- [Blocking calls](#blocking-calls)
- [Privacy and secrets](#privacy-and-secrets)
- [Access control](#access-control)
- [Frontend code](#frontend-code)
- [Device safety](#device-safety)
- [Entities, IDs and availability](#entities-ids-and-availability)
- [Setup, unload and storage](#setup-unload-and-storage)
- [Services](#services)
- [Translations](#translations)
- [Manifest, hacs.json and packaging](#manifest-hacsjson-and-packaging)
- [Minimum Home Assistant version](#minimum-home-assistant-version)
- [README](#readme)
- [Licence](#licence)
- [Responding to a review](#responding-to-a-review)

## Auth and reauth

The most common code-level finding (7 of 32).

- **`ConfigEntryAuthFailed` raised but no reauth flow** [#10629, #9177].
  Raising it starts a reauth flow; without `async_step_reauth` the user gets
  a dead end. Add:

  ```python
  async def async_step_reauth(self, entry_data):
      return await self.async_step_reauth_confirm()

  async def async_step_reauth_confirm(self, user_input=None):
      errors = {}
      if user_input is not None:
          # validate credentials …
          return self.async_update_reload_and_abort(
              self._get_reauth_entry(), data_updates=user_input
          )
      return self.async_show_form(step_id="reauth_confirm", data_schema=…, errors=errors)
  ```

  plus `reauth_confirm` step strings and a `reauth_successful` abort string.
- **Reauth that can never finish**: `async_step_reauth` delegating to
  `async_step_user`, which aborts because the unique ID is already
  configured [#9555]. Use a separate confirm step that skips that check.
- **Silent re-login loops**: logging in again with the stored password on
  every 401, or three retries per poll, forever [#11654, #11491]. On a
  rejected credential stop and raise `ConfigEntryAuthFailed`; keep
  `UpdateFailed` for network errors.
- **Auth and connection errors confused**: everything mapped to
  `cannot_connect`, or network errors raised as auth errors and triggering
  reauth [#8487, #11654, #9345]. Treat only 401/403 as auth. In the config
  flow map to `invalid_auth` vs `cannot_connect`; in setup raise
  `ConfigEntryAuthFailed` vs `ConfigEntryNotReady`.
- **A broad `except Exception` swallowing `ConfigEntryAuthFailed`**
  [#11654]: add `except ConfigEntryAuthFailed: raise` above it.
- **Rotating refresh tokens dropped**: keeping only the new access token when
  the refresh response also returns a new single-use refresh token [#10629].
  Persist both with `hass.config_entries.async_update_entry`.
- No unique ID set on the config entry [#11654].
- Config flow writing `.storage/core.config_entries` directly [#8426]. Only
  ever go through the config-entries API.

## Errors and exceptions

- Entity actions and services leaking library exceptions or bare
  `ValueError` [#10133, #9056]. Catch the library's errors and raise
  `HomeAssistantError`; raise `ServiceValidationError` for bad input; give
  both a `translation_domain` and `translation_key`.
- Calls made outside any handler on one code path (e.g. the "arm" path
  handled, the "ensure connected" pre-check not) [#10133].
- Read helpers that swallow errors and return empty or default data, which
  the rest of the code then treats as real [#9177, #9555, #9086].
- `NameError` / `UnboundLocalError` / `AttributeError` on rarely used paths:
  a constant used without import, a variable assigned in only one branch, a
  service calling a method that does not exist [#7579, #8426, #9086,
  #12257]. Run `ruff check` (pyflakes rules `F821`, `F823`, `F841`) and call
  every service and entity action once.
- Inverted or wrong error mapping in the config flow, e.g.
  `"auth" if not error else …` [#9345].
- A repair issue created with `is_fixable=True` but no fix flow in
  `repairs.py` [#9056]. Set it to `False` or implement the flow.

## Blocking calls

Flagged in 7 of 32. Beyond the obvious `requests`/`time.sleep`:

| Call seen on the event loop | Replacement |
| --- | --- |
| `os.path.exists`, `os.listdir`, `glob.glob`, `Path.is_file`, `mkdir`, `write_text`, `os.path.realpath` [#8426, #12257, #8895, #10809] | one sync helper run with `await hass.async_add_executor_job(...)` |
| `serial.Serial(...)` opened in `connect` [#8426] | executor job, or an async serial library |
| `zmq` context `.term()` [#8257] | executor job |
| `ZoneInfo(hass.config.time_zone)` [#10133] | `dt_util.get_default_time_zone()` |
| `ZoneInfo(name)` [#13045] | `await dt_util.async_get_time_zone(name)` |
| `ZoneInfo("UTC")` [#11491] | `datetime.UTC` |
| reading `manifest.json` at module import [#9056] | `async_get_loaded_integration(hass, DOMAIN).version` |
| file or network I/O in an entity constructor [#10809] | do it in setup or the coordinator |

Related: `date.today()` / `datetime.now()` follow the system clock, not the
configured Home Assistant time zone; use `dt_util.now()` [#10596].

## Privacy and secrets

Flagged in 10 of 32, and the finding most likely to take several rounds,
because the same value leaks through more than one path. When one leak is
reported, grep for every use of that value.

- **Logging credentials**: passwords, tokens, API keys, even partially
  ("last 5 characters"), or logging a whole config-entry dict [#8019, #9086,
  #9554]. Never log them at any level.
- **Identifiers in logs**: full serial numbers, at INFO, WARNING and DEBUG,
  and in notification text [#8019]. Mask them with one helper used
  everywhere.
- **PII in entity state**: phone number and SIM ICCID as attributes, phone
  number in the device name [#5629]; PIN codes in attributes and retained
  MQTT messages [#10809]; signed media or CDN URLs as attributes [#9990,
  #10809] (sign on demand instead).
- **Diagnostics** exporting serials, user names, installation names or raw
  event payloads; or redacting a key that never exists [#10133, #8019]. Use
  `async_redact_data` with the real key names and check the output.
- **A secret used as an identifier** (password as device identifier)
  [#8019]. Use the entry ID or a device serial.
- **API key in a URL query string**, then logged with the URL [#9554]. Put
  it in a header.
- **Shared session cookie jar**: reading cookies from
  `async_get_clientsession(hass)` exposes other integrations' cookies
  [#5629]. Use `async_create_clientsession(hass)` when the integration needs
  cookies, and filter by host.
- **Personal data committed to the repo**: debug dumps containing the
  author's account ID, e-mail and name [#9177]; the author's own entity IDs
  as defaults [#11803]. Check `git ls-files` before releasing.

## Access control

- HTTP views: `requires_auth = False` is not acceptable for anything that
  reads or changes configuration [#8895]. `requires_auth = True` alone still
  lets every non-admin user call it; check `request["hass_user"].is_admin`
  for anything that writes or triggers actions [#11803].
- WebSocket commands that change state need
  `@websocket_api.require_admin`. Marking a sidebar panel `require_admin`
  only hides the panel [#8895].
- Views taking an `entry_id` must check `entry.domain == DOMAIN`, or they
  can return other integrations' stored credentials [#8895].
- Services that read local files, fetch arbitrary URLs, change settings or
  install things: register with
  `homeassistant.helpers.service.async_register_admin_service` [#9990,
  #10809].
- No magic values that bypass a PIN or code check [#10809].
- Do not send stored credentials to a host supplied by the caller (a "test
  connection" service) [#10809].
- Do not serve captures or media from `config/www/`; that directory is
  unauthenticated [#10809].
- No self-updater. HACS updates the integration [#10809].

## Frontend code

Found in 6 of the 32, and in several of the rejected submissions.

- Every value interpolated into `innerHTML` must be escaped: entity names,
  attributes, names from a remote API, version strings, titles, history
  text, card configuration [#7333, #10078, #9990, #11803]. Add one
  module-level `escapeHtml` and use it on every interpolation, or build
  nodes and set `textContent`. Reviewers list each remaining spot round
  after round, so fix them all at once.
- Do not write Lovelace resource entries from Python; nothing removes them
  on uninstall. Use `add_extra_js_url` or document the manual step [#9554].
- Keep the cache-busting query in step with the bundled file's version;
  derive it from the integration version rather than hardcoding [#10133].
- Do not ship stale pre-compressed assets (`.js.gz`) next to a newer `.js`
  [#11803].

## Device safety

Writes to physical equipment are held to a higher standard.

- **Read-modify-write, never fixed defaults.** A setter that sends hardcoded
  calibration or safety values along with the one field the user changed
  resets the rest [#9177]. Read the current settings, change one field, send
  the rest back unchanged, and refuse the write if the read failed (track a
  `valid` flag).
- **Never substitute a fake value for "unavailable".** A parser returning
  `0` for a missing temperature drove a heater towards full output [#9086].
  Omit the value or mark the entity unavailable.
- **Do not write on every poll.** A coordinator sending a setting to the
  device every 15 seconds, even with the option off [#10218]. Write once,
  when needed.
- **Hardcoded account or device IDs** in URLs and identifiers [#11654]. Read
  them from the API.

## Entities, IDs and availability

- `unique_id` not scoped to the config entry, so two entries covering the
  same station or area collide [#9294]. Include `entry.entry_id` (or a
  per-entry device ID) and migrate existing registry entries.
- Building `entity_id` by hand, or hardcoding other entities' IDs in code
  [#9481, #9294]. Let the registry derive IDs; look entities up through the
  registry by unique ID.
- `available` that never goes false: return
  `coordinator.last_update_success` (or use `CoordinatorEntity`) [#9294].
- Cached data reported as live: `online = state is not None` with a stale
  timeout constant that is never used [#9555]. Timestamp incoming data and
  treat it as unavailable when stale.
- A connectivity sensor that inherits the "unavailable when disconnected"
  gating can never show "disconnected" [#9056]. Override `available` for
  that entity.
- Re-scanning the whole entity list on every push message [#9056].
- No hub device: add one and point children at it with `via_device`
  [#9345].
- Multiple config entries: views, media sources and services that always
  use "the first entry" act on the wrong device [#9345]. Carry the entry ID
  in the identifier or URL, return 404 for unknown ones, and never fall back
  to the first entry for a destructive action.
- Routine events logged at INFO or WARNING [#9086, #8426]. Use DEBUG.

## Setup, unload and storage

- A failed first refresh that leaves a TCP listener or connection open
  [#10133]. Wrap the refresh, call `coordinator.async_shutdown()` (or close
  the client), then re-raise.
- Timers and listeners (`async_call_later`, `async_track_*`) not passed to
  `entry.async_on_unload` [#9056].
- After moving to `entry.runtime_data`, leftover code still reading
  `hass.data[DOMAIN]` (diagnostics came back empty) [#9056]. Grep for the
  old pattern after a refactor.
- Options flow relying on `self.config_entry` without the minimum Home
  Assistant version that provides it [#8895, #8019].
- Caches or user data written inside the integration directory are deleted
  on every HACS update [#11654]. Use `homeassistant.helpers.storage.Store`,
  or `persistent_directory` in `hacs.json`.
- Calling a private method of your own class from another module
  (`coordinator._notify`) [#9056]: expose a public one.

## Services

- A service listed in `services.yaml` but never registered, or registered
  without the schema `services.yaml` describes [#11654, #12257].
- Services registered in `async_setup_entry` and never removed, or
  registered twice with a second entry [#9554]. Register once in
  `async_setup`.
- A view or route registered twice [#9345]; extra URL routes that can never
  satisfy the handler's required parameters [#9345].
- Dead modules importing names that do not exist [#11654].

## Translations

Flagged in 6 of 32.

- `translations/en.json` missing while another language is present
  [#10078, #9177]. English is the fallback and is mandatory.
- Strings added to `strings.json` but not copied to `translations/en.json`
  [#10629, #11654]. Custom integrations only load `translations/`.
- Reauth strings missing: `config.step.reauth_confirm` (title, description,
  field labels) and `config.abort.reauth_successful` [#11654, #10629,
  #9177].
- Error and abort keys used in code but absent (`invalid_auth`,
  `no_tams_found`, `already_configured`) [#9345, #11654].
- Keys inconsistent between language files [#9345].

## Manifest, hacs.json and packaging

- `manifest.json` `version` behind the release tag: flagged in 5 of 32,
  often only as a note at approval. Automate it in the release workflow.
- A version bump made in a stray `manifest.json` at the repository root
  instead of the integration's [#9177].
- Release marked **pre-release**, so HACS keeps installing the previous
  version and the reviewer never sees the fix [#8257].
- Release workflow that force-pushes or moves tags [#9345].
- `requirements`: unused packages listed [#8257]; packages imported but not
  listed [#10809]; a git URL with no ref (publish to PyPI and pin) [#9345];
  unbounded `>=` on large SDKs [#9555]; a lower bound older than the API the
  code calls [#9590].
- A bare `except ImportError: pass` around imports hides a missing
  requirement [#9555].
- `content_in_root: true` with files at the repo root: move to
  `custom_components/<domain>/` and drop the key [#9590].
- Integration shipped as a zip asset without `zip_release` and `filename`
  in `hacs.json` [#9056].
- `country` missing for a single-country data source [#7085].
- Junk in the release: `__pycache__`, zero-byte modules, debug dumps,
  duplicate multi-megabyte brand PNGs [#8426, #9086, #9177, #7333].
- The repository's own workflows not running the HACS action and hassfest
  at all [#9177, #11803].
- Derived code: code adapted from Home Assistant core (Apache-2.0) needs
  the upstream notice and licence text kept, even in an MIT repo [#10218].

## Minimum Home Assistant version

`hacs.json` `homeassistant` missing or too low was flagged in 7 of 32.
Reviewers check the APIs the code imports against the declared floor.
Floors cited in reviews:

| API used | Needs at least |
| --- | --- |
| `ClimateEntityFeature.TURN_ON` / `TURN_OFF` | 2024.2 |
| `entry.async_create_background_task` (as cited) | 2024.5 |
| `StaticPathConfig` / `async_register_static_paths` | 2024.7 |
| `FanEntityFeature.TURN_ON` / `TURN_OFF` | 2024.8 |
| `_get_reauth_entry()`, `async_update_reload_and_abort(data_updates=…)` | 2024.11 |
| Options flow using the provided `self.config_entry` | 2024.12 |
| `homeassistant.helpers.service_info.zeroconf.ZeroconfServiceInfo` (and the other `service_info` modules) | 2025.2 |
| Local `brand/` images | 2026.3 |

Set the floor to the highest requirement in use, and always set the key. A
`brand/` directory with a floor below 2026.3 was called dead weight
[#9554, #9555]; raising the floor to 2026.3.0 is the simplest fix.

## README

Non-blocking but raised at approval in 9 of 32:

- Lead installation with "search for it in HACS", keeping "add as a custom
  repository" only as a fallback. The store listing makes the custom
  repository steps obsolete on merge day.
- Document only what exists: entity tables, services, file names and
  example entity IDs must match the code [#10629, #9056, #9294].
- Do not advertise removed features [#10809].
- Link the PR to the current release, not a stale one [#9481].

## Licence

- `LICENSE` must be at the repository root, named `LICENSE` or
  `LICENSE.md` (`LICENSE.txt` was not accepted) [#8487], contain the actual
  licence text (a 0-byte file was caught) [#7333], and be present **in the
  latest release**, not just on the branch [#8487, #8426].

## Responding to a review

1. Read every item, including ones labelled non-blocking. Make a list.
2. For each item, fix the **class** of problem, not the quoted line. Grep
   for the same pattern across the integration and any bundled JS: every
   `innerHTML`, every log call that mentions the value, every `os.path` in
   async code, every service registration. Repeat findings of the same kind
   are what stretch reviews to four or five rounds.
3. If the change renames the domain or changes unique IDs, add a migration
   and say so in the release notes; it is a breaking change for existing
   users.
4. Bump `manifest.json` `version`, run the checks (pre-flight script, ruff,
   hassfest, HACS action), then publish a new **non-pre-release** release
   with a new version number. Never move a tag.
5. Merge `hacs/default` `master` into the PR branch; confirm the diff is one
   added line.
6. Update the three links in the PR description to the new release and the
   new workflow runs.
7. The author replies once, briefly, in their own words, mapping each
   review item to what changed and the release that contains it. Do not
   request a review or ping; if the PR was drafted, mark it ready for review.
8. If an item cannot be done, the author says why in that reply rather than
   skipping it silently.

The reply must be the author's own. The Open Home Foundation AI policy
(<https://developers.home-assistant.io/docs/ai_policy>) says: "Do not use AI
to generate answers to questions from maintainers. You should understand and
be able to explain your own work." Using AI to improve the grammar or clarity
of text the author wrote is allowed. An assistant's job at step 7 is to make
sure the author understands each fix and has the facts to hand, not to write
the comment.
