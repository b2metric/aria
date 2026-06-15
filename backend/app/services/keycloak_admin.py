import logging
from typing import Any, Dict, Optional
import httpx
from fastapi import HTTPException, status
from backend.app.core.config import get_settings

logger = logging.getLogger(__name__)

class KeycloakAdminService:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.keycloak_url
        self.realm = self.settings.keycloak_realm
        # Using bootstrap admin credentials for dev. In prod, use a dedicated service account.
        self.admin_user = "admin"
        self.admin_pass = "admin"
        self.admin_realm = "master"
        self._token: Optional[str] = None
        
    async def _get_admin_token(self, client: httpx.AsyncClient) -> str:
        """Get an admin token from the master realm."""
        token_url = f"{self.base_url}/realms/{self.admin_realm}/protocol/openid-connect/token"
        
        response = await client.post(
            token_url,
            data={
                "client_id": "admin-cli",
                "username": self.admin_user,
                "password": self.admin_pass,
                "grant_type": "password"
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"}
        )
        
        if not response.is_success:
            logger.error(f"Failed to get Keycloak admin token: {response.text}")
            raise HTTPException(status_code=500, detail="Failed to authenticate with Identity Provider")
            
        self._token = response.json().get("access_token")
        return self._token
        
    def _auth_header(self, token: str) -> dict:
        return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    async def create_user(self, email: str, display_name: str, password: str = "123456", role: str = "member", workspace_id: str = "default") -> str:
        """Create a user in Keycloak and return their Keycloak ID."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            
            # 1. Create user
            users_url = f"{self.base_url}/admin/realms/{self.realm}/users"
            user_data = {
                "username": email, # Use email as username
                "email": email,
                "firstName": display_name,
                "enabled": True,
                "emailVerified": True,
                "credentials": [{"type": "password", "value": password, "temporary": False}],
                "attributes": {
                    "workspace_id": [workspace_id],
                    "role": [role]
                }
            }
            
            resp = await client.post(users_url, json=user_data, headers=self._auth_header(token))
            
            if resp.status_code == 409:
                raise HTTPException(status_code=409, detail="User with this email already exists in IdP")
            elif not resp.is_success:
                logger.error(f"Keycloak user creation failed: {resp.text}")
                raise HTTPException(status_code=500, detail="Failed to create user in IdP")
            
            # Keycloak returns 201 Created with Location header pointing to the new user
            location = resp.headers.get("Location")
            if not location:
                # If Location isn't returned, we need to look it up
                get_resp = await client.get(f"{users_url}?username={email}", headers=self._auth_header(token))
                users = get_resp.json()
                kc_user_id = users[0]["id"]
            else:
                kc_user_id = location.split("/")[-1]
                
            return kc_user_id

    async def delete_user(self, kc_user_id: str):
        """Delete user from Keycloak."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            url = f"{self.base_url}/admin/realms/{self.realm}/users/{kc_user_id}"
            
            resp = await client.delete(url, headers=self._auth_header(token))
            if not resp.is_success and resp.status_code != 404:
                logger.error(f"Failed to delete user in Keycloak: {resp.text}")
                
    async def update_user(self, kc_user_id: str, updates: dict):
        """Update user attributes in Keycloak."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            url = f"{self.base_url}/admin/realms/{self.realm}/users/{kc_user_id}"
            
            # Fetch current to merge attributes
            get_resp = await client.get(url, headers=self._auth_header(token))
            if not get_resp.is_success:
                raise HTTPException(status_code=404, detail="User not found in IdP")
                
            user = get_resp.json()
            attrs = user.get("attributes", {})
            
            if "role" in updates:
                attrs["role"] = [updates["role"]]
            if "team_id" in updates:
                if updates["team_id"] is None:
                    attrs.pop("team_id", None)
                else:
                    attrs["team_id"] = [str(updates["team_id"])]
                    
            update_payload = {"attributes": attrs}
            
            resp = await client.put(url, json=update_payload, headers=self._auth_header(token))
            if not resp.is_success:
                logger.error(f"Failed to update user in Keycloak: {resp.text}")
                raise HTTPException(status_code=500, detail="Failed to update user in IdP")
                
    async def create_team_group(self, name: str) -> str:
        """Create a group in Keycloak and return its ID."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            url = f"{self.base_url}/admin/realms/{self.realm}/groups"
            
            payload = {"name": name}
            resp = await client.post(url, json=payload, headers=self._auth_header(token))
            
            if resp.status_code == 409:
                raise HTTPException(status_code=409, detail="Team name already exists in IdP")
            elif not resp.is_success:
                logger.error(f"Failed to create group in Keycloak: {resp.text}")
                raise HTTPException(status_code=500, detail="Failed to create team in IdP")
                
            # Get the group ID
            get_resp = await client.get(f"{url}?search={name}", headers=self._auth_header(token))
            groups = get_resp.json()
            # Find exact match
            for g in groups:
                if g["name"] == name:
                    return g["id"]
                    
            raise HTTPException(status_code=500, detail="Team created but ID could not be resolved")
            
    async def delete_team_group(self, kc_group_id: str):
        """Delete a group in Keycloak."""
        async with httpx.AsyncClient() as client:
            token = await self._get_admin_token(client)
            url = f"{self.base_url}/admin/realms/{self.realm}/groups/{kc_group_id}"
            
            resp = await client.delete(url, headers=self._auth_header(token))
            if not resp.is_success and resp.status_code != 404:
                logger.error(f"Failed to delete group in Keycloak: {resp.text}")
