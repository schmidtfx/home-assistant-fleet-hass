"""Constants for the hafleet integration."""

from __future__ import annotations

DOMAIN = "hafleet"

# Fired by hafleet over its WebSocket connection (see hafleet's internal/fleet/publish.go).
EVENT_STATUS = "hafleet_status"
SCHEMA_VERSION = 1

# The Home Assistant user whose token hafleet uses. Events from other users are ignored.
CONF_USER_ID = "user_id"

# Entities become unavailable when no event arrived for this many heartbeats.
STALE_HEARTBEATS = 3
DEFAULT_HEARTBEAT_SECONDS = 300

STORAGE_VERSION = 1

# Task kinds hafleet knows about; they have translated names. Unknown kinds
# (from a newer hafleet) still get an entity with a generated name.
KNOWN_KINDS = (
    "update",
    "repair",
    "reboot_required",
    "restart_required",
    "unhealthy",
    "unsupported",
    "reauth",
    "setup_failed",
    "backup_stale",
    "disk_low",
    "cert_expiring",
    "entities_unavailable",
    "battery_low",
    "log_errors",
)
