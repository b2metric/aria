"""Provision Keycloak OIDC clients for the embedded admin Service Consoles (SSO).

Idempotent post-deploy setup: the realm import (aria-realm.json) only runs on a
fresh realm, so for existing realms this script creates/updates the SSO clients via
the Keycloak admin REST API.

Currently provisions:
  - litellm-ui : confidential client for the LiteLLM admin UI (embedded in
    /admin/consoles). Adds email + preferred_username mappers because the aria
    realm's only default client scope (`aria-claims`) carries just the ARIA tenant
    claims, and LiteLLM requires an email to identify the SSO user.

It also normalises the dev `admin` user's email to a real TLD: LiteLLM's strict
email validation rejects reserved TLDs like `.local`/`.localhost`, so a dev email
of `admin@aria.local` fails SSO. Real deployments use real emails and are unaffected.

Usage:
    KC_URL=http://auth.aria.localhost/auth KC_ADMIN=admin KC_ADMIN_PASSWORD=admin \\
    LITELLM_UI_SECRET=litellm-ui-dev-secret python infra/keycloak/setup-console-sso.py

Env (all optional, dev defaults shown):
    KC_URL=http://auth.aria.localhost/auth  REALM=aria
    KC_ADMIN=admin  KC_ADMIN_PASSWORD=admin
    LITELLM_UI_SECRET=litellm-ui-dev-secret
    LITELLM_REDIRECT=http://llm.aria.localhost/sso/callback
    DEV_ADMIN_USERNAME=admin  DEV_ADMIN_EMAIL=admin@b2metric.com
"""

import json
import os
import urllib.parse
import urllib.request

KC = os.environ.get("KC_URL", "http://auth.aria.localhost/auth").rstrip("/")
REALM = os.environ.get("REALM", "aria")
ADMIN = os.environ.get("KC_ADMIN", "admin")
ADMIN_PW = os.environ.get("KC_ADMIN_PASSWORD", "admin")
LITELLM_SECRET = os.environ.get("LITELLM_UI_SECRET", "litellm-ui-dev-secret")
LITELLM_REDIRECT = os.environ.get("LITELLM_REDIRECT", "http://llm.aria.localhost/sso/callback")
DEV_ADMIN_USERNAME = os.environ.get("DEV_ADMIN_USERNAME", "admin")
DEV_ADMIN_EMAIL = os.environ.get("DEV_ADMIN_EMAIL", "admin@b2metric.com")


