"""Back-compat re-export — prefer backend.services.email.renderer."""

from backend.services.email.renderer import html_to_text, render_email_template

__all__ = ["render_email_template", "html_to_text"]
