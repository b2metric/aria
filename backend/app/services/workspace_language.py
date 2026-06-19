"""Per-customer response language.

Each customer has exactly ONE response language (stored in ``Customer.settings['language']``).
The chat answer, insights, and follow-up suggestions are all forced to it so a conversation
never drifts between Turkish and English. Defaults to English when unset.
"""

import logging

from sqlalchemy import select

from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import Customer

logger = logging.getLogger(__name__)

SUPPORTED_LANGUAGES = {"en": "English", "tr": "Turkish"}
DEFAULT_LANGUAGE = "en"


def language_name(code: str | None) -> str:
    """Map a language code to its English display name (for LLM prompts)."""
    return SUPPORTED_LANGUAGES.get(code or "", SUPPORTED_LANGUAGES[DEFAULT_LANGUAGE])


def language_directive(code: str | None) -> str:
    """A strict instruction telling the LLM to answer only in the customer's language."""
    name = language_name(code)
    return (
        f"CRITICAL LANGUAGE RULE: Write ALL natural-language output (summary, insights, "
        f"and follow-up questions) ONLY in {name}, regardless of the language of the "
        f"question, column names, or data. Never mix languages."
    )


async def get_workspace_language(workspace_id: str | None) -> str:
    """Return the customer's configured response language code ('en'/'tr').

    Falls back to ``DEFAULT_LANGUAGE`` when the workspace is unknown, unset, or on any error.
    """
    if not workspace_id:
        return DEFAULT_LANGUAGE
    try:
        async with get_sessionmaker()() as session:
            settings = (
                await session.execute(
                    select(Customer.settings).where(Customer.slug == workspace_id)
                )
            ).scalar_one_or_none()
        lang = (settings or {}).get("language") if settings else None
        return lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("get_workspace_language failed for %s: %s", workspace_id, exc)
        return DEFAULT_LANGUAGE
