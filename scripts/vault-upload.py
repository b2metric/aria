#!/usr/bin/env python3
"""vault-upload.py — push offline-extracted metadata JSON into the ARIA vault.

Run this on a machine with network reach to the ARIA API (NOT the air-gapped box).
It takes the JSON produced by ``scripts/vault-extract-standalone.py``, authenticates,
and POSTs it to ``/api/workspaces/vault/import-metadata`` — which CREATES the vault
tables from the JSON columns (when missing) and then enriches them + injects enum
blocks + re-indexes embeddings. The target workspace is whatever the token belongs
to (derived from the JWT, not a query param), so use an ADMIN token for that tenant.

Stdlib only (urllib) — no third-party packages required.

Auth (pick one):
  A) Paste a bearer token:   --token <JWT>           (or env ARIA_TOKEN)
  B) Keycloak password grant: --username --password   (+ --kc-issuer / --client)

Usage:
    # A) with a token
    python scripts/vault-upload.py --json db-metadata-stc.json \
        --api-base http://api.aria.localhost --token "$ARIA_TOKEN"

    # B) with Keycloak (local dev realm shown; override for staging/prod)
    python scripts/vault-upload.py --json db-metadata-stc.json \
        --api-base http://api.aria.localhost \
        --kc-issuer http://auth.aria.localhost/auth/realms/aria \
        --client aria-web --username admin --password '***'

Exit codes: 0 = imported ok; 1 = config/auth error; 2 = API returned an error.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("vault-upload")

DEFAULT_API_BASE = os.environ.get("ARIA_API_BASE", "http://api.aria.localhost")
DEFAULT_KC_ISSUER = os.environ.get(
    "ARIA_KC_ISSUER", "http://auth.aria.localhost/auth/realms/aria"
)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Upload extracted metadata JSON into the ARIA vault.")
    p.add_argument("--json", required=True, help="Path to the metadata JSON (from the extractor)")
    p.add_argument("--api-base", default=DEFAULT_API_BASE, help="ARIA API base URL")
    p.add_argument("--token", default=os.environ.get("ARIA_TOKEN"),
                   help="Bearer JWT (admin). If absent, a Keycloak password grant is attempted.")
    p.add_argument("--kc-issuer", default=DEFAULT_KC_ISSUER,
                   help="Keycloak realm issuer (…/realms/<realm>) for the password grant")
    p.add_argument("--client", default=os.environ.get("ARIA_KC_CLIENT", "aria-web"),
                   help="Keycloak client_id for the password grant")
    p.add_argument("--client-secret", default=os.environ.get("ARIA_KC_CLIENT_SECRET"),
                   help="Keycloak client secret (only for confidential clients)")
    p.add_argument("--username", help="Keycloak username (password grant)")
    p.add_argument("--password", help="Keycloak password (password grant)")
    p.add_argument("--timeout", type=int, default=300, help="HTTP timeout in seconds")
    return p.parse_args()


def _kc_password_grant(args: argparse.Namespace) -> str:
    """Exchange username/password for an access token via Keycloak."""
    if not (args.username and args.password):
        raise SystemExit(
            "No --token given and no --username/--password for a Keycloak grant. See --help."
        )
    token_url = f"{args.kc_issuer.rstrip('/')}/protocol/openid-connect/token"
    form = {
        "grant_type": "password",
        "client_id": args.client,
        "username": args.username,
        "password": args.password,
        "scope": "openid",
    }
    if args.client_secret:
        form["client_secret"] = args.client_secret
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(
        token_url, data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit(f"Keycloak token request failed ({e.code}): {e.read().decode()[:300]}") from e
    token = payload.get("access_token")
    if not token:
        raise SystemExit(f"Keycloak returned no access_token: {payload}")
    logger.info("Authenticated as %s via %s", args.username, args.kc_issuer)
    return token


def _post_multipart(url: str, token: str, json_path: str, timeout: int) -> tuple[int, str]:
    """POST the JSON file as multipart/form-data field ``file`` and return (status, body)."""
    with open(json_path, "rb") as f:
        content = f.read()
    filename = os.path.basename(json_path)
    boundary = "----aria-vault-upload-" + uuid.uuid4().hex
    body = b"".join([
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
        b"Content-Type: application/json\r\n\r\n",
        content,
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    req = urllib.request.Request(
        url, data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main() -> int:
    args = _parse_args()
    if not os.path.isfile(args.json):
        logger.error("JSON file not found: %s", args.json)
        return 1

    token = args.token or _kc_password_grant(args)

    url = f"{args.api_base.rstrip('/')}/api/workspaces/vault/import-metadata"
    logger.info("Uploading %s -> %s", args.json, url)
    status, body = _post_multipart(url, token, args.json, args.timeout)

    try:
        parsed = json.loads(body)
        pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
    except json.JSONDecodeError:
        parsed, pretty = None, body

    if status == 200:
        logger.info("Import OK (HTTP 200)")
        if isinstance(parsed, dict):
            logger.info(
                "tables_created=%s  enum_blocks_updated=%s  embeddings=%s",
                parsed.get("tables_created"),
                parsed.get("enum_blocks_updated"),
                parsed.get("embeddings"),
            )
        print(pretty)
        return 0

    logger.error("Import failed (HTTP %s)", status)
    print(pretty)
    return 2


if __name__ == "__main__":
    sys.exit(main())
