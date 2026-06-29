"""Keycloak JWT validation and claims extraction.

This module validates JWT access tokens issued by Keycloak by fetching
the realm's public key(s) from the JWKS endpoint and verifying the
token signature, issuer, audience, and expiration.

JWKS keys are cached in-process after the first fetch — subsequent
token validations avoid a network round-trip to Keycloak.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError

from backend.app.auth.models import TokenPayload
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JWKS cache (process-lifetime)
# ---------------------------------------------------------------------------

_jwks_cache: dict[str, Any] | None = None
_jwks_cache_ts: float = 0.0
_JWKS_CACHE_TTL: float = 3600.0  # 1 hour


async def _fetch_jwks() -> dict[str, Any]:
    """Fetch the Keycloak realm JWKS, caching the result in memory."""
    global _jwks_cache, _jwks_cache_ts  # noqa: PLW0603

    now = time.monotonic()
    if _jwks_cache is not None and (now - _jwks_cache_ts) < _JWKS_CACHE_TTL:
        return _jwks_cache

    settings = get_settings()
    url = settings.keycloak_jwks_url

    async with httpx.AsyncClient(verify=settings.keycloak_verify_ssl) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            jwks = resp.json()
        except httpx.HTTPError as exc:
            logger.error("Failed to fetch JWKS from %s: %s", url, exc)
            if hasattr(exc, "response") and exc.response is not None:
                logger.error("Response body: %s", exc.response.text)
            raise

    _jwks_cache = jwks
    _jwks_cache_ts = now
    logger.debug("JWKS refreshed from %s (%d keys)", url, len(jwks.get("keys", [])))
    return jwks


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def decode_token(token: str, *, leeway: int | None = None) -> TokenPayload:
    """Validate a JWT access token and return its claims.

    Raises ``UnauthorizedError`` (or subclasses) when the token is
    invalid, expired, or missing required claims.

    Parameters
    ----------
    token:
        Raw JWT access-token string (``Authorization: Bearer <token>``).
    leeway:
        Expiration / not-before leeway in seconds.  Defaults to
        ``Settings.jwt_leeway_seconds``.
    """
    settings = get_settings()
    if leeway is None:
        leeway = getattr(settings, "jwt_leeway_seconds", 60)

    # Decode the header to get the ``kid`` before we fetch JWKS.
    try:
        unverified_header = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise InvalidTokenError("Unable to decode JWT header") from exc

    # Only RSA signature algorithms are accepted — never let the token header pick the
    # algorithm (prevents alg-confusion, e.g. an HS256 token signed with the RSA public key).
    allowed_algorithms = ("RS256", "RS384", "RS512")
    kid = unverified_header.get("kid")
    alg = unverified_header.get("alg", "RS256")
    if not kid:
        raise InvalidTokenError("JWT header missing 'kid'")
    if alg not in allowed_algorithms:
        raise InvalidTokenError(f"Unsupported JWT algorithm: {alg!r}")

    # Fetch JWKS and find the matching public key.
    jwks = await _fetch_jwks()
    key = _find_key(jwks, kid)
    if key is None:
        # Key rotation edge case — try a fresh fetch once.
        logger.warning("Key %s not in cache, forcing JWKS refresh", kid)
        global _jwks_cache  # noqa: PLW0603
        _jwks_cache = None
        jwks = await _fetch_jwks()
        key = _find_key(jwks, kid)
        if key is None:
            raise InvalidTokenError(f"Unknown key id: {kid!r}")

    # Verify signature + standard claims.
    try:
        # Note: Since the token is generated for the frontend ("aria-web") but consumed
        # by the backend, we disable strict audience check for local dev or check against "account".
        payload = jwt.decode(
            token,
            key,
            algorithms=list(allowed_algorithms),
            audience=settings.keycloak_audience,
            issuer=settings.keycloak_issuer,
            options={
                "verify_signature": True,
                # Off by default (Keycloak aud varies by client); enable in prod via
                # keycloak_verify_audience to reject tokens minted for another client.
                "verify_aud": settings.keycloak_verify_audience,
                "verify_iss": True,
                "verify_exp": True,
                "verify_iat": True,
                "leeway": leeway,
            },
        )
    except ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except JWTClaimsError as exc:
        raise InvalidTokenError(f"JWT claim validation failed: {exc}") from exc
    except JWTError as exc:
        raise InvalidTokenError(f"JWT validation failed: {exc}") from exc

    return TokenPayload(**payload)


def _find_key(jwks: dict[str, Any], kid: str) -> dict[str, Any] | None:
    """Locate a JWK by its ``kid``, returning the PEM public key."""
    for key_data in jwks.get("keys", []):
        if key_data.get("kid") == kid:
            # python-jose accepts JWK dicts directly for RSA keys
            return key_data
    return None


# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class AuthError(Exception):
    """Base authentication / authorization error."""


class InvalidTokenError(AuthError):
    """Token is malformed, unsigned, or has invalid claims."""


class TokenExpiredError(InvalidTokenError):
    """Token has passed its ``exp`` claim."""


class MissingTokenError(AuthError):
    """Authorization header is missing entirely."""
