"""Constants for the Frieda integration."""

from __future__ import annotations

DOMAIN = "friedafetch"

# LLM API id under which the tools are exposed (selectable in the MCP Server integration)
LLM_API_ID = "friedafetch"
LLM_API_NAME = "Frieda – iCloud (Calendar, Contacts, Mail, Notes)"

CONF_APPLE_ID = "apple_id"
CONF_APP_PASSWORD = "app_password"  # noqa: S105 - option key, not a secret  # nosec B105
CONF_FROM_ADDRESS = "from_address"
CONF_ACCOUNT_LABEL = "account_label"

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

# Security guard rails (options)
CONF_LIMIT_MAIL_MODIFY = "limit_mail_modify"  # moves/deletes/flag changes per hour, 0 = unlimited
CONF_LIMIT_MAIL_SEND = "limit_mail_send"  # sent mails per hour
CONF_LIMIT_ITEM_DELETE = "limit_item_delete"  # deleted events/contacts/notes per hour
CONF_SEND_POLICY = "send_policy"  # any | contacts | allowlist
CONF_SEND_ALLOWLIST = "send_allowlist"  # addresses or domains
CONF_SEND_MAX_RECIPIENTS = "send_max_recipients"
CONF_SEND_ALLOW_BCC = "send_allow_bcc"
CONF_PROTECTED_CALENDARS = "protected_calendars"  # read-only calendars (ids or names)
CONF_PROTECTED_MAILBOXES = "protected_mailboxes"  # read-only mailboxes
CONF_HIDDEN_MAILBOXES = "hidden_mailboxes"  # mailboxes not exposed at all

DEFAULT_LIMIT_MAIL_MODIFY = 300
DEFAULT_LIMIT_MAIL_SEND = 20
DEFAULT_LIMIT_ITEM_DELETE = 50
DEFAULT_SEND_POLICY = "any"
DEFAULT_SEND_MAX_RECIPIENTS = 10
DEFAULT_SEND_ALLOW_BCC = True
SEND_POLICIES = ("any", "contacts", "allowlist")

# Audit log
AUDIT_EVENT = "friedafetch_action"
AUDIT_MAX_ENTRIES = 500

# Human-in-the-loop approvals
CONF_APPROVAL_SEND = "approval_send"  # sending mail needs approval
CONF_APPROVAL_DELETE = "approval_delete"  # deleting needs approval
CONF_APPROVAL_MASS = "approval_mass"  # mail operations touching more than N messages need approval (0 = off)
CONF_APPROVAL_NOTIFY = "approval_notify"  # notify service (e.g. mobile_app_iphone) for actionable notifications
CONF_APPROVAL_TIMEOUT = "approval_timeout"  # minutes until a pending request expires
DEFAULT_APPROVAL_SEND = False
DEFAULT_APPROVAL_DELETE = False
DEFAULT_APPROVAL_MASS = 0
DEFAULT_APPROVAL_TIMEOUT = 15
APPROVAL_ACTION_PREFIX = "FRIEDAFETCH_"
MOBILE_ACTION_EVENT = "mobile_app_notification_action"

# MCP endpoint
CONF_ENDPOINT_ADMIN_ONLY = "endpoint_admin_only"
DEFAULT_ENDPOINT_ADMIN_ONLY = False