def _req(method, path, token=None, data=None, form=False):
    url = f"{KC}{path}"
    headers = {}
    body = None
    if data is not None:
        if form:
            body = urllib.parse.urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        else:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, resp.read().decode(), dict(resp.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(), dict(e.headers)


def admin_token():
    status, raw, _ = _req(
        "POST",
        "/realms/master/protocol/openid-connect/token",
        data={
            "client_id": "admin-cli",
            "username": ADMIN,
            "password": ADMIN_PW,
            "grant_type": "password",
        },
        form=True,
    )
    assert status == 200, f"admin token failed {status}: {raw}"
    return json.loads(raw)["access_token"]


def _property_mapper(name, user_attr, claim):
    return {
        "name": name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-usermodel-property-mapper",
        "config": {
            "user.attribute": user_attr,
            "claim.name": claim,
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }


def upsert_confidential_client(tok, client_id, secret, redirects, mappers):
    # Delete-then-create for a clean, idempotent result.
    _status, raw, _ = _req("GET", f"/admin/realms/{REALM}/clients?clientId={client_id}", token=tok)
    for c in json.loads(raw):
        _req("DELETE", f"/admin/realms/{REALM}/clients/{c['id']}", token=tok)

    payload = {
        "clientId": client_id,
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "secret": secret,
        "standardFlowEnabled": True,
        "directAccessGrantsEnabled": False,
        "redirectUris": redirects,
        "webOrigins": ["+"],
        "attributes": {"post.logout.redirect.uris": "+"},
    }
    status, _raw, headers = _req("POST", f"/admin/realms/{REALM}/clients", token=tok, data=payload)
    assert status == 201, f"create {client_id} failed {status}: {_raw}"
    cid = headers["Location"].rstrip("/").split("/")[-1]
    for m in mappers:
        s, r, _ = _req(
            "POST",
            f"/admin/realms/{REALM}/clients/{cid}/protocol-mappers/models",
            token=tok,
            data=m,
        )
        assert s == 201, f"mapper {m['name']} failed {s}: {r}"
    print(f"provisioned client {client_id} (+{len(mappers)} mappers)")


def normalise_dev_admin_email(tok):
    status, raw, _ = _req(
        "GET", f"/admin/realms/{REALM}/users?username={DEV_ADMIN_USERNAME}", token=tok
    )
    users = json.loads(raw)
    if not users:
        return
    u = users[0]
    if u.get("email") == DEV_ADMIN_EMAIL:
        return
    _req(
        "PUT",
        f"/admin/realms/{REALM}/users/{u['id']}",
        token=tok,
        data={"email": DEV_ADMIN_EMAIL, "emailVerified": True},
    )
    print(f"set {DEV_ADMIN_USERNAME} email -> {DEV_ADMIN_EMAIL} (was {u.get('email')})")


LANGFUSE_SECRET = os.environ.get("LANGFUSE_SECRET", "langfuse-dev-secret")
LANGFUSE_REDIRECT = os.environ.get(
    "LANGFUSE_REDIRECT", "http://langfuse.aria.localhost/api/auth/callback/keycloak"
)
# Allow the Keycloak admin console to be iframed from the app (relax the master
# realm's frame-ancestors CSP). Browsers honour CSP frame-ancestors over
# X-Frame-Options, so this is sufficient to embed /admin/consoles -> Keycloak.
FRAME_ANCESTORS = os.environ.get("KC_FRAME_ANCESTORS", "'self' http://aria.localhost")


def allow_admin_console_framing(tok):
    """Relax the master realm browser CSP so the KC admin console can be iframed."""
    status, raw, _ = _req("GET", "/admin/realms/master", token=tok)
    if status != 200:
        print(f"skip CSP relax (master realm GET {status})")
        return
    realm = json.loads(raw)
    headers = realm.get("browserSecurityHeaders", {}) or {}
    headers["contentSecurityPolicy"] = f"frame-src 'self'; frame-ancestors {FRAME_ANCESTORS};"
    headers["xFrameOptions"] = ""
    realm["browserSecurityHeaders"] = headers
    s, r, _ = _req("PUT", "/admin/realms/master", token=tok, data=realm)
    print(f"relaxed master realm frame-ancestors -> {FRAME_ANCESTORS} ({s})")


def _hardcoded_claim(name, claim, value):
    return {
        "name": name,
        "protocol": "openid-connect",
        "protocolMapper": "oidc-hardcoded-claim-mapper",
        "config": {
            "claim.name": claim,
            "claim.value": value,
            "jsonType.label": "String",
            "id.token.claim": "true",
            "access.token.claim": "true",
            "userinfo.token.claim": "true",
        },
    }


MINIO_SECRET = os.environ.get("MINIO_CONSOLE_SECRET", "minio-console-dev-secret")
MINIO_REDIRECT = os.environ.get("MINIO_REDIRECT", "http://minio.aria.localhost/oauth_callback")
MINIO_POLICY = os.environ.get("MINIO_POLICY", "consoleAdmin")


def main():
    tok = admin_token()
    mappers = [
        _property_mapper("email", "email", "email"),
        _property_mapper("preferred_username", "username", "preferred_username"),
    ]
    # MinIO admin console (karlspace/MinIO-UI fork) — the hardcoded `policy` claim
    # maps the SSO user to a MinIO policy via STS AssumeRoleWithWebIdentity.
    upsert_confidential_client(
        tok,
        "minio-console",
        MINIO_SECRET,
        [MINIO_REDIRECT, "http://minio.aria.localhost/*"],
        mappers + [_hardcoded_claim("minio-policy", "policy", MINIO_POLICY)],
    )
    upsert_confidential_client(
        tok, "litellm-ui", LITELLM_SECRET, [LITELLM_REDIRECT, "http://llm.aria.localhost/*"], mappers
    )
    upsert_confidential_client(
        tok,
        "langfuse",
        LANGFUSE_SECRET,
        [LANGFUSE_REDIRECT, "http://langfuse.aria.localhost/*"],
        mappers,
    )
    normalise_dev_admin_email(tok)
    allow_admin_console_framing(tok)
    print("done.")


if __name__ == "__main__":
    main()
