from __future__ import annotations

from uuid import uuid4

from app.core.security import verify_password
from app.models.user import User
from scripts.bootstrap_owner import BootstrapInputError, bootstrap_owner, main, validate_password


def _generated_password() -> str:
    return f"Test!{uuid4().hex}A1"


class FakeSession:
    def __init__(self, *scalar_results):
        self._scalar_results = iter(scalar_results)
        self.added = []
        self.commits = 0
        self.rollbacks = 0
        self.closed = False

    def scalar(self, _query):
        return next(self._scalar_results)

    def add(self, item):
        self.added.append(item)

    def flush(self):
        for item in self.added:
            if getattr(item, "id", None) is None:
                item.id = uuid4()

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def test_bootstrap_requires_credentials():
    messages = []
    session = FakeSession()

    exit_code = main(
        [],
        environ={},
        session_factory=lambda: session,
        password_prompt=lambda _prompt: "",
        emit=messages.append,
    )

    assert exit_code == 2
    assert messages == ["Owner bootstrap failed: Owner email is required."]
    assert session.closed


def test_weak_password_is_rejected():
    weak_password = uuid4().hex[:8]

    try:
        validate_password(weak_password)
    except BootstrapInputError as exc:
        assert "at least 12 characters" in str(exc)
    else:
        raise AssertionError("Expected a weak password to be rejected")


def test_bootstrap_hashes_password_before_storage():
    password = _generated_password()
    session = FakeSession(None, None)

    result = bootstrap_owner(
        session,
        email=f"owner-{uuid4().hex}@example.test",
        password=password,
        store_name="Test Store",
        store_code="TEST",
    )

    owner = next(item for item in session.added if isinstance(item, User))
    assert result.created
    assert owner.password_hash != password
    assert verify_password(password, owner.password_hash)
    assert session.commits == 1


def test_bootstrap_is_idempotent_without_update_option():
    password = _generated_password()
    existing_owner = User(
        full_name="Existing Owner",
        email=f"owner-{uuid4().hex}@example.test",
        password_hash="generated-for-test-only",
    )
    session = FakeSession(existing_owner)

    result = bootstrap_owner(
        session,
        email=existing_owner.email,
        password=password,
        store_name="Test Store",
        store_code="TEST",
    )

    assert not result.created
    assert result.message == "Owner already exists; no changes made."
    assert session.added == []
    assert session.commits == 0


def test_password_never_appears_in_command_output():
    password = _generated_password()
    email = f"owner-{uuid4().hex}@example.test"
    messages = []
    session = FakeSession(None, None)

    exit_code = main(
        ["--store-name", "Test Store", "--store-code", "TEST"],
        environ={"OWNER_EMAIL": email, "OWNER_PASSWORD": password},
        session_factory=lambda: session,
        emit=messages.append,
    )

    output = "\n".join(messages)
    assert exit_code == 0
    assert password not in output
    assert "Owner bootstrap complete." in output
