import logging
from typing import Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OpenEMRClient:
    """Async client for OpenEMR REST and FHIR APIs with OAuth2 authentication."""

    def __init__(self, base_url: str | None = None):
        self.base_url = (base_url or settings.openemr_base_url).rstrip("/")
        self._access_token: str | None = None
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=30.0, verify=False)
        return self._client

    async def authenticate(self) -> bool:
        """Authenticate with OpenEMR OAuth2 and obtain access token."""
        try:
            client = await self._get_client()

            # Register client if no client_id
            if not settings.openemr_client_id:
                reg_resp = await client.post(
                    f"{self.base_url}/oauth2/default/registration",
                    json={
                        "application_type": "private",
                        "redirect_uris": ["http://localhost:8000/callback"],
                        "client_name": "AgentForge Healthcare Agent",
                        "scope": "openid api:oemr api:fhir",
                    },
                )
                if reg_resp.status_code == 200:
                    reg_data = reg_resp.json()
                    settings.openemr_client_id = reg_data.get("client_id", "")
                    settings.openemr_client_secret = reg_data.get("client_secret", "")
                    logger.info("Registered OAuth2 client with OpenEMR")

            # Password grant for server-to-server (development)
            token_resp = await client.post(
                f"{self.base_url}/oauth2/default/token",
                data={
                    "grant_type": "password",
                    "client_id": settings.openemr_client_id,
                    "client_secret": settings.openemr_client_secret,
                    "username": "admin",
                    "password": "pass",
                    "scope": "openid api:oemr api:fhir",
                },
            )
            if token_resp.status_code == 200:
                self._access_token = token_resp.json().get("access_token")
                logger.info("Successfully authenticated with OpenEMR")
                return True

            logger.warning("OAuth2 token request failed: %s", token_resp.status_code)
            return False
        except httpx.ConnectError:
            logger.warning("Cannot connect to OpenEMR at %s", self.base_url)
            return False

    def _auth_headers(self) -> dict[str, str]:
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}

    async def _api_get(self, path: str, params: dict | None = None) -> dict[str, Any] | None:
        """Make an authenticated GET request to the OpenEMR API."""
        try:
            client = await self._get_client()
            resp = await client.get(
                f"{self.base_url}{path}",
                headers=self._auth_headers(),
                params=params,
            )
            if resp.status_code == 401:
                # Try re-auth once
                if await self.authenticate():
                    resp = await client.get(
                        f"{self.base_url}{path}",
                        headers=self._auth_headers(),
                        params=params,
                    )
            if resp.status_code == 200:
                return resp.json()
            logger.warning("API request to %s failed: %s", path, resp.status_code)
            return None
        except httpx.ConnectError:
            logger.warning("Cannot connect to OpenEMR for %s", path)
            return None

    async def search_practitioners(self, specialty: str = "", name: str = "") -> list[dict]:
        """Search for practitioners by specialty or name."""
        params = {}
        if name:
            params["name"] = name
        if specialty:
            params["specialty"] = specialty

        data = await self._api_get("/apis/default/fhir/Practitioner", params or None)
        if data and "entry" in data:
            results = []
            for entry in data["entry"]:
                resource = entry.get("resource", {})
                practitioner_name = ""
                if resource.get("name"):
                    n = resource["name"][0]
                    practitioner_name = f"{n.get('given', [''])[0]} {n.get('family', '')}".strip()
                results.append({
                    "id": resource.get("id", ""),
                    "name": practitioner_name,
                    "specialty": specialty,
                    "active": resource.get("active", True),
                })
            return results
        return []

    async def search_patients(self, name: str = "") -> list[dict]:
        """Search patients by name."""
        params = {"name": name} if name else None
        data = await self._api_get("/apis/default/fhir/Patient", params)
        if data and "entry" in data:
            results = []
            for entry in data["entry"]:
                resource = entry.get("resource", {})
                patient_name = ""
                if resource.get("name"):
                    n = resource["name"][0]
                    patient_name = f"{n.get('given', [''])[0]} {n.get('family', '')}".strip()
                results.append({
                    "id": resource.get("id", ""),
                    "name": patient_name,
                    "birthDate": resource.get("birthDate", ""),
                    "gender": resource.get("gender", ""),
                })
            return results
        return []

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None
