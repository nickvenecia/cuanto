"""Secrets (the account sign-in, and AI keys once AI arrives) live in the computer's own keychain, never in a file.

macOS Keychain, Windows Credential Manager, or the Linux Secret Service (GNOME Keyring, KWallet), through
the `keyring` package. If the computer has none, Cuánto won't save a key at all rather than write it
somewhere less safe, and says so. Values are never logged.
"""

from __future__ import annotations

from cuanto.core.log import get_logger

log = get_logger(__name__)

SERVICE = "Cuanto"  # how the entries are named in the keychain ("Cuanto", account "account:session"…)


class SecretsUnavailable(OSError):
    """This computer has no keychain Cuánto can use."""


def _keyring():
    try:
        import keyring
        from keyring.backends import fail
    except ImportError as e:  # pragma: no cover - bundled with the app
        raise SecretsUnavailable("The keychain isn't available in this copy of Cuánto.") from e
    if isinstance(keyring.get_keyring(), fail.Keyring):
        raise SecretsUnavailable("This computer has no keychain for Cuánto to keep keys in.")
    return keyring


def available() -> bool:
    try:
        _keyring()
        return True
    except SecretsUnavailable:
        return False


def get(name: str) -> str:
    """The secret called `name`, or "" (none saved, or no keychain)."""
    try:
        return _keyring().get_password(SERVICE, name) or ""
    except SecretsUnavailable:
        return ""
    except Exception:  # a locked or broken keychain: treat as not saved
        log.warning("couldn't read %s from the keychain", name)
        return ""


def put(name: str, value: str) -> None:
    """Save (or with "", remove) a secret. Raises SecretsUnavailable or OSError."""
    if not value:
        delete(name)
        return
    try:
        _keyring().set_password(SERVICE, name, value)
    except SecretsUnavailable:
        raise
    except Exception as e:
        log.warning("couldn't save %s to the keychain", name)
        raise OSError("Couldn't save it to the keychain.") from e


def delete(name: str) -> None:
    try:
        _keyring().delete_password(SERVICE, name)
    except SecretsUnavailable:
        return
    except Exception:  # already gone
        return
