"""Single source of truth for transactional email configuration.

Import from here — do not call ``os.getenv`` for email senders elsewhere.
"""

from __future__ import annotations

import os

EMAIL_FROM = (os.getenv("EMAIL_FROM") or "Dhund <auth@dhund.com>").strip()
AUTH_EMAIL_FROM = (os.getenv("AUTH_EMAIL_FROM") or EMAIL_FROM).strip() or EMAIL_FROM
NOREPLY_EMAIL_FROM = (
    os.getenv("NOREPLY_EMAIL_FROM") or "Dhund <noreply@dhund.com>"
).strip()
NOTIFICATIONS_EMAIL_FROM = (
    os.getenv("NOTIFICATIONS_EMAIL_FROM")
    or "Dhund Notifications <notifications@dhund.com>"
).strip()
SUPPORT_EMAIL = (os.getenv("SUPPORT_EMAIL") or "support@dhund.com").strip()
RESEND_API_KEY = (os.getenv("RESEND_API_KEY") or "").strip()
PUBLIC_SITE_URL = (os.getenv("PUBLIC_SITE_URL") or "https://dhund.com").strip()
APP_BASE_URL = (os.getenv("APP_BASE_URL") or "http://localhost:5000").strip()

# Sender map (logical → From header)
# Verify / Magic Link / Password Reset / Password Changed → AUTH_EMAIL_FROM
# Welcome → NOREPLY_EMAIL_FROM
# Research Complete / Collaboration Invite → NOTIFICATIONS_EMAIL_FROM
