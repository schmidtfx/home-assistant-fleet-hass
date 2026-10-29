# hafleet for Home Assistant

Shows [hafleet](https://github.com/schmidtfx/home-assistant-fleet)'s view of this Home Assistant instance as entities: open tasks, last sync, connection state, and one problem sensor per task kind (updates, repairs, stale backups, low disk space, …).

hafleet sends a `hafleet_status` event over the WebSocket connection it already has to this instance. Home Assistant never connects to hafleet, and this instance only receives its own data.

## Installation

1. In HACS, add `https://github.com/schmidtfx/home-assistant-fleet-hacs` as a custom repository (category: Integration) and install **hafleet**.
2. Restart Home Assistant.
3. Go to Settings → Devices & services → Add integration → **hafleet**.
4. Select the user whose access token hafleet uses. Events from any other user are ignored. hafleet's instance settings show the user ID to choose.
5. In hafleet, edit this instance and turn on **Publish status to Home Assistant**. The token must belong to an admin user, because firing events needs admin rights.

## Entities

All entities belong to one "hafleet" device.

| Entity | State | Attributes |
|---|---|---|
| `sensor.hafleet_open_tasks` | Number of open tasks (acknowledged tasks not counted) | `critical`, `warning`, `info`, `acknowledged` |
| `sensor.hafleet_last_sync` | When hafleet last read all data from this instance | |
| `sensor.hafleet_connection` | `connected`, `connecting`, `error`, `disabled` (diagnostic) | `warnings` |
| `binary_sensor.hafleet_<kind>` | On while an unacknowledged task of that kind is open | `count`, `max_severity`, `tasks` (title, severity, acknowledged) |

Sensors are created for the task kinds hafleet reports, and removed when hafleet stops reporting a kind.

## Availability

- hafleet sends the status when it changes, and at least every 5 minutes.
- Entities become unavailable when nothing arrived for 3 heartbeats (15 minutes), or when publishing is turned off in hafleet.
- The last status is saved, so entities keep their state across Home Assistant restarts until hafleet reports again.

Home Assistant's recorder stores events, including task titles (at most 20 per kind). Exclude the `hafleet_status` event type in your `recorder` configuration if you don't want them in the database.

## Example automation

```yaml
automation:
  - alias: "Notify about critical hafleet tasks"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.hafleet_open_tasks
        attribute: critical
        above: 0
    actions:
      - action: notify.notify
        data:
          message: "hafleet reports critical tasks on this instance."
```

## Brand images

The integration ships its icon in `custom_components/hafleet/brand/`, rendered from hafleet's favicon. Home Assistant 2026.3 and later shows it; older versions show a placeholder. The HACS store only shows logos from the [home-assistant/brands](https://github.com/home-assistant/brands) repository, so it shows none for hafleet.

## Development

```sh
uv venv --python 3.13 .venv
uv pip install --python .venv -r requirements_test.txt
.venv/bin/python -m pytest
```

## Releasing

1. Set `version` in `custom_components/hafleet/manifest.json`.
2. Add a `# Version X.Y.Z` section at the top of `CHANGES.md`, ending with a `---` line.
3. Commit, then tag and push: `git tag X.Y.Z && git push origin X.Y.Z`.

`.github/workflows/release.yml` fails if the tag (with or without a leading `v`) doesn't match the manifest version. Otherwise it creates a GitHub release whose body is the `CHANGES.md` section followed by GitHub's generated notes. HACS offers the releases as versions to install.
