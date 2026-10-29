"""Client for the Schluter DITRA-HEAT cloud API (Sinopé Neviweb backend)."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import aiohttp

from .const import (
    APP_VERSION,
    BASE_URL,
    ERR_BAD_CREDENTIALS,
    ERR_LOCKED,
    ERR_SESSION_EXPIRED,
    INTERFACE,
)

_LOGGER = logging.getLogger(__name__)

TIMEOUT = aiohttp.ClientTimeout(total=30)


class SchluterError(Exception):
    """Generic API error."""


class SchluterAuthError(SchluterError):
    """Credentials were rejected or the account is locked."""


class SchluterApi:
    """Thin async wrapper around the schluterditraheat.com REST API."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._http = session
        self._username = username
        self._password = password
        self._session_id: str | None = None
        self.account_id: int | None = None
        self._login_lock = asyncio.Lock()

    async def login(self) -> None:
        """Open a new API session."""
        payload = {
            "username": self._username,
            "password": self._password,
            "interface": INTERFACE,
            "stayConnected": 1,
        }
        # The web app identifies itself with this header; /connect is only for
        # resuming a session with a refresh token.
        headers = {
            "SWS-Requester": json.dumps(
                {"web-app": {"interface": INTERFACE, "app-version": APP_VERSION}}
            )
        }
        try:
            async with self._http.post(
                f"{BASE_URL}/login", json=payload, headers=headers, timeout=TIMEOUT
            ) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SchluterError(f"Cannot reach Schluter cloud: {err}") from err

        if error := (data or {}).get("error"):
            code = error.get("code")
            _LOGGER.warning("Schluter login rejected: %s", code)
            if code in ERR_BAD_CREDENTIALS or code in ERR_LOCKED:
                raise SchluterAuthError(code)
            raise SchluterError(f"Login failed: {code}")

        self._session_id = data["session"]
        self.account_id = data.get("account", {}).get("id")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        _retry: bool = True,
    ) -> Any:
        if self._session_id is None:
            async with self._login_lock:
                if self._session_id is None:
                    await self.login()

        headers = {"Session-Id": self._session_id or ""}
        try:
            async with self._http.request(
                method,
                f"{BASE_URL}{path}",
                params=params,
                json=json,
                headers=headers,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status in (401, 403) and _retry:
                    self._session_id = None
                    return await self._request(
                        method, path, params=params, json=json, _retry=False
                    )
                resp.raise_for_status()
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError) as err:
            raise SchluterError(f"{method} {path} failed: {err}") from err

        if isinstance(data, dict) and (error := data.get("error")):
            code = error.get("code")
            if code == ERR_SESSION_EXPIRED and _retry:
                _LOGGER.debug("Session expired, logging in again")
                self._session_id = None
                return await self._request(
                    method, path, params=params, json=json, _retry=False
                )
            raise SchluterError(f"{method} {path} returned error {code}")
        return data

    async def get_locations(self) -> list[dict[str, Any]]:
        params = {"account$id": self.account_id} if self.account_id else None
        return await self._request("GET", "/locations", params=params)

    async def get_location(self, location_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/location/{location_id}")

    async def set_location_mode(self, location_id: int, mode: str) -> dict[str, Any]:
        return await self._request(
            "POST", f"/location/{location_id}/mode", json={"mode": mode}
        )

    async def get_devices(self, location_id: int) -> list[dict[str, Any]]:
        return await self._request(
            "GET", "/devices", params={"location$id": location_id}
        )

    async def get_attributes(
        self, device_id: int, attributes: list[str]
    ) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/device/{device_id}/attribute",
            params={"attributes": ",".join(attributes)},
        )

    async def set_attributes(
        self, device_id: int, values: dict[str, Any]
    ) -> dict[str, Any]:
        """Write attributes; the API echoes back the values it accepted."""
        return await self._request(
            "PUT", f"/device/{device_id}/attribute", json=values
        )

    async def get_consumption(self, device_id: int, period: str) -> list[dict]:
        """Energy history. period: hourly | daily | monthly. Values are Wh."""
        data = await self._request(
            "GET", f"/device/{device_id}/consumption/{period}"
        )
        return data.get("history", []) if isinstance(data, dict) else []
