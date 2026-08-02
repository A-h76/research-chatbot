"""Resend (or console) transport + named transactional email API."""

from __future__ import annotations

import logging
import re
from typing import Any, Callable

from .events import EmailEvent
from .renderer import html_to_text, render_email_template

log = logging.getLogger("email")


def _redact(body: str) -> str:
    text = body or ""
    text = re.sub(r"(token=)[^&\s\"'<>]+", r"\1[REDACTED]", text, flags=re.I)
    text = re.sub(r"(/auth/magic-link\?[^\s\"'<>]+)", "/auth/magic-link?[REDACTED]", text, flags=re.I)
    return text


class TransactionalEmailService:
    """Single entry point for all Dhund transactional email.

    Call named methods from auth code, or ``handle(EmailEvent.*, ...)`` so
    analytics / Slack / Discord can hook the same events later.

    Sender map:
      AUTH_EMAIL_FROM — verify, magic link, password reset/changed, email change
      NOREPLY_EMAIL_FROM — welcome
      NOTIFICATIONS_EMAIL_FROM — invites, research-complete
    """

    @classmethod
    def from_env(cls, *, on_analytics=None) -> "TransactionalEmailService":
        from backend.config.email import (
            APP_BASE_URL,
            AUTH_EMAIL_FROM,
            NOREPLY_EMAIL_FROM,
            NOTIFICATIONS_EMAIL_FROM,
            PUBLIC_SITE_URL,
            RESEND_API_KEY,
            SUPPORT_EMAIL,
        )

        return cls(
            RESEND_API_KEY,
            auth_from=AUTH_EMAIL_FROM,
            noreply_from=NOREPLY_EMAIL_FROM,
            notifications_from=NOTIFICATIONS_EMAIL_FROM,
            support_email=SUPPORT_EMAIL,
            site_url=PUBLIC_SITE_URL,
            app_base_url=APP_BASE_URL,
            on_analytics=on_analytics,
        )

    def __init__(
        self,
        api_key: str,
        *,
        auth_from: str = "Dhund <auth@dhund.com>",
        noreply_from: str = "Dhund <noreply@dhund.com>",
        notifications_from: str = "Dhund Notifications <notifications@dhund.com>",
        support_email: str = "support@dhund.com",
        site_url: str = "https://dhund.com",
        app_base_url: str = "",
        on_analytics: Callable[[str, dict], None] | None = None,
    ):
        self.api_key = (api_key or "").strip()
        self.enabled = bool(self.api_key)
        self.auth_from = auth_from
        self.noreply_from = noreply_from
        self.notifications_from = notifications_from
        # Back-compat alias used by older call sites
        self.sender = auth_from
        self.support_email = support_email
        self.site_url = (site_url or "https://dhund.com").rstrip("/")
        self.app_base_url = (app_base_url or "").rstrip("/")
        self._on_analytics = on_analytics

    # ── Transport ───────────────────────────────────────────────────────
    def send(self, to, subject, html, text=None, reply_to=None, sender=None) -> bool:
        recipients = [to] if isinstance(to, str) else list(to)
        from_addr = sender or self.auth_from
        if not self.enabled:
            log.info(
                "[dev email - not sent]\n  to: %s\n  subject: %s\n  body:\n%s",
                ", ".join(recipients),
                subject,
                _redact(text or html_to_text(html)),
            )
            return True
        payload: dict[str, Any] = {
            "from": from_addr,
            "to": recipients,
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        if reply_to:
            payload["reply_to"] = reply_to
        try:
            import requests

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=15,
            )
            if resp.status_code >= 400:
                log.error("Resend error %s: %s", resp.status_code, resp.text[:300])
                return False
            return True
        except Exception as exc:
            log.error("email send failed: %s", exc)
            return False

    def send_template(self, to, *, template, subject, sender=None, reply_to=None, **ctx) -> bool:
        html, text = render_email_template(
            template,
            support_email=self.support_email,
            site_url=self.site_url,
            app_base_url=self.app_base_url,
            **ctx,
        )
        return self.send(
            to=to,
            subject=subject,
            html=html,
            text=text,
            reply_to=reply_to,
            sender=sender,
        )

    def _track(self, name: str, **fields) -> None:
        if self._on_analytics:
            try:
                self._on_analytics(name, fields)
            except Exception:
                log.warning("analytics hook failed for %s", name, exc_info=True)

    # ── Named methods ───────────────────────────────────────────────────
    def send_verify_email(self, *, to: str, name: str, link: str, hours: int = 24) -> bool:
        ok = self.send_template(
            to,
            template="verify_email",
            subject="Verify your Dhund account",
            sender=self.auth_from,
            name=name,
            link=link,
            hours=hours,
        )
        return ok

    def send_welcome(self, *, to: str, name: str, cta_url: str) -> bool:
        ok = self.send_template(
            to,
            template="welcome",
            subject="Welcome to Dhund",
            sender=self.noreply_from,
            name=name,
            cta_url=cta_url,
        )
        if ok:
            self._track("welcome_sent", email=to)
        return ok

    def send_magic_link(self, *, to: str, link: str, name: str = "") -> bool:
        return self.send_template(
            to,
            template="magic_link",
            subject="Your Dhund sign-in link",
            sender=self.auth_from,
            name=name,
            link=link,
        )

    def send_password_reset(self, *, to: str, link: str, name: str = "", minutes: int = 30) -> bool:
        return self.send_template(
            to,
            template="password_reset",
            subject="Reset your Dhund password",
            sender=self.auth_from,
            name=name,
            link=link,
            hours=max(1, (minutes + 59) // 60) if minutes >= 60 else 1,
            minutes=minutes,
        )

    def send_password_changed(self, *, to: str, name: str = "", cta_url: str = "") -> bool:
        return self.send_template(
            to,
            template="password_changed",
            subject="Your Dhund password was updated",
            sender=self.auth_from,
            name=name,
            cta_url=cta_url,
        )

    def send_invite(self, *, to: str, signup_url: str, days: int = 7) -> bool:
        return self.send_template(
            to,
            template="invite",
            subject="You've been invited to Dhund",
            sender=self.notifications_from,
            email=to,
            signup_url=signup_url,
            days=days,
        )

    def send_research_complete(self, *, to: str, name: str = "", cta_url: str = "", summary: str = "") -> bool:
        """Product notification — research/job finished (notifications@)."""
        return self.send_template(
            to,
            template="welcome",  # dedicated template can replace later
            subject="Your Dhund research is ready",
            sender=self.notifications_from,
            name=name,
            cta_url=cta_url or f"{self.app_base_url}/",
            summary=summary,
        )

    def send_email_change(self, *, to: str, new_email: str, link: str, name: str = "", hours: int = 24) -> bool:
        return self.send_template(
            to,
            template="email_change",
            subject="Confirm your new Dhund email",
            sender=self.auth_from,
            name=name,
            new_email=new_email,
            link=link,
            hours=hours,
        )

    # ── Event dispatch ──────────────────────────────────────────────────
    def handle(self, event: str, **payload) -> bool:
        """Route domain events to the correct branded email."""
        if event == EmailEvent.USER_REGISTERED:
            return self.send_verify_email(
                to=payload["to"],
                name=payload.get("name") or "",
                link=payload["link"],
                hours=int(payload.get("hours") or 24),
            )
        if event == EmailEvent.EMAIL_VERIFIED:
            return self.send_welcome(
                to=payload["to"],
                name=payload.get("name") or "",
                cta_url=payload.get("cta_url") or self.app_base_url or "/",
            )
        if event == EmailEvent.PASSWORD_RESET_REQUESTED:
            return self.send_password_reset(
                to=payload["to"],
                link=payload["link"],
                name=payload.get("name") or "",
                minutes=int(payload.get("minutes") or 30),
            )
        if event == EmailEvent.PASSWORD_CHANGED:
            return self.send_password_changed(
                to=payload["to"],
                name=payload.get("name") or "",
                cta_url=payload.get("cta_url") or f"{self.app_base_url}/auth/sign-in",
            )
        if event == EmailEvent.MAGIC_LINK_REQUESTED:
            return self.send_magic_link(
                to=payload["to"],
                link=payload["link"],
                name=payload.get("name") or "",
            )
        if event == EmailEvent.INVITED:
            return self.send_invite(
                to=payload["to"],
                signup_url=payload["signup_url"],
                days=int(payload.get("days") or 7),
            )
        if event == EmailEvent.EMAIL_CHANGE_REQUESTED:
            return self.send_email_change(
                to=payload["to"],
                new_email=payload["new_email"],
                link=payload["link"],
                name=payload.get("name") or "",
                hours=int(payload.get("hours") or 24),
            )
        log.warning("Unknown email event: %s", event)
        return False
