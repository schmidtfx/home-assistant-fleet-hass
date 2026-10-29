# Version 0.1.0

*First release. Shows [hafleet](https://github.com/schmidtfx/home-assistant-fleet)'s view of this Home Assistant instance as entities, so you can build automations, dashboards and notifications on the tasks hafleet finds. Requires Home Assistant 2025.2 or later and a hafleet version with the **Publish status to Home Assistant** setting.*

## New Features

**Push-based status from hafleet, no inbound connection**

hafleet fires a `hafleet_status` event over the WebSocket connection it already holds to this instance. Home Assistant never connects to hafleet, needs no URL or credentials for it, and only ever receives this instance's own data. hafleet sends the status when something changes, and at least once per heartbeat (5 minutes by default).

**Config flow with a trusted sender**

Settings → Devices & services → Add integration → **hafleet** asks for one thing: the Home Assistant user whose access token hafleet uses. Only events fired by that user are accepted; events from any other user are ignored, so other clients can't fake a status. hafleet's instance settings show the user ID to pick. The integration allows a single config entry.

**Sensors**

All entities belong to one "hafleet" service device, linked to the hafleet project.

- `sensor.hafleet_open_tasks` — number of open tasks, not counting acknowledged ones. Attributes `critical`, `warning`, `info` and `acknowledged` break the count down, so an automation can trigger on critical tasks only (see the README example).
- `sensor.hafleet_last_sync` — timestamp of when hafleet last read all data from this instance.
- `sensor.hafleet_connection` — hafleet's connection state to this instance: `connected`, `connecting`, `error` or `disabled`, with sync problems in the `warnings` attribute. Diagnostic entity.

**One problem binary sensor per task kind**

`binary_sensor.hafleet_<kind>` is on while hafleet has an unacknowledged task of that kind. Attributes: `count`, `max_severity`, and `tasks` (title, severity, acknowledged for each task). Kinds with translated names:

Updates available · Repairs · Host reboot required · Restart required · System unhealthy · Unsupported system · Re-authentication required · Integration setup failed · Backup stale · Disk space low · Certificate expiring · Entities unavailable · Battery low · Log errors

Sensors are created for the kinds hafleet reports and removed when it stops reporting a kind. A kind added in a newer hafleet still gets a sensor, with a name generated from the kind.

**Availability and restarts**

- Entities become unavailable when no status arrived for 3 heartbeats (15 minutes by default), or right away when publishing is turned off in hafleet.
- The last status is saved to Home Assistant's storage, so entities keep their state across restarts until hafleet reports again. Removing the integration deletes the saved status.

**Integration icon**

The icon ships in `custom_components/hafleet/brand/` and is shown by Home Assistant 2026.3 and later. The HACS store only shows logos from the home-assistant/brands repository, so it shows none for hafleet.

## Notes

- **Admin token required.** Firing events needs admin rights, so hafleet's token for this instance must belong to an admin user.
- **Recorder.** The recorder stores events, including task titles (at most 20 per kind). Exclude the `hafleet_status` event type in your `recorder` configuration if you don't want them in the database.
- **Schema version.** Events carry a schema version (currently `1`). Events with a different schema are ignored with a log warning asking you to update the integration.

## Technical Notes

- Event data is treated as untrusted input: every field is type-checked before use, and task kinds must match `^[a-z0-9_]{1,64}$`.
- Entities don't poll. `HafleetHub` listens on the event bus, saves the status with a 10-second delay, and checks for staleness once a minute.
- Tests cover the config flow and the entities (`tests/test_config_flow.py`, `tests/test_entities.py`). CI runs hassfest, HACS validation and pytest.

---
