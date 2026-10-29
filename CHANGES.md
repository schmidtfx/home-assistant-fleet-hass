# Version 0.1.0

*First release. Shows hafleet's view of this Home Assistant instance as entities.*

## New Features

- Config flow to select the Home Assistant user whose token hafleet uses; events from any other user are ignored.
- Listens for the `hafleet_status` event that hafleet fires over its existing WebSocket connection. Home Assistant never connects to hafleet.
- Sensors for open tasks, last sync and connection state, and one problem binary sensor per task kind (updates, repairs, stale backups, low disk space, …).
- Integration icon in `custom_components/hafleet/brand/` (Home Assistant 2026.3 and later).

---
