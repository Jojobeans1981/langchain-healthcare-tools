"""OpenEMR REST API client with OAuth 2.0 authentication.

Connects to the OpenEMR instance for live patient data.
Falls back gracefully when OpenEMR is unavailable (e.g., unit tests, CI).
"""

import logging
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

OPENEMR_BASE = settings.openemr_base_url
API_PATH = "/apis/default/api"
TOKEN_PATH = "/oauth2/default/token"
REGISTRATION_PATH = "/oauth2/default/registration"

OPENEMR_USER = settings.openemr_user
OPENEMR_PASS = settings.openemr_pass


class OpenEMRClient:
    """Authenticated REST API client for OpenEMR."""

    def __init__(self):
        self._token: str | None = None
        self._client_id: str | None = None
        self._client_secret: str | None = None
        self._available: bool | None = None  # None = not checked yet

    def is_available(self) -> bool:
        """Check if OpenEMR is reachable."""
        if not settings.openemr_enabled:
            return False
        if self._available is not None:
            return self._available
        try:
            with httpx.Client(verify=False, timeout=5.0) as client:
                resp = client.get(f"{OPENEMR_BASE}/apis/default/api/facility")
                # 401 means API is up but needs auth — that's fine
                self._available = resp.status_code in (200, 401, 403)
        except Exception:
            self._available = False
            logger.info("OpenEMR not available — tools will use mock data fallback")
        return self._available

    def _register_client(self) -> bool:
        """Register an OAuth2 client with OpenEMR (one-time setup)."""
        try:
            with httpx.Client(verify=False, timeout=10.0) as client:
                resp = client.post(
                    f"{OPENEMR_BASE}{REGISTRATION_PATH}",
                    json={
                        "application_type": "private",
                        "redirect_uris": ["https://localhost"],
                        "client_name": "AgentForge Healthcare AI",
                        "token_endpoint_auth_method": "client_secret_post",
                        "contacts": ["admin@agentforge.local"],
                        "scope": "openid api:oemr api:fhir api:port",
                    },
                )
                if resp.status_code == 201:
                    data = resp.json()
                    self._client_id = data.get("client_id")
                    self._client_secret = data.get("client_secret")
                    logger.info("Registered OAuth2 client: %s", self._client_id)
                    return True
                else:
                    logger.warning("OAuth2 registration failed: %s %s", resp.status_code, resp.text[:200])
                    return False
        except Exception as e:
            logger.warning("OAuth2 registration error: %s", e)
            return False

    def _authenticate(self) -> bool:
        """Get an OAuth2 access token using password grant."""
        if not self._client_id:
            if not self._register_client():
                return False
        try:
            with httpx.Client(verify=False, timeout=10.0) as client:
                resp = client.post(
                    f"{OPENEMR_BASE}{TOKEN_PATH}",
                    data={
                        "grant_type": "password",
                        "username": OPENEMR_USER,
                        "password": OPENEMR_PASS,
                        "client_id": self._client_id,
                        "client_secret": self._client_secret,
                        "scope": "openid api:oemr api:fhir",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    self._token = data.get("access_token")
                    logger.info("OAuth2 authentication successful")
                    return True
                else:
                    logger.warning("OAuth2 auth failed: %s %s", resp.status_code, resp.text[:200])
                    return False
        except Exception as e:
            logger.warning("OAuth2 auth error: %s", e)
            return False

    def _get_headers(self) -> dict:
        """Get authenticated request headers."""
        if not self._token:
            self._authenticate()
        return {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}

    def _api_get(self, endpoint: str, params: dict = None) -> dict | list | None:
        """Make an authenticated GET request to the OpenEMR API."""
        if not self.is_available():
            return None
        try:
            with httpx.Client(verify=False, timeout=10.0) as client:
                resp = client.get(
                    f"{OPENEMR_BASE}{API_PATH}{endpoint}",
                    headers=self._get_headers(),
                    params=params,
                )
                if resp.status_code == 401:
                    # Token expired, re-authenticate and retry
                    self._token = None
                    resp = client.get(
                        f"{OPENEMR_BASE}{API_PATH}{endpoint}",
                        headers=self._get_headers(),
                        params=params,
                    )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning("OpenEMR API %s returned %s", endpoint, resp.status_code)
                return None
        except Exception as e:
            logger.warning("OpenEMR API error on %s: %s", endpoint, e)
            return None

    # =================================================================
    # Domain-specific query methods
    # =================================================================

    def get_practitioners(self, specialty: str = None) -> list[dict] | None:
        """Get practitioners/providers, optionally filtered by specialty."""
        data = self._api_get("/practitioner")
        if data is None:
            return None
        practitioners = data if isinstance(data, list) else data.get("data", [])
        if specialty:
            specialty_lower = specialty.lower()
            practitioners = [
                p for p in practitioners
                if specialty_lower in (p.get("specialty", "") or "").lower()
                or specialty_lower in (p.get("physician_type", "") or "").lower()
                or specialty_lower in (p.get("title", "") or "").lower()
            ]
        return practitioners

    def get_appointments(self, date: str = None, provider_id: int = None) -> list[dict] | None:
        """Get appointments, optionally filtered by date or provider."""
        params = {}
        if date:
            params["pc_eventDate"] = date
        if provider_id:
            params["pc_aid"] = str(provider_id)
        data = self._api_get("/appointment", params=params)
        if data is None:
            return None
        return data if isinstance(data, list) else data.get("data", [])

    def get_patient_insurance(self, patient_id: int) -> list[dict] | None:
        """Get insurance data for a patient."""
        data = self._api_get(f"/patient/{patient_id}/insurance")
        if data is None:
            return None
        return data if isinstance(data, list) else data.get("data", [])

    def get_patients(self, name: str = None) -> list[dict] | None:
        """Get patients, optionally filtered by name."""
        params = {}
        if name:
            params["fname"] = name
        data = self._api_get("/patient", params=params)
        if data is None:
            return None
        return data if isinstance(data, list) else data.get("data", [])

    def get_patient_medications(self, patient_id: int) -> list[dict] | None:
        """Get active medications/prescriptions for a patient."""
        data = self._api_get(f"/patient/{patient_id}/medication")
        if data is None:
            return None
        return data if isinstance(data, list) else data.get("data", [])


# Singleton instance
openemr = OpenEMRClient()
