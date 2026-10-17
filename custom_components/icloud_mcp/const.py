"""Constants for the iCloud MCP integration."""

from __future__ import annotations

DOMAIN = "icloud_mcp"

# LLM API id under which the tools are exposed (selectable in the MCP Server integration)
LLM_API_ID = "icloud_mcp"
LLM_API_NAME = "iCloud (Kalender, Kontakte, Mail, Notizen)"

CONF_APPLE_ID = "apple_id"
CONF_APP_PASSWORD = "app_password"
CONF_FROM_ADDRESS = "from_address"

# Options
CONF_ENABLE_CALENDAR = "enable_calendar"
CONF_ENABLE_CONTACTS = "enable_contacts"
CONF_ENABLE_MAIL = "enable_mail"
CONF_ENABLE_NOTES = "enable_notes"
CONF_READ_ONLY = "read_only"
CONF_ALLOW_SEND_MAIL = "allow_send_mail"
CONF_ALLOW_DELETE = "allow_delete"
CONF_MAX_RESULTS = "max_results"
CONF_RULES_AUTO = "rules_auto"
CONF_RULES_INTERVAL = "rules_interval"

DEFAULT_ENABLE_CALENDAR = True
DEFAULT_ENABLE_CONTACTS = True
DEFAULT_ENABLE_MAIL = True
DEFAULT_ENABLE_NOTES = True
DEFAULT_READ_ONLY = False
DEFAULT_ALLOW_SEND_MAIL = True
DEFAULT_ALLOW_DELETE = True
DEFAULT_MAX_RESULTS = 50
DEFAULT_RULES_AUTO = True
DEFAULT_RULES_INTERVAL = 5  # minutes
MIN_RULES_INTERVAL = 1
MAX_RULES_INTERVAL = 240
MAX_RESULTS_LIMIT = 200

# iCloud endpoints
CALDAV_URL = "https://caldav.icloud.com/"
CARDDAV_URL = "https://contacts.icloud.com/"
IMAP_HOST = "imap.mail.me.com"
IMAP_PORT = 993
SMTP_HOST = "smtp.mail.me.com"
SMTP_PORT = 587

NOTES_MAILBOX = "Notes"

REQUEST_TIMEOUT = 30
