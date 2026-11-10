# Home Assistant best practice for custom integrations

Based on the Home Assistant developer docs
(<https://developers.home-assistant.io>) and the Integration Quality Scale
(<https://developers.home-assistant.io/docs/core/integration-quality-scale/>).
The quality scale is written for core integrations, and custom integrations
cannot declare a tier in their manifest, but its rules are the best available
definition of "done properly". Aim for Bronze as the floor and Silver as the
target; Gold items are listed for completeness.

## Contents

- [File layout](#file-layout)
- [Setup and teardown](#setup-and-teardown)
- [Config flow](#config-flow)
- [Async and I/O](#async-and-io)
- [Fetching data](#fetching-data)
- [Entities](#entities)
- [Devices](#devices)
- [Services (actions)](#services-actions)
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
  config_flow.py     ConfigFlow (+ OptionsFlow, reauth, reconfigure)
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
  `unknown`) that exist in the translations.
- Set a unique ID from something stable (serial number, MAC, account ID) with
  `await self.async_set_unique_id(...)` then
  `self._abort_if_unique_id_configured()`. Never use a name, IP, hostname or a
  user-changeable username. If no stable ID exists, use
  `self._async_abort_entries_match({...})`. The blueprint's
  `slugify(username)` is marked "do NOT use this in production".
- Connection details and credentials go in `entry.data`; tunable behaviour
  (scan interval is discouraged, see below) in `entry.options` via an
  `OptionsFlow`.
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
  Set `_attr_should_poll = False`.
- Set `PARALLEL_UPDATES` in each platform module (`0` for coordinator-backed
  read-only platforms, `1` for devices that cannot handle concurrent
  commands).

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
- Keep `extra_state_attributes` small and stable. Anything worth graphing or
  automating on is its own entity. Never put large or constantly changing
  blobs in attributes.
- Do not do I/O in properties. Properties read cached data.
- Command methods (`async_turn_on`, …) raise `HomeAssistantError` (or
  `ServiceValidationError` for bad input) on failure, then refresh state.
- `supported_features` lists only features whose methods are implemented,
  and command methods cope with optional arguments being absent.
- Expose only controls verified against real hardware.
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
  on, not persistent notifications or log spam.

## Tests and tooling

- `pytest-homeassistant-custom-component` gives the core test fixtures
  (`hass`, `MockConfigEntry`, `enable_custom_integrations`). Minimum useful
  suite: config flow success, each error path, duplicate abort, and setup /
  unload of the entry. Mock the library, not Home Assistant.
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
| brand images only in `home-assistant/brands` | `custom_components/<domain>/brand/` (HA 2026.3+) |
