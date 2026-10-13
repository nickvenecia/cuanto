"""Your Cuánto account: signing in and out.

There's no account service yet. Everything the app needs is here, behind one interface (AccountService),
so connecting one later means writing a class with these four methods and returning it from service():

    class MyAccounts(AccountService):
        connected = True
        def sign_in(self, email, password) -> Session: ...   # ask your server; return a Session
        def sign_out(self, session) -> None: ...
        def reset_password(self, email) -> None: ...

Rules (whatever service it is):
- the password is sent once, over https, and never kept anywhere
- what comes back (a token) lives in the system keychain (services/secrets.py), never in a file
- REQUIRED decides whether the sign-in window shows when Cuánto opens (off until accounts exist)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from cuanto.core.log import get_logger
from cuanto.services import secrets

log = get_logger(__name__)

REQUIRED = False  # True: Cuánto asks you to sign in when it opens (once an account service is connected)
KEYCHAIN_ENTRY = "account:session"  # where the signed-in session is kept in the keychain
EMAIL_OK = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AccountError(OSError):
    """Signing in didn't work, in plain words."""


@dataclass
class Session:
    email: str
    token: str
    name: str = ""


class AccountService:
    """What any account service does. This one is "not connected yet"."""

    connected = False

    def sign_in(self, email: str, password: str) -> Session:
        raise AccountError("Cuánto accounts aren't switched on yet. Everything works without one.")

    def sign_out(self, session: Session) -> None:
        return None

    def reset_password(self, email: str) -> None:
        raise AccountError("Cuánto accounts aren't switched on yet.")


_service: AccountService = AccountService()


def service() -> AccountService:
    """The account service in use (swap it with use() once one exists)."""
    return _service


def use(s: AccountService) -> None:
    global _service
    _service = s


def valid_email(email: str) -> bool:
    return bool(EMAIL_OK.match(email.strip()))


# ---------------------------------------------------------------- the signed-in session
def current() -> Session | None:
    """Who's signed in (the token from the keychain), or None."""
    raw = secrets.get(KEYCHAIN_ENTRY)
    if not raw:
        return None
    try:
        d = json.loads(raw)
        return Session(str(d["email"]), str(d["token"]), str(d.get("name", "")))
    except (ValueError, KeyError, TypeError):
        secrets.delete(KEYCHAIN_ENTRY)
        return None


def sign_in(email: str, password: str) -> Session:
    email = email.strip()
    if not valid_email(email):
        raise AccountError("That doesn't look like an email address.")
    if not password:
        raise AccountError("Type your password.")
    s = service().sign_in(email, password)
    secrets.put(KEYCHAIN_ENTRY, json.dumps({"email": s.email, "token": s.token, "name": s.name}))
    log.info("signed in")  # never the email or the token
    return s


def sign_out() -> None:
    s = current()
    if s is not None:
        try:
            service().sign_out(s)
        except OSError:
            log.info("couldn't tell the account service about signing out")
    secrets.delete(KEYCHAIN_ENTRY)
