"""Password auth + onboarding unit tests."""

from __future__ import annotations

from sqlalchemy import Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from backend.services.email import EmailEvent
from security.ops.password_auth import PasswordAuthService, create_email_token_models


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True)
    name = Column(String(200), default="")
    auth_provider = Column(String(20), default="password")
    status = Column(String(30), default="active")
    email_verified = Column(Integer, default=0)
    email_verified_at = Column(DateTime, nullable=True)
    password_hash = Column(String(255), nullable=True)
    plan = Column(String(30), default="free")
    session_version = Column(Integer, default=0)
    onboarding_completed_at = Column(DateTime, nullable=True)
    research_role = Column(String(40), nullable=True)
    research_fields = Column(Text, nullable=True)
    institution = Column(String(200), nullable=True)
    research_goal = Column(String(40), nullable=True)
    experience_level = Column(String(20), nullable=True)


EmailVerificationToken, PasswordResetToken, EmailChangeToken = create_email_token_models(Base)


class FakeEmail:
    def __init__(self):
        self.sent = []

    def send(self, to, subject, html, text=None, reply_to=None, sender=None):
        self.sent.append({"to": to, "subject": subject, "html": html, "sender": sender})
        return True

    def handle(self, event, **payload):
        template = {
            EmailEvent.USER_REGISTERED: "verify_email",
            EmailEvent.EMAIL_VERIFIED: "welcome",
            EmailEvent.PASSWORD_RESET_REQUESTED: "password_reset",
            EmailEvent.PASSWORD_CHANGED: "password_changed",
            EmailEvent.MAGIC_LINK_REQUESTED: "magic_link",
            EmailEvent.INVITED: "invite",
            EmailEvent.EMAIL_CHANGE_REQUESTED: "email_change",
        }.get(event, event)
        self.sent.append(
            {
                "to": payload.get("to"),
                "subject": event,
                "template": template,
                "ctx": payload,
            }
        )
        return True


def _svc():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    mail = FakeEmail()
    svc = PasswordAuthService(
        Session,
        User,
        EmailVerificationToken,
        PasswordResetToken,
        EmailChangeToken=EmailChangeToken,
        email_service=mail,
        app_base_url="http://localhost:5000",
    )
    return svc, mail, Session


def test_register_verify_sends_welcome():
    svc, mail, _ = _svc()
    user, err = svc.register(name="Ada", email="ada@ox.ac.uk", password="password1234")
    assert err is None
    assert user["status"] == "pending_verification"
    assert any(s["template"] == "verify_email" for s in mail.sent)

    verify = next(s for s in mail.sent if s.get("template") == "verify_email")
    token = verify["ctx"]["link"].split("token=")[-1]
    ok, reason = svc.verify_email(token)
    assert ok and reason == "ok"
    assert any(s["template"] == "welcome" for s in mail.sent)


def test_open_signup_login_and_onboarding():
    svc, mail, Session = _svc()
    svc.register(name="Bob", email="bob@ox.ac.uk", password="password1234")
    verify = next(s for s in mail.sent if s.get("template") == "verify_email")
    token = verify["ctx"]["link"].split("token=")[-1]
    svc.verify_email(token)

    user, err = svc.login("bob@ox.ac.uk", "password1234")
    assert err is None

    ok, _ = svc.complete_onboarding(
        user["id"],
        {
            "research_role": "researcher",
            "research_fields": ["ai", "medicine"],
            "research_goal": "lit_review",
            "experience_level": "intermediate",
            "institution": "Oxford",
        },
    )
    assert ok
    db = Session()
    try:
        row = db.get(User, user["id"])
        assert row.onboarding_completed_at is not None
        assert row.research_role == "researcher"
        assert "ai" in (row.research_fields or "")
        assert row.research_goal == "lit_review"
        assert row.institution == "Oxford"
    finally:
        db.close()


def test_password_reset_sends_changed_email():
    svc, mail, _ = _svc()
    svc.register(name="C", email="c@ox.ac.uk", password="password1234")
    verify = next(s for s in mail.sent if s.get("template") == "verify_email")
    svc.verify_email(verify["ctx"]["link"].split("token=")[-1])
    mail.sent.clear()

    svc.request_password_reset("c@ox.ac.uk")
    reset = next(s for s in mail.sent if s.get("template") == "password_reset")
    token = reset["ctx"]["link"].split("token=")[-1]
    ok, _ = svc.reset_password(token, "newpassword99")
    assert ok
    assert any(s["template"] == "password_changed" for s in mail.sent)


def test_change_password_while_logged_in():
    svc, mail, Session = _svc()
    user, _ = svc.register(name="D", email="d@ox.ac.uk", password="password1234")
    verify = next(s for s in mail.sent if s.get("template") == "verify_email")
    svc.verify_email(verify["ctx"]["link"].split("token=")[-1])
    mail.sent.clear()

    ok, reason, ver = svc.change_password(user["id"], "wrong", "newpassword99")
    assert not ok and reason == "wrong_password"

    ok, reason, ver = svc.change_password(user["id"], "password1234", "newpassword99")
    assert ok and reason == "ok"
    assert ver == 1
    assert any(s["template"] == "password_changed" for s in mail.sent)

    logged, err = svc.login("d@ox.ac.uk", "newpassword99")
    assert err is None and logged["id"] == user["id"]


def test_set_password_for_oauth_user():
    svc, mail, Session = _svc()
    db = Session()
    try:
        row = User(email="g@ox.ac.uk", name="G", auth_provider="google", email_verified=1, status="active")
        db.add(row)
        db.commit()
        uid = row.id
    finally:
        db.close()

    ok, reason, ver = svc.set_password(uid, "password1234")
    assert ok and reason == "ok" and ver == 1
    logged, err = svc.login("g@ox.ac.uk", "password1234")
    assert err is None
    db = Session()
    try:
        assert db.get(User, uid).auth_provider == "password"
    finally:
        db.close()
