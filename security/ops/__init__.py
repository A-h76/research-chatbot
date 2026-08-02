"""Ops: AI gate, kill switch, invites, security events, password auth.

Never ``import server`` — factories take injected SessionLocal / models.
"""

from .events import SecurityEventStore, create_security_event_model
from .gate import AiAccessDenied, AiAccessGate, PLAN_LIMITS
from .invites import InviteService, create_invite_token_model
from .password_auth import PasswordAuthService, create_email_token_models
from .settings import SystemSettingsService, create_system_settings_model
from .estimates import estimate_research_cost_usd, estimate_chat_tokens
from .beta_metrics import BetaMetricsService, record_last_login

__all__ = [
    "AiAccessDenied",
    "AiAccessGate",
    "BetaMetricsService",
    "InviteService",
    "PasswordAuthService",
    "PLAN_LIMITS",
    "SecurityEventStore",
    "SystemSettingsService",
    "create_email_token_models",
    "create_invite_token_model",
    "create_security_event_model",
    "create_system_settings_model",
    "estimate_chat_tokens",
    "estimate_research_cost_usd",
    "record_last_login",
]
