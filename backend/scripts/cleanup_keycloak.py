import asyncio
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.app.services.keycloak_admin import KeycloakAdminService


async def cleanup():
    kc = KeycloakAdminService()
    await kc._ensure_token()

    # Get users
    url = f"{kc.base_url}/admin/realms/{kc.realm}/users"
    headers = {"Authorization": f"Bearer {kc._admin_token}"}

    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 200:
            users = resp.json()
            for user in users:
                if user.get("username") != "admin" and user.get("username") != "tunasonmez":
                    print(f"Deleting user: {user.get('email')} ({user.get('id')})")
                    await client.delete(f"{url}/{user['id']}", headers=headers)
        else:
            print(f"Failed to fetch users: {resp.status_code}")


if __name__ == "__main__":
    asyncio.run(cleanup())
