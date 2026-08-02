"""Email / product analytics event names (auth + onboarding)."""

from __future__ import annotations


class EmailEvent:
    USER_REGISTERED = "USER_REGISTERED"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"
    PASSWORD_CHANGED = "PASSWORD_CHANGED"
    PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
    MAGIC_LINK_REQUESTED = "MAGIC_LINK_REQUESTED"
    INVITED = "INVITED"
    EMAIL_CHANGE_REQUESTED = "EMAIL_CHANGE_REQUESTED"


# Product analytics (also recorded via SecurityEventStore when wired)
ANALYTICS = {
    "signup_started": "signup_started",
    "signup_completed": "signup_completed",
    "email_verified": "email_verified",
    "welcome_sent": "welcome_sent",
    "password_reset_requested": "password_reset_requested",
    "password_reset_completed": "password_reset_completed",
    "google_login": "google_login",
    "magic_link_login": "magic_link_login",
    "password_login": "password_login",
    "onboarding_started": "onboarding_started",
    "onboarding_completed": "onboarding_completed",
}
