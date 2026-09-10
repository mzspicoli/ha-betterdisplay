"""Thin async client for the BetterDisplay HTTP integration API.

API reference: https://github.com/waydabber/BetterDisplay/wiki/Integration-features,-CLI
`GET /get?identifiers` returns comma-separated JSON objects (not a valid JSON
document on its own) -- BetterDisplay does not wrap them in an array.
"""
from __future__ import annotations

import json

from aiohttp import ClientSession, ClientTimeout

TIMEOUT = ClientTimeout(total=5)


class BetterDisplayError(Exception):
    """Raised when the BetterDisplay HTTP API returns an error or is unreachable."""


class BetterDisplayClient:
    def __init__(self, session: ClientSession, host: str, port: int, token: str | None = None) -> None:
        self._session = session
        self._base = f"http://{host}:{port}"
        self._token = token

    def _params(self, **kwargs):
        # A value of None means "flag-style" parameter (e.g. `?identifiers`, `?brightness`
        # with no value) -- BetterDisplay treats an empty string the same way.
        params = {k: ("" if v is None else v) for k, v in kwargs.items()}
        if self._token:
            params["token"] = self._token
        return params

    async def _get_text(self, **params) -> str:
        try:
            async with self._session.get(f"{self._base}/get", params=self._params(**params), timeout=TIMEOUT) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise BetterDisplayError(text.strip() or f"HTTP {resp.status}")
                return text.strip()
        except BetterDisplayError:
            raise
        except Exception as err:
            raise BetterDisplayError(str(err)) from err

    async def list_displays(self) -> list[dict]:
        raw = await self._get_text(identifiers=None)
        try:
            return [d for d in json.loads(f"[{raw}]") if d.get("deviceType") == "Display"]
        except json.JSONDecodeError as err:
            raise BetterDisplayError(f"unexpected identifiers payload: {raw!r}") from err

    async def _set(self, **params) -> None:
        try:
            async with self._session.get(f"{self._base}/set", params=self._params(**params), timeout=TIMEOUT) as resp:
                text = await resp.text()
                if resp.status != 200:
                    raise BetterDisplayError(text.strip() or f"HTTP {resp.status}")
        except BetterDisplayError:
            raise
        except Exception as err:
            raise BetterDisplayError(str(err)) from err

    async def get_brightness(self, tag_id: str) -> float:
        raw = await self._get_text(tagID=tag_id, brightness=None)
        return float(raw)

    async def set_brightness(self, tag_id: str, value: float) -> None:
        await self._set(tagID=tag_id, brightness=max(0.0, min(1.0, value)))

    async def get_backlight(self, tag_id: str) -> bool | None:
        """Hardware backlight state, or None if the display has no DDC/smart backlight control."""
        raw = await self._get_text(tagID=tag_id, hardwareBacklight=None)
        if raw not in ("on", "off"):
            return None
        return raw == "on"

    async def set_backlight(self, tag_id: str, value: bool) -> None:
        await self._set(tagID=tag_id, hardwareBacklight="on" if value else "off")

    async def get_volume(self, tag_id: str) -> float | None:
        """DDC volume 0-1, or None if the display has no hardware volume control."""
        raw = await self._get_text(tagID=tag_id, volume=None)
        try:
            return float(raw)
        except ValueError:
            return None

    async def set_volume(self, tag_id: str, value: float) -> None:
        await self._set(tagID=tag_id, volume=max(0.0, min(1.0, value)))

    async def get_mute(self, tag_id: str) -> bool | None:
        raw = await self._get_text(tagID=tag_id, mute=None)
        if raw not in ("on", "off"):
            return None
        return raw == "on"

    async def set_mute(self, tag_id: str, value: bool) -> None:
        await self._set(tagID=tag_id, mute="on" if value else "off")

    async def list_input_sources(self, tag_id: str) -> dict[str, str]:
        """Map of input source name -> id, empty if the display can't switch inputs.

        `inputSourceList` returns lines like `3 - HDMI 1 [DDCController]`.
        """
        raw = await self._get_text(tagID=tag_id, inputSourceList=None)
        sources: dict[str, str] = {}
        for line in raw.splitlines():
            source_id, _, rest = line.partition(" - ")
            name = rest.split(" [")[0].strip()
            if source_id.strip().isdigit() and name:
                sources[name] = source_id.strip()
        return sources

    async def set_input_source(self, tag_id: str, source_id: str) -> None:
        await self._set(tagID=tag_id, changeInputSource=source_id)
