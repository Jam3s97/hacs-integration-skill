# Home Assistant best practice for custom integrations

Based on the Home Assistant developer docs
(<https://contributors.home-assistant.io>), the Integration Quality Scale
(<https://contributors.home-assistant.io/core/quality-scale/>) and the rules
core gives its own AI agents (`AGENTS.md` and the `ha-integration-knowledge`
skill in <https://github.com/home-assistant/core>, as of November 2026),
adapted where a custom integration differs.
The quality scale is written for core integrations, and custom integrations
cannot declare a tier in their manifest, but its rules are the best available
definition of "done properly". Aim for Bronze as the floor and Silver as the
target; Gold items are listed for completeness.

## Contents

- [File layout](#file-layout)
- [Setup and teardown](#setup-and-teardown)
- [Config flow](#config-flow)
- [OAuth 2.0 accounts](#oauth-20-accounts)
- [Config subentries](#config-subentries)
- [Async and I/O](#async-and-io)
- [Fetching data](#fetching-data)
- [Bluetooth devices](#bluetooth-devices)
- [Entities](#entities)
- [Devices](#devices)
- [Services (actions)](#services-actions)
- [Exceptions and validation](#exceptions-and-validation)
- [Translations](#translations)
- [Security and good citizenship](#security-and-good-citizenship)
- [Bundled frontend code](#bundled-frontend-code)
- [Diagnostics, repairs, logging](#diagnostics-repairs-logging)
- [Tests and tooling](#tests-and-tooling)
- [Quality scale checklist](#quality-scale-checklist)
- [Outdated patterns and their replacements](#outdated-patterns-and-their-replacements)

## File layout

```
custom_components/<domain>/
  __init__.py        async_setup_entry / async_unload_entry
  manifest.json
  config_flow.py     ConfigFlow (+ OptionsFlow, reauth, reconfigure, subentry flows)
  application_credentials.py   only for OAuth 2.0 integrations
  const.py           DOMAIN, LOGGER, constants
  coordinator.py     DataUpdateCoordinator subclass(es)
  data.py            runtime_data dataclass + typed ConfigEntry alias
  entity.py          shared base entity
  sensor.py …        one module per platform
  diagnostics.py
  services.yaml      only if the integration registers actions
  icons.json         entity/service icons
  translations/en.json
  brand/icon.png
```

Protocol and API code belongs in a separate library on PyPI, listed in
`requirements` and pinned. The integration is glue: it maps library objects to
Home Assistant entities. The blueprint keeps a small `api.py` in-tree, which
is fine for a thin HTTP wrapper but should move to a library as it grows.
Protocol parsing and device state machines are library code; if unsure
whether something belongs in the integration, ask the user before inlining
it. Do not work around a library's bug or limitation in the integration: fix
the library and bump the requirement.

A constant used by more than one module goes in `const.py`; one used by a
single module stays in that module (tests do not count as a user). That
includes entity descriptions and service schemas. Never import a constant
from one platform module into another.

## Setup and teardown

```python
type AwesomeConfigEntry = ConfigEntry[AwesomeData]

async def async_setup_entry(hass: HomeAssistant, entry: AwesomeConfigEntry) -> bool:
    client = AwesomeClient(entry.data[CONF_HOST], async_get_clientsession(hass))
    coordinator = AwesomeCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = AwesomeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: AwesomeConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
```

- Store per-entry objects in `entry.runtime_data`, never in
  `hass.data[DOMAIN][entry.entry_id]` for new code. Code that reads
  `runtime_data` from outside setup (services, websocket handlers) must check
  the entry is loaded first.
- Test the connection during setup. Raise `ConfigEntryNotReady` when the
  device or service is unreachable (Home Assistant retries),
  `ConfigEntryAuthFailed` when credentials are rejected (starts reauth),
  `ConfigEntryError` for permanent failures.
  `async_config_entry_first_refresh()` does this for coordinators.
- Unload must close connections, cancel tasks and remove listeners. Register
  cleanups with `entry.async_on_unload(...)`.
- Register services in `async_setup`, not `async_setup_entry`, so they exist
  regardless of entry state and are not registered twice.
- Changing stored data shape: bump `VERSION` / `MINOR_VERSION` on the flow and
  implement `async_migrate_entry`.
- Implement `async_remove_config_entry_device` if users should be able to
  delete stale devices, and remove devices that disappear from the API.

## Config flow

- `"config_flow": true` and UI-only setup. No `configuration.yaml` schema for
  new integrations.
- Validate input by actually connecting before `async_create_entry`. Map
  failures to `errors["base"]` keys (`cannot_connect`, `invalid_auth`,
  `unknown`) that exist in the translations. Do not log the known failures.
  Catch anything unexpected, log it with `_LOGGER.exception()` and map it to
  `unknown`. Do not mix translated and untranslated text in an error shown
  to the user.
- Set a unique ID from something stable (serial number, MAC, account ID) with
  `await self.async_set_unique_id(...)` then
  `self._abort_if_unique_id_configured()`. Never use a name, IP, hostname or a
  user-changeable username. If no stable ID exists, use
  `self._async_abort_entries_match({...})`. The blueprint's
  `slugify(username)` is marked "do NOT use this in production".
- Only one instance makes sense (a public API with no account or host):
  set `"single_config_entry": true` in `manifest.json`. Do not fake it with
  `async_set_unique_id(DOMAIN)`.
- Connection details and credentials go in `entry.data`; tunable behaviour
  (scan interval is discouraged, see below) in `entry.options` via an
  `OptionsFlow`.
- Options must take effect the way the README says they do. Either read
  `entry.options` (falling back to `entry.data`) at the point the value is
  used, or register `entry.async_on_unload(entry.add_update_listener(...))`
  and reload the entry when options change. A value read once in
  `async_setup_entry` and kept in a closure or attribute goes stale: later
  callbacks, such as adding newly discovered devices, keep using the old
  value until a restart or reload.
- Use selectors (`TextSelector(type=PASSWORD)`, `NumberSelector`, …).
  Passwords, tokens and API keys must use a password-type field.
- Add `async_step_reauth` / `async_step_reauth_confirm` when credentials can
  expire, and `async_step_reconfigure` so host or credentials can be changed
  without re-adding.
- Add discovery steps (`zeroconf`, `dhcp`, `ssdp`, `bluetooth`, `usb`) when
  the device can be found on the network, and update the stored host when a
  known device is rediscovered at a new address.
- Do not let users set the entry title or entity names in the flow; derive
  them from the device.
- Do not expose a user-configurable polling interval. Pick a sensible one;
  users who need another can disable polling and call
  `homeassistant.update_entity`.

## OAuth 2.0 accounts

For a cloud service that signs users in with OAuth 2.0, use Home Assistant's
helpers instead of writing token handling (developer docs: "OAuth 2.0
support" and "Application credentials").

- Add `"application_credentials"` to manifest `dependencies` and an
  `application_credentials.py` with `async_get_authorization_server`
  returning the provider's `authorize_url` and `token_url`. Return
  `LocalOAuth2ImplementationWithPkce` from `async_get_auth_implementation`
  only if the provider requires PKCE.
- Users enter their own client ID and secret in the Application Credentials
  dialog. Nabu Casa account linking is not available to a custom
  integration, and a client secret committed to the repository is a
  security finding in review (see Security below). Put instructions for
  creating credentials, with a link to the provider's console, under the
  `application_credentials` `description` key in `translations/en.json`;
  fill URLs in with `async_get_description_placeholders`.
- The config flow subclasses
  `config_entry_oauth2_flow.AbstractOAuth2FlowHandler`, sets scopes in
  `extra_authorize_data`, and in `async_oauth_create_entry` sets a unique ID
  from the account (fetched with the new token), not from the token itself.
- Always add reauth. In `async_oauth_create_entry`, when
  `self.source == SOURCE_REAUTH`, call `_abort_if_unique_id_mismatch()` and
  `async_update_reload_and_abort(self._get_reauth_entry(), data_updates=data)`
  so a different account cannot replace the original.
- In setup, get the implementation with
  `async_get_config_entry_implementation`, wrap it in `OAuth2Session`, and
  hand the session to the library, which calls `async_ensure_token_valid()`
  before each request. Do a first coordinator refresh (or call
  `async_ensure_token_valid()` in `async_setup_entry`) before forwarding
  platforms.
- Let the helper's exceptions propagate. The token request errors are
  already `ConfigEntryAuthFailed` or `ConfigEntryNotReady` subclasses with
  translated messages, and a coordinator handles them. Do not catch them to
  re-raise as the same thing, and keep token logic out of entities.
- Do not accept client credentials in `configuration.yaml`.

## Config subentries

Use subentries when one account or connection holds several user-chosen
things that are each added, changed and removed on their own: locations for
a weather service, rooms, conversation agents on one API key. The parent
entry keeps the credentials; each subentry keeps one item's settings. Do not
use options or a list in `entry.data` for this.

- In the config flow class, return the types from the classmethod
  `async_get_supported_subentry_types(cls, config_entry)`, e.g.
  `{"location": LocationSubentryFlowHandler}`. Each handler subclasses
  `ConfigSubentryFlow` and returns `SubentryFlowResult`.
- A subentry flow starts only from `user` or `reconfigure`: no discovery and
  no reauth (reauth belongs to the parent entry). In `reconfigure`, read the
  parent with `self._get_entry()` and the item with
  `self._get_reconfigure_subentry()`.
- A subentry unique ID only needs to be unique within its parent entry.
- In setup, loop over `entry.subentries.values()` (check `subentry_type`,
  read `subentry.data`) and add each item's entities with
  `async_add_entities(entities, config_subentry_id=subentry.subentry_id)`, so
  they and their device belong to that subentry and go when it is removed. A
  device belongs to at most one subentry, and child devices must be in the
  same subentry as their parent.
- Strings go under `config_subentries.<type>` in `translations/en.json`,
  with the same `step` / `error` / `abort` layout as `config`.
- A repair can hand off to a subentry's reconfigure flow through
  `hass.config_entries.subentries.async_init`.

## Async and I/O

Home Assistant runs one event loop. Anything that blocks it freezes the whole
system, and Home Assistant logs "Detected blocking call" against the
integration.

- No `requests`, `urllib`, `time.sleep`, `open()`, `os.listdir`, `subprocess`,
  `socket` or heavy parsing (large XML/JSON, image work) in `async def` code.
- Prefer async libraries. For a sync library or file access:
  `await hass.async_add_executor_job(func, arg)`.
- HTTP: `async_get_clientsession(hass)` (aiohttp) or `get_async_client(hass)`
  (httpx). Use `async_create_clientsession` only when you need separate
  cookies. Never `aiohttp.ClientSession()` directly.
- Timeouts: `async with asyncio.timeout(10):`.
- Background work: `entry.async_create_background_task(hass, coro, name)` so
  it is cancelled on unload. Timers: `async_track_time_interval` with the
  unsubscribe passed to `entry.async_on_unload`.
- Methods prefixed `async_` or decorated `@callback` run on the loop; plain
  methods on entities (`turn_on`, `update`) run in the executor. Do not mix:
  calling `async_write_ha_state` from a thread is an error, use
  `schedule_update_ha_state`.
- Importing a heavy module at call time blocks too; import at module top.
- Times come from `homeassistant.util.dt` (`dt_util.utcnow()`, `dt_util.now()`,
  `dt_util.as_local()`), which are timezone-aware; never naive `datetime.now()`.
- `ZoneInfo(name)` reads from disk: use
  `await dt_util.async_get_time_zone(name)`.
- List every core component the code uses (`http`, `frontend`,
  `websocket_api`, `bluetooth`…) in manifest `dependencies` or
  `after_dependencies`; hassfest fails otherwise.

## Fetching data

- Polling one endpoint for many entities: one `DataUpdateCoordinator`
  subclass, entities inherit `CoordinatorEntity`. Pass `config_entry=` to the
  coordinator constructor.
- In `_async_update_data` raise `UpdateFailed` for communication errors and
  `ConfigEntryAuthFailed` for auth errors. Do not catch and log; the
  coordinator logs once when it goes unavailable and once when it recovers.
- Use `_async_setup` on the coordinator for one-time initial loading.
- Choose an interval that suits the source: seconds to a minute for local
  devices, minutes for cloud APIs. A few seconds against a cloud API is
  abusive and gets flagged. Respect rate limits
  (`UpdateFailed(retry_after=...)`).
- Push sources: subscribe in `async_added_to_hass`, unsubscribe via
  `self.async_on_remove(...)`, and call `async_write_ha_state()` on updates.
  Set `_attr_should_poll = False`. Keep `async_added_to_hass` and
  `async_will_remove_from_hass` symmetrical: whatever one sets up the other
  tears down, and nothing is torn down that was not set up there.
- Set `PARALLEL_UPDATES` in each platform module (`0` for coordinator-backed
  read-only platforms, `1` for devices that cannot handle concurrent
  commands).

## Bluetooth devices

Home Assistant owns the Bluetooth adapters, including remote ESPHome
proxies. An integration uses them through the `bluetooth` component and
never opens its own scanner (developer docs: "Bluetooth", "Bluetooth API"
and "Fetching Bluetooth data").

- Manifest: `"dependencies": ["bluetooth_adapters"]` so remote adapters are
  connected before setup, a `bluetooth` matcher list (`local_name`,
  `service_uuid`, `service_data_uuid`, `manufacturer_id`,
  `manufacturer_data_start`; no wildcard in the first three characters of
  `local_name`), and `"connectable": false` in the matcher when the device
  only needs advertisements, so passive proxies work too.
- Config flow: `async_step_bluetooth(discovery_info)` sets the unique ID from
  `discovery_info.address`. The `user` step offers devices from
  `bluetooth.async_discovered_service_info(hass)` rather than asking for a
  MAC address. Reject discovered devices that need a connection when
  `discovery_info.connectable` is false.
- Choose the coordinator by how the device reports:
  - advertisements only, sensor-like:
    `PassiveBluetoothProcessorCoordinator`;
  - advertisements, but some values need a connection:
    `ActiveBluetoothProcessorCoordinator`;
  - advertisements, not sensor-like (lights, locks…):
    `PassiveBluetoothCoordinator` or `ActiveBluetoothDataUpdateCoordinator`;
  - connection only, no useful advertisements: a normal
    `DataUpdateCoordinator`.
  Processor coordinators are started with `entry.async_on_unload(coordinator.async_start())`
  after the platforms are forwarded.
- Connecting: get the device with
  `bluetooth.async_ble_device_from_address(hass, address, connectable=True)`
  and raise `ConfigEntryNotReady` if it is `None`. Use a fresh `BleakClient`
  per connection, a timeout of at least ten seconds, and
  `bleak-retry-connector`. If a library needs a scanner, pass it
  `bluetooth.async_get_scanner(hass)`.
- Availability: use `bluetooth.async_track_unavailable` or
  `async_address_present`, not a timer of your own.
  `bluetooth.async_address_reachability_diagnostics` gives a readable reason
  for logs and errors; do not parse it.
- `iot_class` is usually `local_push` for advertisement-driven devices and
  `local_polling` when the integration connects to poll.

## Entities

```python
class AwesomeSensor(AwesomeEntity, SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.device.serial}_{description.key}"
```

- `_attr_has_entity_name = True`; the entity name is only the data point
  ("Temperature"), the device supplies the prefix. Main feature of a device:
  `_attr_name = None`.
- `unique_id` is stable and unique within platform + domain: device serial
  plus a key. Never derived from name, IP or config-entry title. Without one
  the entity cannot be renamed or managed in the UI.
- Describe entities with `EntityDescription` dataclasses (with `value_fn`
  lambdas) instead of one class per sensor.
- Use the platform's native properties: `native_value`,
  `native_unit_of_measurement`, `device_class`, `state_class`
  (`MEASUREMENT`, `TOTAL_INCREASING` for energy-style counters),
  `suggested_display_precision`. Units from `homeassistant.const` enums
  (`UnitOfTemperature.CELSIUS`).
- Pick the right platform. A read-only boolean is a `binary_sensor` with a
  device class, not a sensor with "on"/"off". Something settable is
  `number`/`select`/`switch`, not a service. Firmware goes in `update`.
- `entity_category = EntityCategory.DIAGNOSTIC` or `CONFIG` for non-primary
  entities; `entity_registry_enabled_default = False` for noisy or rarely
  used ones.
- `available` must go false when the device is unreachable
  (`CoordinatorEntity` handles coordinator failure; add device-level checks).
  When overriding it, combine with the parent:
  `return super().available and ...`.
- Use `_attr_*` attributes rather than properties for values that never
  change. Make them class attributes only when every instance shares the
  value; otherwise set them in `__init__`.
- The platform base class (`SensorEntity`, `TrackerEntity`, …) is a stable
  API. Do not redeclare attributes, properties or methods it already
  provides, and do not guard against its behaviour changing.
- Do not add entities for data Home Assistant deliberately exposes only
  through an action, for example weather forecasts
  (`weather.get_forecasts`).
- Keep `extra_state_attributes` small, stable and JSON-serialisable (convert
  `datetime` and library objects to strings or numbers). Anything worth graphing or
  automating on is its own entity. Never put large or constantly changing
  blobs in attributes.
- Do not do I/O in properties. Properties read cached data.
- Command methods (`async_turn_on`, …) raise `HomeAssistantError` (or
  `ServiceValidationError` for bad input) on failure, then refresh state.
- `supported_features` lists only features whose methods are implemented,
  and command methods cope with optional arguments being absent.
- Expose only controls verified against real hardware.
- Respect the user's choices in the entity registry. When the integration
  enables, disables, shows or hides its own entities in bulk, only change
  entries it set itself: re-enable only where `disabled_by is
  er.RegistryEntryDisabler.INTEGRATION` and unhide only where `hidden_by is
  er.RegistryEntryHider.INTEGRATION`. Entries with `USER` (or any other
  disabler) stay as the user left them.
- Do not set `entity_id` by hand and do not hardcode `icon` when a device
  class already provides one; other icons go in `icons.json`.

## Devices

- Provide `DeviceInfo` with `identifiers={(DOMAIN, stable_id)}`, plus
  `manufacturer`, `model`, `sw_version`, `serial_number`,
  `configuration_url`, and `connections` (MAC) where known. Sub-devices use
  `via_device`.
- A service-type integration with no physical device uses
  `entry_type=DeviceEntryType.SERVICE`.
- Only create, modify or remove devices and entities that belong to this
  integration's config entries.

## Services (actions)

- Describe every service in `services.yaml` and translate names and
  descriptions. The voluptuous schema must accept exactly the fields
  documented; mismatches surface as `extra keys not allowed`.
- Validate input (ranges, colours, icons, IP addresses) in the schema.
- Services that return data use `supports_response=SupportsResponse.ONLY` or
  `OPTIONAL` and return a JSON-serialisable dict.
- Prefer entity services (`platform.async_register_entity_service`) over
  services that take an entity ID string.
- Raise `ServiceValidationError` / `HomeAssistantError` with translated
  messages.
- For an integration's first actions, define the action names and fields as
  `StrEnum`s named `<Prefix>Service` and `<Prefix>ServiceArgument` (the
  integration's usual class prefix, e.g. `AwesomeService`), in `services.py`,
  or in `const.py` when other modules need them. Use the members for
  registration, schema keys and `call.data` lookups instead of raw strings.
  Members match what `services.yaml` lists, no more. Shared selector fields
  (`config_entry_id`, `device_id`, `entity_id`) keep using the
  `homeassistant.const` constants. This is the convention for new work, not
  a reason to rewrite an integration that already has actions.
- Actions that change configuration or have security implications require
  an admin user: register them with
  `homeassistant.helpers.service.async_register_admin_service`.

## Exceptions and validation

- Keep `try` blocks as small as possible: wrap the call that can raise, not
  the whole function, and do not catch exceptions from code that is not
  expected to raise them.
- Do not pass the original exception text (`str(err)`) as a placeholder of a
  translated exception (`HomeAssistantError`, `ServiceValidationError`,
  `ConfigEntryNotReady`, `UpdateFailed`). It mixes untranslated text into a
  translated message, and Home Assistant already logs these. Raise more
  specific, translatable errors from one central handler (a decorator or
  helper method).
- Trust validation. When a schema guarantees a key is present, index it
  directly (`data["key"]`), not `.get("key")`, so a broken assumption fails
  loudly. Do not add defensive checks for action fields the schema and
  entity filters already enforce; add guards only where a value bypasses
  validation or is transformed unsafely.
- An `assert` that exists only to narrow a type for the type checker goes
  behind `if TYPE_CHECKING:` so it does not run.

## Translations

- Custom integrations ship `translations/en.json` directly. `strings.json` is
  a core build input and is **not** read for custom integrations. English is
  mandatory even when the primary audience uses another language.
- Every config-flow `step_id`, field, `errors` key and `abort` reason used in
  code has an entry. hassfest validates the file's structure.
- Entities use `_attr_translation_key` with names under
  `entity.<platform>.<key>.name`; state values and attributes can be
  translated the same way.
- Exceptions shown to users use `translation_domain` / `translation_key`.

## Security and good citizenship

These come up repeatedly in hacs/default reviews.

- No secrets in the repository: no shared API keys, client secrets or
  tokens baked into `const.py`. Each user supplies their own credentials.
- Talk to the vendor's production endpoints, not a development or staging
  host.
- Keep TLS verification on; if a device needs it off, make it an explicit
  option.
- Redact credentials, tokens, location and serials in logs and diagnostics.
- Stay inside your own namespace: your own `.storage` key
  (`Store(hass, VERSION, f"{DOMAIN}.something")`), your own domain's
  services, events prefixed with the domain. Do not read another
  integration's stored tokens, write to its registry entries, or edit the
  user's YAML files (`automations.yaml`, `scripts.yaml`, dashboards).
- Use public Home Assistant APIs. Importing private helpers or poking at
  internals breaks on upgrade and is grounds for rejection.
- WebSocket commands and HTTP views that change things need
  `@websocket_api.require_admin` / `requires_auth = True` and input
  validation.
- Do not download and execute code at runtime (remote JS from a CDN, pip
  installs outside `requirements`, auto-updaters). Everything that runs ships
  in the release.
- Do not write files outside the integration's own storage or
  `persistent_directory`.

## Bundled frontend code

HACS installs only `custom_components/<domain>/` for an integration. A card or
panel in the repository root (`www/`, `dist/`) is never delivered.

- Ship the JS inside the integration directory and serve it with
  `await hass.http.async_register_static_paths([StaticPathConfig(url, path, cache)])`,
  then `frontend.add_extra_js_url(hass, url)`. Do not copy files into
  `config/www/` or register `/local/` resources.
- Set the `hacs.json` `homeassistant` minimum to a version that has the APIs
  used (`StaticPathConfig` needs 2024.7+).
- Escape every value interpolated into HTML: entity names, attributes,
  service data and card configuration (including colours, sizes, icons and
  `id` attributes). Prefer `textContent` or Lit templates over `innerHTML`.

## Diagnostics, repairs, logging

- `diagnostics.py` with `async_get_config_entry_diagnostics`, using
  `async_redact_data` for anything sensitive.
- Log at `debug` for routine events. One `warning`/`info` when a device goes
  unavailable and one when it returns, not one per poll.
- Lazy formatting: `_LOGGER.debug("Got %s", value)`. No `print`.
- Use repair issues (`ir.async_create_issue`) for problems the user must act
  on, not persistent notifications or log spam. Only raise one for something
  the user can resolve. The issue text says what the problem is, why it
  matters, the exact steps to fix it (numbered when there are several; not
  just "update firmware") and what to expect afterwards, with context such
  as the device name. Severity: `WARNING` for something that will break
  later, `ERROR` for something needing attention now, `CRITICAL` only for
  extreme cases.

## Tests and tooling

- `pytest-homeassistant-custom-component` gives the core test fixtures
  (`hass`, `MockConfigEntry`, `enable_custom_integrations`). Minimum useful
  suite: config flow success, each error path, duplicate abort, and setup /
  unload of the entry. Mock the library, not Home Assistant.
- Test through Home Assistant: set up the config entry, then assert on
  states, registries and service calls. Do not call or mock the
  integration's own internals
  (<https://contributors.home-assistant.io/core/development/tests/#test-through-home-assistant>).
- Shared mocks are fixtures in `conftest.py`, including a
  `mock_config_entry` (with a `unique_id` when the integration's entries
  have one), so every platform test reuses them.
- Load substantial or reused mock API data from JSON files in
  `tests/fixtures/` with `load_json_object_fixture` /
  `load_json_array_fixture` (from
  `pytest_homeassistant_custom_component.common`) instead of building it
  inline.
- Use snapshot tests (syrupy's `snapshot` fixture) for entity states and
  diagnostics, and do not also assert by hand what a snapshot covers.
- Patch objects where they are used, not where they are defined.
- To give one test different mock data, parametrize the fixture that
  provides it (`pytest.mark.parametrize(..., indirect=True)` when it reads
  `request.param`) rather than patching again inside the test. Merge
  near-identical tests with `parametrize` and avoid branching in a test.
- Use `Platform` members and `ATTR_*` constants in tests where they exist,
  not string literals. Annotate test function parameters.
- `ruff check` and `ruff format` (the blueprint ships a config).
- Type hints throughout; `mypy --strict` if you want the Platinum bar.
- CI: lint, tests, hassfest and HACS action on push, PR and a nightly
  schedule, so breakage from a new Home Assistant release shows up early.
- Run the integration in a real Home Assistant (`scripts/develop` in the
  blueprint) and watch the log for blocking-call and deprecation warnings.
  Deprecations name the release in which the old API is removed.

## Quality scale checklist

Bronze (baseline):

- [ ] Set up via config flow, with field descriptions (`data_description`)
- [ ] Connection tested in the config flow and again at setup
- [ ] Unique config entry (no duplicates)
- [ ] `entry.runtime_data` used
- [ ] Entities have unique IDs and `has_entity_name = True`
- [ ] Event subscriptions made in `async_added_to_hass` and removed on removal
- [ ] Appropriate polling interval
- [ ] Services registered in `async_setup`
- [ ] Shared patterns in common modules (`coordinator.py`, `entity.py`)
- [ ] Dependencies are on PyPI, built from public source, pinned
- [ ] Brand assets present
- [ ] Docs: description, install steps, removal steps, actions
- [ ] Config flow tests

Silver (reliability):

- [ ] Config entry unloads cleanly
- [ ] Entities become unavailable when the source is, logged once each way
- [ ] Reauthentication flow
- [ ] Service calls raise on failure
- [ ] `PARALLEL_UPDATES` set
- [ ] Active code owner
- [ ] Docs: configuration parameters, installation parameters
- [ ] Good test coverage

Gold (experience):

- [ ] Devices created with full `DeviceInfo`
- [ ] Discovery, and address updates from discovery
- [ ] Reconfigure flow
- [ ] Diagnostics
- [ ] Entity, exception and icon translations
- [ ] Entity categories, device classes, disabled-by-default where apt
- [ ] Dynamic devices added, stale devices removed
- [ ] Repair issues where useful
- [ ] Docs: supported devices, functions, data update method, use cases,
      examples, known limitations, troubleshooting

Platinum: fully async dependency, injected web session, strict typing.

## Outdated patterns and their replacements

| Seen in code | Use instead |
| --- | --- |
| `hass.data[DOMAIN][entry.entry_id] = …` | `entry.runtime_data` |
| `async_forward_entry_setup` / `hass.async_create_task(…forward…)` | `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)` |
| `async_setup_platform` + YAML `PLATFORM_SCHEMA` | config entry + `async_setup_entry` |
| `TEMP_CELSIUS`, `ENERGY_KILO_WATT_HOUR`, `POWER_WATT` | `UnitOfTemperature`, `UnitOfEnergy`, `UnitOfPower` |
| `DEVICE_CLASS_*`, `STATE_CLASS_*` constants | `SensorDeviceClass`, `SensorStateClass` enums |
| `SUPPORT_*` feature constants | `<Platform>EntityFeature` enums |
| `state` / `unit_of_measurement` on sensors | `native_value` / `native_unit_of_measurement` |
| `self.config_entry = config_entry` in `OptionsFlow.__init__` | drop it; `self.config_entry` is provided (2024.12+) |
| `FlowResult` from `data_entry_flow` in a config flow | `ConfigFlowResult` |
| `hass.helpers.<x>` | import the helper module directly |
| `hass.http.register_static_path` | `await hass.http.async_register_static_paths([...])` |
| `async_get_registry` | `er.async_get(hass)` / `dr.async_get(hass)` |
| `device_state_attributes` | `extra_state_attributes` |
| `hass.loop.create_task`, `asyncio.get_event_loop()` | `hass.async_create_task`, `entry.async_create_background_task` |
| `async_timeout.timeout` | `asyncio.timeout` |
| `strings.json` only | `translations/en.json` |
| Legacy device tracker (`get_scanner`, `async_setup_scanner`, `DeviceScanner`, `see` / `async_see`, `known_devices.yaml`) | config entry with `ScannerEntity` / `TrackerEntity`; removed in HA 2027.5. Do not import the YAML, read or edit `known_devices.yaml`, or reuse the old entity IDs; tell users to remove the platform and their `known_devices.yaml` entries, restart, then set up from the UI |
| brand images only in `home-assistant/brands` | `custom_components/<domain>/brand/` (HA 2026.3+) |
