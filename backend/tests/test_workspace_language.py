"""Tests for per-customer response-language resolution."""

from backend.app.services.workspace_language import (
    DEFAULT_LANGUAGE,
    language_directive,
    language_name,
)


def test_language_name_known_codes():
    assert language_name("en") == "English"
    assert language_name("tr") == "Turkish"


def test_language_name_defaults_to_english():
    assert language_name(None) == "English"
    assert language_name("") == "English"
    assert language_name("xx") == "English"
    assert DEFAULT_LANGUAGE == "en"


def test_directive_names_the_target_language_and_forbids_mixing():
    tr = language_directive("tr")
    assert "Turkish" in tr
    assert "English" not in tr  # a Turkish customer must never be told to use English
    assert "Never mix languages" in tr

    en = language_directive("en")
    assert "English" in en
    assert "Turkish" not in en


def test_unknown_code_directive_falls_back_to_english():
    assert "English" in language_directive("de")
