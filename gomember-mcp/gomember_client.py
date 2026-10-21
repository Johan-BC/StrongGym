"""
HTTP-klient til goMember/MemberLink API'et.

Denne fil har med vilje kun ÉN metode der rammer nettet: get(). Der er ingen
post/put/patch/delete-metoder defineret noget sted i klassen - det er den
egentlige garanti for at integrationen er read-only, uafhængigt af hvad
det fiktive medlems kontorettigheder i goMember faktisk tillader.

Autentificering sker via OAuth2 "Resource Owner Password Credentials" mod
/auth/token, sådan som swagger-filens securityDefinitions angiver. Token
caches i hukommelsen og forny's automatisk når det udløber eller et kald
fejler med 401.
"""
import os
import time
import threading
from typing import Optional

import requests


class GoMemberAuthError(RuntimeError):
    pass


class GoMemberClient:
    def __init__(
        self,
        base_url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        client_id: Optional[str] = None,
    ):
        self.base_url = (base_url or os.environ.get("GOMEMBER_BASE_URL") or "https://www.stronggym.dk").rstrip("/")
        self.username = username or os.environ.get("GOMEMBER_USERNAME")
        self.password = password or os.environ.get("GOMEMBER_PASSWORD")
        # client_id er ikke dokumenteret i swagger-filen for /auth/token - nogle
        # MemberLink/goMember-installationer kræver det, andre ikke. Sæt
        # GOMEMBER_CLIENT_ID hvis test-kaldet i README fejler med "invalid_client".
        self.client_id = client_id or os.environ.get("GOMEMBER_CLIENT_ID")

        if not self.username or not self.password:
            raise GoMemberAuthError(
                "GOMEMBER_USERNAME og GOMEMBER_PASSWORD skal være sat som miljøvariabler "
                "(login for det fiktive read-only medlem i goMember)."
            )

        self._session = requests.Session()
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._lock = threading.Lock()

    def _fetch_token(self) -> None:
        data = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
        }
        if self.client_id:
            data["client_id"] = self.client_id

        resp = self._session.post(f"{self.base_url}/auth/token", data=data, timeout=30)
        if resp.status_code != 200:
            raise GoMemberAuthError(
                f"Kunne ikke hente token fra /auth/token (status {resp.status_code}): {resp.text[:500]}"
            )
        payload = resp.json()
        token = payload.get("access_token")
        if not token:
            raise GoMemberAuthError(f"Svar fra /auth/token indeholdt ikke access_token: {payload}")

        expires_in = float(payload.get("expires_in", 3600))
        self._token = token
        # Forny 60 sekunder før faktisk udløb, for sikkerheds skyld
        self._token_expires_at = time.time() + max(expires_in - 60, 30)

    def _ensure_token(self) -> None:
        with self._lock:
            if self._token is None or time.time() >= self._token_expires_at:
                self._fetch_token()

    def get(self, path_template: str, path_params: Optional[dict] = None, query_params: Optional[dict] = None) -> dict:
        """Udfør et GET-kald mod goMember API'et. Ingen andre HTTP-metoder er implementeret."""
        self._ensure_token()
        path = path_template.format(**(path_params or {}))
        url = f"{self.base_url}{path}"

        headers = {"Authorization": f"Bearer {self._token}"}
        resp = self._session.get(url, params=query_params or {}, headers=headers, timeout=30)

        if resp.status_code == 401:
            # Token kan være udløbet server-side før vores egen timer nåede det - forny én gang og prøv igen
            with self._lock:
                self._token = None
            self._ensure_token()
            headers = {"Authorization": f"Bearer {self._token}"}
            resp = self._session.get(url, params=query_params or {}, headers=headers, timeout=30)

        resp.raise_for_status()
        if not resp.content:
            return {}
        try:
            return resp.json()
        except ValueError:
            return {"raw_text": resp.text}
