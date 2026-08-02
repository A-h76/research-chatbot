"""Jinja email rendering (templates live in templates/email/)."""

from __future__ import annotations

from typing import Any


def render_email_template(
    template_name: str,
    *,
    support_email: str = "support@dhund.com",
    site_url: str = "https://dhund.com",
    app_base_url: str = "",
    **ctx: Any,
) -> tuple[str, str]:
    """Return (html, text) for templates/email/<name>.html."""
    from flask import render_template

    name = template_name if template_name.endswith(".html") else f"{template_name}.html"
    html = render_template(
        f"email/{name}",
        support_email=support_email,
        site_url=site_url.rstrip("/"),
        app_base_url=(app_base_url or "").rstrip("/"),
        **ctx,
    )
    return html, html_to_text(html)


def html_to_text(html: str) -> str:
    import re

    text = re.sub(r"(?is)<style.*?>.*?</style>", " ", html or "")
    text = re.sub(r"(?is)<script.*?>.*?</script>", " ", text)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
