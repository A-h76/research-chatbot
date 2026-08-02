"""Step-up reauth challenges for destructive account actions (V1 #16).

Password accounts must re-enter their password. OAuth / magic-link-only
accounts (no password_hash) must re-type their account email. Both paths
also require the literal confirmation string ``DELETE``.
"""

from __future__ import annotations

CONFIRM_DELETE = "DELETE"


def authorize_account_delete(
    *,
    has_password: bool,
    user_email: str,
    body: dict | None,
    password_matches: bool | None = None,
) -> tuple[bool, str]:
    """Return ``(ok, reason)``. ``reason`` is a stable machine code for the API.

    ``password_matches`` is only consulted when ``has_password`` is True —
    callers verify the hash outside this function (keeps crypto at the
    PasswordAuth / Werkzeug boundary).
    """
    data = body if isinstance(body, dict) else {}
    confirm = str(data.get("confirm") or "").strip()
    if confirm != CONFIRM_DELETE:
        return False, "confirm_required"

    if has_password:
        password = data.get("password")
        if password is None or str(password) == "":
            return False, "password_required"
        if password_matches is not True:
            return False, "wrong_password"
        return True, "ok"

    email = str(data.get("email") or "").strip().lower()
    if not email:
        return False, "email_required"
    if email != (user_email or "").strip().lower():
        return False, "email_mismatch"
    return True, "ok"


STEP_UP_ERROR_DETAIL = {
    "confirm_required": f'Type confirm: "{CONFIRM_DELETE}" in the request body.',
    "password_required": "Password is required to delete this account.",
    "wrong_password": "Password is incorrect.",
    "email_required": "Re-enter your account email to confirm deletion.",
    "email_mismatch": "Email does not match this account.",
}
